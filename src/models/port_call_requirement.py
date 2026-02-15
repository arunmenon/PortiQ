"""PortCallRequirement model — demand planning items tied to a port call."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import RequirementCategory, RequirementPriority, RequirementStatus

if TYPE_CHECKING:
    from src.models.port_call import PortCall
    from src.models.product import Product
    from src.models.rfq import Rfq


class PortCallRequirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "port_call_requirements"

    port_call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("port_calls.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Product reference (optional — can be free-text description)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
    )
    impa_code: Mapped[str | None] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Quantity
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False)

    # Classification
    category: Mapped[RequirementCategory] = mapped_column(
        SQLAlchemyEnum(
            RequirementCategory,
            name="requirementcategory",
            create_type=False,
        ),
        nullable=False,
        server_default="OTHER",
    )
    priority: Mapped[RequirementPriority] = mapped_column(
        SQLAlchemyEnum(
            RequirementPriority,
            name="requirementpriority",
            create_type=False,
        ),
        nullable=False,
        server_default="MEDIUM",
    )
    status: Mapped[RequirementStatus] = mapped_column(
        SQLAlchemyEnum(
            RequirementStatus,
            name="requirementstatus",
            create_type=False,
        ),
        nullable=False,
        server_default="DRAFT",
    )

    # Optional link to the RFQ created from this requirement
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
    )

    # Specifications and notes
    specifications: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    port_call: Mapped[PortCall] = relationship("PortCall", lazy="noload")
    product: Mapped[Product | None] = relationship("Product", lazy="noload")
    rfq: Mapped[Rfq | None] = relationship("Rfq", lazy="noload")

    __table_args__ = (
        Index("ix_port_call_requirements_port_call", "port_call_id"),
        Index("ix_port_call_requirements_org", "organization_id"),
        Index("ix_port_call_requirements_status", "status"),
        Index("ix_port_call_requirements_rfq", "rfq_id"),
    )
