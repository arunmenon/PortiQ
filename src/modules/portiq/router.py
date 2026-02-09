"""PortiQ AI router — chat, actions, and session history endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.modules.portiq.chat_service import ChatService
from src.modules.portiq.schemas import (
    ActionRequest,
    ActionResponse,
    ChatRequest,
    ChatResponse,
    SessionHistoryResponse,
)
from src.modules.portiq.session_service import SessionService
from src.modules.portiq.tool_executor import ToolExecutor
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portiq", tags=["PortiQ AI"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ChatResponse:
    """Send a message to the PortiQ AI assistant and receive a structured response."""
    svc = ChatService(db)
    return await svc.handle_chat(
        message=body.message,
        session_id=body.session_id,
        context=body.context,
        user=current_user,
    )


@router.post("/action", response_model=ActionResponse)
async def execute_action(
    body: ActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ActionResponse:
    """Execute an AI-suggested action (e.g., create RFQ from search results)."""
    executor = ToolExecutor(db, current_user)

    try:
        result = await executor.execute(body.action, body.params)
        if "error" in result:
            return ActionResponse(
                success=False,
                message=result["error"],
            )
        return ActionResponse(
            success=True,
            message=f"Action '{body.action}' completed successfully.",
            data=result,
        )
    except Exception as exc:
        logger.warning("Action %s failed: %s", body.action, exc, exc_info=True)
        return ActionResponse(
            success=False,
            message=f"Action failed: {str(exc)}",
        )


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SessionHistoryResponse:
    """Get conversation history for a session."""
    svc = SessionService(db)
    session = await svc.get_history(session_id, user_id=current_user.id)

    if session is None:
        from src.exceptions import NotFoundException

        raise NotFoundException(f"Session {session_id} not found")

    return SessionHistoryResponse(
        session_id=str(session.id),
        messages=session.messages or [],
        created_at=session.created_at,
    )
