"""Product validators — IMPA code format checking and JSONB specification validation."""

from __future__ import annotations

import uuid

from jsonschema import Draft7Validator, ValidationError as JsonSchemaValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ValidationException
from src.modules.product.constants import IMPA_CODE_REGEX


def validate_impa_code_format(code: str) -> bool:
    """Check whether *code* matches the IMPA format (6-digit or EXT-XXXXXX)."""
    return bool(IMPA_CODE_REGEX.match(code))


def validate_specifications(specs: dict, attribute_schema: dict | None) -> None:
    """Validate product specifications JSONB against a category's attribute_schema.

    Uses JSON Schema Draft 7.  If *attribute_schema* is ``None`` any dict is valid.
    Raises :class:`ValidationException` with per-field detail on failure.
    """
    if attribute_schema is None:
        return

    validator = Draft7Validator(attribute_schema)
    errors = sorted(validator.iter_errors(specs), key=lambda e: list(e.absolute_path))

    if not errors:
        return

    details = []
    for error in errors:
        field_path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        details.append({"field": field_path, "message": error.message})

    raise ValidationException(
        message="Product specifications do not match the category schema",
        details=details,
    )


async def validate_specifications_with_schema(
    specs: dict,
    category_id: uuid.UUID,
    session: AsyncSession,
) -> dict:
    """Validate product specifications against the effective inherited schema.

    Looks up the effective schema for the category (walking ancestors) and
    validates the specs dict against it using JSON Schema Draft 7.

    Returns a dict with:
    - ``valid``: bool
    - ``errors``: list of validation error dicts (empty if valid)
    - ``schema_source``: "inherited" | "category" | None

    Raises nothing — returns validation result rather than raising.
    """
    from src.modules.product.category_service import CategoryService

    svc = CategoryService(session)
    effective_schema = await svc.get_effective_schema(category_id)

    if effective_schema is None:
        return {"valid": True, "errors": [], "schema_source": None}

    validator = Draft7Validator(effective_schema)
    errors = sorted(validator.iter_errors(specs), key=lambda e: list(e.absolute_path))

    if not errors:
        return {"valid": True, "errors": [], "schema_source": "inherited"}

    details = []
    for error in errors:
        field_path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        details.append({"field": field_path, "message": error.message})

    return {"valid": False, "errors": details, "schema_source": "inherited"}
