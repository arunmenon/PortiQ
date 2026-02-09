"""Tests for PortiQ AI router — 3 endpoints, auth required."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.portiq.router import router
from src.modules.portiq.schemas import ChatResponse


@pytest.fixture
def mock_user():
    return MagicMock(
        id=uuid.uuid4(),
        email="buyer@test.com",
        organization_id=uuid.uuid4(),
        organization_type="BUYER",
        role="ADMIN",
        is_platform_admin=False,
    )


@pytest.fixture
def app(mock_user):
    from fastapi.responses import JSONResponse

    from src.database.session import get_db
    from src.exceptions import AppException
    from src.modules.tenancy.auth import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )

    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestChatEndpoint:
    def test_chat_requires_message(self, client):
        response = client.post("/api/v1/portiq/chat", json={})
        assert response.status_code == 422

    def test_chat_success(self, client, mock_user):
        with patch(
            "src.modules.portiq.router.ChatService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.handle_chat.return_value = ChatResponse(
                message="Hello!",
                session_id=str(uuid.uuid4()),
            )
            mock_svc_cls.return_value = mock_svc

            response = client.post(
                "/api/v1/portiq/chat",
                json={"message": "Hello", "sessionId": str(uuid.uuid4())},
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "session_id" in data

    def test_chat_with_context(self, client, mock_user):
        with patch(
            "src.modules.portiq.router.ChatService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.handle_chat.return_value = ChatResponse(
                message="I see you're looking at an RFQ.",
                session_id=str(uuid.uuid4()),
            )
            mock_svc_cls.return_value = mock_svc

            response = client.post(
                "/api/v1/portiq/chat",
                json={
                    "message": "Tell me about this RFQ",
                    "context": {"type": "rfq", "data": {"id": "abc"}},
                },
            )

            assert response.status_code == 200


class TestActionEndpoint:
    def test_action_requires_fields(self, client):
        response = client.post("/api/v1/portiq/action", json={})
        assert response.status_code == 422

    def test_action_success(self, client, mock_user):
        with patch(
            "src.modules.portiq.router.ToolExecutor"
        ) as mock_executor_cls:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = {"id": "123", "status": "created"}
            mock_executor_cls.return_value = mock_executor

            response = client.post(
                "/api/v1/portiq/action",
                json={
                    "actionId": "act-1",
                    "action": "create_rfq",
                    "params": {"title": "Test RFQ"},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_action_error(self, client, mock_user):
        with patch(
            "src.modules.portiq.router.ToolExecutor"
        ) as mock_executor_cls:
            mock_executor = AsyncMock()
            mock_executor.execute.return_value = {"error": "Invalid params"}
            mock_executor_cls.return_value = mock_executor

            response = client.post(
                "/api/v1/portiq/action",
                json={
                    "actionId": "act-2",
                    "action": "bad_action",
                    "params": {},
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestSessionHistoryEndpoint:
    def test_session_history_success(self, client, mock_user):
        session_id = uuid.uuid4()
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        mock_session.created_at = datetime.now(UTC)

        with patch(
            "src.modules.portiq.router.SessionService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_history.return_value = mock_session
            mock_svc_cls.return_value = mock_svc

            response = client.get(f"/api/v1/portiq/sessions/{session_id}/history")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == str(session_id)
            assert len(data["messages"]) == 2

    def test_session_history_not_found(self, client, mock_user):
        session_id = uuid.uuid4()

        with patch(
            "src.modules.portiq.router.SessionService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.get_history.return_value = None
            mock_svc_cls.return_value = mock_svc

            response = client.get(f"/api/v1/portiq/sessions/{session_id}/history")

            assert response.status_code == 404
