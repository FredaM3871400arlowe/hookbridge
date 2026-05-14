import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from hookbridge.config import AppConfig, load_config
from hookbridge.dispatcher import dispatch_all

logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    config: AppConfig = None

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)

    def send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_body(self) -> Optional[dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON body: %s", exc)
            return None

    def do_POST(self) -> None:
        path = self.path.rstrip("/")
        matching_routes = [
            r for r in self.config.routes if r.path == path
        ]

        if not matching_routes:
            self.send_json(404, {"error": f"No routes configured for path '{path}'"})
            return

        body = self.read_body()
        if body is None:
            self.send_json(400, {"error": "Invalid JSON payload"})
            return

        results = dispatch_all(matching_routes, body)
        summary = [
            {"target": r.target_url, "success": r.success, "detail": r.detail}
            for r in results
        ]
        all_ok = all(r.success for r in results)
        status = 200 if all_ok else 207
        self.send_json(status, {"dispatched": len(results), "results": summary})


def create_server(config: AppConfig) -> HTTPServer:
    WebhookHandler.config = config
    server = HTTPServer((config.host, config.port), WebhookHandler)
    logger.info("HookBridge listening on %s:%d", config.host, config.port)
    return server


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    config = load_config()
    server = create_server(config)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down HookBridge")
        server.server_close()


if __name__ == "__main__":
    run()
