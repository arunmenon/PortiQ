"""Data Export API router — 3 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.modules.export.schemas import (
    ExportCreateRequest,
    ExportDownloadResponse,
    ExportJobResponse,
)
from src.modules.export.service import ExportService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/exports", tags=["exports"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_job_response(job, download_url: str | None = None) -> ExportJobResponse:
    """Build an ExportJobResponse from an ExportJob model instance."""
    resp = ExportJobResponse.model_validate(job)
    if download_url is not None:
        resp.download_url = download_url
    return resp


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=ExportJobResponse, status_code=201)
async def create_export(
    body: ExportCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a new data export (type, format, filters).

    Creates an ExportJob record with status PENDING.
    For MVP, the actual generation is deferred (Celery task placeholder).
    """
    svc = ExportService(db)
    job = await svc.create_export(request=body, user=user)
    return _build_job_response(job)


@router.get("/{job_id}", response_model=ExportJobResponse)
async def get_export_status(
    job_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get export job status and download URL (if completed)."""
    svc = ExportService(db)
    job = await svc.get_export_status(job_id, organization_id=user.organization_id)
    return _build_job_response(job)


@router.get("/{job_id}/download", response_model=ExportDownloadResponse)
async def download_export(
    job_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get download URL for a completed export job.

    Returns the presigned URL details. In production, this would
    redirect to the S3 presigned URL for direct download.
    """
    svc = ExportService(db)
    result = await svc.get_download_url(job_id, organization_id=user.organization_id)
    return ExportDownloadResponse(**result)
