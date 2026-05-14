"""Payload filtering logic for hookbridge routes."""

import re
from typing import Any


def get_nested(data: dict, path: str) -> Any:
    """Retrieve a nested value from a dict using dot-notation path."""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def evaluate_condition(payload: dict, condition: dict) -> bool:
    """
    Evaluate a single filter condition against a payload.

    Supported operators: eq, neq, contains, regex, exists
    """
    field = condition.get("field")
    operator = condition.get("operator", "eq")
    expected = condition.get("value")

    value = get_nested(payload, field)

    if operator == "exists":
        return value is not None
    if operator == "eq":
        return value == expected
    if operator == "neq":
        return value != expected
    if operator == "contains":
        if isinstance(value, str):
            return expected in value
        if isinstance(value, list):
            return expected in value
        return False
    if operator == "regex":
        if not isinstance(value, str):
            return False
        return bool(re.search(expected, value))

    raise ValueError(f"Unknown filter operator: {operator}")


def matches_filters(payload: dict, filters: list[dict]) -> bool:
    """
    Return True if the payload matches ALL filter conditions.
    An empty filter list always matches.
    """
    for condition in filters:
        if not evaluate_condition(payload, condition):
            return False
    return True
