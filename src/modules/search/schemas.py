"""Pydantic request/response models for the search module."""

from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class SearchProductsRequest(BaseModel):
    query: str = Field(max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.5, ge=0.0, le=1.0)
    category_id: UUID | None = None
    precision: str = Field(default="balanced", pattern="^(fast|balanced|accurate)$")


class MatchLineItemRequest(BaseModel):
    product_name: str = Field(max_length=500)
    specifications: str | None = Field(default=None, max_length=2000)
    impa_code: str | None = Field(default=None, max_length=6)
    unit: str | None = Field(default=None, max_length=20)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    expected_category: str | None = Field(default=None, max_length=255)


class GenerateEmbeddingsRequest(BaseModel):
    product_ids: list[UUID] = Field(max_length=500)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class SimilarProductResult(BaseModel):
    id: UUID
    impa_code: str
    name: str
    description: str | None
    category_name: str | None
    similarity: float

    model_config = {"from_attributes": True}


class ProductMatchResult(BaseModel):
    product: SimilarProductResult
    confidence: float
    match_reason: str


class SearchResponse(BaseModel):
    results: list[SimilarProductResult]
    query: str
    total: int


class MatchResponse(BaseModel):
    match: ProductMatchResult | None
    candidates_evaluated: int


class GenerateEmbeddingsResponse(BaseModel):
    task_id: str
    product_count: int
    message: str


# ---------------------------------------------------------------------------
# Text search schemas (FTS + trigram + hybrid)
# ---------------------------------------------------------------------------

class TextSearchRequest(BaseModel):
    query: str = Field(max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    category_id: UUID | None = None
    mode: str = Field(default="hybrid", pattern="^(keyword|fuzzy|hybrid)$")


class TextSearchResult(BaseModel):
    id: UUID
    impa_code: str
    name: str
    description: str | None
    category_name: str | None
    score: float
    highlight: str | None = None

    model_config = {"from_attributes": True}


class FacetCount(BaseModel):
    value: str
    count: int


class TextSearchResponse(BaseModel):
    results: list[TextSearchResult]
    query: str
    total: int
    page: int
    total_pages: int


# ---------------------------------------------------------------------------
# Faceted search schemas
# ---------------------------------------------------------------------------

class FacetedSearchRequest(BaseModel):
    query: str = Field(max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    category_id: UUID | None = None
    ihm_relevant: bool | None = None
    hazmat_class: str | None = None


class FacetedSearchResponse(BaseModel):
    results: list[TextSearchResult]
    query: str
    total: int
    page: int
    total_pages: int
    facets: dict[str, list[FacetCount]]


class SynonymEntry(BaseModel):
    term: str
    synonyms: list[str]
    domain: str

    model_config = {"from_attributes": True}
