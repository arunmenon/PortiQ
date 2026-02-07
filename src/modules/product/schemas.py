"""Pydantic request/response schemas for the product module."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import CategoryStatus, SchemaStatus, TagSource, TagType, UnitType
from src.modules.product.constants import IMPA_CODE_PATTERN


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    impa_code: str = Field(..., pattern=IMPA_CODE_PATTERN, max_length=10)
    issa_code: str | None = Field(None, max_length=20)
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    category_id: uuid.UUID
    unit_of_measure: str = Field(..., max_length=20)
    ihm_relevant: bool = False
    hazmat_class: str | None = Field(None, max_length=20)
    specifications: dict = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    impa_code: str | None = Field(None, pattern=IMPA_CODE_PATTERN, max_length=10)
    issa_code: str | None = None
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    category_id: uuid.UUID | None = None
    unit_of_measure: str | None = Field(None, max_length=20)
    ihm_relevant: bool | None = None
    hazmat_class: str | None = None
    specifications: dict | None = None
    version: int = Field(..., description="Expected version for optimistic locking")


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    impa_code: str
    issa_code: str | None
    name: str
    description: str | None
    category_id: uuid.UUID
    category_name: str | None = None
    unit_of_measure: str
    ihm_relevant: bool
    hazmat_class: str | None
    specifications: dict
    version: int
    created_at: datetime
    updated_at: datetime


class ProductDetailResponse(ProductResponse):
    supplier_products: list[SupplierProductResponse] = []
    translations: list[TranslationResponse] = []
    tags: list[CategoryTagResponse] = []


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# IMPA Validation
# ---------------------------------------------------------------------------

class ImpaValidateRequest(BaseModel):
    impa_code: str = Field(..., min_length=1, max_length=10)


class ImpaValidationResponse(BaseModel):
    is_valid_format: bool
    is_known_code: bool
    suggested_category_id: uuid.UUID | None = None
    suggested_category_name: str | None = None


# ---------------------------------------------------------------------------
# Supplier Products
# ---------------------------------------------------------------------------

class SupplierProductCreate(BaseModel):
    supplier_id: uuid.UUID
    supplier_sku: str | None = Field(None, max_length=100)
    manufacturer: str | None = Field(None, max_length=255)
    brand: str | None = Field(None, max_length=255)
    part_number: str | None = Field(None, max_length=100)
    lead_time_days: int | None = None
    min_order_quantity: int = 1
    pack_size: int = 1
    specifications: dict = Field(default_factory=dict)


class SupplierProductUpdate(BaseModel):
    supplier_sku: str | None = None
    manufacturer: str | None = None
    brand: str | None = None
    part_number: str | None = None
    lead_time_days: int | None = None
    min_order_quantity: int | None = None
    pack_size: int | None = None
    specifications: dict | None = None
    is_active: bool | None = None
    version: int = Field(..., description="Expected version for optimistic locking")


class SupplierProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_sku: str | None
    manufacturer: str | None
    brand: str | None
    part_number: str | None
    lead_time_days: int | None
    min_order_quantity: int
    pack_size: int
    specifications: dict
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Supplier Prices
# ---------------------------------------------------------------------------

class SupplierPriceCreate(BaseModel):
    price: Decimal = Field(..., gt=0, decimal_places=4)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$", max_length=3)
    min_quantity: int = 1
    valid_from: datetime
    valid_to: datetime | None = None


class SupplierPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_product_id: uuid.UUID
    price: Decimal
    currency: str
    min_quantity: int
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoryCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    impa_prefix: str | None = Field(None, max_length=2)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    parent_id: uuid.UUID | None = None
    attribute_schema: dict | None = None
    ihm_category: bool = False
    icon: str | None = Field(None, max_length=100)
    display_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    attribute_schema: dict | None = None
    ihm_category: bool | None = None
    icon: str | None = None
    display_order: int | None = None
    status: CategoryStatus | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    impa_prefix: str | None
    name: str
    description: str | None
    path: str
    level: int
    attribute_schema: dict | None
    ihm_category: bool
    icon: str | None
    display_order: int
    status: CategoryStatus
    product_count: int | None = None
    created_at: datetime
    updated_at: datetime


class CategoryTreeNode(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    path: str
    level: int
    icon: str | None
    display_order: int
    status: CategoryStatus
    children_count: int = 0
    product_count: int = 0


class CategoryBreadcrumb(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    level: int


class CategoryMoveRequest(BaseModel):
    new_parent_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# IMPA / ISSA Mappings
# ---------------------------------------------------------------------------

class ImpaMappingCreate(BaseModel):
    impa_prefix: str = Field(..., min_length=2, max_length=2)
    impa_category_name: str = Field(..., max_length=255)
    internal_category_id: uuid.UUID
    mapping_confidence: str = "EXACT"
    notes: str | None = None


class ImpaMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    impa_prefix: str
    impa_category_name: str
    internal_category_id: uuid.UUID
    mapping_confidence: str
    notes: str | None
    last_verified: datetime


class IssaMappingCreate(BaseModel):
    issa_prefix: str = Field(..., min_length=2, max_length=2)
    issa_category_name: str = Field(..., max_length=255)
    internal_category_id: uuid.UUID
    impa_equivalent: str | None = Field(None, max_length=2)
    mapping_confidence: str = "EXACT"
    notes: str | None = None


class IssaMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issa_prefix: str
    issa_category_name: str
    internal_category_id: uuid.UUID
    impa_equivalent: str | None
    mapping_confidence: str
    notes: str | None
    last_verified: datetime


# ---------------------------------------------------------------------------
# Category Tags
# ---------------------------------------------------------------------------

class CategoryTagCreate(BaseModel):
    category_id: uuid.UUID
    tag_type: TagType
    confidence: Decimal = Field(Decimal("1.0"), ge=0, le=1)
    created_by: TagSource


class CategoryTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    category_id: uuid.UUID
    tag_type: TagType
    confidence: Decimal
    created_by: TagSource
    created_at: datetime
    category_name: str | None = None


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

class TranslationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)
    search_keywords: list[str] = Field(default_factory=list)


class TranslationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    locale: str
    name: str
    description: str | None
    search_keywords: list[str]


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    unit_type: UnitType
    base_unit: str | None
    display_order: int


class ConvertRequest(BaseModel):
    value: Decimal = Field(..., gt=0)
    from_unit: str = Field(..., max_length=10)
    to_unit: str = Field(..., max_length=10)
    category_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None


class ConversionResult(BaseModel):
    original_value: Decimal
    converted_value: Decimal
    conversion_factor: Decimal
    conversion_path: list[str]


class UnitConversionCreate(BaseModel):
    from_unit: str = Field(..., max_length=10)
    to_unit: str = Field(..., max_length=10)
    conversion_factor: Decimal = Field(..., gt=0)
    category_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None


class UnitConversionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_unit: str
    to_unit: str
    conversion_factor: Decimal
    category_id: uuid.UUID | None
    product_id: uuid.UUID | None


# ---------------------------------------------------------------------------
# Category Schemas (Catalog Extensibility)
# ---------------------------------------------------------------------------


class CategorySchemaCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_definition: dict = Field(..., alias="schema_json")


class CategorySchemaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    category_id: uuid.UUID
    version: int
    schema_definition: dict = Field(..., alias="schema_json")
    status: SchemaStatus
    created_by: uuid.UUID | None
    created_at: datetime
    activated_at: datetime | None


class SchemaHistoryResponse(BaseModel):
    items: list[CategorySchemaResponse]
    category_id: uuid.UUID
    total: int


class SpecsValidationResponse(BaseModel):
    valid: bool
    errors: list[dict] = []
    schema_source: str | None = None


# Forward-ref rebuild for nested models
ProductDetailResponse.model_rebuild()
