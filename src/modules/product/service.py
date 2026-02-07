"""Product service — CRUD, IMPA validation, supplier products, tags, translations."""

from __future__ import annotations

import random
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import ConflictException, NotFoundException, ValidationException
from src.models.audit import ProductAuditLog
from src.models.category import Category
from src.models.enums import CategoryStatus
from src.models.product import Product
from src.models.product_category_tag import ProductCategoryTag
from src.models.supplier_product import SupplierProduct, SupplierProductPrice
from src.models.translation import ProductTranslation
from src.models.unit import UnitOfMeasure
from src.modules.product.constants import EXTENSION_CODE_PREFIX, IMPA_PREFIX_LENGTH
from src.modules.product.schemas import (
    CategoryTagCreate,
    ImpaValidationResponse,
    ProductCreate,
    ProductUpdate,
    SupplierPriceCreate,
    SupplierProductCreate,
    SupplierProductUpdate,
    TranslationCreate,
)
from src.modules.product.validators import validate_impa_code_format, validate_specifications
from src.modules.tenancy.auth import AuthenticatedUser


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_product(self, data: ProductCreate, user: AuthenticatedUser) -> Product:
        # Validate IMPA format
        if not validate_impa_code_format(data.impa_code):
            raise ValidationException(f"Invalid IMPA code format: {data.impa_code}")

        # Check uniqueness
        existing = await self._session.execute(
            select(Product.id).where(Product.impa_code == data.impa_code)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(f"Product with IMPA code '{data.impa_code}' already exists")

        # Validate category exists and is active
        category = await self._get_active_category(data.category_id)

        # Validate specifications against category schema
        validate_specifications(data.specifications, category.attribute_schema)

        # Validate unit of measure exists
        await self._validate_unit(data.unit_of_measure)

        product = Product(
            impa_code=data.impa_code,
            issa_code=data.issa_code,
            name=data.name,
            description=data.description,
            category_id=data.category_id,
            unit_of_measure=data.unit_of_measure,
            ihm_relevant=data.ihm_relevant,
            hazmat_class=data.hazmat_class,
            specifications=data.specifications,
        )
        self._session.add(product)
        await self._session.flush()

        await self._audit_log(
            entity_type="Product",
            entity_id=product.id,
            operation="CREATE",
            changed_fields=data.model_dump(),
            changed_by_id=user.id,
            version=product.version,
        )

        return product

    async def get_product(self, product_id: uuid.UUID) -> Product:
        return await self._get_product_or_404(product_id)

    async def get_product_detail(self, product_id: uuid.UUID) -> Product:
        stmt = (
            select(Product)
            .options(
                selectinload(Product.supplier_products).selectinload(SupplierProduct.prices),
                selectinload(Product.translations),
                selectinload(Product.product_category_tags),
                selectinload(Product.category),
            )
            .where(Product.id == product_id)
        )
        result = await self._session.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException(f"Product {product_id} not found")
        return product

    async def get_product_by_impa(self, impa_code: str) -> Product:
        stmt = select(Product).where(Product.impa_code == impa_code)
        result = await self._session.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            raise NotFoundException(f"Product with IMPA code '{impa_code}' not found")
        return product

    async def list_products(
        self,
        category_id: uuid.UUID | None = None,
        ihm_relevant: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        stmt = select(Product)
        count_stmt = select(func.count()).select_from(Product)

        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
            count_stmt = count_stmt.where(Product.category_id == category_id)
        if ihm_relevant is not None:
            stmt = stmt.where(Product.ihm_relevant == ihm_relevant)
            count_stmt = count_stmt.where(Product.ihm_relevant == ihm_relevant)
        if search is not None:
            escaped = re.sub(r"([%_\\])", r"\\\1", search)
            like_pattern = f"%{escaped}%"
            search_filter = Product.name.ilike(like_pattern) | Product.impa_code.ilike(like_pattern)
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.options(selectinload(Product.category))
        stmt = stmt.order_by(Product.name).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        products = list(result.scalars().all())

        return products, total

    async def update_product(
        self,
        product_id: uuid.UUID,
        data: ProductUpdate,
        user: AuthenticatedUser,
    ) -> Product:
        product = await self._get_product_or_404(product_id)

        # Optimistic locking check
        if product.version != data.version:
            raise ConflictException(
                f"Version conflict: expected {data.version}, actual {product.version}"
            )

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        if "impa_code" in update_data and update_data["impa_code"] is not None:
            if not validate_impa_code_format(update_data["impa_code"]):
                raise ValidationException(f"Invalid IMPA code format: {update_data['impa_code']}")
            # Check uniqueness if changing impa_code
            if update_data["impa_code"] != product.impa_code:
                existing = await self._session.execute(
                    select(Product.id).where(Product.impa_code == update_data["impa_code"])
                )
                if existing.scalar_one_or_none() is not None:
                    raise ConflictException(
                        f"Product with IMPA code '{update_data['impa_code']}' already exists"
                    )

        if "category_id" in update_data and update_data["category_id"] is not None:
            category = await self._get_active_category(update_data["category_id"])
            specs = update_data.get("specifications", product.specifications)
            validate_specifications(specs, category.attribute_schema)
        elif "specifications" in update_data:
            category = await self._session.get(Category, product.category_id)
            if category is not None:
                validate_specifications(update_data["specifications"], category.attribute_schema)

        if "unit_of_measure" in update_data and update_data["unit_of_measure"] is not None:
            await self._validate_unit(update_data["unit_of_measure"])

        for field, value in update_data.items():
            setattr(product, field, value)
        product.version += 1

        await self._session.flush()

        await self._audit_log(
            entity_type="Product",
            entity_id=product.id,
            operation="UPDATE",
            changed_fields=update_data,
            changed_by_id=user.id,
            version=product.version,
        )

        return product

    async def delete_product(self, product_id: uuid.UUID, user: AuthenticatedUser) -> None:
        product = await self._get_product_or_404(product_id)
        await self._audit_log(
            entity_type="Product",
            entity_id=product.id,
            operation="DELETE",
            changed_fields=None,
            changed_by_id=user.id,
            version=product.version,
        )
        await self._session.delete(product)
        await self._session.flush()

    # ------------------------------------------------------------------
    # IMPA
    # ------------------------------------------------------------------

    async def validate_impa_code(self, code: str) -> ImpaValidationResponse:
        is_valid = validate_impa_code_format(code)
        is_known = False
        suggested_category_id = None
        suggested_category_name = None

        if is_valid:
            # Check if the code already exists
            existing = await self._session.execute(
                select(Product).options(selectinload(Product.category)).where(Product.impa_code == code)
            )
            product = existing.scalar_one_or_none()
            if product is not None:
                is_known = True
                suggested_category_id = product.category_id
                if product.category is not None:
                    suggested_category_name = product.category.name
            elif not code.startswith(EXTENSION_CODE_PREFIX) and len(code) >= IMPA_PREFIX_LENGTH:
                # Try to suggest category based on IMPA prefix
                prefix = code[:IMPA_PREFIX_LENGTH]
                category = await self._session.execute(
                    select(Category).where(Category.impa_prefix == prefix)
                )
                cat = category.scalar_one_or_none()
                if cat is not None:
                    suggested_category_id = cat.id
                    suggested_category_name = cat.name

        return ImpaValidationResponse(
            is_valid_format=is_valid,
            is_known_code=is_known,
            suggested_category_id=suggested_category_id,
            suggested_category_name=suggested_category_name,
        )

    async def generate_extension_code(self) -> str:
        """Generate a unique extension code (EXT-XXXXXX)."""
        for _ in range(100):
            number = random.randint(100000, 999999)
            code = f"{EXTENSION_CODE_PREFIX}{number}"
            existing = await self._session.execute(
                select(Product.id).where(Product.impa_code == code)
            )
            if existing.scalar_one_or_none() is None:
                return code
        raise ConflictException("Unable to generate unique extension code after 100 attempts")

    # ------------------------------------------------------------------
    # Supplier Products
    # ------------------------------------------------------------------

    async def add_supplier_product(
        self,
        product_id: uuid.UUID,
        data: SupplierProductCreate,
        user: AuthenticatedUser,
    ) -> SupplierProduct:
        await self._get_product_or_404(product_id)
        sp = SupplierProduct(
            product_id=product_id,
            supplier_id=data.supplier_id,
            supplier_sku=data.supplier_sku,
            manufacturer=data.manufacturer,
            brand=data.brand,
            part_number=data.part_number,
            lead_time_days=data.lead_time_days,
            min_order_quantity=data.min_order_quantity,
            pack_size=data.pack_size,
            specifications=data.specifications,
        )
        self._session.add(sp)
        await self._session.flush()

        await self._audit_log(
            entity_type="SupplierProduct",
            entity_id=sp.id,
            operation="CREATE",
            changed_fields=data.model_dump(),
            changed_by_id=user.id,
            version=sp.version,
        )
        return sp

    async def update_supplier_product(
        self,
        product_id: uuid.UUID,
        sp_id: uuid.UUID,
        data: SupplierProductUpdate,
        user: AuthenticatedUser,
    ) -> SupplierProduct:
        sp = await self._get_supplier_product_or_404(sp_id)
        if sp.product_id != product_id:
            raise NotFoundException(f"Supplier product {sp_id} not found for product {product_id}")

        if sp.version != data.version:
            raise ConflictException(
                f"Version conflict: expected {data.version}, actual {sp.version}"
            )

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(sp, field, value)
        sp.version += 1

        await self._session.flush()

        await self._audit_log(
            entity_type="SupplierProduct",
            entity_id=sp.id,
            operation="UPDATE",
            changed_fields=update_data,
            changed_by_id=user.id,
            version=sp.version,
        )
        return sp

    async def list_supplier_products(
        self,
        product_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[SupplierProduct]:
        await self._get_product_or_404(product_id)
        stmt = select(SupplierProduct).where(SupplierProduct.product_id == product_id)
        if active_only:
            stmt = stmt.where(SupplierProduct.is_active.is_(True))
        stmt = stmt.order_by(SupplierProduct.created_at)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------

    async def add_supplier_price(
        self,
        product_id: uuid.UUID,
        sp_id: uuid.UUID,
        data: SupplierPriceCreate,
        user: AuthenticatedUser,
    ) -> SupplierProductPrice:
        sp = await self._get_supplier_product_or_404(sp_id)
        if sp.product_id != product_id:
            raise NotFoundException(f"Supplier product {sp_id} not found for product {product_id}")

        # Auto-close previous open price windows for same currency/quantity
        # Only close prices whose valid_from is before the new price's valid_from
        stmt = (
            select(SupplierProductPrice)
            .where(
                SupplierProductPrice.supplier_product_id == sp_id,
                SupplierProductPrice.currency == data.currency,
                SupplierProductPrice.min_quantity == data.min_quantity,
                SupplierProductPrice.valid_to.is_(None),
                SupplierProductPrice.valid_from < data.valid_from,
            )
        )
        result = await self._session.execute(stmt)
        closed_prices = list(result.scalars().all())
        for existing_price in closed_prices:
            existing_price.valid_to = data.valid_from

        price = SupplierProductPrice(
            supplier_product_id=sp_id,
            price=data.price,
            currency=data.currency,
            min_quantity=data.min_quantity,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
        )
        self._session.add(price)
        await self._session.flush()

        await self._audit_log(
            entity_type="SupplierProductPrice",
            entity_id=price.id,
            operation="CREATE",
            changed_fields={
                **data.model_dump(mode="json"),
                "auto_closed_count": len(closed_prices),
            },
            changed_by_id=user.id,
            version=1,
        )

        return price

    async def get_current_price(
        self,
        sp_id: uuid.UUID,
        currency: str | None = None,
        quantity: int | None = None,
    ) -> SupplierProductPrice | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(SupplierProductPrice)
            .where(
                SupplierProductPrice.supplier_product_id == sp_id,
                SupplierProductPrice.valid_from <= now,
            )
            .where(
                (SupplierProductPrice.valid_to.is_(None))
                | (SupplierProductPrice.valid_to > now)
            )
        )
        if currency is not None:
            stmt = stmt.where(SupplierProductPrice.currency == currency)
        if quantity is not None:
            stmt = stmt.where(SupplierProductPrice.min_quantity <= quantity)
        stmt = stmt.order_by(SupplierProductPrice.min_quantity.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_supplier_prices(self, product_id: uuid.UUID, sp_id: uuid.UUID) -> list[SupplierProductPrice]:
        sp = await self._get_supplier_product_or_404(sp_id)
        if sp.product_id != product_id:
            raise NotFoundException(f"Supplier product {sp_id} not found for product {product_id}")
        stmt = (
            select(SupplierProductPrice)
            .where(SupplierProductPrice.supplier_product_id == sp_id)
            .order_by(SupplierProductPrice.valid_from.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    async def add_category_tag(
        self,
        product_id: uuid.UUID,
        data: CategoryTagCreate,
        user: AuthenticatedUser,
    ) -> ProductCategoryTag:
        await self._get_product_or_404(product_id)
        tag = ProductCategoryTag(
            product_id=product_id,
            category_id=data.category_id,
            tag_type=data.tag_type,
            confidence=data.confidence,
            created_by=data.created_by,
        )
        self._session.add(tag)
        await self._session.flush()

        await self._audit_log(
            entity_type="ProductCategoryTag",
            entity_id=tag.id,
            operation="CREATE",
            changed_fields=data.model_dump(mode="json"),
            changed_by_id=user.id,
            version=1,
        )
        return tag

    async def remove_category_tag(
        self, product_id: uuid.UUID, tag_id: uuid.UUID, user: AuthenticatedUser,
    ) -> None:
        tag = await self._session.get(ProductCategoryTag, tag_id)
        if tag is None or tag.product_id != product_id:
            raise NotFoundException(f"Tag {tag_id} not found for product {product_id}")
        await self._audit_log(
            entity_type="ProductCategoryTag",
            entity_id=tag.id,
            operation="DELETE",
            changed_fields={"category_id": str(tag.category_id), "tag_type": str(tag.tag_type)},
            changed_by_id=user.id,
            version=1,
        )
        await self._session.delete(tag)
        await self._session.flush()

    async def get_product_tags(self, product_id: uuid.UUID) -> list[ProductCategoryTag]:
        await self._get_product_or_404(product_id)
        stmt = (
            select(ProductCategoryTag)
            .where(ProductCategoryTag.product_id == product_id)
            .order_by(ProductCategoryTag.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Translations
    # ------------------------------------------------------------------

    async def set_translation(
        self,
        product_id: uuid.UUID,
        locale: str,
        data: TranslationCreate,
        user: AuthenticatedUser,
    ) -> ProductTranslation:
        await self._get_product_or_404(product_id)
        stmt = select(ProductTranslation).where(
            ProductTranslation.product_id == product_id,
            ProductTranslation.locale == locale,
        )
        result = await self._session.execute(stmt)
        translation = result.scalar_one_or_none()

        if translation is not None:
            operation = "UPDATE"
            translation.name = data.name
            translation.description = data.description
            translation.search_keywords = data.search_keywords
        else:
            operation = "CREATE"
            translation = ProductTranslation(
                product_id=product_id,
                locale=locale,
                name=data.name,
                description=data.description,
                search_keywords=data.search_keywords,
            )
            self._session.add(translation)

        await self._session.flush()

        await self._audit_log(
            entity_type="ProductTranslation",
            entity_id=translation.id,
            operation=operation,
            changed_fields={"locale": locale, **data.model_dump()},
            changed_by_id=user.id,
            version=1,
        )

        return translation

    async def get_translations(self, product_id: uuid.UUID) -> list[ProductTranslation]:
        await self._get_product_or_404(product_id)
        stmt = (
            select(ProductTranslation)
            .where(ProductTranslation.product_id == product_id)
            .order_by(ProductTranslation.locale)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_product_or_404(self, product_id: uuid.UUID) -> Product:
        product = await self._session.get(Product, product_id)
        if product is None:
            raise NotFoundException(f"Product {product_id} not found")
        return product

    async def _get_supplier_product_or_404(self, sp_id: uuid.UUID) -> SupplierProduct:
        sp = await self._session.get(SupplierProduct, sp_id)
        if sp is None:
            raise NotFoundException(f"Supplier product {sp_id} not found")
        return sp

    async def _get_active_category(self, category_id: uuid.UUID) -> Category:
        category = await self._session.get(Category, category_id)
        if category is None:
            raise NotFoundException(f"Category {category_id} not found")
        if category.status != CategoryStatus.ACTIVE:
            raise ValidationException(f"Category {category_id} is not active (status: {category.status.value})")
        return category

    async def _validate_unit(self, unit_code: str) -> None:
        unit = await self._session.get(UnitOfMeasure, unit_code)
        if unit is None:
            raise ValidationException(f"Unit of measure '{unit_code}' does not exist")

    async def _audit_log(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        operation: str,
        changed_fields: dict | None,
        changed_by_id: uuid.UUID,
        version: int,
    ) -> None:
        log = ProductAuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            changed_fields=changed_fields,
            changed_by_id=changed_by_id,
            version=version,
        )
        self._session.add(log)
