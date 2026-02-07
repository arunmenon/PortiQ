from __future__ import annotations

from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import OrganizationType


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    organization_type: Mapped[OrganizationType] = mapped_column(nullable=False)
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    is_system: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "organization_type", name="uq_roles_name_org_type"),
        Index("ix_roles_organization_type", "organization_type"),
    )
