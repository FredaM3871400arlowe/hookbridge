"""CORS (Cross-Origin Resource Sharing) support for hookbridge."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CORSConfig:
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    allowed_methods: List[str] = field(default_factory=lambda: ["POST", "GET", "OPTIONS"])
    allowed_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization", "X-Hub-Signature-256"])
    allow_credentials: bool = False
    max_age_seconds: int = 600


def config_from_dict(data: dict) -> CORSConfig:
    """Build a CORSConfig from a raw config dictionary."""
    return CORSConfig(
        allowed_origins=data.get("allowed_origins", ["*"]),
        allowed_methods=data.get("allowed_methods", ["POST", "GET", "OPTIONS"]),
        allowed_headers=data.get("allowed_headers", ["Content-Type", "Authorization", "X-Hub-Signature-256"]),
        allow_credentials=data.get("allow_credentials", False),
        max_age_seconds=data.get("max_age_seconds", 600),
    )


def get_cors_config(app_config) -> Optional[CORSConfig]:
    """Extract global CORS config from AppConfig, if defined."""
    raw = getattr(app_config, "cors", None)
    if raw is None:
        return None
    return config_from_dict(raw) if isinstance(raw, dict) else raw


def build_cors_headers(config: CORSConfig, request_origin: Optional[str] = None) -> dict:
    """Return a dict of CORS headers to attach to a response."""
    origins = config.allowed_origins
    if "*" in origins:
        origin_value = "*"
    elif request_origin and request_origin in origins:
        origin_value = request_origin
    else:
        origin_value = None

    headers = {}
    if origin_value:
        headers["Access-Control-Allow-Origin"] = origin_value
    headers["Access-Control-Allow-Methods"] = ", ".join(config.allowed_methods)
    headers["Access-Control-Allow-Headers"] = ", ".join(config.allowed_headers)
    headers["Access-Control-Max-Age"] = str(config.max_age_seconds)
    if config.allow_credentials:
        headers["Access-Control-Allow-Credentials"] = "true"
    return headers


def is_preflight(method: str, headers: dict) -> bool:
    """Return True if the request looks like a CORS preflight (OPTIONS + Origin)."""
    return method == "OPTIONS" and "origin" in {k.lower() for k in headers}
