"""TCO Configuration model — per-organization weighting profiles for TCO scoring."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import TcoTemplateType

if TYPE_CHECKING:
    from src.models.organization import Organization


class TcoConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tco_configurations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[TcoTemplateType] = mapped_column(
        nullable=False, server_default="COMMODITY"
    )
    weight_unit_price: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.4000"
    )
    weight_shipping: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.1500"
    )
    weight_lead_time: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.1500"
    )
    weight_quality: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.1500"
    )
    weight_payment_terms: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.1000"
    )
    weight_supplier_rating: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.0500"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    # Relationships
    organization: Mapped[Organization] = relationship("Organization", lazy="noload")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", name="uq_tco_configurations_org_name"
        ),
        CheckConstraint(
            "ABS("
            "weight_unit_price + weight_shipping + weight_lead_time "
            "+ weight_quality + weight_payment_terms + weight_supplier_rating "
            "- 1.0) < 0.001",
            name="ck_tco_configurations_weights_sum",
        ),
        Index("ix_tco_configurations_organization_id", "organization_id"),
        Index("ix_tco_configurations_is_default", "is_default"),
    )
