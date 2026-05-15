"""Plugin system for hookbridge — allows custom payload processors to be
registered and invoked during dispatch."""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Registry: plugin_name -> callable(payload: dict, route_name: str) -> dict
_REGISTRY: Dict[str, Callable[[Dict[str, Any], str], Dict[str, Any]]] = {}


def register_plugin(name: str, fn: Callable[[Dict[str, Any], str], Dict[str, Any]]) -> None:
    """Register a plugin function under *name*."""
    if name in _REGISTRY:
        logger.warning("Plugin '%s' is already registered — overwriting.", name)
    _REGISTRY[name] = fn
    logger.debug("Plugin '%s' registered.", name)


def unregister_plugin(name: str) -> None:
    """Remove a plugin from the registry (useful in tests)."""
    _REGISTRY.pop(name, None)


def load_plugin_from_dotpath(dotpath: str) -> None:
    """Import *dotpath* (e.g. 'mypackage.myplugin') and expect it to call
    ``register_plugin`` at module level as a side-effect."""
    try:
        importlib.import_module(dotpath)
        logger.info("Loaded plugin module '%s'.", dotpath)
    except ImportError as exc:
        raise ImportError(f"Cannot import plugin module '{dotpath}': {exc}") from exc


def apply_plugins(
    payload: Dict[str, Any],
    route_name: str,
    plugin_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run *payload* through each named plugin in order.

    If *plugin_names* is None or empty, return *payload* unchanged.
    Raises ``KeyError`` if a requested plugin is not registered.
    """
    if not plugin_names:
        return payload

    result = payload
    for name in plugin_names:
        if name not in _REGISTRY:
            raise KeyError(f"Plugin '{name}' is not registered.")
        try:
            result = _REGISTRY[name](result, route_name)
            logger.debug("Plugin '%s' applied to route '%s'.", name, route_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Plugin '%s' raised an error: %s", name, exc)
            raise
    return result


def list_plugins() -> List[str]:
    """Return names of all currently registered plugins."""
    return list(_REGISTRY.keys())
