"""Pydantic v2 schemas for Data Export API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import ExportFormat, ExportJobStatus, ExportType


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ExportCreateRequest(BaseModel):
    export_type: ExportType
    export_format: ExportFormat
    filters: dict = Field(default_factory=dict)
    entity_id: uuid.UUID | None = None
    entity_type: str | None = Field(None, max_length=30)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by: uuid.UUID
    export_type: ExportType
    export_format: ExportFormat
    filters: dict = Field(default_factory=dict)
    entity_id: uuid.UUID | None = None
    entity_type: str | None = None
    status: ExportJobStatus
    progress_percent: int = 0
    error_message: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    content_type: str | None = None
    download_url: str | None = None
    total_rows: int | None = None
    processed_rows: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class ExportDownloadResponse(BaseModel):
    download_url: str
    file_name: str
    content_type: str
    expires_at: datetime | None = None
