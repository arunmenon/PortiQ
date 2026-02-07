"""Schema governance — validation rules and breaking change detection for category schemas."""

from __future__ import annotations

import json
import sys

from src.exceptions import ValidationException

# Governance limits
MAX_NESTING_DEPTH = 3
MAX_SCHEMA_SIZE_BYTES = 64 * 1024  # 64 KB


class SchemaGovernanceService:

    def validate_schema(self, schema_json: dict) -> None:
        """Validate a JSON Schema against governance rules.

        Checks:
        - Must be a valid JSON Schema-like object (dict with "type" or "properties")
        - Max nesting depth of 3 levels
        - Max serialized size of 64 KB

        Raises ValidationException on failure.
        """
        if not isinstance(schema_json, dict):
            raise ValidationException("Schema must be a JSON object")

        serialized = json.dumps(schema_json)
        if sys.getsizeof(serialized.encode("utf-8")) > MAX_SCHEMA_SIZE_BYTES:
            raise ValidationException(
                f"Schema exceeds maximum size of {MAX_SCHEMA_SIZE_BYTES // 1024} KB"
            )

        depth = self._measure_nesting_depth(schema_json)
        if depth > MAX_NESTING_DEPTH:
            raise ValidationException(
                f"Schema nesting depth {depth} exceeds maximum of {MAX_NESTING_DEPTH}"
            )

    def detect_breaking_changes(
        self, old_schema: dict | None, new_schema: dict
    ) -> list[dict]:
        """Compare old and new schemas and return a list of breaking changes.

        Breaking changes include:
        - Removal of a field that was previously required
        - Type change of an existing property

        Returns a list of dicts with "field" and "reason" keys.
        """
        if old_schema is None:
            return []

        breaking_changes: list[dict] = []

        old_properties = old_schema.get("properties", {})
        new_properties = new_schema.get("properties", {})
        old_required = set(old_schema.get("required", []))

        # Check for removed required fields
        for field_name in old_required:
            if field_name in old_properties and field_name not in new_properties:
                breaking_changes.append({
                    "field": field_name,
                    "reason": "Required field removed",
                })

        # Check for type changes on existing properties
        for field_name, old_prop in old_properties.items():
            if field_name not in new_properties:
                continue
            new_prop = new_properties[field_name]
            old_type = old_prop.get("type")
            new_type = new_prop.get("type")
            if old_type is not None and new_type is not None and old_type != new_type:
                breaking_changes.append({
                    "field": field_name,
                    "reason": f"Type changed from '{old_type}' to '{new_type}'",
                })

            # Recurse into nested object properties
            if old_type == "object" and new_type == "object":
                nested_breaks = self.detect_breaking_changes(old_prop, new_prop)
                for change in nested_breaks:
                    breaking_changes.append({
                        "field": f"{field_name}.{change['field']}",
                        "reason": change["reason"],
                    })

        return breaking_changes

    def _measure_nesting_depth(self, schema: dict, current_depth: int = 0) -> int:
        """Recursively measure the deepest nesting level in a JSON Schema."""
        max_depth = current_depth
        properties = schema.get("properties", {})
        for prop in properties.values():
            if not isinstance(prop, dict):
                continue
            prop_type = prop.get("type")
            if prop_type == "object":
                nested_depth = self._measure_nesting_depth(prop, current_depth + 1)
                max_depth = max(max_depth, nested_depth)
            elif prop_type == "array":
                items = prop.get("items", {})
                if isinstance(items, dict) and items.get("type") == "object":
                    nested_depth = self._measure_nesting_depth(items, current_depth + 1)
                    max_depth = max(max_depth, nested_depth)
        return max_depth
