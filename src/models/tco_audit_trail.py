"""TCO Audit Trail model — append-only log of TCO actions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.rfq import Rfq
    from src.models.tco_calculation import TcoCalculation
    from src.models.user import User


class TcoAuditTrail(UUIDPrimaryKeyMixin, Base):
    """Append-only audit trail for TCO operations. No updated_at — immutable rows."""

    __tablename__ = "tco_audit_trail"

    calculation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tco_calculations.id", ondelete="CASCADE"),
        nullable=False,
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    calculation: Mapped[TcoCalculation] = relationship("TcoCalculation", lazy="noload")
    rfq: Mapped[Rfq] = relationship("Rfq", lazy="noload")
    actor: Mapped[User] = relationship("User", lazy="noload")
    actor_organization: Mapped[Organization] = relationship(
        "Organization", lazy="noload"
    )

    __table_args__ = (
        Index("ix_tco_audit_trail_calculation_id", "calculation_id"),
        Index("ix_tco_audit_trail_rfq_id", "rfq_id"),
        Index("ix_tco_audit_trail_actor_id", "actor_id"),
        Index("ix_tco_audit_trail_created_at", "created_at"),
    )
