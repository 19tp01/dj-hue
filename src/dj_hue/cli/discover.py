"""Discover Hue lights and show their current order.

Use this to see available lights and generate config for custom ordering.
"""

import os
import yaml
import requests
import urllib3

# Suppress SSL warnings for Hue bridge self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_config():
    """Load Hue config from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config not found: {config_path}\n" "Run 'dj-hue --setup' first."
        )

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config.get("hue", {})


def get_entertainment_config(bridge_ip: str, username: str, area_id: str) -> dict | None:
    """Get entertainment configuration with channel details."""
    url = f"https://{bridge_ip}/clip/v2/resource/entertainment_configuration/{area_id}"
    headers = {"hue-application-key": username}

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        data = response.json()
        if data.get("data"):
            return data["data"][0]
        return None
    except Exception as e:
        print(f"Failed to get entertainment config: {e}")
        return None


def get_all_lights(bridge_ip: str, username: str) -> dict[str, dict]:
    """Get all lights from bridge, keyed by ID."""
    url = f"https://{bridge_ip}/clip/v2/resource/light"
    headers = {"hue-application-key": username}

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        data = response.json()

        lights = {}
        for item in data.get("data", []):
            lights[item["id"]] = {
                "id": item["id"],
                "name": item.get("metadata", {}).get("name", "Unknown"),
                "type": item.get("type", "unknown"),
                "archetype": item.get("metadata", {}).get("archetype", "unknown"),
            }
        return lights
    except Exception as e:
        print(f"Failed to get lights: {e}")
        return {}


def main():
    """Discover and display light configuration."""
    print("=" * 60)
    print("  DJ-Hue Light Discovery")
    print("=" * 60)
    print()

    # Load config
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    bridge_ip = config.get("bridge_ip")
    username = config.get("username")
    area_id = config.get("entertainment_area_id")

    if not all([bridge_ip, username, area_id]):
        print("Error: Missing hue config (bridge_ip, username, or entertainment_area_id)")
        return 1

    print(f"Bridge: {bridge_ip}")
    print(f"Entertainment Area: {area_id}")
    print()

    # Get all lights for name lookup
    all_lights = get_all_lights(bridge_ip, username)
    if not all_lights:
        print("Error: Could not fetch lights from bridge")
        return 1

    # Get entertainment area config
    ent_config = get_entertainment_config(bridge_ip, username, area_id)
    if not ent_config:
        print("Error: Could not fetch entertainment configuration")
        return 1

    print(f"Entertainment Area: {ent_config.get('name', 'Unknown')}")
    print()

    # Build channel list with light info
    channels = []
    for i, channel in enumerate(ent_config.get("channels", [])):
        channel_info = {
            "index": i,
            "channel_id": channel.get("channel_id"),
            "position": channel.get("position", {}),
            "members": [],
        }

        for member in channel.get("members", []):
            service = member.get("service", {})
            rid = service.get("rid", "")
            light_info = all_lights.get(rid, {})

            channel_info["members"].append({
                "rid": rid,
                "name": light_info.get("name", "Unknown"),
                "archetype": light_info.get("archetype", "unknown"),
            })

        channels.append(channel_info)

    # Display current order
    print("CURRENT CHANNEL ORDER (from Entertainment Area):")
    print("-" * 60)

    for ch in channels:
        idx = ch["index"]
        pos = ch["position"]
        pos_str = f"x={pos.get('x', 0):.2f}, y={pos.get('y', 0):.2f}, z={pos.get('z', 0):.2f}"

        for member in ch["members"]:
            name = member["name"]
            rid = member["rid"]
            arch = member["archetype"]
            print(f"  [{idx:2d}] {name:<25} ({arch})")
            print(f"       ID: {rid}")
            print(f"       Position: {pos_str}")
        print()

    # Check for existing light_order config
    existing_order = config.get("light_order", [])
    if existing_order:
        print()
        print("CONFIGURED LIGHT ORDER (from config.yaml):")
        print("-" * 60)
        for i, name in enumerate(existing_order):
            print(f"  [{i:2d}] {name}")
        print()

    # Generate sample config
    print()
    print("SAMPLE CONFIG (add to config.yaml under 'hue:'):")
    print("-" * 60)
    print("  # Custom light order - pattern index 0 = first light listed")
    print("  light_order:")

    # Use light names for readability
    seen_names = set()
    for ch in channels:
        for member in ch["members"]:
            name = member["name"]
            rid = member["rid"]
            # If name is unique, use it; otherwise use ID
            if name not in seen_names:
                print(f'    - "{name}"')
                seen_names.add(name)
            else:
                print(f'    - "{rid}"  # {name} (duplicate name)')

    print()
    print("To reorder: rearrange the list above in your desired order.")
    print("Pattern index 0 will be the first light in the list.")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
