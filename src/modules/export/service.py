"""Export service — create export jobs, check status, generate download URLs."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BusinessRuleException, NotFoundException
from src.models.enums import ExportJobStatus
from src.models.export_job import ExportJob
from src.modules.export.constants import (
    EVENT_EXPORT_REQUESTED,
    EXPORT_FILE_TTL_DAYS,
    EXPORT_PRESIGNED_URL_EXPIRY_SECONDS,
    EXPORT_S3_BUCKET,
    EXPORT_S3_PREFIX,
    EXPORT_TYPE_ALLOWED_FORMATS,
    FORMAT_CONTENT_TYPES,
    FORMAT_EXTENSIONS,
)
from src.modules.export.schemas import ExportCreateRequest
from src.modules.events.outbox_service import OutboxService
from src.modules.tenancy.auth import AuthenticatedUser

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Create export job
    # ------------------------------------------------------------------

    async def create_export(
        self,
        request: ExportCreateRequest,
        user: AuthenticatedUser,
    ) -> ExportJob:
        """Create an ExportJob record with status PENDING.

        For MVP, the actual Celery task dispatch is a TODO.
        Returns the job immediately so the client can poll for status.
        """
        # Validate format is allowed for this export type
        allowed_formats = EXPORT_TYPE_ALLOWED_FORMATS.get(request.export_type, set())
        if request.export_format not in allowed_formats:
            raise BusinessRuleException(
                f"Format '{request.export_format.value}' is not supported for "
                f"export type '{request.export_type.value}'. "
                f"Allowed formats: {[f.value for f in allowed_formats]}"
            )

        # Build file name
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        extension = FORMAT_EXTENSIONS[request.export_format]
        file_name = f"{request.export_type.value.lower()}_{timestamp}{extension}"

        # Build S3 key (placeholder — actual upload is future work)
        s3_key = (
            f"{EXPORT_S3_PREFIX}/{user.organization_id}/"
            f"{request.export_type.value.lower()}/{file_name}"
        )

        content_type = FORMAT_CONTENT_TYPES[request.export_format]

        job = ExportJob(
            organization_id=user.organization_id,
            requested_by=user.id,
            export_type=request.export_type,
            export_format=request.export_format,
            filters=request.filters,
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            status=ExportJobStatus.PENDING,
            progress_percent=0,
            s3_key=s3_key,
            s3_bucket=EXPORT_S3_BUCKET,
            file_name=file_name,
            content_type=content_type,
            expires_at=datetime.now(UTC) + timedelta(days=EXPORT_FILE_TTL_DAYS),
        )
        self.db.add(job)
        await self.db.flush()

        # Emit event
        outbox = OutboxService(self.db)
        await outbox.publish_event(
            event_type=EVENT_EXPORT_REQUESTED,
            aggregate_type="export_job",
            aggregate_id=str(job.id),
            payload={
                "job_id": str(job.id),
                "export_type": request.export_type.value,
                "export_format": request.export_format.value,
                "organization_id": str(user.organization_id),
                "requested_by": str(user.id),
            },
        )

        # TODO: Dispatch Celery task for actual export generation
        # from src.tasks.export import generate_export
        # generate_export.delay(str(job.id))

        logger.info(
            "Created export job %s: type=%s format=%s for org=%s",
            job.id,
            request.export_type.value,
            request.export_format.value,
            user.organization_id,
        )

        return job

    # ------------------------------------------------------------------
    # Get export job status
    # ------------------------------------------------------------------

    async def get_export_status(
        self,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> ExportJob:
        """Return current job status. Scoped to the user's organization."""
        result = await self.db.execute(
            select(ExportJob).where(
                ExportJob.id == job_id,
                ExportJob.organization_id == organization_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise NotFoundException(f"Export job {job_id} not found")
        return job

    # ------------------------------------------------------------------
    # Get download URL
    # ------------------------------------------------------------------

    async def get_download_url(
        self,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> dict:
        """Return a download URL for a completed export job.

        For MVP, returns a placeholder presigned URL.
        Actual S3 presigned URL generation is future work.
        """
        job = await self.get_export_status(job_id, organization_id)

        if job.status != ExportJobStatus.COMPLETED:
            raise BusinessRuleException(
                f"Export job is in status '{job.status.value}'. "
                "Download is only available for completed jobs."
            )

        # TODO: Generate actual S3 presigned URL
        # from src.services.s3 import generate_presigned_url
        # url = generate_presigned_url(
        #     bucket=job.s3_bucket,
        #     key=job.s3_key,
        #     expiry=EXPORT_PRESIGNED_URL_EXPIRY_SECONDS,
        # )
        placeholder_url = (
            f"https://{job.s3_bucket}.s3.ap-south-1.amazonaws.com/"
            f"{job.s3_key}?presigned=placeholder"
            f"&expires={EXPORT_PRESIGNED_URL_EXPIRY_SECONDS}"
        )

        expires_at = datetime.now(UTC) + timedelta(
            seconds=EXPORT_PRESIGNED_URL_EXPIRY_SECONDS
        )

        return {
            "download_url": placeholder_url,
            "file_name": job.file_name or "export",
            "content_type": job.content_type or "application/octet-stream",
            "expires_at": expires_at,
        }
