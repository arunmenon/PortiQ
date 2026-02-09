"""Pydantic v2 schemas for PortiQ AI chat endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CardSchema(BaseModel):
    """Structured card data returned with AI responses."""

    model_config = ConfigDict(populate_by_name=True)

    type: str
    title: str
    data: dict


class ActionSchema(BaseModel):
    """Action button suggested by the AI assistant."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    variant: str = "primary"
    action: str
    params: dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request body for POST /portiq/chat."""

    model_config = ConfigDict(populate_by_name=True)

    message: str
    context: dict | None = None
    session_id: str | None = Field(None, alias="sessionId")


class ChatResponse(BaseModel):
    """Response body for POST /portiq/chat."""

    model_config = ConfigDict(populate_by_name=True, by_alias=True)

    message: str
    cards: list[CardSchema] | None = None
    actions: list[ActionSchema] | None = None
    context: dict | None = None
    session_id: str = Field(alias="session_id")


class ActionRequest(BaseModel):
    """Request body for POST /portiq/action."""

    model_config = ConfigDict(populate_by_name=True)

    action_id: str = Field(alias="actionId")
    action: str
    params: dict = Field(default_factory=dict)


class ActionResponse(BaseModel):
    """Response body for POST /portiq/action."""

    model_config = ConfigDict(populate_by_name=True)

    success: bool
    message: str
    data: dict | None = None


class SessionHistoryResponse(BaseModel):
    """Response body for GET /portiq/sessions/{session_id}/history."""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    messages: list[dict]
    created_at: datetime
