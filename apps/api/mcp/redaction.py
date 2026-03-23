"""
MCP Redaction Rules for audit logging (Task #69).

This module provides MCP-specific data redaction for audit logs:
1. PII detection and masking
2. Connector-specific sensitive field handling
3. Logging boundary enforcement (only metadata, no raw data)

Design principle: Only log what's necessary for debugging and auditing.
Never log: credentials, tokens, personal data, raw API responses.
"""

import re
from typing import Any, Optional

from utils.data_protection import DataMasker

# MCP-specific sensitive keys that should always be redacted
MCP_SENSITIVE_KEYS = {
    # Credentials
    "api_key",
    "apikey",
    "api-key",
    "secret",
    "secret_key",
    "access_token",
    "refresh_token",
    "auth_token",
    "bearer_token",
    "authorization",
    # Connection details
    "password",
    "passwd",
    "pwd",
    "connection_string",
    "database_url",
    "redis_url",
    "endpoint_url",
    # MCP-specific
    "credentials",
    "private_key",
    "webhook_secret",
    "signature",
    # Personal data
    "email",
    "phone",
    "ssn",
    "social_security",
    "credit_card",
    "card_number",
    "account_number",
    # Property-specific PII
    "owner_name",
    "owner_email",
    "owner_phone",
    "tenant_name",
    "tenant_email",
}

# Patterns for detecting sensitive data in strings
MCP_SENSITIVE_PATTERNS = [
    # API keys
    (r"sk-[a-zA-Z0-9-]+", "sk-***"),
    (r"pk-[a-zA-Z0-9-]+", "pk-***"),
    (r"gh[pousr]_[a-zA-Z0-9-]+", "***"),
    # Tokens
    (r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer ***"),
    (r"token[:\s]+[a-zA-Z0-9_\-\.]+", "token: ***"),
    # URLs with credentials
    (r"(https?://)[^:]+:[^@]+(@)", r"\1***:***\2"),
    # Emails
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "***@***.***"),
]


def redact_for_audit(
    data: Any,
    max_depth: int = 5,
    max_items: int = 10,
    max_string_length: int = 100,
) -> dict[str, Any]:
    """
    Redact sensitive data for audit logging.

    This function creates a safe metadata representation of input data
    by removing/masking sensitive values and limiting size.

    Args:
        data: Input data to redact
        max_depth: Maximum nesting depth to process
        max_items: Maximum items in lists/dicts to include
        max_string_length: Maximum string length before truncation

    Returns:
        Redacted dictionary safe for logging
    """
    if max_depth <= 0:
        return {"_truncated": "max_depth_exceeded"}

    if data is None:
        return {"_type": "None"}

    if isinstance(data, (bool, int, float)):
        return {"_type": type(data).__name__, "_value": data}

    if isinstance(data, str):
        return _redact_string(data, max_string_length)

    if isinstance(data, dict):
        return _redact_dict(data, max_depth, max_items, max_string_length)

    if isinstance(data, (list, tuple, set)):
        return _redact_list(data, max_depth, max_items, max_string_length)

    # For other types, just log the type name
    return {"_type": type(data).__name__}


def _redact_string(value: str, max_length: int) -> dict[str, Any]:
    """Redact a string value."""
    # Check for sensitive patterns
    redacted = value
    for pattern, replacement in MCP_SENSITIVE_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    # If the string was modified (contains sensitive data), fully redact
    if redacted != value:
        return {"_type": "str", "_redacted": True, "_value": "***"}

    # Truncate if too long
    if len(value) > max_length:
        return {
            "_type": "str",
            "_truncated": True,
            "_length": len(value),
            "_preview": value[:max_length] + "...",
        }

    return {"_type": "str", "_value": value}


def _redact_dict(
    data: dict[str, Any],
    max_depth: int,
    max_items: int,
    max_string_length: int,
) -> dict[str, Any]:
    """Redact a dictionary."""
    result: dict[str, Any] = {}
    keys = list(data.keys())[:max_items]

    for key in keys:
        key_lower = key.lower()

        # Check if key is sensitive
        if key_lower in MCP_SENSITIVE_KEYS or any(
            sensitive in key_lower for sensitive in MCP_SENSITIVE_KEYS
        ):
            result[key] = {"_redacted": True, "_reason": "sensitive_key"}
            continue

        # Recursively redact value
        value = data[key]
        result[key] = redact_for_audit(value, max_depth - 1, max_items, max_string_length)

    if len(data) > max_items:
        result["_truncated"] = True
        result["_total_keys"] = len(data)

    return result


def _redact_list(
    data: list[Any] | tuple[Any, ...] | set[Any],
    max_depth: int,
    max_items: int,
    max_string_length: int,
) -> dict[str, Any]:
    """Redact a list, tuple, or set."""
    items = list(data)[:max_items]
    result = [
        redact_for_audit(item, max_depth - 1, max_items, max_string_length) for item in items
    ]

    response: dict[str, Any] = {
        "_type": type(data).__name__,
        "_items": result,
    }

    if len(data) > max_items:
        response["_truncated"] = True
        response["_total_items"] = len(data)

    return response


def redact_params(params: Optional[dict[str, Any]]) -> dict[str, Any]:
    """
    Redact connector parameters for audit logging.

    This is the primary entry point for redacting connector call parameters.
    Only metadata is logged: param names, types, and counts.

    Args:
        params: Connector parameters to redact

    Returns:
        Redacted parameters metadata
    """
    if params is None:
        return {"_type": "None", "_param_count": 0}

    # Create a summary of params without actual values
    summary: dict[str, Any] = {
        "_param_count": len(params),
        "_param_types": {},
    }

    for key, value in params.items():
        key_lower = key.lower()

        # Mark sensitive keys
        if key_lower in MCP_SENSITIVE_KEYS or any(
            sensitive in key_lower for sensitive in MCP_SENSITIVE_KEYS
        ):
            summary["_param_types"][key] = "REDACTED"
        else:
            summary["_param_types"][key] = type(value).__name__

    return summary


def redact_result(result: Any) -> dict[str, Any]:
    """
    Redact connector result for audit logging.

    Only metadata is logged: status, type, and size indicators.

    Args:
        result: Connector result to redact

    Returns:
        Redacted result metadata
    """
    if result is None:
        return {"_type": "None"}

    # Handle MCPConnectorResult-like objects
    if hasattr(result, "success"):
        summary: dict[str, Any] = {
            "_type": "MCPConnectorResult",
            "success": getattr(result, "success", None),
        }

        # Log execution time if available
        if hasattr(result, "execution_time_ms"):
            summary["execution_time_ms"] = result.execution_time_ms

        # Log data size/type without content
        if hasattr(result, "data") and result.data is not None:
            data = result.data
            if isinstance(data, dict):
                summary["data_type"] = "dict"
                summary["data_keys"] = list(data.keys())[:10]
            elif isinstance(data, list):
                summary["data_type"] = "list"
                summary["data_count"] = len(data)
            else:
                summary["data_type"] = type(data).__name__

        # Log errors without sensitive details
        if hasattr(result, "errors") and result.errors:
            summary["error_count"] = len(result.errors)
            summary["has_errors"] = True

        return summary

    # Handle generic results
    return redact_for_audit(result, max_depth=2)


def sanitize_error_message(error: str, max_length: int = 200) -> str:
    """
    Sanitize an error message for safe logging.

    Removes potentially sensitive information from error messages.

    Args:
        error: Error message to sanitize
        max_length: Maximum length for the message

    Returns:
        Sanitized error message
    """
    if not error:
        return error

    sanitized = error

    # Apply all sensitive patterns
    for pattern, replacement in MCP_SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    # Use DataMasker for additional PII detection
    sanitized = DataMasker.detect_and_mask(sanitized)

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized
