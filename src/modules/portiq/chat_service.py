"""ChatService — orchestrates the PortiQ AI chat loop with OpenAI function calling."""

from __future__ import annotations

import json
import logging
import uuid

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.modules.portiq.constants import MAX_TOOL_CALL_ITERATIONS
from src.modules.portiq.schemas import (
    ActionSchema,
    CardSchema,
    ChatResponse,
)
from src.modules.portiq.session_service import SessionService
from src.modules.portiq.system_prompt import SYSTEM_PROMPT
from src.modules.portiq.tool_executor import ToolExecutor
from src.modules.portiq.tools import TOOL_DEFINITIONS
from src.modules.tenancy.auth import AuthenticatedUser

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates the PortiQ AI conversation loop."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.session_service = SessionService(db)

    async def handle_chat(
        self,
        message: str,
        session_id: str | None,
        context: dict | None,
        user: AuthenticatedUser,
    ) -> ChatResponse:
        """Process a user message through the AI chat loop.

        1. Load/create session
        2. Build OpenAI messages from system prompt + history + new message
        3. Loop (max iterations): call LLM, execute tool calls if any
        4. Parse final response for structured cards/actions
        5. Persist to session
        6. Return ChatResponse
        """
        # 1. Load or create session
        session = await self.session_service.get_or_create(
            user_id=user.id,
            organization_id=user.organization_id,
            session_id=session_id,
        )

        # 2. Build messages
        openai_messages = self._build_messages(session.messages, message, context)

        # 3. Chat loop with tool calling
        tool_executor = ToolExecutor(self.db, user)
        final_content = ""

        for iteration in range(MAX_TOOL_CALL_ITERATIONS):
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=openai_messages,
                tools=TOOL_DEFINITIONS,
                max_tokens=settings.portiq_max_tokens,
            )

            choice = response.choices[0]
            assistant_message = choice.message

            if not assistant_message.tool_calls:
                # No tool calls — this is the final response
                final_content = assistant_message.content or ""
                break

            # Append assistant message with tool calls
            openai_messages.append(assistant_message.model_dump())

            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                logger.info(
                    "Executing tool %s (call_id=%s, iteration=%d)",
                    tool_name,
                    tool_call.id,
                    iteration,
                )
                result = await tool_executor.execute(tool_name, arguments)

                openai_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        else:
            # Reached max iterations — use whatever we have
            if not final_content:
                final_content = "I've gathered the information. Let me summarize what I found."

        # 4. Parse structured response
        cards, actions, response_context = self._parse_structured_response(final_content)

        # Use message text from parsed response
        display_message = self._extract_message(final_content)

        # 5. Persist session
        session_messages = list(session.messages or [])
        session_messages.append({"role": "user", "content": message})
        session_messages.append({
            "role": "assistant",
            "content": display_message,
            "cards": [c.model_dump() for c in cards] if cards else None,
            "actions": [a.model_dump() for a in actions] if actions else None,
        })

        # Auto-generate title from first message
        title = session.title
        if not title and message:
            title = message[:100]

        await self.session_service.update_session(
            session_id=session.id,
            messages=session_messages,
            context=response_context or context,
            title=title,
        )

        # 6. Return response
        return ChatResponse(
            message=display_message,
            cards=cards if cards else None,
            actions=actions if actions else None,
            context=response_context,
            session_id=str(session.id),
        )

    def _build_messages(
        self,
        session_messages: list[dict],
        new_message: str,
        context: dict | None,
    ) -> list[dict]:
        """Build the OpenAI messages array."""
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Add session history (only user/assistant messages)
        for msg in (session_messages or []):
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Add context hint if available
        if context:
            context_hint = f"[Current context: {json.dumps(context, default=str)}]"
            messages.append({"role": "system", "content": context_hint})

        # Add new user message
        messages.append({"role": "user", "content": new_message})

        return messages

    def _parse_structured_response(
        self, content: str
    ) -> tuple[list[CardSchema] | None, list[ActionSchema] | None, dict | None]:
        """Try to parse structured JSON from the LLM response.

        The system prompt instructs the LLM to return JSON, but it may
        return plain text. We handle both gracefully.
        """
        if not content:
            return None, None, None

        # Try to extract JSON from the response
        stripped = content.strip()

        # Try direct JSON parse
        parsed = self._try_parse_json(stripped)

        # Try extracting from markdown code block
        if parsed is None and "```" in stripped:
            start = stripped.find("```json")
            if start != -1:
                start = stripped.find("\n", start) + 1
                end = stripped.find("```", start)
                if end != -1:
                    parsed = self._try_parse_json(stripped[start:end].strip())
            if parsed is None:
                start = stripped.find("```")
                if start != -1:
                    start = stripped.find("\n", start) + 1
                    end = stripped.find("```", start)
                    if end != -1:
                        parsed = self._try_parse_json(stripped[start:end].strip())

        if parsed is None or not isinstance(parsed, dict):
            return None, None, None

        cards = None
        if "cards" in parsed and isinstance(parsed["cards"], list):
            cards = []
            for card_data in parsed["cards"]:
                if isinstance(card_data, dict):
                    cards.append(
                        CardSchema(
                            type=card_data.get("type", "suggestion"),
                            title=card_data.get("title", ""),
                            data=card_data.get("data", {}),
                        )
                    )

        actions = None
        if "actions" in parsed and isinstance(parsed["actions"], list):
            actions = []
            for action_data in parsed["actions"]:
                if isinstance(action_data, dict):
                    actions.append(
                        ActionSchema(
                            id=action_data.get("id", str(uuid.uuid4())),
                            label=action_data.get("label", ""),
                            variant=action_data.get("variant", "primary"),
                            action=action_data.get("action", ""),
                            params=action_data.get("params", {}),
                        )
                    )

        context = parsed.get("context") if isinstance(parsed.get("context"), dict) else None

        return cards, actions, context

    def _extract_message(self, content: str) -> str:
        """Extract the display message from the LLM response.

        If the response is JSON, extract the 'message' field.
        Otherwise return the raw content.
        """
        if not content:
            return "I'm here to help with maritime procurement. What would you like to do?"

        stripped = content.strip()
        parsed = self._try_parse_json(stripped)

        # Try code block extraction
        if parsed is None and "```" in stripped:
            start = stripped.find("```json")
            if start != -1:
                start = stripped.find("\n", start) + 1
                end = stripped.find("```", start)
                if end != -1:
                    parsed = self._try_parse_json(stripped[start:end].strip())

        if parsed and isinstance(parsed, dict) and "message" in parsed:
            return parsed["message"]

        return content

    @staticmethod
    def _try_parse_json(text: str) -> dict | list | None:
        """Attempt to parse JSON, returning None on failure."""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
