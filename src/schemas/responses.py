"""Base response and pagination schemas per ADR-NF-007."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """A single field-level or contextual error detail."""

    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    """Structured error body returned inside every error response."""

    code: str
    message: str
    details: list[ErrorDetail] = []
    request_id: str = Field(alias="requestId")

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    """Top-level error envelope."""

    error: ErrorBody


class PaginationMeta(BaseModel):
    """Pagination counters."""

    page: int
    limit: int
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}


class PaginatedMeta(BaseModel):
    """Metadata block for paginated responses."""

    pagination: PaginationMeta
    request_id: str = Field(alias="requestId")

    model_config = {"populate_by_name": True}


class PaginationLinks(BaseModel):
    """HATEOAS-style pagination links."""

    self_link: str = Field(alias="self")
    first: str | None = None
    prev: str | None = None
    next: str | None = None
    last: str | None = None

    model_config = {"populate_by_name": True}
