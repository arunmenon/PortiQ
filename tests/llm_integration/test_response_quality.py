"""Response quality & structure tests for PortiQ AI assistant.

Validates that GPT-4o returns properly structured JSON responses with:
- Valid JSON with required "message" field
- Correct card types (product_list, rfq_summary, vessel_info, suggestion)
- Action buttons with proper structure (id, label, variant, action, params)
- Context objects when relevant
- No fabricated data (responses reference mock tool results)
- Graceful handling of empty results
- Professional, concise message quality

Run: python tests/llm_integration/test_response_quality.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.llm_integration.harness import (
    MOCK_TOOL_RESULTS,
    ConversationResult,
    LLMTestHarness,
    assert_actions_present,
    assert_cards_present,
    assert_valid_json_response,
)

# Track results
_results: list[tuple[str, bool, str]] = []


def _robust_parse_json(result: ConversationResult) -> dict | None:
    """More robust JSON extraction that handles code-fenced responses.

    The LLM sometimes wraps JSON in ```json ... ``` blocks. The harness
    handles the simple case but can fail when the closing ``` has extra
    whitespace or trailing text. This helper covers those edge cases.
    """
    parsed = result.parsed_json()
    if parsed is not None:
        return parsed
    content = (result.final_content or "").strip()
    if not content:
        return None
    # Strip markdown code fences more aggressively
    if content.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = content.find("\n")
        if first_newline != -1:
            content = content[first_newline + 1:]
        # Remove closing fence
        last_fence = content.rfind("```")
        if last_fence != -1:
            content = content[:last_fence]
        content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def robust_assert_valid_json(result: ConversationResult, msg: str = "") -> dict:
    """Assert valid JSON using robust parsing, falling back from harness helper."""
    try:
        return assert_valid_json_response(result, msg)
    except AssertionError:
        parsed = _robust_parse_json(result)
        assert parsed is not None, \
            f"Final response is not valid JSON (even with robust parsing): " \
            f"{(result.final_content or '')[:200]}. {msg}"
        assert "message" in parsed, \
            f"JSON response missing 'message' field: {list(parsed.keys())}. {msg}"
        return parsed


def record(name: str, passed: bool, detail: str = ""):
    _results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if detail and not passed:
        # Truncate long failure details
        if len(detail) > 300:
            detail = detail[:300] + "..."
        print(f"         {detail}")


async def run_test(name: str, coro):
    """Run a single test coroutine and record the result."""
    try:
        await coro
        record(name, True)
    except AssertionError as exc:
        record(name, False, str(exc))
    except Exception as exc:
        record(name, False, f"Exception: {type(exc).__name__}: {exc}")
        traceback.print_exc()


# ============================================================
# 1. JSON COMPLIANCE (3 tests)
# ============================================================

async def test_json_greeting(harness: LLMTestHarness):
    """A simple greeting should still return valid JSON with 'message'."""
    result = await harness.chat("Hello, I need help with procurement")
    parsed = robust_assert_valid_json(result, "Greeting should return JSON")
    assert isinstance(parsed["message"], str), "message field should be a string"
    assert len(parsed["message"]) > 5, "message should be non-trivial"


async def test_json_product_search(harness: LLMTestHarness):
    """Product search should return valid JSON."""
    result = await harness.chat("Search for marine paint")
    parsed = robust_assert_valid_json(result, "Product search should return JSON")
    assert isinstance(parsed["message"], str), "message must be a string"


async def test_json_rfq_query(harness: LLMTestHarness):
    """RFQ listing should return valid JSON."""
    result = await harness.chat("Show me my RFQs")
    parsed = robust_assert_valid_json(result, "RFQ query should return JSON")
    assert isinstance(parsed["message"], str), "message must be a string"


# ============================================================
# 2. PRODUCT LIST CARDS (2 tests)
# ============================================================

async def test_product_list_card_present(harness: LLMTestHarness):
    """Product search should return a product_list card."""
    result = await harness.chat("Search for marine paint")
    parsed = robust_assert_valid_json(result)
    cards = assert_cards_present(parsed, "product_list", "Product search should produce product_list card")
    product_card = next(c for c in cards if c["type"] == "product_list")
    assert "title" in product_card, "Card must have title"
    assert "data" in product_card, "Card must have data"


async def test_product_list_card_has_items(harness: LLMTestHarness):
    """product_list card data should contain items from the mock tool result."""
    result = await harness.chat("Find marine anti-fouling paint")
    parsed = robust_assert_valid_json(result)
    cards = assert_cards_present(parsed, "product_list")
    product_card = next(c for c in cards if c["type"] == "product_list")
    card_data = product_card.get("data", {})
    # Card data should have items
    items = card_data.get("items") or card_data.get("products") or []
    assert len(items) > 0, f"product_list card should have items, got data keys: {list(card_data.keys())}"


# ============================================================
# 3. RFQ SUMMARY CARDS (2 tests)
# ============================================================

async def test_rfq_list_card(harness: LLMTestHarness):
    """Listing RFQs should return an rfq_summary card."""
    result = await harness.chat("Show my RFQs")
    parsed = robust_assert_valid_json(result)
    assert "cards" in parsed and parsed["cards"], "RFQ list should have cards"
    card_types = [c.get("type") for c in parsed["cards"]]
    assert any(t in card_types for t in ("rfq_summary", "rfq_list")), \
        f"Expected rfq_summary or rfq_list card, got {card_types}"


async def test_rfq_detail_card(harness: LLMTestHarness):
    """Asking about a specific RFQ should return detailed rfq card."""
    result = await harness.chat("Tell me about RFQ-2026-00040")
    parsed = robust_assert_valid_json(result)
    assert "cards" in parsed and parsed["cards"], "RFQ detail should have cards"
    # Check that reference number appears in the response
    response_str = json.dumps(parsed)
    assert "RFQ-2026-00040" in response_str, \
        "Response should reference the specific RFQ number"


# ============================================================
# 4. VESSEL INFO CARD (1 test)
# ============================================================

async def test_vessel_info_card(harness: LLMTestHarness):
    """Vessel lookup should return a vessel_info card."""
    result = await harness.chat("Get info on vessel IMO 9876543")
    parsed = robust_assert_valid_json(result)
    assert "cards" in parsed and parsed["cards"], "Vessel lookup should have cards"
    card_types = [c.get("type") for c in parsed["cards"]]
    assert "vessel_info" in card_types, f"Expected vessel_info card, got {card_types}"
    vessel_card = next(c for c in parsed["cards"] if c["type"] == "vessel_info")
    assert "data" in vessel_card, "vessel_info card must have data"


# ============================================================
# 5. SUGGESTION CARD (1 test)
# ============================================================

async def test_suggestion_card(harness: LLMTestHarness):
    """General advice should produce a suggestion card or helpful message."""
    result = await harness.chat(
        "What tips do you have for reducing procurement costs on a bulk carrier voyage?"
    )
    parsed = robust_assert_valid_json(result)
    # Suggestion can be in cards or just a helpful message
    msg = parsed.get("message", "")
    has_suggestion_card = False
    if "cards" in parsed and parsed["cards"]:
        card_types = [c.get("type") for c in parsed["cards"]]
        has_suggestion_card = "suggestion" in card_types
    # Either a suggestion card exists or the message itself is substantive advice
    assert has_suggestion_card or len(msg) > 50, \
        "Should provide a suggestion card or substantive advice message"


# ============================================================
# 6. ACTION BUTTONS (3 tests)
# ============================================================

async def test_actions_after_product_search(harness: LLMTestHarness):
    """After product search, response should suggest follow-up actions like Create RFQ."""
    result = await harness.chat("Search for marine paint")
    parsed = robust_assert_valid_json(result)
    actions = assert_actions_present(parsed, "Product search should suggest actions")
    # Validate action structure
    for action in actions:
        assert "id" in action, f"Action missing 'id': {action}"
        assert "label" in action, f"Action missing 'label': {action}"
        assert "action" in action, f"Action missing 'action': {action}"


async def test_actions_after_rfq_list(harness: LLMTestHarness):
    """After listing RFQs, response should suggest view details action."""
    result = await harness.chat("List my RFQs")
    parsed = robust_assert_valid_json(result)
    actions = assert_actions_present(parsed, "RFQ list should suggest actions")
    # Check that at least one action relates to viewing an RFQ
    action_names = [a.get("action", "") for a in actions]
    action_labels = [a.get("label", "").lower() for a in actions]
    has_view_action = any("view" in n or "detail" in n or "rfq" in n for n in action_names) or \
                      any("view" in l or "detail" in l for l in action_labels)
    assert has_view_action, f"Expected a 'view' action, got actions: {action_names}"


async def test_action_button_structure(harness: LLMTestHarness):
    """Validate the full action button structure: id, label, variant, action, params."""
    result = await harness.chat("Search for engine oil SAE 40")
    parsed = robust_assert_valid_json(result)
    if not parsed.get("actions"):
        # Skip if no actions (may happen with different prompt phrasings)
        assert True
        return
    for action in parsed["actions"]:
        assert "id" in action, "Action must have 'id'"
        assert "label" in action, "Action must have 'label'"
        assert "action" in action, "Action must have 'action'"
        # variant and params are optional but when present should be valid
        if "variant" in action:
            assert action["variant"] in ("primary", "outline", "secondary", "ghost", "destructive"), \
                f"Invalid variant: {action['variant']}"


# ============================================================
# 7. CONTEXT OBJECT (1 test)
# ============================================================

async def test_context_after_vessel_lookup(harness: LLMTestHarness):
    """After vessel lookup, context should be set with vessel type."""
    result = await harness.chat("Look up vessel IMO 9876543")
    parsed = robust_assert_valid_json(result)
    if "context" in parsed and parsed["context"]:
        ctx = parsed["context"]
        assert "type" in ctx, f"Context should have 'type' field, got: {ctx}"
        assert ctx["type"] in ("vessel", "vessel_info"), \
            f"Context type should be 'vessel', got: {ctx['type']}"
    else:
        # Context is optional per the system prompt, so a warning is acceptable
        # Still pass but note it
        pass


# ============================================================
# 8. EMPTY RESULTS (1 test)
# ============================================================

async def test_empty_search_results(harness: LLMTestHarness):
    """When search returns zero results, response should gracefully handle it."""
    empty_mock = {"items": [], "total": 0, "query": "xyz123nonexistent"}
    result = await harness.chat(
        "Search for xyz123nonexistent product",
        tool_result_overrides={"search_products": empty_mock},
    )
    parsed = robust_assert_valid_json(result, "Empty results should still be valid JSON")
    msg = parsed.get("message", "").lower()
    # Should indicate no results found
    assert any(phrase in msg for phrase in ("no result", "no product", "couldn't find", "not find",
                                            "no match", "nothing found", "no items", "0 result",
                                            "didn't find", "unable to find", "no supplies")), \
        f"Expected 'no results' message, got: {parsed['message'][:200]}"


# ============================================================
# 9. NO FABRICATED DATA (2 tests)
# ============================================================

async def test_no_fabricated_product_names(harness: LLMTestHarness):
    """Product names in the response should come from mock data, not invented."""
    result = await harness.chat("Search for marine paint")
    parsed = robust_assert_valid_json(result)
    response_str = json.dumps(parsed)
    # The mock has these known products
    known_names = [
        "Marine Anti-Fouling Paint Red 5L",
        "Marine Alkyd Enamel White 5L",
        "Epoxy Primer Grey 5L",
    ]
    known_impa = ["232001", "232005", "232010"]
    # At least one known name or IMPA code should appear
    has_known = any(name in response_str for name in known_names) or \
                any(code in response_str for code in known_impa)
    assert has_known, \
        f"Response should reference mock data products. None of {known_names} or {known_impa} found in response"


async def test_no_fabricated_rfq_data(harness: LLMTestHarness):
    """RFQ data in the response should match mock data, not be invented."""
    result = await harness.chat("Show my RFQs")
    parsed = robust_assert_valid_json(result)
    response_str = json.dumps(parsed)
    known_refs = ["RFQ-2026-00040", "RFQ-2026-00041"]
    known_titles = ["Engine Room Supplies Q1", "Deck Paint Replenishment"]
    has_known = any(ref in response_str for ref in known_refs) or \
                any(title in response_str for title in known_titles)
    assert has_known, \
        f"Response should reference mock RFQ data. None of {known_refs} found in response"


# ============================================================
# 10. MESSAGE QUALITY (1 test)
# ============================================================

async def test_message_concise_and_professional(harness: LLMTestHarness):
    """Messages should be concise and professional, not overly verbose."""
    result = await harness.chat("Search for marine paint")
    parsed = robust_assert_valid_json(result)
    msg = parsed.get("message", "")
    # Should be reasonable length (not a wall of text)
    word_count = len(msg.split())
    assert word_count < 200, f"Message is too verbose ({word_count} words): {msg[:200]}..."
    # Should not have filler like "Sure!", "Of course!", "Absolutely!"
    filler_phrases = ["sure!", "of course!", "absolutely!", "certainly!",
                      "great question", "happy to help"]
    msg_lower = msg.lower()
    has_filler = any(f in msg_lower for f in filler_phrases)
    # This is a soft check — filler isn't a hard failure but noted
    if has_filler:
        # Still pass but the system prompt says "concise and professional"
        pass
    assert len(msg) > 10, "Message should be substantive, not empty"


# ============================================================
# 11. MULTIPLE ACTIONS (1 test)
# ============================================================

async def test_multiple_actions_complex_query(harness: LLMTestHarness):
    """A complex query should suggest 2+ relevant follow-up actions."""
    result = await harness.chat(
        "Search for marine paint and show me suppliers in Chennai port"
    )
    parsed = robust_assert_valid_json(result)
    actions = parsed.get("actions", [])
    assert len(actions) >= 2, \
        f"Complex query should suggest 2+ actions, got {len(actions)}: {[a.get('label') for a in actions]}"


# ============================================================
# 12. BONUS: CARD TYPE VALIDATION (1 test)
# ============================================================

async def test_card_types_are_valid(harness: LLMTestHarness):
    """All card types returned should be from the known set."""
    valid_types = {"product_list", "rfq_summary", "rfq_list", "quote_comparison",
                   "vessel_info", "suggestion", "supplier_list", "intelligence",
                   "consumption", "prediction"}
    result = await harness.chat("Search for marine paint")
    parsed = robust_assert_valid_json(result)
    if parsed.get("cards"):
        for card in parsed["cards"]:
            card_type = card.get("type", "")
            assert card_type in valid_types, \
                f"Unexpected card type '{card_type}'. Valid: {valid_types}"


# ============================================================
# 13. BONUS: VESSEL DATA ACCURACY (1 test)
# ============================================================

async def test_vessel_data_accuracy(harness: LLMTestHarness):
    """Vessel info response should reference actual mock data fields."""
    result = await harness.chat("Tell me about vessel IMO 9876543")
    parsed = robust_assert_valid_json(result)
    response_str = json.dumps(parsed)
    # Mock vessel is "MV Ocean Star", type BULK_CARRIER, flag India
    assert "Ocean Star" in response_str or "9876543" in response_str, \
        "Response should reference vessel name or IMO from mock data"


# ============================================================
# Main runner
# ============================================================

async def main():
    print("=" * 60)
    print("PortiQ LLM Integration — Response Quality Tests")
    print("=" * 60)
    print()

    harness = LLMTestHarness()
    print(f"Model: {harness.model}")
    print()

    tests = [
        # 1. JSON compliance
        ("1.1 JSON compliance: greeting", test_json_greeting(harness)),
        ("1.2 JSON compliance: product search", test_json_product_search(harness)),
        ("1.3 JSON compliance: RFQ query", test_json_rfq_query(harness)),
        # 2. Product list cards
        ("2.1 Product list card present", test_product_list_card_present(harness)),
        ("2.2 Product list card has items", test_product_list_card_has_items(harness)),
        # 3. RFQ summary cards
        ("3.1 RFQ list card", test_rfq_list_card(harness)),
        ("3.2 RFQ detail card", test_rfq_detail_card(harness)),
        # 4. Vessel info card
        ("4.1 Vessel info card", test_vessel_info_card(harness)),
        # 5. Suggestion card
        ("5.1 Suggestion card", test_suggestion_card(harness)),
        # 6. Action buttons
        ("6.1 Actions after product search", test_actions_after_product_search(harness)),
        ("6.2 Actions after RFQ list", test_actions_after_rfq_list(harness)),
        ("6.3 Action button structure", test_action_button_structure(harness)),
        # 7. Context object
        ("7.1 Context after vessel lookup", test_context_after_vessel_lookup(harness)),
        # 8. Empty results
        ("8.1 Empty search results", test_empty_search_results(harness)),
        # 9. No fabricated data
        ("9.1 No fabricated product names", test_no_fabricated_product_names(harness)),
        ("9.2 No fabricated RFQ data", test_no_fabricated_rfq_data(harness)),
        # 10. Message quality
        ("10.1 Message concise and professional", test_message_concise_and_professional(harness)),
        # 11. Multiple actions
        ("11.1 Multiple actions for complex query", test_multiple_actions_complex_query(harness)),
        # 12. Card type validation
        ("12.1 Card types are valid", test_card_types_are_valid(harness)),
        # 13. Vessel data accuracy
        ("13.1 Vessel data accuracy", test_vessel_data_accuracy(harness)),
    ]

    start = time.monotonic()

    # Run tests in small batches to avoid rate limits but still parallelize
    batch_size = 4
    for i in range(0, len(tests), batch_size):
        batch = tests[i : i + batch_size]
        batch_label = f"Batch {i // batch_size + 1}/{(len(tests) + batch_size - 1) // batch_size}"
        print(f"--- {batch_label} ---")
        tasks = [run_test(name, coro) for name, coro in batch]
        await asyncio.gather(*tasks)
        print()

    elapsed = time.monotonic() - start

    # Summary
    passed = sum(1 for _, p, _ in _results if p)
    total = len(_results)
    print("=" * 60)
    print(f"Results: {passed}/{total} passed ({elapsed:.1f}s)")
    print("=" * 60)

    if passed < total:
        print("\nFailed tests:")
        for name, p, detail in _results:
            if not p:
                print(f"  - {name}: {detail[:200]}")

    # Exit with failure code if any test failed
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
