"""Handler mixin that adds an OPTIONS route and injects CORS headers."""

from hookbridge.cors import get_cors_config
from hookbridge.cors_middleware import apply_cors_to_handler, flush_cors_headers


def add_cors_support(base_class):
    """Class decorator that wraps a BaseHTTPRequestHandler subclass with CORS support."""

    class CORSAwareHandler(base_class):
        def do_OPTIONS(self):
            config = get_cors_config(getattr(self, "app_config", None))
            apply_cors_to_handler(self, config)

        def send_response(self, code, message=None):
            super().send_response(code, message)
            config = get_cors_config(getattr(self, "app_config", None))
            if config is not None:
                from hookbridge.cors_middleware import _get_origin
                from hookbridge.cors import build_cors_headers
                origin = _get_origin(self)
                for key, value in build_cors_headers(config, origin).items():
                    self.send_header(key, value)

        def log_message(self, fmt, *args):  # suppress default stderr logging
            pass

    CORSAwareHandler.__name__ = f"CORS{base_class.__name__}"
    return CORSAwareHandler


class CORSMixin:
    """Mixin that can be used directly in handler class hierarchies."""

    def do_OPTIONS(self):
        config = get_cors_config(getattr(self, "app_config", None))
        apply_cors_to_handler(self, config)

    def _write_cors_headers(self):
        config = get_cors_config(getattr(self, "app_config", None))
        if config is None:
            return
        from hookbridge.cors_middleware import _get_origin
        from hookbridge.cors import build_cors_headers
        origin = _get_origin(self)
        for key, value in build_cors_headers(config, origin).items():
            self.send_header(key, value)
