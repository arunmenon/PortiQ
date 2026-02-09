"""TcoConfigService — CRUD for TCO weight configurations."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictException, NotFoundException, ValidationException
from src.models.tco_configuration import TcoConfiguration
from src.modules.tco.constants import INDUSTRY_TEMPLATES
from src.modules.tco.schemas import TcoConfigCreate, TcoConfigUpdate, TcoTemplateResponse

logger = logging.getLogger(__name__)


class TcoConfigService:
    """Service layer for TCO configuration management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_config(
        self,
        organization_id: uuid.UUID,
        data: TcoConfigCreate,
    ) -> TcoConfiguration:
        """Create a new TCO configuration for an organization.

        Validates:
        - Weights sum to 1.0 (handled by schema validator + DB CHECK constraint)
        - Name is unique within organization
        """
        # Check name uniqueness within org
        existing = await self.db.execute(
            select(TcoConfiguration).where(
                TcoConfiguration.organization_id == organization_id,
                TcoConfiguration.name == data.name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                f"Configuration with name '{data.name}' already exists for this organization"
            )

        # If this is the default, unset any existing default
        if data.is_default:
            await self._clear_org_defaults(organization_id)

        config = TcoConfiguration(
            organization_id=organization_id,
            name=data.name,
            template_type=data.template_type,
            weight_unit_price=data.weight_unit_price,
            weight_shipping=data.weight_shipping,
            weight_lead_time=data.weight_lead_time,
            weight_quality=data.weight_quality,
            weight_payment_terms=data.weight_payment_terms,
            weight_supplier_rating=data.weight_supplier_rating,
            is_default=data.is_default,
        )
        self.db.add(config)
        await self.db.flush()
        logger.info(
            "Created TCO config %s (%s) for org %s",
            config.id,
            data.name,
            organization_id,
        )
        return config

    async def list_configs(
        self,
        organization_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[TcoConfiguration]:
        """List all TCO configurations for an organization."""
        stmt = (
            select(TcoConfiguration)
            .where(TcoConfiguration.organization_id == organization_id)
            .order_by(TcoConfiguration.created_at.desc())
        )
        if active_only:
            stmt = stmt.where(TcoConfiguration.is_active.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_config(self, config_id: uuid.UUID) -> TcoConfiguration:
        """Get a single TCO configuration by ID."""
        result = await self.db.execute(
            select(TcoConfiguration).where(TcoConfiguration.id == config_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            raise NotFoundException(f"TCO configuration {config_id} not found")
        return config

    async def update_config(
        self,
        config_id: uuid.UUID,
        organization_id: uuid.UUID,
        data: TcoConfigUpdate,
    ) -> TcoConfiguration:
        """Update a TCO configuration. Validates weights if any weight field is changed."""
        config = await self.get_config(config_id)

        # Check ownership
        if config.organization_id != organization_id:
            raise NotFoundException(f"TCO configuration {config_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return config

        # If any weight is being updated, validate all weights sum to 1.0
        weight_fields = {
            "weight_unit_price",
            "weight_shipping",
            "weight_lead_time",
            "weight_quality",
            "weight_payment_terms",
            "weight_supplier_rating",
        }
        if weight_fields & update_data.keys():
            # Merge current and new values
            merged = {
                f: update_data.get(f, getattr(config, f))
                for f in weight_fields
            }
            total = sum(Decimal(str(v)) for v in merged.values())
            if abs(total - Decimal("1.0")) >= Decimal("0.001"):
                raise ValidationException(
                    f"Weights must sum to 1.0 (got {total})"
                )

        # Check name uniqueness if name is changing
        if "name" in update_data and update_data["name"] != config.name:
            existing = await self.db.execute(
                select(TcoConfiguration).where(
                    TcoConfiguration.organization_id == organization_id,
                    TcoConfiguration.name == update_data["name"],
                    TcoConfiguration.id != config_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictException(
                    f"Configuration with name '{update_data['name']}' already exists"
                )

        # Handle default flag
        if update_data.get("is_default") is True and not config.is_default:
            await self._clear_org_defaults(organization_id)

        for field, value in update_data.items():
            setattr(config, field, value)

        await self.db.flush()
        logger.info("Updated TCO config %s", config_id)
        return config

    async def get_default_config(
        self,
        organization_id: uuid.UUID,
    ) -> TcoConfiguration | None:
        """Get the default TCO configuration for an organization, or None."""
        result = await self.db.execute(
            select(TcoConfiguration).where(
                TcoConfiguration.organization_id == organization_id,
                TcoConfiguration.is_default.is_(True),
                TcoConfiguration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    def get_templates(self) -> list[TcoTemplateResponse]:
        """Return built-in industry templates from constants."""
        templates = []
        for template_type, weights in INDUSTRY_TEMPLATES.items():
            templates.append(
                TcoTemplateResponse(
                    template_type=template_type,
                    **weights,
                )
            )
        return templates

    async def _clear_org_defaults(self, organization_id: uuid.UUID) -> None:
        """Unset is_default on all configs for an organization."""
        await self.db.execute(
            update(TcoConfiguration)
            .where(
                TcoConfiguration.organization_id == organization_id,
                TcoConfiguration.is_default.is_(True),
            )
            .values(is_default=False)
        )
