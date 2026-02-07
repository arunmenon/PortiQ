from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import OrganizationStatus, OrganizationType

if TYPE_CHECKING:
    from src.models.organization_membership import OrganizationMembership
    from src.models.supplier_product import SupplierProduct
    from src.models.user import User


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[OrganizationType] = mapped_column(nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    # New multi-tenancy fields
    legal_name: Mapped[str | None] = mapped_column(String(255))
    slug: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[OrganizationStatus] = mapped_column(server_default="ACTIVE", nullable=False)
    primary_email: Mapped[str | None] = mapped_column(String(255))
    primary_phone: Mapped[str | None] = mapped_column(String(20))
    website: Mapped[str | None] = mapped_column(String(255))
    settings: Mapped[dict | None] = mapped_column(JSONB, server_default="{}")

    # Relationships
    users: Mapped[list[User]] = relationship(
        "User", foreign_keys="User.organization_id", back_populates="organization", cascade="all, delete-orphan"
    )
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    supplier_products: Mapped[list[SupplierProduct]] = relationship("SupplierProduct", back_populates="supplier")

    __table_args__ = (
        Index("ix_organizations_slug", "slug", unique=True, postgresql_where=text("slug IS NOT NULL")),
    )
