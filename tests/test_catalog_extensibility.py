"""Tests for Phase 2.2 — Catalog Extensibility.

Covers:
- Schema governance (nesting depth, size limits, breaking change detection)
- Schema registry (register, activate, history)
- Effective schema inheritance via category hierarchy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.exceptions import BusinessRuleException, NotFoundException, ValidationException
from src.models.category_schema import CategorySchema
from src.models.enums import SchemaStatus
from src.modules.product.schema_governance import (
    MAX_NESTING_DEPTH,
    MAX_SCHEMA_SIZE_BYTES,
    SchemaGovernanceService,
)


# =========================================================================
# Schema Governance
# =========================================================================


class TestSchemaGovernanceValidation:
    """Tests for SchemaGovernanceService.validate_schema."""

    def setup_method(self) -> None:
        self.governance = SchemaGovernanceService()

    def test_valid_flat_schema(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "diameter_mm": {"type": "number"},
            },
            "required": ["material"],
        }
        self.governance.validate_schema(schema)

    def test_valid_nested_within_limit(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "object",
                    "properties": {
                        "outer": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "number"},
                            },
                        },
                    },
                },
            },
        }
        # 3 levels: root -> dimensions -> outer -> width properties
        self.governance.validate_schema(schema)

    def test_reject_nesting_exceeding_max_depth(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "level2": {
                            "type": "object",
                            "properties": {
                                "level3": {
                                    "type": "object",
                                    "properties": {
                                        "level4": {
                                            "type": "object",
                                            "properties": {
                                                "value": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
        with pytest.raises(ValidationException, match="nesting depth"):
            self.governance.validate_schema(schema)

    def test_reject_oversized_schema(self) -> None:
        large_properties = {}
        for i in range(5000):
            large_properties[f"field_{i}"] = {
                "type": "string",
                "description": "A" * 100,
            }
        schema = {"type": "object", "properties": large_properties}
        with pytest.raises(ValidationException, match="maximum size"):
            self.governance.validate_schema(schema)

    def test_reject_non_dict_schema(self) -> None:
        with pytest.raises(ValidationException, match="must be a JSON object"):
            self.governance.validate_schema("not a dict")  # type: ignore[arg-type]

    def test_empty_schema_is_valid(self) -> None:
        self.governance.validate_schema({})

    def test_array_items_nesting_counts(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "items_list": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nested_obj": {
                                "type": "object",
                                "properties": {
                                    "deep_obj": {
                                        "type": "object",
                                        "properties": {
                                            "too_deep": {
                                                "type": "object",
                                                "properties": {
                                                    "value": {"type": "string"},
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
        with pytest.raises(ValidationException, match="nesting depth"):
            self.governance.validate_schema(schema)


class TestSchemaGovernanceBreakingChanges:
    """Tests for SchemaGovernanceService.detect_breaking_changes."""

    def setup_method(self) -> None:
        self.governance = SchemaGovernanceService()

    def test_no_breaking_changes_when_adding_fields(self) -> None:
        old_schema = {
            "type": "object",
            "properties": {"material": {"type": "string"}},
            "required": ["material"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "color": {"type": "string"},
            },
            "required": ["material"],
        }
        changes = self.governance.detect_breaking_changes(old_schema, new_schema)
        assert changes == []

    def test_detect_removed_required_field(self) -> None:
        old_schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "grade": {"type": "string"},
            },
            "required": ["material", "grade"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
            },
            "required": ["material"],
        }
        changes = self.governance.detect_breaking_changes(old_schema, new_schema)
        assert len(changes) == 1
        assert changes[0]["field"] == "grade"
        assert "removed" in changes[0]["reason"].lower()

    def test_detect_type_change(self) -> None:
        old_schema = {
            "type": "object",
            "properties": {"diameter": {"type": "number"}},
        }
        new_schema = {
            "type": "object",
            "properties": {"diameter": {"type": "string"}},
        }
        changes = self.governance.detect_breaking_changes(old_schema, new_schema)
        assert len(changes) == 1
        assert changes[0]["field"] == "diameter"
        assert "number" in changes[0]["reason"]
        assert "string" in changes[0]["reason"]

    def test_detect_nested_breaking_change(self) -> None:
        old_schema = {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "number"},
                    },
                    "required": ["width"],
                },
            },
        }
        new_schema = {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "object",
                    "properties": {},
                },
            },
        }
        changes = self.governance.detect_breaking_changes(old_schema, new_schema)
        assert len(changes) == 1
        assert changes[0]["field"] == "dimensions.width"

    def test_no_old_schema_returns_empty(self) -> None:
        new_schema = {"type": "object", "properties": {"x": {"type": "string"}}}
        changes = self.governance.detect_breaking_changes(None, new_schema)
        assert changes == []

    def test_removing_optional_field_not_breaking(self) -> None:
        old_schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "color": {"type": "string"},
            },
            "required": ["material"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
            },
            "required": ["material"],
        }
        changes = self.governance.detect_breaking_changes(old_schema, new_schema)
        assert changes == []


# =========================================================================
# Schema Registry (unit-tested with mocked DB session)
# =========================================================================


class TestSchemaRegistryService:
    """Tests for SchemaRegistryService using a mocked AsyncSession."""

    def _make_schema(
        self,
        category_id: uuid.UUID,
        version: int = 1,
        status: SchemaStatus = SchemaStatus.DRAFT,
        schema_json: dict | None = None,
    ) -> CategorySchema:
        schema = CategorySchema(
            id=uuid.uuid4(),
            category_id=category_id,
            version=version,
            schema_json=schema_json or {"type": "object", "properties": {}},
            status=status,
            created_by=None,
            activated_at=None,
        )
        schema.created_at = datetime.now(timezone.utc)
        schema.updated_at = datetime.now(timezone.utc)
        return schema

    @pytest.mark.asyncio
    async def test_register_schema_first_version(self) -> None:
        from src.modules.product.schema_registry import SchemaRegistryService

        category_id = uuid.uuid4()
        session = AsyncMock()

        # Mock: no active schema
        active_result = MagicMock()
        active_result.scalar_one_or_none.return_value = None

        # Mock: max version = 0
        max_version_result = MagicMock()
        max_version_result.scalar.return_value = 0

        session.execute = AsyncMock(side_effect=[active_result, max_version_result])

        registry = SchemaRegistryService(session)
        schema_json = {
            "type": "object",
            "properties": {"material": {"type": "string"}},
        }

        schema = await registry.register_schema(category_id, schema_json, uuid.uuid4())

        assert schema.version == 1
        assert schema.status == SchemaStatus.DRAFT
        assert schema.schema_json == schema_json
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_schema_rejects_breaking_changes(self) -> None:
        from src.modules.product.schema_registry import SchemaRegistryService

        category_id = uuid.uuid4()
        session = AsyncMock()

        # Mock: active schema has a required field
        active_schema = self._make_schema(
            category_id,
            version=1,
            status=SchemaStatus.ACTIVE,
            schema_json={
                "type": "object",
                "properties": {"material": {"type": "string"}},
                "required": ["material"],
            },
        )
        active_result = MagicMock()
        active_result.scalar_one_or_none.return_value = active_schema
        session.execute = AsyncMock(return_value=active_result)

        registry = SchemaRegistryService(session)

        # New schema removes the required "material" field
        new_schema_json = {
            "type": "object",
            "properties": {"color": {"type": "string"}},
        }

        with pytest.raises(BusinessRuleException, match="breaking changes"):
            await registry.register_schema(category_id, new_schema_json)

    @pytest.mark.asyncio
    async def test_activate_schema(self) -> None:
        from src.modules.product.schema_registry import SchemaRegistryService

        category_id = uuid.uuid4()
        schema_id = uuid.uuid4()
        session = AsyncMock()

        draft_schema = self._make_schema(category_id, version=2, status=SchemaStatus.DRAFT)
        draft_schema.id = schema_id
        session.get = AsyncMock(return_value=draft_schema)
        session.execute = AsyncMock()

        registry = SchemaRegistryService(session)
        result = await registry.activate_schema(schema_id)

        assert result.status == SchemaStatus.ACTIVE
        assert result.activated_at is not None
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_activate_non_draft_raises(self) -> None:
        from src.modules.product.schema_registry import SchemaRegistryService

        schema_id = uuid.uuid4()
        session = AsyncMock()

        active_schema = self._make_schema(uuid.uuid4(), version=1, status=SchemaStatus.ACTIVE)
        active_schema.id = schema_id
        session.get = AsyncMock(return_value=active_schema)

        registry = SchemaRegistryService(session)

        with pytest.raises(BusinessRuleException, match="must be DRAFT"):
            await registry.activate_schema(schema_id)

    @pytest.mark.asyncio
    async def test_activate_nonexistent_raises(self) -> None:
        from src.modules.product.schema_registry import SchemaRegistryService

        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        registry = SchemaRegistryService(session)

        with pytest.raises(NotFoundException):
            await registry.activate_schema(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_list_schema_history(self) -> None:
        from src.modules.product.schema_registry import SchemaRegistryService

        category_id = uuid.uuid4()
        session = AsyncMock()

        schemas = [
            self._make_schema(category_id, version=2, status=SchemaStatus.ACTIVE),
            self._make_schema(category_id, version=1, status=SchemaStatus.DEPRECATED),
        ]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = schemas
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        registry = SchemaRegistryService(session)
        history = await registry.list_schema_history(category_id)

        assert len(history) == 2
        assert history[0].version == 2
        assert history[1].version == 1


# =========================================================================
# Schema-Aware Validation
# =========================================================================


class TestSchemaAwareValidation:
    """Tests for validate_specifications_with_schema in validators.py."""

    @pytest.mark.asyncio
    async def test_validation_passes_with_no_schema(self) -> None:
        from src.modules.product.validators import validate_specifications_with_schema

        session = AsyncMock()
        with patch(
            "src.modules.product.category_service.CategoryService"
        ) as mock_cat_svc_cls:
            mock_instance = MagicMock()
            mock_instance.get_effective_schema = AsyncMock(return_value=None)
            mock_cat_svc_cls.return_value = mock_instance

            result = await validate_specifications_with_schema(
                specs={"anything": "goes"},
                category_id=uuid.uuid4(),
                session=session,
            )

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["schema_source"] is None

    @pytest.mark.asyncio
    async def test_validation_passes_with_matching_schema(self) -> None:
        from src.modules.product.validators import validate_specifications_with_schema

        effective_schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "diameter_mm": {"type": "number"},
            },
            "required": ["material"],
        }

        session = AsyncMock()
        with patch(
            "src.modules.product.category_service.CategoryService"
        ) as mock_cat_svc_cls:
            mock_instance = MagicMock()
            mock_instance.get_effective_schema = AsyncMock(return_value=effective_schema)
            mock_cat_svc_cls.return_value = mock_instance

            result = await validate_specifications_with_schema(
                specs={"material": "steel", "diameter_mm": 25.4},
                category_id=uuid.uuid4(),
                session=session,
            )

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["schema_source"] == "inherited"

    @pytest.mark.asyncio
    async def test_validation_fails_with_invalid_specs(self) -> None:
        from src.modules.product.validators import validate_specifications_with_schema

        effective_schema = {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
            },
            "required": ["material"],
        }

        session = AsyncMock()
        with patch(
            "src.modules.product.category_service.CategoryService"
        ) as mock_cat_svc_cls:
            mock_instance = MagicMock()
            mock_instance.get_effective_schema = AsyncMock(return_value=effective_schema)
            mock_cat_svc_cls.return_value = mock_instance

            result = await validate_specifications_with_schema(
                specs={"color": "red"},  # missing required "material"
                category_id=uuid.uuid4(),
                session=session,
            )

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["schema_source"] == "inherited"


# =========================================================================
# Effective Schema Inheritance (mocked DB)
# =========================================================================


class TestEffectiveSchemaInheritance:
    """Tests for CategoryService.get_effective_schema with mocked session."""

    @pytest.mark.asyncio
    async def test_returns_own_active_schema(self) -> None:
        from src.modules.product.category_service import CategoryService

        category_id = uuid.uuid4()
        expected_schema = {"type": "object", "properties": {"x": {"type": "string"}}}

        # Build mock session
        session = AsyncMock()

        # _get_category_or_404 succeeds
        mock_category = MagicMock()
        session.get = AsyncMock(return_value=mock_category)

        # Ancestor query: self only
        ancestor_result = MagicMock()
        ancestor_result.all.return_value = [(category_id,)]

        # Schema query: found
        active_schema = MagicMock()
        active_schema.schema_json = expected_schema
        schema_result = MagicMock()
        schema_result.scalar_one_or_none.return_value = active_schema

        session.execute = AsyncMock(side_effect=[ancestor_result, schema_result])

        svc = CategoryService(session)
        result = await svc.get_effective_schema(category_id)

        assert result == expected_schema

    @pytest.mark.asyncio
    async def test_inherits_from_parent_when_self_has_no_schema(self) -> None:
        from src.modules.product.category_service import CategoryService

        child_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        parent_schema = {"type": "object", "properties": {"inherited": {"type": "boolean"}}}

        session = AsyncMock()

        # _get_category_or_404
        mock_category = MagicMock()
        session.get = AsyncMock(return_value=mock_category)

        # Ancestors: self, then parent
        ancestor_result = MagicMock()
        ancestor_result.all.return_value = [(child_id,), (parent_id,)]

        # Schema for child: none
        child_schema_result = MagicMock()
        child_schema_result.scalar_one_or_none.return_value = None

        # Schema for parent: found
        parent_schema_obj = MagicMock()
        parent_schema_obj.schema_json = parent_schema
        parent_schema_result = MagicMock()
        parent_schema_result.scalar_one_or_none.return_value = parent_schema_obj

        session.execute = AsyncMock(
            side_effect=[ancestor_result, child_schema_result, parent_schema_result]
        )

        svc = CategoryService(session)
        result = await svc.get_effective_schema(child_id)

        assert result == parent_schema

    @pytest.mark.asyncio
    async def test_returns_none_when_no_ancestor_has_schema(self) -> None:
        from src.modules.product.category_service import CategoryService

        category_id = uuid.uuid4()
        session = AsyncMock()

        mock_category = MagicMock()
        session.get = AsyncMock(return_value=mock_category)

        ancestor_result = MagicMock()
        ancestor_result.all.return_value = [(category_id,)]

        schema_result = MagicMock()
        schema_result.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[ancestor_result, schema_result])

        svc = CategoryService(session)
        result = await svc.get_effective_schema(category_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_raises_not_found_for_invalid_category(self) -> None:
        from src.modules.product.category_service import CategoryService

        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        svc = CategoryService(session)

        with pytest.raises(NotFoundException):
            await svc.get_effective_schema(uuid.uuid4())


# =========================================================================
# Nesting Depth Helper (edge cases)
# =========================================================================


class TestNestingDepthMeasurement:
    """Edge-case tests for _measure_nesting_depth."""

    def setup_method(self) -> None:
        self.governance = SchemaGovernanceService()

    def test_flat_schema_depth_zero(self) -> None:
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
        }
        assert self.governance._measure_nesting_depth(schema) == 0

    def test_one_level_nesting(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"y": {"type": "number"}},
                },
            },
        }
        assert self.governance._measure_nesting_depth(schema) == 1

    def test_exactly_max_depth(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "a": {
                    "type": "object",
                    "properties": {
                        "b": {
                            "type": "object",
                            "properties": {
                                "c": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }
        depth = self.governance._measure_nesting_depth(schema)
        assert depth == 2

    def test_depth_3_is_at_limit(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "a": {
                    "type": "object",
                    "properties": {
                        "b": {
                            "type": "object",
                            "properties": {
                                "c": {
                                    "type": "object",
                                    "properties": {"d": {"type": "string"}},
                                },
                            },
                        },
                    },
                },
            },
        }
        depth = self.governance._measure_nesting_depth(schema)
        assert depth == 3
        # This is exactly at limit, should pass governance validation
        self.governance.validate_schema(schema)
