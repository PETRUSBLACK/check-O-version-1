"""
Shared reusable validators for SmartMall.
Use these in serializers and model fields — never duplicate validation logic.
"""

import re

from django.core.exceptions import ValidationError


# ─── Phone ────────────────────────────────────────────────────────────────────

_PHONE_RE = re.compile(r"^\+?[1-9]\d{6,14}$")


def validate_phone_number(value: str) -> None:
    """
    Validates international phone numbers.
    Accepts optional leading +, then 7–15 digits.
    Examples: +2348012345678, 08012345678
    """
    if value and not _PHONE_RE.match(value.strip()):
        raise ValidationError(
            "Enter a valid phone number (e.g. +2348012345678 or 08012345678)."
        )


# ─── Nigerian Business Registration ───────────────────────────────────────────

_CAC_RE = re.compile(r"^(RC|BN|IT)\d{5,8}$", re.IGNORECASE)


def validate_cac_number(value: str) -> None:
    """
    Validates Nigerian CAC registration numbers.
    Accepted formats: RC1234567, BN1234567, IT12345
    """
    if value and not _CAC_RE.match(value.strip()):
        raise ValidationError(
            "Enter a valid CAC registration number (e.g. RC1234567, BN1234567)."
        )


# ─── Slug ─────────────────────────────────────────────────────────────────────

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_slug(value: str) -> None:
    """
    Validates URL-safe slugs: lowercase letters, digits, and hyphens only.
    Must not start or end with a hyphen.
    """
    if value and not _SLUG_RE.match(value):
        raise ValidationError(
            "Slug may only contain lowercase letters, digits, and hyphens, "
            "and must not start or end with a hyphen."
        )


# ─── Price ────────────────────────────────────────────────────────────────────

def validate_positive_price(value) -> None:
    """Price must be greater than zero."""
    if value is not None and value <= 0:
        raise ValidationError("Price must be greater than zero.")


def validate_price_range(min_price, max_price) -> None:
    """Min price must be less than or equal to max price."""
    if min_price is not None and max_price is not None:
        if min_price > max_price:
            raise ValidationError("Minimum price cannot exceed maximum price.")


# ─── Password ─────────────────────────────────────────────────────────────────

def validate_password_not_numeric(value: str) -> None:
    """Password must not be entirely numeric."""
    if value and value.isdigit():
        raise ValidationError("Password cannot be entirely numeric.")


# ─── Tax ID ───────────────────────────────────────────────────────────────────

_TAX_RE = re.compile(r"^\d{8,12}$")


def validate_tax_identifier(value: str) -> None:
    """
    Validates Nigerian TIN (Tax Identification Number).
    Must be 8-12 digits.
    """
    if value and not _TAX_RE.match(value.strip()):
        raise ValidationError(
            "Enter a valid Tax ID (8–12 digits)."
        )
