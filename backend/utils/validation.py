"""
backend/utils/validation.py
============================
PURPOSE
    Small, dependency-free validators used by every service. Centralizing
    these avoids subtly-different regexes scattered across route handlers,
    and gives every 4xx response the same shape.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


class ValidationError(Exception):
    """Raised for a single bad field. Routes turn this into HTTP 422."""

    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


def require(condition: bool, field: str, message: str) -> None:
    if not condition:
        raise ValidationError(field, message)


def clean_str(value: Any, field: str, *, min_len: int = 1, max_len: int = 255,
              required: bool = True) -> str:
    if value is None:
        if required:
            raise ValidationError(field, "is required")
        return ""
    text = str(value).strip()
    if required:
        require(len(text) >= min_len, field, f"must be at least {min_len} character(s)")
    require(len(text) <= max_len, field, f"must be at most {max_len} characters")
    return text


def clean_email(value: Any) -> str:
    text = clean_str(value, "email", min_len=5, max_len=254)
    require(bool(EMAIL_RE.match(text)), "email", "is not a valid email address")
    return text.lower()


def clean_username(value: Any) -> str:
    text = clean_str(value, "username", min_len=3, max_len=20)
    require(bool(USERNAME_RE.match(text)), "username",
            "must be 3-20 characters: letters, numbers, underscore only")
    return text.lower()


def clean_password(value: Any) -> str:
    text = str(value) if value is not None else ""
    require(len(text) >= 8, "password", "must be at least 8 characters")
    require(any(c.isalpha() for c in text) and any(c.isdigit() for c in text),
            "password", "must contain both letters and numbers")
    return text


def clean_choice(value: Any, field: str, choices: Iterable[str]) -> str:
    text = clean_str(value, field)
    choices = list(choices)
    require(text.upper() in [c.upper() for c in choices], field,
            f"must be one of {', '.join(choices)}")
    return text.upper()


def clean_positive_number(value: Any, field: str, *, allow_zero: bool = True) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(field, "must be a number")
    if allow_zero:
        require(number >= 0, field, "must not be negative")
    else:
        require(number > 0, field, "must be greater than zero")
    require(number < 1_000_000, field, "is unreasonably large")
    return number


def clean_date(value: Any, field: str, *, required: bool = True) -> str:
    """Accepts 'YYYY-MM-DD' and returns it unchanged (stored as ISO text)."""
    if not value:
        if required:
            raise ValidationError(field, "is required")
        return ""
    text = str(value).strip()
    require(re.match(r"^\d{4}-\d{2}-\d{2}$", text) is not None, field,
            "must use YYYY-MM-DD format")
    return text
