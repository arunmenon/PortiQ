"""Session service — manages PortiQ conversation session persistence."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation_session import ConversationSession
from src.modules.portiq.constants import MAX_SESSION_HISTORY_MESSAGES

logger = logging.getLogger(__name__)


class SessionService:
    """CRUD for conversation sessions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        session_id: str | None = None,
    ) -> ConversationSession:
        """Find an existing session by ID or create a new one."""
        if session_id:
            try:
                parsed_id = uuid.UUID(session_id)
                result = await self.db.execute(
                    select(ConversationSession).where(
                        ConversationSession.id == parsed_id,
                        ConversationSession.user_id == user_id,
                        ConversationSession.is_active.is_(True),
                    )
                )
                session = result.scalar_one_or_none()
                if session is not None:
                    return session
            except (ValueError, AttributeError):
                pass

        # Create new session
        session = ConversationSession(
            user_id=user_id,
            organization_id=organization_id,
            messages=[],
            is_active=True,
        )
        self.db.add(session)
        await self.db.flush()
        logger.info("Created new conversation session %s for user %s", session.id, user_id)
        return session

    async def get_history(
        self, session_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> ConversationSession | None:
        """Return session with its messages.

        When user_id is provided, enforces ownership check (prevents IDOR).
        """
        query = select(ConversationSession).where(
            ConversationSession.id == session_id
        )
        if user_id is not None:
            query = query.where(ConversationSession.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_session(
        self,
        session_id: uuid.UUID,
        messages: list[dict],
        context: dict | None = None,
        title: str | None = None,
    ) -> None:
        """Persist messages and context to the session.

        Trims messages to MAX_SESSION_HISTORY_MESSAGES.
        """
        trimmed = messages[-MAX_SESSION_HISTORY_MESSAGES:]
        update_values: dict = {"messages": trimmed}
        if context is not None:
            update_values["context"] = context
        if title is not None:
            update_values["title"] = title

        await self.db.execute(
            update(ConversationSession)
            .where(ConversationSession.id == session_id)
            .values(**update_values)
        )

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[ConversationSession]:
        """List a user's active sessions, most recent first."""
        result = await self.db.execute(
            select(ConversationSession)
            .where(
                ConversationSession.user_id == user_id,
                ConversationSession.is_active.is_(True),
            )
            .order_by(ConversationSession.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
