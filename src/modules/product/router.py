"""Product module API router — products, categories, and units."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import limiter
from src.database.session import get_db
from src.exceptions import ValidationException
from src.models.enums import UnitType
from src.modules.product.category_service import CategoryService
from src.modules.product.schemas import (
    CategoryBreadcrumb,
    CategoryCreate,
    CategoryMoveRequest,
    CategoryResponse,
    CategorySchemaCreate,
    CategorySchemaResponse,
    CategoryTagCreate,
    CategoryTagResponse,
    CategoryTreeNode,
    CategoryUpdate,
    ConversionResult,
    ConvertRequest,
    ImpaValidateRequest,
    ImpaValidationResponse,
    ImpaMappingCreate,
    ImpaMappingResponse,
    IssaMappingCreate,
    IssaMappingResponse,
    ProductCreate,
    ProductDetailResponse,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    SchemaHistoryResponse,
    SpecsValidationResponse,
    SupplierPriceCreate,
    SupplierPriceResponse,
    SupplierProductCreate,
    SupplierProductResponse,
    SupplierProductUpdate,
    TranslationCreate,
    TranslationResponse,
    UnitConversionCreate,
    UnitConversionResponse,
    UnitResponse,
)
from src.modules.product.schema_registry import SchemaRegistryService
from src.modules.product.service import ProductService
from src.modules.product.unit_service import UnitConversionService
from src.modules.product.validators import validate_specifications_with_schema
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user


# ====================================================================
# Product Router
# ====================================================================

product_router = APIRouter(prefix="/products", tags=["products"])


@product_router.post("", response_model=ProductResponse, status_code=201)
@limiter.limit("30/minute")
async def create_product(
    request: Request,
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProductResponse:
    svc = ProductService(db)
    product = await svc.create_product(data, user)
    return ProductResponse.model_validate(product)


@product_router.get("", response_model=ProductListResponse)
@limiter.limit("60/minute")
async def list_products(
    request: Request,
    category_id: uuid.UUID | None = None,
    ihm_relevant: bool | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProductListResponse:
    svc = ProductService(db)
    products, total = await svc.list_products(
        category_id=category_id,
        ihm_relevant=ihm_relevant,
        search=search,
        limit=limit,
        offset=offset,
    )
    items = []
    for p in products:
        resp = ProductResponse.model_validate(p)
        if p.category is not None:
            resp.category_name = p.category.name
        items.append(resp)
    return ProductListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# Static product routes BEFORE /{product_id} to avoid shadowing
@product_router.post("/validate-impa", response_model=ImpaValidationResponse)
@limiter.limit("30/minute")
async def validate_impa(
    request: Request,
    data: ImpaValidateRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ImpaValidationResponse:
    svc = ProductService(db)
    return await svc.validate_impa_code(data.impa_code)


@product_router.get("/impa/{impa_code}", response_model=ProductResponse)
@limiter.limit("60/minute")
async def get_product_by_impa(
    request: Request,
    impa_code: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProductResponse:
    svc = ProductService(db)
    product = await svc.get_product_by_impa(impa_code)
    return ProductResponse.model_validate(product)


# Parameterized product routes
@product_router.get("/{product_id}", response_model=ProductDetailResponse)
@limiter.limit("60/minute")
async def get_product(
    request: Request,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProductDetailResponse:
    svc = ProductService(db)
    product = await svc.get_product_detail(product_id)
    resp = ProductDetailResponse.model_validate(product)
    if product.category is not None:
        resp.category_name = product.category.name
    resp.tags = [
        CategoryTagResponse.model_validate(t) for t in product.product_category_tags
    ]
    return resp


@product_router.patch("/{product_id}", response_model=ProductResponse)
@limiter.limit("30/minute")
async def update_product(
    request: Request,
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProductResponse:
    svc = ProductService(db)
    product = await svc.update_product(product_id, data, user)
    return ProductResponse.model_validate(product)


@product_router.delete("/{product_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_product(
    request: Request,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    svc = ProductService(db)
    await svc.delete_product(product_id, user)


# --- Supplier Products ---


@product_router.post(
    "/{product_id}/suppliers", response_model=SupplierProductResponse, status_code=201,
)
@limiter.limit("30/minute")
async def add_supplier_product(
    request: Request,
    product_id: uuid.UUID,
    data: SupplierProductCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SupplierProductResponse:
    svc = ProductService(db)
    sp = await svc.add_supplier_product(product_id, data, user)
    return SupplierProductResponse.model_validate(sp)


@product_router.get("/{product_id}/suppliers", response_model=list[SupplierProductResponse])
@limiter.limit("60/minute")
async def list_supplier_products(
    request: Request,
    product_id: uuid.UUID,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[SupplierProductResponse]:
    svc = ProductService(db)
    items = await svc.list_supplier_products(product_id, active_only=active_only)
    return [SupplierProductResponse.model_validate(sp) for sp in items]


@product_router.patch(
    "/{product_id}/suppliers/{sp_id}", response_model=SupplierProductResponse,
)
@limiter.limit("30/minute")
async def update_supplier_product(
    request: Request,
    product_id: uuid.UUID,
    sp_id: uuid.UUID,
    data: SupplierProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SupplierProductResponse:
    svc = ProductService(db)
    sp = await svc.update_supplier_product(product_id, sp_id, data, user)
    return SupplierProductResponse.model_validate(sp)


# --- Prices ---


@product_router.post(
    "/{product_id}/suppliers/{sp_id}/prices",
    response_model=SupplierPriceResponse,
    status_code=201,
)
@limiter.limit("30/minute")
async def add_supplier_price(
    request: Request,
    product_id: uuid.UUID,
    sp_id: uuid.UUID,
    data: SupplierPriceCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SupplierPriceResponse:
    svc = ProductService(db)
    price = await svc.add_supplier_price(product_id, sp_id, data, user)
    return SupplierPriceResponse.model_validate(price)


@product_router.get(
    "/{product_id}/suppliers/{sp_id}/prices", response_model=list[SupplierPriceResponse],
)
@limiter.limit("60/minute")
async def list_supplier_prices(
    request: Request,
    product_id: uuid.UUID,
    sp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[SupplierPriceResponse]:
    svc = ProductService(db)
    prices = await svc.list_supplier_prices(product_id, sp_id)
    return [SupplierPriceResponse.model_validate(p) for p in prices]


# --- Tags ---


@product_router.post("/{product_id}/tags", response_model=CategoryTagResponse, status_code=201)
@limiter.limit("30/minute")
async def add_category_tag(
    request: Request,
    product_id: uuid.UUID,
    data: CategoryTagCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryTagResponse:
    svc = ProductService(db)
    tag = await svc.add_category_tag(product_id, data, user)
    return CategoryTagResponse.model_validate(tag)


@product_router.get("/{product_id}/tags", response_model=list[CategoryTagResponse])
@limiter.limit("60/minute")
async def get_product_tags(
    request: Request,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[CategoryTagResponse]:
    svc = ProductService(db)
    tags = await svc.get_product_tags(product_id)
    return [CategoryTagResponse.model_validate(t) for t in tags]


@product_router.delete("/{product_id}/tags/{tag_id}", status_code=204)
@limiter.limit("30/minute")
async def remove_category_tag(
    request: Request,
    product_id: uuid.UUID,
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    svc = ProductService(db)
    await svc.remove_category_tag(product_id, tag_id, user)


# --- Translations ---


@product_router.put(
    "/{product_id}/translations/{locale}", response_model=TranslationResponse,
)
@limiter.limit("30/minute")
async def set_translation(
    request: Request,
    product_id: uuid.UUID,
    locale: str = Path(..., pattern=r"^[a-z]{2}(-[A-Z]{2})?$", max_length=5),
    data: TranslationCreate = ...,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> TranslationResponse:
    svc = ProductService(db)
    t = await svc.set_translation(product_id, locale, data, user)
    return TranslationResponse.model_validate(t)


@product_router.get("/{product_id}/translations", response_model=list[TranslationResponse])
@limiter.limit("60/minute")
async def get_translations(
    request: Request,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[TranslationResponse]:
    svc = ProductService(db)
    translations = await svc.get_translations(product_id)
    return [TranslationResponse.model_validate(t) for t in translations]


# ====================================================================
# Category Router
# ====================================================================

category_router = APIRouter(prefix="/categories", tags=["categories"])


# --- Static category routes FIRST (before /{category_id}) ---


@category_router.get("/mappings/impa", response_model=list[ImpaMappingResponse])
@limiter.limit("120/minute")
async def list_impa_mappings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[ImpaMappingResponse]:
    svc = CategoryService(db)
    mappings = await svc.list_impa_mappings()
    return [ImpaMappingResponse.model_validate(m) for m in mappings]


@category_router.get("/mappings/issa", response_model=list[IssaMappingResponse])
@limiter.limit("120/minute")
async def list_issa_mappings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[IssaMappingResponse]:
    svc = CategoryService(db)
    mappings = await svc.list_issa_mappings()
    return [IssaMappingResponse.model_validate(m) for m in mappings]


@category_router.get("/resolve/impa/{prefix}", response_model=CategoryResponse | None)
@limiter.limit("120/minute")
async def resolve_impa_prefix(
    request: Request,
    prefix: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryResponse | None:
    svc = CategoryService(db)
    category = await svc.resolve_category_by_impa_prefix(prefix)
    if category is None:
        return None
    return CategoryResponse.model_validate(category)


@category_router.get("/resolve/issa/{prefix}", response_model=CategoryResponse | None)
@limiter.limit("120/minute")
async def resolve_issa_prefix(
    request: Request,
    prefix: str,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryResponse | None:
    svc = CategoryService(db)
    category = await svc.resolve_category_by_issa_prefix(prefix)
    if category is None:
        return None
    return CategoryResponse.model_validate(category)


@category_router.put("/mappings/impa/{prefix}", response_model=ImpaMappingResponse)
@limiter.limit("30/minute")
async def upsert_impa_mapping(
    request: Request,
    prefix: str,
    data: ImpaMappingCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ImpaMappingResponse:
    if prefix != data.impa_prefix:
        raise ValidationException(
            f"URL prefix '{prefix}' does not match body impa_prefix '{data.impa_prefix}'"
        )
    svc = CategoryService(db)
    mapping = await svc.upsert_impa_mapping(data, user_id=user.id)
    return ImpaMappingResponse.model_validate(mapping)


@category_router.put("/mappings/issa/{prefix}", response_model=IssaMappingResponse)
@limiter.limit("30/minute")
async def upsert_issa_mapping(
    request: Request,
    prefix: str,
    data: IssaMappingCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> IssaMappingResponse:
    if prefix != data.issa_prefix:
        raise ValidationException(
            f"URL prefix '{prefix}' does not match body issa_prefix '{data.issa_prefix}'"
        )
    svc = CategoryService(db)
    mapping = await svc.upsert_issa_mapping(data)
    return IssaMappingResponse.model_validate(mapping)


# --- Parameterized category routes ---


@category_router.post("", response_model=CategoryResponse, status_code=201)
@limiter.limit("30/minute")
async def create_category(
    request: Request,
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryResponse:
    svc = CategoryService(db)
    category = await svc.create_category(data)
    return CategoryResponse.model_validate(category)


@category_router.get("", response_model=list[CategoryTreeNode])
@limiter.limit("120/minute")
async def list_categories(
    request: Request,
    max_depth: int | None = Query(None, ge=0, le=20),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[CategoryTreeNode]:
    svc = CategoryService(db)
    return await svc.get_tree(max_depth=max_depth)


@category_router.get("/{category_id}", response_model=CategoryResponse)
@limiter.limit("120/minute")
async def get_category(
    request: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryResponse:
    svc = CategoryService(db)
    category = await svc.get_category(category_id)
    return CategoryResponse.model_validate(category)


@category_router.get("/{category_id}/tree", response_model=list[CategoryTreeNode])
@limiter.limit("120/minute")
async def get_category_tree(
    request: Request,
    category_id: uuid.UUID,
    max_depth: int | None = Query(None, ge=0, le=20),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[CategoryTreeNode]:
    svc = CategoryService(db)
    return await svc.get_tree(root_id=category_id, max_depth=max_depth)


@category_router.get("/{category_id}/breadcrumbs", response_model=list[CategoryBreadcrumb])
@limiter.limit("120/minute")
async def get_breadcrumbs(
    request: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[CategoryBreadcrumb]:
    svc = CategoryService(db)
    return await svc.get_breadcrumbs(category_id)


@category_router.get("/{category_id}/children", response_model=list[CategoryResponse])
@limiter.limit("120/minute")
async def get_children(
    request: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[CategoryResponse]:
    svc = CategoryService(db)
    children = await svc.get_children(category_id)
    return [CategoryResponse.model_validate(c) for c in children]


@category_router.patch("/{category_id}", response_model=CategoryResponse)
@limiter.limit("30/minute")
async def update_category(
    request: Request,
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryResponse:
    svc = CategoryService(db)
    category = await svc.update_category(category_id, data)
    return CategoryResponse.model_validate(category)


@category_router.post("/{category_id}/move", response_model=CategoryResponse)
@limiter.limit("30/minute")
async def move_category(
    request: Request,
    category_id: uuid.UUID,
    data: CategoryMoveRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategoryResponse:
    svc = CategoryService(db)
    category = await svc.move_subtree(category_id, data.new_parent_id)
    return CategoryResponse.model_validate(category)


# ====================================================================
# Unit Router
# ====================================================================

unit_router = APIRouter(prefix="/units", tags=["units"])


@unit_router.get("", response_model=list[UnitResponse])
@limiter.limit("120/minute")
async def list_units(
    request: Request,
    unit_type: UnitType | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[UnitResponse]:
    svc = UnitConversionService(db)
    units = await svc.list_units(unit_type=unit_type)
    return [UnitResponse.model_validate(u) for u in units]


@unit_router.post("/convert", response_model=ConversionResult)
@limiter.limit("120/minute")
async def convert_units(
    request: Request,
    data: ConvertRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ConversionResult:
    svc = UnitConversionService(db)
    return await svc.convert(
        value=data.value,
        from_unit=data.from_unit,
        to_unit=data.to_unit,
        category_id=data.category_id,
        product_id=data.product_id,
    )


@unit_router.post("/conversions", response_model=UnitConversionResponse, status_code=201)
@limiter.limit("30/minute")
async def create_conversion(
    request: Request,
    data: UnitConversionCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> UnitConversionResponse:
    svc = UnitConversionService(db)
    conversion = await svc.create_conversion(data)
    return UnitConversionResponse.model_validate(conversion)


@unit_router.get("/conversions", response_model=list[UnitConversionResponse])
@limiter.limit("120/minute")
async def list_conversions(
    request: Request,
    from_unit: str | None = None,
    category_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[UnitConversionResponse]:
    svc = UnitConversionService(db)
    conversions = await svc.list_conversions(
        from_unit=from_unit, category_id=category_id, product_id=product_id,
    )
    return [UnitConversionResponse.model_validate(c) for c in conversions]


# ====================================================================
# Category Schema Endpoints (Catalog Extensibility)
# ====================================================================


@category_router.get("/{category_id}/schema", response_model=CategorySchemaResponse | None)
@limiter.limit("120/minute")
async def get_category_schema(
    request: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategorySchemaResponse | None:
    """Get the currently ACTIVE schema for a category."""
    registry = SchemaRegistryService(db)
    schema = await registry.get_active_schema(category_id)
    if schema is None:
        return None
    return CategorySchemaResponse.model_validate(schema)


@category_router.put("/{category_id}/schema", response_model=CategorySchemaResponse, status_code=201)
@limiter.limit("30/minute")
async def register_category_schema(
    request: Request,
    category_id: uuid.UUID,
    data: CategorySchemaCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CategorySchemaResponse:
    """Register a new schema version (DRAFT) for a category."""
    # Verify category exists
    cat_svc = CategoryService(db)
    await cat_svc.get_category(category_id)

    registry = SchemaRegistryService(db)
    schema = await registry.register_schema(
        category_id=category_id,
        schema_json=data.schema_json,
        created_by_id=user.id,
    )
    return CategorySchemaResponse.model_validate(schema)


@category_router.get("/{category_id}/schema/history", response_model=SchemaHistoryResponse)
@limiter.limit("120/minute")
async def get_schema_history(
    request: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SchemaHistoryResponse:
    """Get schema version history for a category."""
    registry = SchemaRegistryService(db)
    schemas = await registry.list_schema_history(category_id)
    return SchemaHistoryResponse(
        items=[CategorySchemaResponse.model_validate(s) for s in schemas],
        category_id=category_id,
        total=len(schemas),
    )


@product_router.post("/{product_id}/validate-specs", response_model=SpecsValidationResponse)
@limiter.limit("60/minute")
async def validate_product_specs(
    request: Request,
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SpecsValidationResponse:
    """Validate a product's specifications against the effective category schema."""
    svc = ProductService(db)
    product = await svc.get_product(product_id)
    result = await validate_specifications_with_schema(
        specs=product.specifications,
        category_id=product.category_id,
        session=db,
    )
    return SpecsValidationResponse(**result)
