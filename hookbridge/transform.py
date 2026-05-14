"""Payload transformation utilities for hookbridge routes."""

from typing import Any

from hookbridge.filter import get_nested


def apply_template(template: Any, payload: dict) -> Any:
    """
    Recursively resolve a template structure against the incoming payload.

    String values starting with '$.' are treated as dot-notation references
    into the payload. All other values are passed through unchanged.
    """
    if isinstance(template, dict):
        return {k: apply_template(v, payload) for k, v in template.items()}
    if isinstance(template, list):
        return [apply_template(item, payload) for item in template]
    if isinstance(template, str) and template.startswith("$."):
        path = template[2:]
        return get_nested(payload, path)
    return template


def transform_payload(payload: dict, transform: dict | None) -> dict:
    """
    Apply a transformation spec to a payload.

    The transform dict may contain:
      - "template": a dict template to build the outgoing payload
      - "add_fields": key/value pairs to merge into the payload
      - "remove_fields": list of top-level keys to drop

    If no transform is provided the original payload is returned unchanged.
    """
    if not transform:
        return payload

    result = dict(payload)

    template = transform.get("template")
    if template:
        result = apply_template(template, payload)
        if not isinstance(result, dict):
            result = {"data": result}

    for key, value in transform.get("add_fields", {}).items():
        result[key] = apply_template(value, payload)

    for key in transform.get("remove_fields", []):
        result.pop(key, None)

    return result
