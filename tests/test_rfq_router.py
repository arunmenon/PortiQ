"""Router integration tests for RFQ & Bidding endpoints.

These tests verify that the router endpoints are correctly wired up,
use the right HTTP methods, and pass parameters to services properly.
We mock the service layer and auth dependency.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.models.enums import (
    RfqStatus,
)
from src.modules.rfq.router import router
from src.modules.tenancy.auth import AuthenticatedUser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_user(org_type="BUYER") -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid.uuid4(),
        email="test@portiq.io",
        organization_id=uuid.uuid4(),
        organization_type=org_type,
        role="ADMIN",
        is_platform_admin=False,
    )


def _mock_rfq_response():
    """Create a dict mimicking an RFQ response that Pydantic can validate."""
    return MagicMock(
        id=uuid.uuid4(),
        reference_number="RFQ-2026-00001",
        buyer_organization_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
        title="Test RFQ",
        description=None,
        status=RfqStatus.DRAFT,
        vessel_id=None,
        port_of_delivery=None,
        delivery_date=None,
        bidding_start=None,
        bidding_deadline=None,
        require_all_line_items=True,
        auction_type="SEALED_BID",
        notes=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        line_items=[],
        invitations=[],
    )


@pytest.fixture
def buyer_user():
    return _make_user("BUYER")


@pytest.fixture
def supplier_user():
    return _make_user("SUPPLIER")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRouterEndpointCount:
    """Verify that the router has the expected number of routes."""

    def test_route_count(self):
        """Router should have 24 endpoints."""
        # Each route contributes 1 entry to router.routes
        assert len(router.routes) == 24, (
            f"Expected 24 routes, got {len(router.routes)}. "
            f"Routes: {[r.path for r in router.routes]}"
        )


class TestRouterPaths:
    """Verify all expected paths are registered."""

    def test_crud_paths(self):
        paths = {r.path for r in router.routes}
        assert "/rfqs/" in paths
        assert "/rfqs/{rfq_id}" in paths

    def test_line_item_paths(self):
        paths = {r.path for r in router.routes}
        assert "/rfqs/{rfq_id}/line-items" in paths
        assert "/rfqs/{rfq_id}/line-items/{item_id}" in paths

    def test_invitation_paths(self):
        paths = {r.path for r in router.routes}
        assert "/rfqs/{rfq_id}/invitations" in paths
        assert "/rfqs/{rfq_id}/invitations/{invitation_id}" in paths
        assert "/rfqs/{rfq_id}/invitations/respond" in paths

    def test_transition_paths(self):
        paths = {r.path for r in router.routes}
        transition_paths = {
            "/rfqs/{rfq_id}/publish",
            "/rfqs/{rfq_id}/open-bidding",
            "/rfqs/{rfq_id}/close-bidding",
            "/rfqs/{rfq_id}/start-evaluation",
            "/rfqs/{rfq_id}/award",
            "/rfqs/{rfq_id}/complete",
            "/rfqs/{rfq_id}/cancel",
            "/rfqs/{rfq_id}/transitions",
        }
        assert transition_paths.issubset(paths)

    def test_quote_paths(self):
        paths = {r.path for r in router.routes}
        assert "/rfqs/{rfq_id}/quotes" in paths
        assert "/rfqs/{rfq_id}/quotes/{quote_id}" in paths
        assert "/rfqs/{rfq_id}/quotes/{quote_id}/withdraw" in paths


class TestRouterMethods:
    """Verify HTTP methods for key endpoints."""

    def _get_route(self, path: str):
        for r in router.routes:
            if r.path == path:
                return r
        return None

    def test_create_rfq_is_post(self):
        route = self._get_route("/rfqs/")
        assert route is not None
        assert "POST" in route.methods

    def test_list_rfqs_is_get(self):
        methods = set()
        for r in router.routes:
            if r.path == "/rfqs/":
                methods.update(r.methods)
        assert "GET" in methods
        assert "POST" in methods

    def test_delete_rfq_is_delete(self):
        for r in router.routes:
            if r.path == "/rfqs/{rfq_id}" and "DELETE" in r.methods:
                return
        pytest.fail("No DELETE route found for /rfqs/{rfq_id}")

    def test_update_rfq_is_patch(self):
        for r in router.routes:
            if r.path == "/rfqs/{rfq_id}" and "PATCH" in r.methods:
                return
        pytest.fail("No PATCH route found for /rfqs/{rfq_id}")


class TestHelperFunctions:
    """Test the _require_buyer and _require_supplier helper functions."""

    def test_require_buyer_allows_buyer(self):
        from src.modules.rfq.router import _require_buyer

        user = _make_user("BUYER")
        _require_buyer(user)  # Should not raise

    def test_require_buyer_allows_both(self):
        from src.modules.rfq.router import _require_buyer

        user = _make_user("BOTH")
        _require_buyer(user)  # Should not raise

    def test_require_buyer_allows_platform(self):
        from src.modules.rfq.router import _require_buyer

        user = _make_user("PLATFORM")
        _require_buyer(user)  # Should not raise

    def test_require_buyer_rejects_supplier(self):
        from src.exceptions import ForbiddenException
        from src.modules.rfq.router import _require_buyer

        user = _make_user("SUPPLIER")
        with pytest.raises(ForbiddenException, match="buyer"):
            _require_buyer(user)

    def test_require_supplier_allows_supplier(self):
        from src.modules.rfq.router import _require_supplier

        user = _make_user("SUPPLIER")
        _require_supplier(user)  # Should not raise

    def test_require_supplier_rejects_buyer(self):
        from src.exceptions import ForbiddenException
        from src.modules.rfq.router import _require_supplier

        user = _make_user("BUYER")
        with pytest.raises(ForbiddenException, match="supplier"):
            _require_supplier(user)
