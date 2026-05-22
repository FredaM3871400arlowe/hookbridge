"""IP allowlist middleware for restricting webhook sources per route."""

import ipaddress
from typing import Optional


def _parse_network(entry: str):
    """Parse a string into an IPv4/IPv6 address or network."""
    try:
        return ipaddress.ip_network(entry, strict=False)
    except ValueError:
        return None


def ip_is_allowed(client_ip: str, allowlist: list[str]) -> bool:
    """Return True if *client_ip* matches any entry in *allowlist*.

    Each entry may be a single IP address or a CIDR network string.
    An empty allowlist means *all* IPs are permitted.
    """
    if not allowlist:
        return True

    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in allowlist:
        network = _parse_network(entry)
        if network is not None and addr in network:
            return True
    return False


def get_route_allowlist(route_config: dict) -> list[str]:
    """Extract the ip_allowlist from a route config dict.

    Returns an empty list when the key is absent, meaning no restriction.
    """
    return route_config.get("ip_allowlist") or []


def check_ip_for_route(
    client_ip: str,
    route_config: dict,
) -> Optional[str]:
    """Validate *client_ip* against the route's allowlist.

    Returns *None* when the request is permitted, or a human-readable
    rejection reason string when it should be blocked.
    """
    allowlist = get_route_allowlist(route_config)
    if not ip_is_allowed(client_ip, allowlist):
        return f"IP {client_ip!r} is not in the allowlist for this route"
    return None


def build_ip_rejection_response(reason: str) -> dict:
    """Build a standard 403 response body for an IP rejection."""
    return {"error": "forbidden", "detail": reason}
