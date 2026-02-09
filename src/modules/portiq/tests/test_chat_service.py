"""Tests for PortiQ ChatService — chat loop, tool calling, session persistence."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.portiq.schemas import ChatResponse


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


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
def mock_session():
    session = MagicMock()
    session.id = uuid.uuid4()
    session.messages = []
    session.title = None
    session.context = None
    session.is_active = True
    session.created_at = datetime.now(UTC)
    return session


@pytest.fixture
def chat_service(mock_db):
    """Create ChatService with mocked OpenAI client to avoid SOCKS proxy issues."""
    with patch("src.modules.portiq.chat_service.AsyncOpenAI"):
        from src.modules.portiq.chat_service import ChatService

        svc = ChatService(mock_db)
    return svc


class TestChatServiceParseResponse:
    """Test _parse_structured_response and _extract_message."""

    def test_parse_plain_text(self, chat_service):
        cards, actions, context = chat_service._parse_structured_response(
            "Hello, how can I help?"
        )
        assert cards is None
        assert actions is None
        assert context is None

    def test_parse_json_with_cards(self, chat_service):
        content = json.dumps({
            "message": "Found 3 products",
            "cards": [
                {"type": "product_list", "title": "Marine Paints", "data": {"items": []}}
            ],
            "actions": [
                {
                    "id": "a1",
                    "label": "Create RFQ",
                    "variant": "primary",
                    "action": "create_rfq",
                    "params": {},
                }
            ],
        })
        cards, actions, context = chat_service._parse_structured_response(content)
        assert cards is not None
        assert len(cards) == 1
        assert cards[0].type == "product_list"
        assert actions is not None
        assert len(actions) == 1
        assert actions[0].label == "Create RFQ"

    def test_parse_json_in_code_block(self, chat_service):
        content = (
            '```json\n{"message": "test", "cards": '
            '[{"type": "suggestion", "title": "Tip", "data": {"text": "hint"}}]}\n```'
        )
        cards, actions, context = chat_service._parse_structured_response(content)
        assert cards is not None
        assert len(cards) == 1

    def test_extract_message_from_json(self, chat_service):
        content = json.dumps({"message": "Here are your results", "cards": []})
        msg = chat_service._extract_message(content)
        assert msg == "Here are your results"

    def test_extract_message_plain_text(self, chat_service):
        msg = chat_service._extract_message("Just a plain answer")
        assert msg == "Just a plain answer"

    def test_extract_message_empty(self, chat_service):
        msg = chat_service._extract_message("")
        assert "help" in msg.lower()

    def test_parse_json_with_context(self, chat_service):
        content = json.dumps({
            "message": "RFQ created",
            "context": {"type": "rfq", "data": {"id": "abc"}},
        })
        cards, actions, context = chat_service._parse_structured_response(content)
        assert context is not None
        assert context["type"] == "rfq"


class TestChatServiceBuildMessages:
    """Test _build_messages."""

    def test_build_with_empty_history(self, chat_service):
        messages = chat_service._build_messages([], "Hello", None)
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Hello"

    def test_build_with_history(self, chat_service):
        history = [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ]
        messages = chat_service._build_messages(history, "new question", None)
        # system + 2 history + 1 new = 4
        assert len(messages) == 4
        assert messages[1]["content"] == "previous question"

    def test_build_with_context(self, chat_service):
        context = {"type": "rfq", "data": {"id": "123"}}
        messages = chat_service._build_messages([], "Hello", context)
        # system + context_hint + user = 3
        assert len(messages) == 3
        assert "context" in messages[1]["content"].lower()


class TestChatServiceHandleChat:
    """Test the full handle_chat loop."""

    @pytest.mark.asyncio
    async def test_simple_response_no_tools(
        self, chat_service, mock_user, mock_session
    ):
        svc = chat_service

        # Mock session service
        with patch.object(
            svc.session_service, "get_or_create", return_value=mock_session
        ):
            with patch.object(
                svc.session_service, "update_session", new_callable=AsyncMock
            ):
                # Mock OpenAI response with no tool calls
                mock_choice = MagicMock()
                mock_choice.message.tool_calls = None
                mock_choice.message.content = json.dumps({
                    "message": "Hello! How can I help with maritime procurement?",
                })
                mock_response = MagicMock()
                mock_response.choices = [mock_choice]
                svc.client.chat.completions.create = AsyncMock(
                    return_value=mock_response
                )

                result = await svc.handle_chat(
                    message="Hello",
                    session_id=str(mock_session.id),
                    context=None,
                    user=mock_user,
                )

                assert isinstance(result, ChatResponse)
                assert "Hello" in result.message or "help" in result.message.lower()
                assert result.session_id == str(mock_session.id)

    @pytest.mark.asyncio
    async def test_response_with_tool_calls(
        self, chat_service, mock_user, mock_session
    ):
        svc = chat_service

        with patch.object(
            svc.session_service, "get_or_create", return_value=mock_session
        ):
            with patch.object(
                svc.session_service, "update_session", new_callable=AsyncMock
            ):
                # First call returns tool call
                tool_call = MagicMock()
                tool_call.id = "call_123"
                tool_call.function.name = "search_products"
                tool_call.function.arguments = json.dumps(
                    {"query": "marine paint", "limit": 5}
                )

                first_choice = MagicMock()
                first_choice.message.tool_calls = [tool_call]
                first_choice.message.content = None
                first_choice.message.model_dump.return_value = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "search_products",
                            "arguments": '{"query": "marine paint"}',
                        },
                    }],
                }
                first_response = MagicMock()
                first_response.choices = [first_choice]

                # Second call returns final response
                second_choice = MagicMock()
                second_choice.message.tool_calls = None
                second_choice.message.content = json.dumps({
                    "message": "Found 2 marine paints.",
                    "cards": [
                        {
                            "type": "product_list",
                            "title": "Marine Paints",
                            "data": {"items": []},
                        }
                    ],
                })
                second_response = MagicMock()
                second_response.choices = [second_choice]

                svc.client.chat.completions.create = AsyncMock(
                    side_effect=[first_response, second_response]
                )

                # Mock tool executor
                with patch(
                    "src.modules.portiq.chat_service.ToolExecutor"
                ) as mock_executor_cls:
                    mock_executor = AsyncMock()
                    mock_executor.execute.return_value = {
                        "items": [
                            {"name": "Marine Paint A"},
                            {"name": "Marine Paint B"},
                        ],
                        "total": 2,
                    }
                    mock_executor_cls.return_value = mock_executor

                    result = await svc.handle_chat(
                        message="Find marine paints",
                        session_id=str(mock_session.id),
                        context=None,
                        user=mock_user,
                    )

                    assert isinstance(result, ChatResponse)
                    assert (
                        "paint" in result.message.lower()
                        or result.cards is not None
                    )
                    mock_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_title_auto_set(
        self, chat_service, mock_user, mock_session
    ):
        svc = chat_service

        with patch.object(
            svc.session_service, "get_or_create", return_value=mock_session
        ):
            with patch.object(
                svc.session_service,
                "update_session",
                new_callable=AsyncMock,
            ) as update_mock:
                mock_choice = MagicMock()
                mock_choice.message.tool_calls = None
                mock_choice.message.content = "Simple response"
                mock_response = MagicMock()
                mock_response.choices = [mock_choice]
                svc.client.chat.completions.create = AsyncMock(
                    return_value=mock_response
                )

                await svc.handle_chat(
                    message="Find anchors",
                    session_id=str(mock_session.id),
                    context=None,
                    user=mock_user,
                )

                update_mock.assert_called_once()
                call_kwargs = update_mock.call_args
                title = (
                    call_kwargs.kwargs.get("title")
                    or call_kwargs[1].get("title")
                )
                assert title == "Find anchors"
