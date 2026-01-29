"""Touch server for iPad control UI.

Serves the React frontend and proxies WebSocket to DJ-Hue control server.
Run as: uv run dj-hue-touch
"""

import argparse
import asyncio
import socket
from pathlib import Path

from aiohttp import web, WSMsgType, ClientSession


def get_network_addresses() -> list[str]:
    """Get all network addresses that can be reached from other devices."""
    import subprocess
    import re

    addresses = []

    try:
        # Use ifconfig to get all addresses (works on macOS/Linux)
        result = subprocess.run(['ifconfig'], capture_output=True, text=True)
        output = result.stdout

        # Find IPv6 unique local addresses (fd/fc prefix) - used for USB connections
        # Match inet6 followed by address, handling various ifconfig formats
        ipv6_pattern = r'inet6\s+([fF][cCdD][0-9a-fA-F:]+)'
        for match in re.finditer(ipv6_pattern, output):
            addr = match.group(1)
            # Remove scope ID if present (e.g., %en0)
            if '%' in addr:
                addr = addr.split('%')[0]
            # Remove prefix length if captured (e.g., /64)
            if '/' in addr:
                addr = addr.split('/')[0]
            addresses.append(f"[{addr}]")

        # Find IPv4 addresses
        ipv4_pattern = r'inet\s+(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(ipv4_pattern, output):
            addr = match.group(1)
            # Skip localhost
            if not addr.startswith('127.'):
                addresses.append(addr)

    except Exception as e:
        print(f"[TOUCH] Warning: ifconfig failed: {e}")
        # Fallback: try socket method for IPv4
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            addresses.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass

    # Debug: if no IPv6 found, mention it
    has_ipv6 = any(addr.startswith('[') for addr in addresses)
    if not has_ipv6:
        print("[TOUCH] Note: No IPv6 addresses found (iPad USB not connected?)")

    return addresses

# Default ports
TOUCH_SERVER_PORT = 8080
DJHUE_CONTROL_PORT = 9876


class TouchServer:
    """Server that proxies WebSocket to DJ-Hue and serves static files."""

    def __init__(
        self,
        host: str = "::",  # Listen on all interfaces (IPv4 and IPv6)
        port: int = TOUCH_SERVER_PORT,
        djhue_host: str = "localhost",
        djhue_port: int = DJHUE_CONTROL_PORT,
        static_dir: Path | None = None,
    ):
        self.host = host
        self.port = port
        self.djhue_url = f"ws://{djhue_host}:{djhue_port}/ws"

        # Find static files directory
        if static_dir is None:
            # Default: look for built React app in touch-ui/dist or static/
            module_dir = Path(__file__).parent
            candidates = [
                module_dir / "static",  # Production: built files in package
                module_dir.parent.parent.parent.parent / "touch-ui" / "dist",  # Dev: Vite build
            ]
            for candidate in candidates:
                if candidate.exists() and (candidate / "index.html").exists():
                    static_dir = candidate
                    break

        self.static_dir = static_dir

        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Proxy WebSocket connection to DJ-Hue control server."""
        client_ws = web.WebSocketResponse()
        await client_ws.prepare(request)

        print(f"[TOUCH] Client connected, proxying to {self.djhue_url}")

        async with ClientSession() as session:
            try:
                async with session.ws_connect(self.djhue_url) as djhue_ws:
                    # Bidirectional proxy
                    async def client_to_djhue():
                        async for msg in client_ws:
                            if msg.type == WSMsgType.TEXT:
                                await djhue_ws.send_str(msg.data)
                            elif msg.type == WSMsgType.CLOSE:
                                await djhue_ws.close()
                                break
                            elif msg.type == WSMsgType.ERROR:
                                break

                    async def djhue_to_client():
                        async for msg in djhue_ws:
                            if msg.type == WSMsgType.TEXT:
                                await client_ws.send_str(msg.data)
                            elif msg.type == WSMsgType.CLOSE:
                                await client_ws.close()
                                break
                            elif msg.type == WSMsgType.ERROR:
                                break

                    # Run both directions concurrently
                    await asyncio.gather(
                        client_to_djhue(),
                        djhue_to_client(),
                        return_exceptions=True,
                    )

            except Exception as e:
                print(f"[TOUCH] Connection error: {e}")
                await client_ws.send_json({
                    "type": "error",
                    "message": f"Cannot connect to DJ-Hue: {e}. Make sure DJ-Hue is running.",
                })

        print("[TOUCH] Client disconnected")
        return client_ws

    async def _handle_index(self, request: web.Request) -> web.Response:
        """Serve index.html for SPA routes."""
        if self.static_dir is None:
            return web.Response(
                text="Touch UI not built. Run: cd touch-ui && npm run build",
                status=503,
            )
        index_path = self.static_dir / "index.html"
        if not index_path.exists():
            return web.Response(
                text="index.html not found. Run: cd touch-ui && npm run build",
                status=503,
            )
        return web.FileResponse(index_path)

    async def start(self) -> None:
        """Start the touch server."""
        self._app = web.Application()

        # WebSocket endpoint
        self._app.router.add_get("/ws", self._handle_websocket)

        # Static files (if available)
        if self.static_dir and self.static_dir.exists():
            # Serve static assets
            self._app.router.add_static("/assets", self.static_dir / "assets")
            # Serve index.html for all other routes (SPA)
            self._app.router.add_get("/", self._handle_index)
            self._app.router.add_get("/{tail:.*}", self._handle_index)
            print(f"[TOUCH] Serving static files from {self.static_dir}")
        else:
            # No static files - just proxy mode
            self._app.router.add_get("/", self._handle_index)
            print("[TOUCH] No static files found - WebSocket proxy only")

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()

        print(f"[TOUCH] Server running on http://{self.host}:{self.port}")
        print(f"[TOUCH] Proxying WebSocket to {self.djhue_url}")

    async def stop(self) -> None:
        """Stop the server."""
        if self._runner:
            await self._runner.cleanup()


async def run_server(args: argparse.Namespace) -> None:
    """Run the touch server."""
    server = TouchServer(
        host=args.host,
        port=args.port,
        djhue_host=args.djhue_host,
        djhue_port=args.djhue_port,
    )

    await server.start()

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


def main():
    """Entry point for dj-hue-touch command."""
    parser = argparse.ArgumentParser(
        description="Touch server for iPad DJ-Hue control"
    )
    parser.add_argument(
        "--host",
        default="::",
        help="Host to bind to (default: :: for IPv4+IPv6)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=TOUCH_SERVER_PORT,
        help=f"Port to listen on (default: {TOUCH_SERVER_PORT})",
    )
    parser.add_argument(
        "--djhue-host",
        default="localhost",
        help="DJ-Hue control server host (default: localhost)",
    )
    parser.add_argument(
        "--djhue-port",
        type=int,
        default=DJHUE_CONTROL_PORT,
        help=f"DJ-Hue control server port (default: {DJHUE_CONTROL_PORT})",
    )

    args = parser.parse_args()

    addresses = get_network_addresses()

    print("=" * 60)
    print("  DJ-Hue Touch Server")
    print("=" * 60)
    print()
    if addresses:
        print("  Connect from iPad:")
        for addr in addresses:
            print(f"    http://{addr}:{args.port}")
    else:
        print(f"  Connect from iPad:  http://localhost:{args.port}")
    print()
    print("=" * 60)

    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        print("\n[TOUCH] Shutting down...")


if __name__ == "__main__":
    main()
