from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import UserRole, UserStatus

if TYPE_CHECKING:
    from src.models.audit import ProductAuditLog
    from src.models.organization import Organization
    from src.models.organization_membership import OrganizationMembership


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[UserRole] = mapped_column(server_default="MEMBER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    # New multi-tenancy fields
    phone: Mapped[str | None] = mapped_column(String(20))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[UserStatus] = mapped_column(server_default="ACTIVE", nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    default_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locale: Mapped[str] = mapped_column(String(10), server_default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), server_default="UTC", nullable=False)

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization", foreign_keys=[organization_id], back_populates="users"
    )
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership",
        foreign_keys="OrganizationMembership.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[ProductAuditLog]] = relationship("ProductAuditLog", back_populates="changed_by")
    verified_mappings: Mapped[list] = relationship("ImpaCategoryMapping", back_populates="verified_by")

    __table_args__ = (
        Index("idx_users_organization_id", "organization_id"),
    )
