"""Shared test harness for PortiQ LLM integration testing.

Calls OpenAI directly with the PortiQ system prompt and tool definitions.
No database needed — tests the LLM handshake independently of backend services.

Usage:
    harness = LLMTestHarness()
    result = await harness.chat("Find marine paint")
    assert result.tool_calls[0].function.name == "search_products"
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from openai import AsyncOpenAI

# Import from our codebase
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.modules.portiq.system_prompt import SYSTEM_PROMPT
from src.modules.portiq.tools import TOOL_DEFINITIONS

# Load key from .env if not in environment
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_env_path) and not os.environ.get("OPENAI_API_KEY"):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


@dataclass
class ToolCall:
    """Represents a single tool call from the LLM."""
    id: str
    name: str
    arguments: dict
    raw_arguments: str


@dataclass
class LLMTurn:
    """Result from a single LLM API call."""
    content: str | None
    tool_calls: list[ToolCall]
    finish_reason: str
    model: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    @property
    def tool_names(self) -> list[str]:
        return [tc.name for tc in self.tool_calls]

    def parsed_json(self) -> dict | None:
        """Try to parse the content as JSON."""
        if not self.content:
            return None
        try:
            return json.loads(self.content.strip())
        except json.JSONDecodeError:
            # Try extracting from code block
            if "```json" in self.content:
                start = self.content.find("```json") + 7
                end = self.content.find("```", start)
                if end != -1:
                    try:
                        return json.loads(self.content[start:end].strip())
                    except json.JSONDecodeError:
                        pass
            return None


@dataclass
class ConversationResult:
    """Full conversation result after multiple turns."""
    turns: list[LLMTurn] = field(default_factory=list)
    final_content: str | None = None
    all_tool_calls: list[ToolCall] = field(default_factory=list)
    total_latency_ms: float = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    @property
    def tool_names_used(self) -> list[str]:
        return [tc.name for tc in self.all_tool_calls]

    def parsed_json(self) -> dict | None:
        if not self.final_content:
            return None
        try:
            return json.loads(self.final_content.strip())
        except json.JSONDecodeError:
            if "```json" in self.final_content:
                start = self.final_content.find("```json") + 7
                end = self.final_content.find("```", start)
                if end != -1:
                    try:
                        return json.loads(self.final_content[start:end].strip())
                    except json.JSONDecodeError:
                        pass
            return None


# Pre-built mock tool results for common tool calls
MOCK_TOOL_RESULTS = {
    "search_products": {
        "items": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "impa_code": "232001",
                "name": "Marine Anti-Fouling Paint Red 5L",
                "description": "Self-polishing anti-fouling paint for underwater hull application",
                "category": "Paints & Coatings",
                "score": 0.92,
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "impa_code": "232005",
                "name": "Marine Alkyd Enamel White 5L",
                "description": "High-gloss marine alkyd enamel for superstructure",
                "category": "Paints & Coatings",
                "score": 0.85,
            },
            {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "impa_code": "232010",
                "name": "Epoxy Primer Grey 5L",
                "description": "Two-component epoxy primer for steel surfaces",
                "category": "Paints & Coatings",
                "score": 0.78,
            },
        ],
        "total": 3,
        "query": "marine paint",
    },
    "get_product_details": {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "impa_code": "232001",
        "name": "Marine Anti-Fouling Paint Red 5L",
        "description": "Self-polishing anti-fouling paint for underwater hull application. TBT-free, copper-based.",
        "unit_of_measure": "LTR",
        "category_id": "cat-paints-001",
        "specifications": {
            "color": "Red",
            "volume": "5L",
            "type": "Anti-fouling",
            "application": "Underwater hull",
        },
    },
    "create_rfq": {
        "id": "rfq-550e8400-001",
        "reference_number": "RFQ-2026-00042",
        "title": "Paint Order for MV Ocean Star",
        "status": "DRAFT",
        "delivery_port": "INMAA",
        "line_item_count": 3,
    },
    "list_rfqs": {
        "items": [
            {
                "id": "rfq-001",
                "reference_number": "RFQ-2026-00040",
                "title": "Engine Room Supplies Q1",
                "status": "BIDDING_OPEN",
                "delivery_port": "INMAA",
                "created_at": "2026-01-15T10:30:00Z",
            },
            {
                "id": "rfq-002",
                "reference_number": "RFQ-2026-00041",
                "title": "Deck Paint Replenishment",
                "status": "DRAFT",
                "delivery_port": "INBOM",
                "created_at": "2026-02-01T09:00:00Z",
            },
        ],
        "total": 2,
    },
    "get_rfq_details": {
        "id": "rfq-001",
        "reference_number": "RFQ-2026-00040",
        "title": "Engine Room Supplies Q1",
        "description": "Quarterly engine room supply procurement",
        "status": "BIDDING_OPEN",
        "delivery_port": "INMAA",
        "delivery_date": "2026-03-01",
        "bidding_deadline": "2026-02-20T18:00:00Z",
        "currency": "USD",
        "line_items": [
            {"line_number": 1, "description": "Engine Oil SAE 40", "quantity": 200, "unit_of_measure": "LTR", "impa_code": "450120"},
            {"line_number": 2, "description": "Oil Filter Element", "quantity": 10, "unit_of_measure": "PCS", "impa_code": "451001"},
        ],
        "invitations": [
            {"supplier_organization_id": "sup-001", "status": "ACCEPTED"},
            {"supplier_organization_id": "sup-002", "status": "PENDING"},
        ],
        "created_at": "2026-01-15T10:30:00Z",
    },
    "list_suppliers": {
        "items": [
            {
                "id": "sup-001",
                "company_name": "Chennai Marine Supplies Pvt Ltd",
                "tier": "PREFERRED",
                "categories": ["Paints", "Chemicals", "Safety Equipment"],
                "port_coverage": ["INMAA", "INTUT"],
                "city": "Chennai",
                "country": "India",
            },
            {
                "id": "sup-002",
                "company_name": "Mumbai Ship Stores International",
                "tier": "VERIFIED",
                "categories": ["Engine Parts", "Paints", "Provisions"],
                "port_coverage": ["INBOM", "INNSA"],
                "city": "Mumbai",
                "country": "India",
            },
        ],
        "total": 2,
    },
    "get_intelligence": {
        "price_benchmarks": [
            {"impa_code": "232001", "p25": 85.0, "p50": 120.0, "p75": 155.0, "sample_count": 24, "currency": "USD"},
        ],
        "suppliers": {
            "ranked": [
                {"supplier_id": "sup-001", "company_name": "Chennai Marine Supplies", "tier": "PREFERRED", "score": 0.92},
                {"supplier_id": "sup-003", "company_name": "Vizag Chandlers", "tier": "VERIFIED", "score": 0.78},
            ],
            "total": 5,
        },
        "risks": [
            {"type": "TIGHT_TIMELINE", "severity": "MEDIUM", "message": "Delivery deadline is within 10 days of expected arrival."},
        ],
        "timing": {
            "assessment": "SUFFICIENT",
            "recommended_bidding_window_days": 7,
            "vessel_eta": "2026-02-25T14:00:00Z",
            "avg_response_days": 3.5,
        },
    },
    "predict_consumption": {
        "items": [
            {"category": "Provisions", "product_name": "Rice", "impa_code": "390001", "predicted_quantity": 500, "unit": "KG", "confidence": 0.88},
            {"category": "Provisions", "product_name": "Cooking Oil", "impa_code": "390050", "predicted_quantity": 100, "unit": "LTR", "confidence": 0.85},
            {"category": "Cabin Stores", "product_name": "Toilet Paper", "impa_code": "174001", "predicted_quantity": 200, "unit": "ROL", "confidence": 0.82},
        ],
        "vessel_id": "vessel-001",
        "voyage_days": 14,
    },
    "get_vessel_info": {
        "id": "vessel-001",
        "name": "MV Ocean Star",
        "imo_number": "9876543",
        "mmsi": "419000123",
        "vessel_type": "BULK_CARRIER",
        "status": "ACTIVE",
        "flag_state": "India",
        "gross_tonnage": 52000,
        "deadweight_tonnage": 82000,
        "year_built": 2018,
        "latest_position": {
            "latitude": 13.0827,
            "longitude": 80.2707,
            "speed_knots": 12.5,
            "recorded_at": "2026-02-08T06:30:00Z",
        },
    },
    "match_suppliers_for_port": {
        "port": "INMAA",
        "ranked_suppliers": [
            {
                "supplier_id": "sup-001",
                "company_name": "Chennai Marine Supplies Pvt Ltd",
                "tier": "PREFERRED",
                "score": 0.92,
                "port_coverage": ["INMAA", "INTUT"],
                "category_match_ratio": 0.85,
            },
        ],
        "total_candidates": 5,
    },
}


class LLMTestHarness:
    """Test harness for PortiQ LLM integration testing.

    Calls OpenAI directly with the PortiQ system prompt and tool definitions.
    Tool calls are intercepted and mock results are returned, allowing us to
    test the full conversation loop without a database.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        max_iterations: int = 5,
        custom_system_prompt: str | None = None,
        mock_results: dict | None = None,
    ):
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.max_iterations = max_iterations
        self.system_prompt = custom_system_prompt or SYSTEM_PROMPT
        self.tool_definitions = TOOL_DEFINITIONS
        self.mock_results = mock_results or MOCK_TOOL_RESULTS

    async def single_turn(
        self,
        message: str,
        history: list[dict] | None = None,
        context: dict | None = None,
    ) -> LLMTurn:
        """Send a single message and get one LLM response (may include tool calls).

        Does NOT execute tools — just returns whatever the LLM decides to do.
        Useful for testing tool selection logic.
        """
        messages = self._build_messages(history, message, context)

        start = time.monotonic()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tool_definitions,
            max_tokens=self.max_tokens,
        )
        latency = (time.monotonic() - start) * 1000

        choice = response.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                    raw_arguments=tc.function.arguments,
                ))

        return LLMTurn(
            content=choice.message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            model=response.model,
            latency_ms=latency,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
        )

    async def chat(
        self,
        message: str,
        history: list[dict] | None = None,
        context: dict | None = None,
        tool_result_overrides: dict[str, dict] | None = None,
    ) -> ConversationResult:
        """Run a full conversation loop with mock tool execution.

        Mirrors the ChatService loop: call LLM → execute tools → call LLM again
        until the LLM produces a final text response or max iterations reached.
        """
        messages = self._build_messages(history, message, context)
        result = ConversationResult()
        overrides = tool_result_overrides or {}

        for _ in range(self.max_iterations):
            start = time.monotonic()
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_definitions,
                max_tokens=self.max_tokens,
            )
            latency = (time.monotonic() - start) * 1000

            choice = response.choices[0]
            tool_calls = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args,
                        raw_arguments=tc.function.arguments,
                    ))

            turn = LLMTurn(
                content=choice.message.content,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                model=response.model,
                latency_ms=latency,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
            )
            result.turns.append(turn)
            result.total_latency_ms += latency
            result.total_prompt_tokens += turn.prompt_tokens
            result.total_completion_tokens += turn.completion_tokens

            if not choice.message.tool_calls:
                result.final_content = choice.message.content or ""
                break

            # Append assistant message and execute tool calls with mocks
            messages.append(choice.message.model_dump())
            result.all_tool_calls.extend(tool_calls)

            for tc in tool_calls:
                mock = overrides.get(tc.name) or self.mock_results.get(tc.name, {"error": f"No mock for {tc.name}"})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(mock, default=str),
                })
        else:
            result.final_content = result.turns[-1].content if result.turns else None

        return result

    async def multi_turn_chat(
        self,
        messages_sequence: list[str],
        context: dict | None = None,
    ) -> list[ConversationResult]:
        """Run a multi-turn conversation (simulating session history).

        Each message in the sequence builds on the previous conversation.
        Returns a list of ConversationResult, one per user message.
        """
        history: list[dict] = []
        results: list[ConversationResult] = []

        for msg in messages_sequence:
            result = await self.chat(msg, history=history, context=context)
            results.append(result)

            # Build history for next turn
            history.append({"role": "user", "content": msg})
            if result.final_content:
                history.append({"role": "assistant", "content": result.final_content})

        return results

    def _build_messages(
        self,
        history: list[dict] | None,
        message: str,
        context: dict | None,
    ) -> list[dict]:
        """Build the OpenAI messages array — mirrors ChatService._build_messages."""
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
        ]
        for msg in (history or []):
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        if context:
            messages.append({
                "role": "system",
                "content": f"[Current context: {json.dumps(context, default=str)}]",
            })
        messages.append({"role": "user", "content": message})
        return messages


# ---- Assertion helpers ----

def assert_tool_called(turn_or_result, tool_name: str, msg: str = "") -> ToolCall:
    """Assert that a specific tool was called and return it."""
    if isinstance(turn_or_result, LLMTurn):
        names = turn_or_result.tool_names
        calls = turn_or_result.tool_calls
    else:
        names = turn_or_result.tool_names_used
        calls = turn_or_result.all_tool_calls
    assert tool_name in names, f"Expected tool '{tool_name}' to be called, got {names}. {msg}"
    return next(tc for tc in calls if tc.name == tool_name)


def assert_no_tool_calls(turn: LLMTurn, msg: str = ""):
    """Assert the LLM did not make any tool calls."""
    assert not turn.has_tool_calls, f"Expected no tool calls, got {turn.tool_names}. {msg}"


def assert_valid_json_response(result: ConversationResult, msg: str = "") -> dict:
    """Assert the final response is valid JSON with at least a 'message' field."""
    parsed = result.parsed_json()
    assert parsed is not None, f"Final response is not valid JSON: {result.final_content[:200] if result.final_content else 'None'}. {msg}"
    assert "message" in parsed, f"JSON response missing 'message' field: {list(parsed.keys())}. {msg}"
    return parsed


def assert_cards_present(parsed: dict, expected_type: str | None = None, msg: str = "") -> list:
    """Assert cards are present in the parsed JSON response."""
    assert "cards" in parsed and parsed["cards"], f"Expected cards in response, got none. {msg}"
    cards = parsed["cards"]
    if expected_type:
        types = [c.get("type") for c in cards]
        assert expected_type in types, f"Expected card type '{expected_type}', got {types}. {msg}"
    return cards


def assert_actions_present(parsed: dict, msg: str = "") -> list:
    """Assert action buttons are present in the parsed JSON response."""
    assert "actions" in parsed and parsed["actions"], f"Expected actions in response, got none. {msg}"
    return parsed["actions"]


def assert_message_contains(result: ConversationResult, *keywords: str, case_sensitive: bool = False):
    """Assert the final message contains specific keywords."""
    content = result.final_content or ""
    parsed = result.parsed_json()
    if parsed and "message" in parsed:
        content = parsed["message"]

    check = content if case_sensitive else content.lower()
    for kw in keywords:
        kw_check = kw if case_sensitive else kw.lower()
        assert kw_check in check, f"Expected '{kw}' in response message, got: {content[:300]}"


def assert_tool_argument(tool_call: ToolCall, key: str, expected_value=None, msg: str = ""):
    """Assert a tool call has a specific argument, optionally with a specific value."""
    assert key in tool_call.arguments, f"Expected argument '{key}' in {tool_call.name} args {tool_call.arguments}. {msg}"
    if expected_value is not None:
        actual = tool_call.arguments[key]
        assert actual == expected_value, f"Expected {key}={expected_value}, got {actual}. {msg}"
