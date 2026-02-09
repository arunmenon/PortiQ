"""Tests for TcoConfigService — CRUD, validation, and template retrieval."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import ConflictException, NotFoundException, ValidationException
from src.models.enums import TcoTemplateType
from src.models.tco_configuration import TcoConfiguration
from src.modules.tco.config_service import TcoConfigService
from src.modules.tco.schemas import TcoConfigCreate, TcoConfigUpdate


def _make_config(
    org_id: uuid.UUID | None = None,
    name: str = "Test Config",
    is_default: bool = False,
    **kwargs,
) -> TcoConfiguration:
    """Helper to build a TcoConfiguration with sensible defaults."""
    config = TcoConfiguration(
        id=uuid.uuid4(),
        organization_id=org_id or uuid.uuid4(),
        name=name,
        template_type=TcoTemplateType.COMMODITY,
        weight_unit_price=Decimal("0.4000"),
        weight_shipping=Decimal("0.1500"),
        weight_lead_time=Decimal("0.1500"),
        weight_quality=Decimal("0.1500"),
        weight_payment_terms=Decimal("0.1000"),
        weight_supplier_rating=Decimal("0.0500"),
        is_default=is_default,
        is_active=True,
        **kwargs,
    )
    return config


def _mock_scalar_one_or_none(value):
    """Create a mock result whose .scalar_one_or_none() returns value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mock_scalars_all(values):
    """Create a mock result whose .scalars().all() returns values."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


class TestTcoConfigServiceCreate:
    """Tests for create_config."""

    @pytest.mark.asyncio
    async def test_create_config_success(self) -> None:
        db = AsyncMock()
        org_id = uuid.uuid4()

        # First call checks name uniqueness (no conflict)
        db.execute.return_value = _mock_scalar_one_or_none(None)

        service = TcoConfigService(db)
        data = TcoConfigCreate(
            name="My Config",
            template_type=TcoTemplateType.COMMODITY,
        )
        result = await service.create_config(org_id, data)

        assert result.name == "My Config"
        assert result.organization_id == org_id
        assert result.template_type == TcoTemplateType.COMMODITY
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_config_duplicate_name_raises(self) -> None:
        db = AsyncMock()
        org_id = uuid.uuid4()
        existing = _make_config(org_id=org_id, name="Existing")
        db.execute.return_value = _mock_scalar_one_or_none(existing)

        service = TcoConfigService(db)
        data = TcoConfigCreate(name="Existing")

        with pytest.raises(ConflictException, match="already exists"):
            await service.create_config(org_id, data)


class TestTcoConfigServiceList:
    """Tests for list_configs."""

    @pytest.mark.asyncio
    async def test_list_configs_returns_all(self) -> None:
        db = AsyncMock()
        org_id = uuid.uuid4()
        configs = [
            _make_config(org_id=org_id, name="A"),
            _make_config(org_id=org_id, name="B"),
        ]
        db.execute.return_value = _mock_scalars_all(configs)

        service = TcoConfigService(db)
        result = await service.list_configs(org_id)

        assert len(result) == 2


class TestTcoConfigServiceGet:
    """Tests for get_config."""

    @pytest.mark.asyncio
    async def test_get_config_found(self) -> None:
        db = AsyncMock()
        config = _make_config()
        db.execute.return_value = _mock_scalar_one_or_none(config)

        service = TcoConfigService(db)
        result = await service.get_config(config.id)

        assert result.id == config.id

    @pytest.mark.asyncio
    async def test_get_config_not_found(self) -> None:
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(None)

        service = TcoConfigService(db)
        with pytest.raises(NotFoundException):
            await service.get_config(uuid.uuid4())


class TestTcoConfigServiceUpdate:
    """Tests for update_config."""

    @pytest.mark.asyncio
    async def test_update_config_name(self) -> None:
        db = AsyncMock()
        org_id = uuid.uuid4()
        config = _make_config(org_id=org_id, name="Old Name")

        # get_config call returns the config, then name check returns no conflict
        db.execute.side_effect = [
            _mock_scalar_one_or_none(config),
            _mock_scalar_one_or_none(None),
        ]

        service = TcoConfigService(db)
        data = TcoConfigUpdate(name="New Name")
        result = await service.update_config(config.id, org_id, data)

        assert result.name == "New Name"
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_config_invalid_weights_raises(self) -> None:
        db = AsyncMock()
        org_id = uuid.uuid4()
        config = _make_config(org_id=org_id)
        db.execute.return_value = _mock_scalar_one_or_none(config)

        service = TcoConfigService(db)
        data = TcoConfigUpdate(weight_unit_price=Decimal("0.9999"))

        with pytest.raises(ValidationException, match="Weights must sum to 1.0"):
            await service.update_config(config.id, org_id, data)


class TestTcoConfigServiceDefault:
    """Tests for get_default_config."""

    @pytest.mark.asyncio
    async def test_get_default_config_found(self) -> None:
        db = AsyncMock()
        org_id = uuid.uuid4()
        config = _make_config(org_id=org_id, is_default=True)
        db.execute.return_value = _mock_scalar_one_or_none(config)

        service = TcoConfigService(db)
        result = await service.get_default_config(org_id)

        assert result is not None
        assert result.is_default is True

    @pytest.mark.asyncio
    async def test_get_default_config_none(self) -> None:
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(None)

        service = TcoConfigService(db)
        result = await service.get_default_config(uuid.uuid4())

        assert result is None


class TestTcoConfigServiceTemplates:
    """Tests for get_templates."""

    def test_get_templates_returns_five(self) -> None:
        db = AsyncMock()
        service = TcoConfigService(db)
        templates = service.get_templates()

        assert len(templates) == 5
        template_types = {t.template_type for t in templates}
        assert TcoTemplateType.COMMODITY in template_types
        assert TcoTemplateType.TECHNICAL in template_types
        assert TcoTemplateType.URGENT in template_types
        assert TcoTemplateType.STRATEGIC in template_types
        assert TcoTemplateType.QUALITY_CRITICAL in template_types

        # Each template weights should sum to 1.0
        for t in templates:
            total = (
                t.weight_unit_price
                + t.weight_shipping
                + t.weight_lead_time
                + t.weight_quality
                + t.weight_payment_terms
                + t.weight_supplier_rating
            )
            assert abs(total - Decimal("1.0")) < Decimal("0.001"), (
                f"Template {t.template_type} weights sum to {total}"
            )
