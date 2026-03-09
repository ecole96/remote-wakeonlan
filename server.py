from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import subprocess
import json
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# DEVICES format:
# {
#   "MyPC": { "targetIpAddress": "192.168.4.50", "macAddress": "AA-BB-CC-DD-EE-FF" }
# }
DEVICES = json.loads(os.environ.get("DEVICES", "{}"))
PORT = int(os.environ.get("PORT", 8765))

if not DEVICES:
    logger.warning("No devices configured. Set the DEVICES environment variable.")

# Endpoints:
#   GET /                 - API documentation
#   GET /devices          - List all configured device names
#   GET /wake?device=<n>  - Send WoL magic packet to named device

DOCS = {
    "endpoints": {
        "GET /": "API documentation",
        "GET /devices": "List all configured device names",
        "GET /wake?device=<n>": "Send WoL magic packet to named device",
    }
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        ip = self.client_address[0]

        logger.info(f"REQUEST  {ip} - {self.command} {self.path}")

        try:
            if parsed.path == "/":
                status, data = 200, DOCS

            elif parsed.path == "/devices":
                status, data = 200, list(DEVICES.keys())

            elif parsed.path == "/wake":
                device = params.get("device", [None])[0]
                config = DEVICES.get(device)
                if not device:
                    status, data = 400, {"error": "Missing 'device' parameter"}
                elif not config:
                    status, data = 404, {"error": f"Unknown device: {device}"}
                else:
                    target_ip = config["targetIpAddress"]
                    mac = config["macAddress"]
                    subprocess.run(["wakeonlan", "-i", target_ip, mac], check=True)
                    logger.info(f"WOL      {ip} - Sent magic packet to {device} ({mac}) via {target_ip}")
                    status, data = 200, {"ok": True, "device": device}

            else:
                status, data = 404, {"error": "Not found"}

        except KeyError as e:
            logger.error(f"ERROR    {ip} - Missing device config key: {e}")
            status, data = 500, {"error": f"Device config missing key: {e}"}

        except subprocess.CalledProcessError as e:
            logger.error(f"ERROR    {ip} - wakeonlan failed: {e}")
            status, data = 500, {"error": "Failed to send WoL packet"}

        except Exception as e:
            logger.error(f"ERROR    {ip} - Unhandled exception: {e}", exc_info=True)
            status, data = 500, {"error": "Internal server error"}

        logger.info(f"RESPONSE {ip} - {self.command} {self.path} - {status}")
        self._respond(status, data)

    def _respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # silenced in favour of explicit REQUEST/RESPONSE logs above


if __name__ == "__main__":
    logger.info(f"WoL server running on port {PORT}")
    logger.info(f"Known devices: {', '.join(DEVICES.keys())}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()