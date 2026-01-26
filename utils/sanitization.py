"""
Input sanitization utilities for security.

Provides functions to sanitize and validate user input to prevent:
- Control character injection
- Excessive input length
- HTML/JavaScript injection
- Path traversal attempts
"""

import re

# Control characters (excluding common whitespace)
CONTROL_CHARS = bytearray(range(0x00, 0x20)) + bytearray(range(0x7F, 0xA0))
# Allow tab, newline, carriage return
ALLOWED_CONTROL = {0x09, 0x0A, 0x0D}
CONTROL_CHARS_FILTER = bytes(b for b in CONTROL_CHARS if b not in ALLOWED_CONTROL)

# Max lengths for different input types
DEFAULT_MAX_LENGTH = 10_000
CHAT_MAX_LENGTH = 50_000
SEARCH_MAX_LENGTH = 1_000
EMAIL_MAX_LENGTH = 254
PROPERTY_ID_MAX_LENGTH = 100


def sanitize_string(
    input_str: str,
    max_length: int = DEFAULT_MAX_LENGTH,
    remove_html: bool = True,
    allow_control_chars: bool = False,
) -> str:
    """
    Sanitize a string input for security.

    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        remove_html: Whether to remove HTML tags
        allow_control_chars: Whether to allow control characters (excluding tab, newline, CR)

    Returns:
        Sanitized string

    Raises:
        ValueError: If input exceeds max_length
    """
    if not isinstance(input_str, str):
        return ""

    # Check length
    if len(input_str) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")

    # Remove or filter control characters
    if not allow_control_chars:
        input_str = input_str.translate(CONTROL_CHARS_FILTER)

    # Remove HTML tags if requested
    if remove_html:
        input_str = _strip_html(input_str)

    # Remove excessive whitespace
    input_str = " ".join(input_str.split())

    return input_str


def _strip_html(input_str: str) -> str:
    """
    Strip HTML tags from string.

    Uses a simple regex-based approach. For more complex cases,
    consider using a proper HTML parser like bleach.

    Args:
        input_str: Input string potentially containing HTML

    Returns:
        String with HTML tags removed
    """
    # Remove script tags and content
    input_str = re.sub(r"<script\b[^>]*>(.*?)</script>", "", input_str, flags=re.IGNORECASE | re.DOTALL)

    # Remove style tags and content
    input_str = re.sub(r"<style\b[^>]*>(.*?)</style>", "", input_str, flags=re.IGNORECASE | re.DOTALL)

    # Remove HTML comments
    input_str = re.sub(r"<!--.*?-->", "", input_str, flags=re.DOTALL)

    # Remove remaining HTML tags
    input_str = re.sub(r"<[^>]+>", "", input_str)

    # Decode HTML entities
    import html

    try:
        input_str = html.unescape(input_str)
    except Exception:
        pass

    return input_str


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query input.

    Args:
        query: Search query string

    Returns:
        Sanitized query suitable for vector search

    Raises:
        ValueError: If query is invalid or too long
    """
    if not query:
        raise ValueError("Search query cannot be empty")

    return sanitize_string(
        query,
        max_length=SEARCH_MAX_LENGTH,
        remove_html=True,
        allow_control_chars=False,
    )


def sanitize_chat_message(message: str) -> str:
    """
    Sanitize chat message input.

    Args:
        message: Chat message string

    Returns:
        Sanitized message

    Raises:
        ValueError: If message is invalid or too long
    """
    if not message or not message.strip():
        raise ValueError("Chat message cannot be empty")

    return sanitize_string(
        message,
        max_length=CHAT_MAX_LENGTH,
        remove_html=False,  # Allow markdown formatting
        allow_control_chars=False,
    )


def sanitize_email(email: str) -> str:
    """
    Sanitize and validate email input.

    Args:
        email: Email address string

    Returns:
        Sanitized email

    Raises:
        ValueError: If email is invalid
    """
    if not email:
        return ""

    email = sanitize_string(email, max_length=EMAIL_MAX_LENGTH, remove_html=True)

    # Basic email validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValueError(f"Invalid email format: {email}")

    return email.lower().strip()


def sanitize_property_id(property_id: str) -> str:
    """
    Sanitize property ID input.

    Args:
        property_id: Property identifier

    Returns:
        Sanitized property ID

    Raises:
        ValueError: If property_id is invalid
    """
    if not property_id:
        raise ValueError("Property ID cannot be empty")

    property_id = sanitize_string(
        property_id,
        max_length=PROPERTY_ID_MAX_LENGTH,
        remove_html=True,
        allow_control_chars=False,
    )

    # Remove any path traversal attempts
    property_id = property_id.replace("..", "").replace("\\", "").replace("/", "")

    if not property_id:
        raise ValueError("Property ID cannot be empty after sanitization")

    return property_id


def validate_json_fields(data: dict, allowed_fields: set, max_field_length: int = 1000) -> dict:
    """
    Validate JSON request body fields.

    Args:
        data: Request data dictionary
        allowed_fields: Set of allowed field names
        max_field_length: Maximum length for string field values

    Returns:
        Validated data dictionary

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")

    # Check for unexpected fields
    unexpected = set(data.keys()) - allowed_fields
    if unexpected:
        raise ValueError(f"Unexpected fields in request: {', '.join(unexpected)}")

    validated = {}
    for key, value in data.items():
        if isinstance(value, str):
            if len(value) > max_field_length:
                raise ValueError(f"Field '{key}' exceeds maximum length")
            validated[key] = value.strip()
        elif isinstance(value, (int, float, bool, list, dict)):
            validated[key] = value
        else:
            raise ValueError(f"Field '{key}' has invalid type")

    return validated


def truncate_for_logging(value: str, max_length: int = 200) -> str:
    """
    Truncate a string for logging while preserving readability.

    Args:
        value: String to truncate
        max_length: Maximum length

    Returns:
        Truncated string with ellipsis if needed
    """
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
