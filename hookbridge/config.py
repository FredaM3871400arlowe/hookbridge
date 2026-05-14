"""Configuration loading and validation for hookbridge."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RouteConfig:
    name: str
    source_path: str
    target_url: str
    secret: Optional[str] = None
    filter_rules: List[dict] = field(default_factory=list)
    transform: Optional[str] = None


@dataclass
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"
    routes: List[RouteConfig] = field(default_factory=list)


def load_config(path: Optional[str] = None) -> AppConfig:
    """Load configuration from a JSON file or environment variables."""
    config_path = path or os.environ.get("HOOKBRIDGE_CONFIG", "hookbridge.json")

    if not os.path.exists(config_path):
        return AppConfig()

    with open(config_path, "r") as f:
        raw = json.load(f)

    routes = [
        RouteConfig(
            name=r["name"],
            source_path=r["source_path"],
            target_url=r["target_url"],
            secret=r.get("secret"),
            filter_rules=r.get("filter_rules", []),
            transform=r.get("transform"),
        )
        for r in raw.get("routes", [])
    ]

    return AppConfig(
        host=raw.get("host", "0.0.0.0"),
        port=int(raw.get("port", 8080)),
        log_level=raw.get("log_level", "INFO"),
        routes=routes,
    )
