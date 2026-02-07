from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import MembershipStatus

if TYPE_CHECKING:
    from src.models.organization import Organization
    from src.models.role import Role
    from src.models.user import User


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        nullable=False, server_default="INVITED"
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    job_title: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id], back_populates="memberships")
    organization: Mapped[Organization] = relationship("Organization", back_populates="memberships")
    role: Mapped[Role] = relationship("Role")
    inviter: Mapped[User | None] = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
        Index("ix_memberships_user_id", "user_id"),
        Index("ix_memberships_org_id", "organization_id"),
        Index("ix_memberships_status", "status"),
        Index("ix_memberships_user_org_status", "user_id", "organization_id", "status"),
    )
