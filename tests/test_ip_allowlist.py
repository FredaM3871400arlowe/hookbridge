"""Tests for hookbridge.ip_allowlist."""

import pytest
from hookbridge.ip_allowlist import (
    ip_is_allowed,
    get_route_allowlist,
    check_ip_for_route,
    build_ip_rejection_response,
)


# ---------------------------------------------------------------------------
# ip_is_allowed
# ---------------------------------------------------------------------------

def test_empty_allowlist_permits_any_ip():
    assert ip_is_allowed("1.2.3.4", []) is True


def test_exact_ipv4_match():
    assert ip_is_allowed("10.0.0.1", ["10.0.0.1"]) is True


def test_exact_ipv4_no_match():
    assert ip_is_allowed("10.0.0.2", ["10.0.0.1"]) is False


def test_cidr_ipv4_match():
    assert ip_is_allowed("192.168.1.50", ["192.168.1.0/24"]) is True


def test_cidr_ipv4_outside_range():
    assert ip_is_allowed("192.168.2.1", ["192.168.1.0/24"]) is False


def test_multiple_entries_first_matches():
    assert ip_is_allowed("10.1.1.1", ["10.1.1.1", "10.2.2.0/24"]) is True


def test_multiple_entries_second_matches():
    assert ip_is_allowed("10.2.2.5", ["10.1.1.1", "10.2.2.0/24"]) is True


def test_multiple_entries_none_match():
    assert ip_is_allowed("172.16.0.1", ["10.1.1.1", "10.2.2.0/24"]) is False


def test_ipv6_exact_match():
    assert ip_is_allowed("::1", ["::1"]) is True


def test_ipv6_cidr_match():
    assert ip_is_allowed("2001:db8::1", ["2001:db8::/32"]) is True


def test_invalid_client_ip_returns_false():
    assert ip_is_allowed("not-an-ip", ["10.0.0.0/8"]) is False


# ---------------------------------------------------------------------------
# get_route_allowlist
# ---------------------------------------------------------------------------

def test_get_route_allowlist_present():
    route = {"ip_allowlist": ["1.2.3.4", "5.6.7.0/24"]}
    assert get_route_allowlist(route) == ["1.2.3.4", "5.6.7.0/24"]


def test_get_route_allowlist_missing_returns_empty():
    assert get_route_allowlist({}) == []


def test_get_route_allowlist_none_returns_empty():
    assert get_route_allowlist({"ip_allowlist": None}) == []


# ---------------------------------------------------------------------------
# check_ip_for_route
# ---------------------------------------------------------------------------

def test_check_ip_allowed_returns_none():
    route = {"ip_allowlist": ["203.0.113.0/24"]}
    assert check_ip_for_route("203.0.113.42", route) is None


def test_check_ip_blocked_returns_reason():
    route = {"ip_allowlist": ["203.0.113.0/24"]}
    result = check_ip_for_route("198.51.100.1", route)
    assert result is not None
    assert "198.51.100.1" in result


def test_check_ip_no_allowlist_always_passes():
    assert check_ip_for_route("1.2.3.4", {}) is None


# ---------------------------------------------------------------------------
# build_ip_rejection_response
# ---------------------------------------------------------------------------

def test_build_ip_rejection_response_structure():
    resp = build_ip_rejection_response("IP '1.2.3.4' is not allowed")
    assert resp["error"] == "forbidden"
    assert "1.2.3.4" in resp["detail"]
