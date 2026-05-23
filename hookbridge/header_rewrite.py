"""Header rewrite middleware — add, remove, or override headers on forwarded requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class HeaderRewriteConfig:
    """Describes header mutations to apply before relaying a request."""

    add: Dict[str, str] = field(default_factory=dict)
    """Headers to add (only if not already present)."""

    set: Dict[str, str] = field(default_factory=dict)
    """Headers to set (overwrite if present)."""

    remove: List[str] = field(default_factory=list)
    """Header names to strip (case-insensitive)."""


def config_from_dict(raw: dict) -> HeaderRewriteConfig:
    """Build a HeaderRewriteConfig from a plain dict (e.g. parsed JSON)."""
    return HeaderRewriteConfig(
        add=dict(raw.get("add", {})),
        set=dict(raw.get("set", {})),
        remove=[h.lower() for h in raw.get("remove", [])],
    )


def get_route_rewrite_config(route: object) -> Optional[HeaderRewriteConfig]:
    """Extract HeaderRewriteConfig from a RouteConfig, or None if not configured."""
    raw = getattr(route, "header_rewrite", None)
    if not raw:
        return None
    if isinstance(raw, HeaderRewriteConfig):
        return raw
    return config_from_dict(raw)


def apply_header_rewrites(
    headers: Dict[str, str],
    config: HeaderRewriteConfig,
) -> Dict[str, str]:
    """Return a new header dict with rewrites applied.

    Order of operations:
      1. Remove listed headers.
      2. Add headers that are not already present.
      3. Set headers (overwrite unconditionally).
    """
    result: Dict[str, str] = {
        k: v
        for k, v in headers.items()
        if k.lower() not in config.remove
    }

    for name, value in config.add.items():
        if name.lower() not in {k.lower() for k in result}:
            result[name] = value

    for name, value in config.set.items():
        # Replace any existing key that matches case-insensitively.
        keys_to_drop = [k for k in result if k.lower() == name.lower()]
        for k in keys_to_drop:
            del result[k]
        result[name] = value

    return result
