"""
Command parsing utility functions.
"""

def parse_equals(text):
    """Split text on = and return [left, right] parts with whitespace stripped."""
    if not text or "=" not in text:
        return None
    parts = [part.strip() for part in text.split("=", 1)]
    return parts if all(parts) else None


def parse_comma(text, expected_parts=2):
    """Split text on comma and return parts with whitespace stripped."""
    if not text:
        return None
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return parts if len(parts) == expected_parts else None