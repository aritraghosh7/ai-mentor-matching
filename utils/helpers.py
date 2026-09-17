"""
General utility functions.
"""

from __future__ import annotations

import re
from typing import Any


# ============================================================
# EMAIL VALIDATION
# ============================================================

def is_valid_email(
    email: str,
) -> bool:
    """
    Basic email validation.
    """

    if not email:

        return False

    pattern = (
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )

    return bool(
        re.match(
            pattern,
            email.strip(),
        )
    )


# ============================================================
# PARSE COMMA-SEPARATED VALUES
# ============================================================

def parse_comma_separated(
    value: Any,
) -> list[str]:
    """
    Convert a comma/semicolon/pipe-separated value
    into a clean list.
    """

    if value is None:

        return []

    parts = re.split(
        r"[,;|\n]+",
        str(value),
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


# ============================================================
# AVAILABILITY LABEL
# ============================================================

def availability_label(
    current_mentees: int,
    max_mentees: int,
) -> str:
    """
    Return availability text based on the exact
    business rule.
    """

    if current_mentees < max_mentees:

        return "AVAILABLE"

    return "FULL"


# ============================================================
# STATUS CLASS
# ============================================================

def status_class(
    status: str,
) -> str:
    """
    Convert status into a CSS-friendly class name.
    """

    return (
        str(status)
        .strip()
        .lower()
        .replace(" ", "-")
    )