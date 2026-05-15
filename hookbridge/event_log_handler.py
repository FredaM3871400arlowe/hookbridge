"""HTTP handler routes for querying the event log."""

import json
from http.server import BaseHTTPRequestHandler
from hookbridge.event_log import EventLog


def add_event_log_routes(handler_class):
    """Mixin factory: extend a BaseHTTPRequestHandler subclass with event log GET/DELETE routes."""

    class EventLogAwareHandler(handler_class):
        event_log: EventLog = None  # set at server creation

        def do_GET(self):
            if self.path == "/events" or self.path.startswith("/events?"):
                self._serve_events()
            elif self.path.startswith("/events/"):
                self._serve_event_by_id()
            else:
                super().do_GET()

        def do_DELETE(self):
            if self.path == "/events":
                self._clear_events()
            else:
                try:
                    super().do_DELETE()
                except AttributeError:
                    self.send_response(404)
                    self.end_headers()

        def _serve_events(self):
            log: EventLog = self.__class__.event_log
            if log is None:
                self._json_response(503, {"error": "event log not configured"})
                return

            route = None
            if "?" in self.path:
                qs = self.path.split("?", 1)[1]
                for part in qs.split("&"):
                    if part.startswith("route="):
                        route = part[len("route="):]

            entries = log.for_route(route) if route else log.all()
            self._json_response(200, [e.to_dict() for e in entries])

        def _serve_event_by_id(self):
            log: EventLog = self.__class__.event_log
            if log is None:
                self._json_response(503, {"error": "event log not configured"})
                return
            try:
                event_id = int(self.path.split("/events/", 1)[1])
            except (ValueError, IndexError):
                self._json_response(400, {"error": "invalid event id"})
                return
            entry = log.get(event_id)
            if entry is None:
                self._json_response(404, {"error": "event not found"})
            else:
                self._json_response(200, entry.to_dict())

        def _clear_events(self):
            log: EventLog = self.__class__.event_log
            if log is None:
                self._json_response(503, {"error": "event log not configured"})
                return
            log.clear()
            self._json_response(200, {"status": "cleared"})

        def _json_response(self, status: int, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):  # silence default stderr output
            pass

    return EventLogAwareHandler
