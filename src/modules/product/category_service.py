"""Category service — hierarchy management, IMPA/ISSA mapping resolution."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import ConflictException, NotFoundException, ValidationException
from src.models.category import Category, CategoryClosure
from src.models.category_schema import CategorySchema
from src.models.enums import CategoryStatus, SchemaStatus
from src.models.impa_mapping import ImpaCategoryMapping, IssaCategoryMapping
from src.models.product import Product
from src.modules.product.schemas import (
    CategoryBreadcrumb,
    CategoryCreate,
    CategoryMoveRequest,
    CategoryTreeNode,
    CategoryUpdate,
    ImpaMappingCreate,
    IssaMappingCreate,
)


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_category(self, data: CategoryCreate) -> Category:
        """Create a category and populate the closure table entries."""
        # Check for duplicate code
        existing = await self._session.execute(
            select(Category.id).where(Category.code == data.code)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(f"Category code '{data.code}' already exists")

        # Resolve parent
        parent: Category | None = None
        if data.parent_id is not None:
            parent = await self._get_category_or_404(data.parent_id)

        path = f"{parent.path}.{data.code}" if parent else data.code
        level = (parent.level + 1) if parent else 0

        category = Category(
            code=data.code,
            impa_prefix=data.impa_prefix,
            name=data.name,
            description=data.description,
            path=path,
            level=level,
            attribute_schema=data.attribute_schema,
            ihm_category=data.ihm_category,
            icon=data.icon,
            display_order=data.display_order,
            status=CategoryStatus.ACTIVE,
        )
        self._session.add(category)
        await self._session.flush()

        # Populate closure table: self-reference + all ancestors
        self._session.add(CategoryClosure(
            ancestor_id=category.id, descendant_id=category.id, depth=0,
        ))
        if parent is not None:
            # Copy all ancestor entries for the parent, incrementing depth by 1
            ancestor_stmt = select(CategoryClosure).where(
                CategoryClosure.descendant_id == parent.id
            )
            result = await self._session.execute(ancestor_stmt)
            for closure in result.scalars().all():
                self._session.add(CategoryClosure(
                    ancestor_id=closure.ancestor_id,
                    descendant_id=category.id,
                    depth=closure.depth + 1,
                ))

        await self._session.flush()
        return category

    async def get_category(self, category_id: uuid.UUID) -> Category:
        return await self._get_category_or_404(category_id)

    async def update_category(self, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
        category = await self._get_category_or_404(category_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        await self._session.flush()
        return category

    # ------------------------------------------------------------------
    # Hierarchy
    # ------------------------------------------------------------------

    async def get_tree(
        self,
        root_id: uuid.UUID | None = None,
        max_depth: int | None = None,
    ) -> list[CategoryTreeNode]:
        """Return a flat list of categories with hierarchy info for client tree-building.

        If *root_id* is given, returns the subtree rooted at that category.
        """
        # Subquery: direct children count per category
        children_sub = (
            select(
                CategoryClosure.ancestor_id.label("cat_id"),
                func.count().label("children_count"),
            )
            .where(CategoryClosure.depth == 1)
            .group_by(CategoryClosure.ancestor_id)
            .subquery()
        )

        # Subquery: product count per category
        product_sub = (
            select(
                Product.category_id.label("cat_id"),
                func.count().label("product_count"),
            )
            .group_by(Product.category_id)
            .subquery()
        )

        stmt = (
            select(
                Category,
                func.coalesce(children_sub.c.children_count, 0).label("children_count"),
                func.coalesce(product_sub.c.product_count, 0).label("product_count"),
            )
            .outerjoin(children_sub, children_sub.c.cat_id == Category.id)
            .outerjoin(product_sub, product_sub.c.cat_id == Category.id)
        )

        if root_id is not None:
            descendant_ids = (
                select(CategoryClosure.descendant_id)
                .where(CategoryClosure.ancestor_id == root_id)
            )
            if max_depth is not None:
                descendant_ids = descendant_ids.where(CategoryClosure.depth <= max_depth)
            stmt = stmt.where(Category.id.in_(descendant_ids))
        else:
            if max_depth is not None:
                stmt = stmt.where(Category.level <= max_depth)

        stmt = stmt.order_by(Category.level, Category.display_order, Category.name)
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            CategoryTreeNode(
                id=cat.id,
                code=cat.code,
                name=cat.name,
                path=cat.path,
                level=cat.level,
                icon=cat.icon,
                display_order=cat.display_order,
                status=cat.status,
                children_count=children_count,
                product_count=product_count,
            )
            for cat, children_count, product_count in rows
        ]

    async def get_breadcrumbs(self, category_id: uuid.UUID) -> list[CategoryBreadcrumb]:
        """Return ancestor chain ordered from root to the given category."""
        stmt = (
            select(Category)
            .join(CategoryClosure, CategoryClosure.ancestor_id == Category.id)
            .where(CategoryClosure.descendant_id == category_id)
            .order_by(CategoryClosure.depth.desc())
        )
        result = await self._session.execute(stmt)
        categories = result.scalars().all()
        if not categories:
            raise NotFoundException(f"Category {category_id} not found")
        return [
            CategoryBreadcrumb(id=c.id, code=c.code, name=c.name, level=c.level)
            for c in categories
        ]

    async def get_children(self, category_id: uuid.UUID) -> list[Category]:
        """Direct children of the given category (depth=1 in closure table)."""
        await self._get_category_or_404(category_id)
        stmt = (
            select(Category)
            .join(CategoryClosure, CategoryClosure.descendant_id == Category.id)
            .where(
                CategoryClosure.ancestor_id == category_id,
                CategoryClosure.depth == 1,
            )
            .order_by(Category.display_order, Category.name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def move_subtree(self, category_id: uuid.UUID, new_parent_id: uuid.UUID | None) -> Category:
        """Move a category subtree to a new parent, updating paths and closure entries."""
        category = await self._get_category_or_404(category_id)

        new_parent: Category | None = None
        if new_parent_id is not None:
            new_parent = await self._get_category_or_404(new_parent_id)
            # Prevent moving under own descendant
            is_descendant = await self._session.execute(
                select(CategoryClosure.ancestor_id).where(
                    CategoryClosure.ancestor_id == category_id,
                    CategoryClosure.descendant_id == new_parent_id,
                )
            )
            if is_descendant.scalar_one_or_none() is not None:
                raise ValidationException("Cannot move a category under its own descendant")

        # Get all descendant IDs (including self)
        desc_stmt = select(CategoryClosure.descendant_id).where(
            CategoryClosure.ancestor_id == category_id
        )
        desc_result = await self._session.execute(desc_stmt)
        descendant_ids = [row[0] for row in desc_result.all()]

        # Bulk delete: remove all closure entries where descendant is in subtree
        # and ancestor is NOT in subtree (i.e., external ancestor links)
        await self._session.execute(
            delete(CategoryClosure).where(
                CategoryClosure.descendant_id.in_(descendant_ids),
                CategoryClosure.ancestor_id.not_in(descendant_ids),
            )
        )

        # Bulk insert new ancestor links
        if new_parent is not None:
            # Get all ancestors of new_parent (including self-ref)
            ancestor_stmt = select(CategoryClosure).where(
                CategoryClosure.descendant_id == new_parent_id
            )
            ancestor_result = await self._session.execute(ancestor_stmt)
            parent_closures = ancestor_result.scalars().all()

            # Get relative depths of all descendants in one query
            rel_stmt = select(
                CategoryClosure.descendant_id, CategoryClosure.depth
            ).where(
                CategoryClosure.ancestor_id == category_id,
                CategoryClosure.descendant_id.in_(descendant_ids),
            )
            rel_result = await self._session.execute(rel_stmt)
            relative_depths = {row[0]: row[1] for row in rel_result.all()}

            new_closures = []
            for d_id in descendant_ids:
                relative_depth = relative_depths.get(d_id, 0)
                for pc in parent_closures:
                    new_closures.append(CategoryClosure(
                        ancestor_id=pc.ancestor_id,
                        descendant_id=d_id,
                        depth=pc.depth + 1 + relative_depth,
                    ))
            self._session.add_all(new_closures)

        # Bulk update paths and levels using SQL
        old_path_prefix = category.path
        new_path_prefix = f"{new_parent.path}.{category.code}" if new_parent else category.code
        old_level = category.level
        new_level = (new_parent.level + 1) if new_parent else 0
        level_diff = new_level - old_level

        # Use SQL concat/replace for path update and arithmetic for level
        await self._session.execute(
            update(Category)
            .where(Category.id.in_(descendant_ids))
            .values(
                path=func.concat(
                    new_path_prefix,
                    func.substring(Category.path, len(old_path_prefix) + 1),
                ),
                level=Category.level + level_diff,
            )
        )

        await self._session.flush()

        # Refresh the moved category to return updated state
        await self._session.refresh(category)
        return category

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    async def resolve_category_by_impa_prefix(self, prefix: str) -> Category | None:
        stmt = (
            select(Category)
            .join(ImpaCategoryMapping, ImpaCategoryMapping.internal_category_id == Category.id)
            .where(ImpaCategoryMapping.impa_prefix == prefix)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def resolve_category_by_issa_prefix(self, prefix: str) -> Category | None:
        stmt = (
            select(Category)
            .join(IssaCategoryMapping, IssaCategoryMapping.internal_category_id == Category.id)
            .where(IssaCategoryMapping.issa_prefix == prefix)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_impa_mappings(self) -> list[ImpaCategoryMapping]:
        result = await self._session.execute(select(ImpaCategoryMapping))
        return list(result.scalars().all())

    async def list_issa_mappings(self) -> list[IssaCategoryMapping]:
        result = await self._session.execute(select(IssaCategoryMapping))
        return list(result.scalars().all())

    async def upsert_impa_mapping(self, data: ImpaMappingCreate, user_id: uuid.UUID | None = None) -> ImpaCategoryMapping:
        result = await self._session.execute(
            select(ImpaCategoryMapping).where(ImpaCategoryMapping.impa_prefix == data.impa_prefix)
        )
        mapping = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if mapping is not None:
            mapping.impa_category_name = data.impa_category_name
            mapping.internal_category_id = data.internal_category_id
            mapping.mapping_confidence = data.mapping_confidence
            mapping.notes = data.notes
            mapping.last_verified = now
            mapping.verified_by_id = user_id
        else:
            mapping = ImpaCategoryMapping(
                impa_prefix=data.impa_prefix,
                impa_category_name=data.impa_category_name,
                internal_category_id=data.internal_category_id,
                mapping_confidence=data.mapping_confidence,
                notes=data.notes,
                last_verified=now,
                verified_by_id=user_id,
            )
            self._session.add(mapping)
        await self._session.flush()
        return mapping

    async def upsert_issa_mapping(self, data: IssaMappingCreate) -> IssaCategoryMapping:
        result = await self._session.execute(
            select(IssaCategoryMapping).where(IssaCategoryMapping.issa_prefix == data.issa_prefix)
        )
        mapping = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if mapping is not None:
            mapping.issa_category_name = data.issa_category_name
            mapping.internal_category_id = data.internal_category_id
            mapping.impa_equivalent = data.impa_equivalent
            mapping.mapping_confidence = data.mapping_confidence
            mapping.notes = data.notes
            mapping.last_verified = now
        else:
            mapping = IssaCategoryMapping(
                issa_prefix=data.issa_prefix,
                issa_category_name=data.issa_category_name,
                internal_category_id=data.internal_category_id,
                impa_equivalent=data.impa_equivalent,
                mapping_confidence=data.mapping_confidence,
                notes=data.notes,
                last_verified=now,
            )
            self._session.add(mapping)
        await self._session.flush()
        return mapping

    # ------------------------------------------------------------------
    # Schema Inheritance
    # ------------------------------------------------------------------

    async def get_effective_schema(self, category_id: uuid.UUID) -> dict | None:
        """Walk ancestors via CategoryClosure to find the nearest ACTIVE schema.

        Starting from the category itself, then moving up to its parent, grandparent,
        etc.  Returns the schema_json dict of the nearest ancestor with an ACTIVE
        CategorySchema, or None if no ancestor has one.
        """
        await self._get_category_or_404(category_id)

        # Get all ancestors ordered by depth ascending (self first, root last)
        stmt = (
            select(CategoryClosure.ancestor_id)
            .where(CategoryClosure.descendant_id == category_id)
            .order_by(CategoryClosure.depth.asc())
        )
        result = await self._session.execute(stmt)
        ancestor_ids = [row[0] for row in result.all()]

        if not ancestor_ids:
            return None

        # For each ancestor (self -> parent -> grandparent -> ...),
        # check for an ACTIVE schema.
        for ancestor_id in ancestor_ids:
            schema_stmt = (
                select(CategorySchema)
                .where(
                    CategorySchema.category_id == ancestor_id,
                    CategorySchema.status == SchemaStatus.ACTIVE,
                )
            )
            schema_result = await self._session.execute(schema_stmt)
            active_schema = schema_result.scalar_one_or_none()
            if active_schema is not None:
                return active_schema.schema_json

        return None

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def count_products_in_subtree(self, category_id: uuid.UUID) -> int:
        """Count products in the category and all its descendants."""
        descendant_ids = select(CategoryClosure.descendant_id).where(
            CategoryClosure.ancestor_id == category_id
        )
        stmt = select(func.count()).select_from(Product).where(
            Product.category_id.in_(descendant_ids)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_category_or_404(self, category_id: uuid.UUID) -> Category:
        category = await self._session.get(Category, category_id)
        if category is None:
            raise NotFoundException(f"Category {category_id} not found")
        return category
