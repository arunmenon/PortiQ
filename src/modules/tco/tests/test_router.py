"""Tests for TCO router — endpoint access, auth, and buyer-only checks."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import ForbiddenException, NotFoundException
from src.modules.tco.router import _require_buyer_or_platform, _verify_rfq_access
from src.modules.tenancy.auth import AuthenticatedUser


def _make_user(
    org_type: str = "BUYER",
    is_platform_admin: bool = False,
    org_id: uuid.UUID | None = None,
) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid.uuid4(),
        email="test@example.com",
        organization_id=org_id or uuid.uuid4(),
        organization_type=org_type,
        role="ADMIN",
        is_platform_admin=is_platform_admin,
    )


class TestRequireBuyerOrPlatform:
    def test_buyer_allowed(self) -> None:
        user = _make_user(org_type="BUYER")
        _require_buyer_or_platform(user)  # Should not raise

    def test_platform_allowed(self) -> None:
        user = _make_user(org_type="PLATFORM")
        _require_buyer_or_platform(user)  # Should not raise

    def test_both_allowed(self) -> None:
        user = _make_user(org_type="BOTH")
        _require_buyer_or_platform(user)  # Should not raise

    def test_supplier_rejected(self) -> None:
        user = _make_user(org_type="SUPPLIER")
        with pytest.raises(ForbiddenException, match="buyer organizations only"):
            _require_buyer_or_platform(user)


class TestVerifyRfqAccess:
    @pytest.mark.asyncio
    async def test_owner_has_access(self) -> None:
        org_id = uuid.uuid4()
        user = _make_user(org_id=org_id)

        rfq = MagicMock()
        rfq.id = uuid.uuid4()
        rfq.buyer_organization_id = org_id

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rfq
        db.execute.return_value = mock_result

        result = await _verify_rfq_access(rfq.id, user, db)
        assert result.id == rfq.id

    @pytest.mark.asyncio
    async def test_non_owner_denied(self) -> None:
        user = _make_user(org_id=uuid.uuid4())

        rfq = MagicMock()
        rfq.id = uuid.uuid4()
        rfq.buyer_organization_id = uuid.uuid4()  # Different org

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rfq
        db.execute.return_value = mock_result

        with pytest.raises(ForbiddenException, match="do not have access"):
            await _verify_rfq_access(rfq.id, user, db)

    @pytest.mark.asyncio
    async def test_platform_admin_has_access(self) -> None:
        user = _make_user(org_id=uuid.uuid4(), is_platform_admin=True)

        rfq = MagicMock()
        rfq.id = uuid.uuid4()
        rfq.buyer_organization_id = uuid.uuid4()  # Different org

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rfq
        db.execute.return_value = mock_result

        result = await _verify_rfq_access(rfq.id, user, db)
        assert result.id == rfq.id

    @pytest.mark.asyncio
    async def test_rfq_not_found(self) -> None:
        user = _make_user()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(NotFoundException, match="RFQ"):
            await _verify_rfq_access(uuid.uuid4(), user, db)
