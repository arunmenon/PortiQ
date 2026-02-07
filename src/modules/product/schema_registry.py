"""Schema registry — versioned schema management for category attribute schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BusinessRuleException, ConflictException, NotFoundException
from src.models.category_schema import CategorySchema
from src.models.enums import SchemaStatus
from src.modules.product.schema_governance import SchemaGovernanceService


class SchemaRegistryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._governance = SchemaGovernanceService()

    async def get_active_schema(self, category_id: uuid.UUID) -> CategorySchema | None:
        """Return the current ACTIVE schema for a category, or None."""
        stmt = (
            select(CategorySchema)
            .where(
                CategorySchema.category_id == category_id,
                CategorySchema.status == SchemaStatus.ACTIVE,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def register_schema(
        self,
        category_id: uuid.UUID,
        schema_json: dict,
        created_by_id: uuid.UUID | None = None,
    ) -> CategorySchema:
        """Register a new DRAFT schema version for a category.

        Auto-increments the version number, validates governance rules,
        and detects breaking changes against the current active schema.
        Returns the newly created CategorySchema.
        """
        # Validate governance rules (nesting depth, size)
        self._governance.validate_schema(schema_json)

        # Detect breaking changes against current active schema
        active_schema = await self.get_active_schema(category_id)
        if active_schema is not None:
            breaking_changes = self._governance.detect_breaking_changes(
                active_schema.schema_json, schema_json
            )
            if breaking_changes:
                raise BusinessRuleException(
                    message="New schema introduces breaking changes",
                    details=breaking_changes,
                )

        # Determine next version number
        max_version_stmt = (
            select(func.coalesce(func.max(CategorySchema.version), 0))
            .where(CategorySchema.category_id == category_id)
        )
        result = await self._session.execute(max_version_stmt)
        next_version = result.scalar() + 1

        schema = CategorySchema(
            category_id=category_id,
            version=next_version,
            schema_json=schema_json,
            status=SchemaStatus.DRAFT,
            created_by=created_by_id,
        )
        self._session.add(schema)
        await self._session.flush()
        return schema

    async def activate_schema(self, schema_id: uuid.UUID) -> CategorySchema:
        """Transition a DRAFT schema to ACTIVE.

        Deprecates the previously ACTIVE schema for the same category and
        sets the activated_at timestamp.
        """
        schema = await self._session.get(CategorySchema, schema_id)
        if schema is None:
            raise NotFoundException(f"CategorySchema {schema_id} not found")

        if schema.status != SchemaStatus.DRAFT:
            raise BusinessRuleException(
                f"Cannot activate schema in status '{schema.status.value}'; must be DRAFT"
            )

        # Deprecate previous ACTIVE schema for this category
        await self._session.execute(
            update(CategorySchema)
            .where(
                CategorySchema.category_id == schema.category_id,
                CategorySchema.status == SchemaStatus.ACTIVE,
            )
            .values(status=SchemaStatus.DEPRECATED)
        )

        schema.status = SchemaStatus.ACTIVE
        schema.activated_at = datetime.now(timezone.utc)

        await self._session.flush()
        return schema

    async def list_schema_history(self, category_id: uuid.UUID) -> list[CategorySchema]:
        """Return all schema versions for a category, ordered by version descending."""
        stmt = (
            select(CategorySchema)
            .where(CategorySchema.category_id == category_id)
            .order_by(CategorySchema.version.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
