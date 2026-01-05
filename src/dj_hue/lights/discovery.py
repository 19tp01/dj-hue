"""Hue bridge discovery and authentication."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import time
import warnings

# Suppress SSL warnings for Hue bridge (uses self-signed cert)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class HueCredentials:
    """Stored Hue bridge credentials."""
    bridge_ip: str
    username: str
    clientkey: str
    bridge_id: str = ""


@dataclass
class EntertainmentArea:
    """Entertainment area configuration."""
    id: str
    name: str
    light_ids: list[int]


class HueSetup:
    """Handle Hue bridge discovery and authentication."""

    def __init__(self, credentials_file: Path = Path("hue_credentials.json")):
        self.credentials_file = credentials_file
        self._bridge = None

    def discover_bridges(self) -> list[dict]:
        """
        Discover Hue bridges on the network.

        Returns list of dicts with 'id', 'ip', 'name' keys.
        """
        bridges_found = []

        # Try mDNS discovery via zeroconf
        try:
            from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
            import socket

            class HueListener(ServiceListener):
                def __init__(self):
                    self.bridges = []

                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        ip = socket.inet_ntoa(info.addresses[0]) if info.addresses else None
                        if ip:
                            bridge_id = name.split(".")[0].replace("Philips Hue - ", "")
                            self.bridges.append({
                                "id": bridge_id,
                                "ip": ip,
                                "name": f"Philips Hue ({ip})",
                            })

                def remove_service(self, zc, type_, name):
                    pass

                def update_service(self, zc, type_, name):
                    pass

            zc = Zeroconf()
            listener = HueListener()
            browser = ServiceBrowser(zc, "_hue._tcp.local.", listener)

            # Wait a bit for discovery
            import time
            time.sleep(3)

            bridges_found = listener.bridges
            zc.close()

        except Exception as e:
            print(f"mDNS discovery failed: {e}")

        # Fallback: try meethue.com discovery API
        if not bridges_found:
            try:
                import requests
                response = requests.get(
                    "https://discovery.meethue.com/",
                    timeout=5
                )
                if response.status_code == 200:
                    for bridge in response.json():
                        bridges_found.append({
                            "id": bridge.get("id", "unknown"),
                            "ip": bridge.get("internalipaddress", ""),
                            "name": f"Philips Hue ({bridge.get('internalipaddress', '')})",
                        })
            except Exception as e:
                print(f"Cloud discovery failed: {e}")

        return bridges_found

    def authenticate(
        self,
        bridge_ip: str,
        app_name: str = "dj_hue",
        timeout: int = 30,
    ) -> HueCredentials:
        """
        Authenticate with a Hue bridge.

        User must press the bridge button within timeout seconds.

        Args:
            bridge_ip: IP address of the bridge
            app_name: Application name for registration
            timeout: Seconds to wait for button press

        Returns:
            HueCredentials with username and clientkey

        Raises:
            TimeoutError: If button not pressed in time
            Exception: If authentication fails
        """
        import requests

        url = f"https://{bridge_ip}/api"
        payload = {
            "devicetype": f"{app_name}#device",
            "generateclientkey": True,
        }

        print(f"Please press the button on your Hue bridge...")
        print(f"Waiting up to {timeout} seconds...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Hue bridge uses self-signed cert
                response = requests.post(url, json=payload, verify=False, timeout=5)
                result = response.json()

                if isinstance(result, list) and len(result) > 0:
                    if "success" in result[0]:
                        success = result[0]["success"]
                        return HueCredentials(
                            bridge_ip=bridge_ip,
                            username=success["username"],
                            clientkey=success["clientkey"],
                        )
                    elif "error" in result[0]:
                        error = result[0]["error"]
                        if error.get("type") == 101:
                            # Link button not pressed yet
                            time.sleep(1)
                            continue
                        else:
                            raise Exception(f"Auth error: {error.get('description')}")

            except requests.exceptions.RequestException as e:
                print(f"Connection error: {e}")
                time.sleep(1)

        raise TimeoutError("Bridge button was not pressed in time")

    def load_credentials(self) -> Optional[HueCredentials]:
        """Load saved credentials from file."""
        if not self.credentials_file.exists():
            return None

        try:
            data = json.loads(self.credentials_file.read_text())
            return HueCredentials(
                bridge_ip=data["bridge_ip"],
                username=data["username"],
                clientkey=data["clientkey"],
                bridge_id=data.get("bridge_id", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to load credentials: {e}")
            return None

    def save_credentials(self, creds: HueCredentials) -> None:
        """Save credentials to file."""
        data = {
            "bridge_ip": creds.bridge_ip,
            "username": creds.username,
            "clientkey": creds.clientkey,
            "bridge_id": creds.bridge_id,
        }
        self.credentials_file.write_text(json.dumps(data, indent=2))
        print(f"Credentials saved to {self.credentials_file}")

    def get_entertainment_areas(
        self,
        bridge_ip: str,
        username: str,
    ) -> list[EntertainmentArea]:
        """
        Get available entertainment areas from bridge.

        Args:
            bridge_ip: Bridge IP address
            username: Authenticated username

        Returns:
            List of EntertainmentArea objects
        """
        import requests

        url = f"https://{bridge_ip}/clip/v2/resource/entertainment_configuration"
        headers = {"hue-application-key": username}

        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            data = response.json()

            areas = []
            for item in data.get("data", []):
                light_ids = []
                for channel in item.get("channels", []):
                    for member in channel.get("members", []):
                        service = member.get("service", {})
                        if service.get("rtype") == "light":
                            # Extract light ID from rid
                            rid = service.get("rid", "")
                            light_ids.append(rid)

                areas.append(EntertainmentArea(
                    id=item["id"],
                    name=item.get("name", "Unknown"),
                    light_ids=light_ids,
                ))

            return areas

        except Exception as e:
            print(f"Failed to get entertainment areas: {e}")
            return []

    def get_lights(
        self,
        bridge_ip: str,
        username: str,
    ) -> list[dict]:
        """
        Get all lights from bridge.

        Returns list of dicts with 'id', 'name', 'type' keys.
        """
        import requests

        url = f"https://{bridge_ip}/clip/v2/resource/light"
        headers = {"hue-application-key": username}

        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            data = response.json()

            return [
                {
                    "id": item["id"],
                    "name": item.get("metadata", {}).get("name", "Unknown"),
                    "type": item.get("type", "unknown"),
                }
                for item in data.get("data", [])
            ]

        except Exception as e:
            print(f"Failed to get lights: {e}")
            return []


def run_setup_wizard(credentials_file: Path = Path("hue_credentials.json")) -> Optional[HueCredentials]:
    """
    Interactive setup wizard for Hue bridge.

    Returns credentials if setup successful.
    """
    setup = HueSetup(credentials_file)

    # Check for existing credentials
    existing = setup.load_credentials()
    if existing:
        print(f"Found existing credentials for bridge at {existing.bridge_ip}")
        response = input("Use existing credentials? [Y/n]: ").strip().lower()
        if response != "n":
            return existing

    # Discover bridges
    print("\nSearching for Hue bridges...")
    bridges = setup.discover_bridges()

    if not bridges:
        print("No bridges found. Enter IP manually:")
        bridge_ip = input("Bridge IP: ").strip()
        if not bridge_ip:
            print("No IP provided, aborting.")
            return None
    elif len(bridges) == 1:
        bridge_ip = bridges[0]["ip"]
        print(f"Found bridge: {bridges[0]['name']} at {bridge_ip}")
    else:
        print("\nFound multiple bridges:")
        for i, bridge in enumerate(bridges):
            print(f"  {i + 1}. {bridge['name']} ({bridge['ip']})")
        choice = input(f"Select bridge [1-{len(bridges)}]: ").strip()
        try:
            idx = int(choice) - 1
            bridge_ip = bridges[idx]["ip"]
        except (ValueError, IndexError):
            print("Invalid selection, using first bridge")
            bridge_ip = bridges[0]["ip"]

    # Authenticate
    try:
        creds = setup.authenticate(bridge_ip)
        setup.save_credentials(creds)

        # Show entertainment areas
        print("\nAvailable entertainment areas:")
        areas = setup.get_entertainment_areas(bridge_ip, creds.username)
        if areas:
            for area in areas:
                print(f"  - {area.name} (ID: {area.id})")
                print(f"    Lights: {len(area.light_ids)}")
        else:
            print("  No entertainment areas found.")
            print("  Create one in the Hue app: Settings -> Entertainment areas")

        return creds

    except TimeoutError:
        print("\nSetup timed out. Please try again and press the bridge button.")
        return None
    except Exception as e:
        print(f"\nSetup failed: {e}")
        return None
