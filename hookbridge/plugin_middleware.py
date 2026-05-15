"""Middleware helpers that integrate the plugin system with RouteConfig
and the dispatch pipeline."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from hookbridge.plugin import apply_plugins, load_plugin_from_dotpath

logger = logging.getLogger(__name__)


def load_plugins_from_config(plugin_dotpaths: Optional[List[str]]) -> None:
    """Import every dotpath listed under the top-level ``plugins`` config key.

    Silently skips ``None`` / empty lists so callers don't need to guard.
    """
    if not plugin_dotpaths:
        return
    for dotpath in plugin_dotpaths:
        load_plugin_from_dotpath(dotpath)


def get_route_plugins(route: Any) -> List[str]:
    """Return the list of plugin names declared on *route*, or an empty list.

    Accepts any object with an optional ``plugins`` attribute as well as plain
    dicts, keeping it compatible with both ``RouteConfig`` dataclasses and raw
    config dictionaries.
    """
    if isinstance(route, dict):
        return route.get("plugins") or []
    return getattr(route, "plugins", None) or []


def run_plugins_for_route(
    payload: Dict[str, Any],
    route: Any,
) -> Dict[str, Any]:
    """Convenience wrapper: resolve plugin names from *route* and apply them.

    Returns the (potentially transformed) payload.  If no plugins are
    configured the original payload dict is returned unchanged.
    """
    plugin_names = get_route_plugins(route)
    if not plugin_names:
        return payload
    route_name = (
        route.get("name") if isinstance(route, dict) else getattr(route, "name", "<unknown>")
    )
    logger.debug(
        "Running plugins %s for route '%s'.", plugin_names, route_name
    )
    return apply_plugins(payload, route_name, plugin_names)
