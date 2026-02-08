from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import InvitationStatus

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.rfq import Rfq
    from src.models.user import User


class RfqInvitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rfq_invitations"

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[InvitationStatus] = mapped_column(
        nullable=False, server_default="PENDING"
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decline_reason: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    rfq: Mapped[Rfq] = relationship("Rfq", back_populates="invitations", lazy="noload")
    supplier_organization: Mapped[Organization] = relationship(
        "Organization", lazy="noload"
    )
    inviter: Mapped[User] = relationship("User", lazy="noload")

    __table_args__ = (
        UniqueConstraint(
            "rfq_id", "supplier_organization_id",
            name="uq_rfq_invitations_rfq_supplier",
        ),
        Index("ix_rfq_invitations_rfq_id", "rfq_id"),
        Index("ix_rfq_invitations_supplier_org_id", "supplier_organization_id"),
    )
