"""Payload field rewrite rules: rename, drop, or set static values on outgoing payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PayloadRewriteConfig:
    rename: dict[str, str] = field(default_factory=dict)   # {old_key: new_key}
    drop: list[str] = field(default_factory=list)           # top-level keys to remove
    set_fields: dict[str, Any] = field(default_factory=dict)  # key: static value


def config_from_dict(raw: dict) -> PayloadRewriteConfig:
    """Build a PayloadRewriteConfig from a plain dict (e.g. from route config)."""
    return PayloadRewriteConfig(
        rename=dict(raw.get("rename", {})),
        drop=list(raw.get("drop", [])),
        set_fields=dict(raw.get("set", {})),
    )


def get_route_rewrite_config(route) -> PayloadRewriteConfig | None:
    """Extract payload_rewrite config from a RouteConfig object, or None if absent."""
    raw = getattr(route, "payload_rewrite", None)
    if not raw:
        return None
    return config_from_dict(raw)


def apply_payload_rewrites(payload: dict, cfg: PayloadRewriteConfig) -> dict:
    """Return a *new* dict with rename/drop/set rules applied.

    Processing order:
      1. drop   – remove unwanted keys first
      2. rename – rename remaining keys
      3. set    – overwrite / inject static values last
    """
    result = dict(payload)

    # 1. drop
    for key in cfg.drop:
        result.pop(key, None)

    # 2. rename
    for old_key, new_key in cfg.rename.items():
        if old_key in result:
            result[new_key] = result.pop(old_key)

    # 3. set static values
    result.update(cfg.set_fields)

    return result
