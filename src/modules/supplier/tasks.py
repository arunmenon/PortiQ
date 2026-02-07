"""Celery background tasks for supplier verification workflows."""

from __future__ import annotations

from celery_app import celery


@celery.task(name="src.modules.supplier.verify_supplier_documents")
def verify_supplier_documents(supplier_id: str) -> dict:
    """Validate document presence and mark verification status.

    TODO: Integrate with Signzy/Karza for real document verification.
    """
    return {"supplier_id": supplier_id, "status": "stub_verification_pending"}


@celery.task(name="src.modules.supplier.check_document_expiry")
def check_document_expiry() -> dict:
    """Periodic task to flag documents nearing expiry.

    TODO: Implement expiry checking logic + notification triggers.
    """
    return {"status": "stub_expiry_check_pending"}
