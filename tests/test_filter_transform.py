"""Tests for hookbridge filtering and transformation modules."""

import pytest

from hookbridge.filter import evaluate_condition, matches_filters, get_nested
from hookbridge.transform import apply_template, transform_payload


PAYLOAD = {
    "event": "push",
    "repository": {"name": "hookbridge", "private": False},
    "commits": ["abc123", "def456"],
    "sender": {"login": "alice"},
}


# --- get_nested ---

def test_get_nested_simple():
    assert get_nested(PAYLOAD, "event") == "push"


def test_get_nested_deep():
    assert get_nested(PAYLOAD, "repository.name") == "hookbridge"


def test_get_nested_missing():
    assert get_nested(PAYLOAD, "repository.missing") is None


# --- evaluate_condition ---

def test_condition_eq_match():
    assert evaluate_condition(PAYLOAD, {"field": "event", "operator": "eq", "value": "push"})


def test_condition_eq_no_match():
    assert not evaluate_condition(PAYLOAD, {"field": "event", "operator": "eq", "value": "pull_request"})


def test_condition_neq():
    assert evaluate_condition(PAYLOAD, {"field": "event", "operator": "neq", "value": "delete"})


def test_condition_contains_string():
    assert evaluate_condition(PAYLOAD, {"field": "repository.name", "operator": "contains", "value": "hook"})


def test_condition_contains_list():
    assert evaluate_condition(PAYLOAD, {"field": "commits", "operator": "contains", "value": "abc123"})


def test_condition_regex():
    assert evaluate_condition(PAYLOAD, {"field": "sender.login", "operator": "regex", "value": "^ali"})


def test_condition_exists():
    assert evaluate_condition(PAYLOAD, {"field": "repository.private", "operator": "exists"})
    assert not evaluate_condition(PAYLOAD, {"field": "repository.unknown", "operator": "exists"})


def test_unknown_operator_raises():
    with pytest.raises(ValueError, match="Unknown filter operator"):
        evaluate_condition(PAYLOAD, {"field": "event", "operator": "gt", "value": 1})


# --- matches_filters ---

def test_matches_filters_all_pass():
    filters = [
        {"field": "event", "operator": "eq", "value": "push"},
        {"field": "repository.name", "operator": "contains", "value": "hook"},
    ]
    assert matches_filters(PAYLOAD, filters)


def test_matches_filters_one_fails():
    filters = [
        {"field": "event", "operator": "eq", "value": "push"},
        {"field": "event", "operator": "eq", "value": "delete"},
    ]
    assert not matches_filters(PAYLOAD, filters)


def test_matches_filters_empty():
    assert matches_filters(PAYLOAD, [])


# --- transform_payload ---

def test_transform_no_transform():
    assert transform_payload(PAYLOAD, None) == PAYLOAD


def test_transform_template():
    transform = {"template": {"repo": "$.repository.name", "action": "$.event"}}
    result = transform_payload(PAYLOAD, transform)
    assert result == {"repo": "hookbridge", "action": "push"}


def test_transform_add_fields():
    transform = {"add_fields": {"source": "github", "repo": "$.repository.name"}}
    result = transform_payload(PAYLOAD, transform)
    assert result["source"] == "github"
    assert result["repo"] == "hookbridge"
    assert result["event"] == "push"  # original fields preserved


def test_transform_remove_fields():
    transform = {"remove_fields": ["sender", "commits"]}
    result = transform_payload(PAYLOAD, transform)
    assert "sender" not in result
    assert "commits" not in result
    assert "event" in result
