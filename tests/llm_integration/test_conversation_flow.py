"""Multi-turn conversation flow integration tests for PortiQ AI assistant.

Tests verify that PortiQ handles multi-turn conversations with proper context
retention, tool selection, and flow progression.

Run: python tests/llm_integration/test_conversation_flow.py
Requires: OPENAI_API_KEY in .env or environment
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
    LLMTestHarness,
    assert_tool_called,
    assert_message_contains,
)

passed = 0
failed = 0
errors: list[str] = []


def record_pass(name: str, duration_s: float):
    global passed
    passed += 1
    print(f"  PASS  {name}  ({duration_s:.1f}s)")


def record_fail(name: str, reason: str, duration_s: float):
    global failed
    failed += 1
    errors.append(f"{name}: {reason}")
    print(f"  FAIL  {name}  ({duration_s:.1f}s)")
    print(f"        Reason: {reason}")


# ---------------------------------------------------------------------------
# Test 1: Search -> Create RFQ (2 turns)
# ---------------------------------------------------------------------------
async def test_search_then_create_rfq(harness: LLMTestHarness):
    """Turn 1: search for marine paint. Turn 2: create RFQ with results for Chennai."""
    results = await harness.multi_turn_chat([
        "Find marine paint",
        "Create an RFQ with those for Chennai port",
    ])

    # Turn 1: should call search_products
    assert_tool_called(results[0], "search_products", "Turn 1 should search")

    # Turn 2: should call create_rfq
    rfq_call = assert_tool_called(results[1], "create_rfq", "Turn 2 should create RFQ")
    port_arg = json.dumps(rfq_call.arguments).lower()
    assert "chennai" in port_arg or "inmaa" in port_arg, (
        f"Expected Chennai/INMAA in create_rfq args, got: {rfq_call.arguments}"
    )


# ---------------------------------------------------------------------------
# Test 2: Search refinement (3 turns)
# ---------------------------------------------------------------------------
async def test_search_refinement(harness: LLMTestHarness):
    """Progressively refine a search across 3 turns."""
    results = await harness.multi_turn_chat([
        "Search for bolts",
        "Only stainless steel ones",
        "Now show me matching nuts too",
    ])

    # All 3 turns should call search_products
    for i, result in enumerate(results):
        assert_tool_called(result, "search_products", f"Turn {i+1} should search")

    # Turn 2 query should mention stainless steel
    turn2_call = assert_tool_called(results[1], "search_products")
    query = turn2_call.arguments.get("query", "").lower()
    assert "stainless" in query or "steel" in query or "ss" in query, (
        f"Turn 2 search query should contain stainless/steel/ss, got: '{query}'"
    )


# ---------------------------------------------------------------------------
# Test 3: RFQ exploration (3 turns)
# ---------------------------------------------------------------------------
async def test_rfq_exploration(harness: LLMTestHarness):
    """List RFQs -> details of first -> find suppliers for it."""
    results = await harness.multi_turn_chat([
        "Show my RFQs",
        "Tell me about the first one",
        "What suppliers could fulfill it?",
    ])

    # Turn 1: list_rfqs
    assert_tool_called(results[0], "list_rfqs", "Turn 1 should list RFQs")

    # Turn 2: get_rfq_details
    assert_tool_called(results[1], "get_rfq_details", "Turn 2 should get RFQ details")

    # Turn 3: supplier lookup (list_suppliers or match_suppliers_for_port)
    turn3_tools = results[2].tool_names_used
    supplier_tool_found = (
        "list_suppliers" in turn3_tools
        or "match_suppliers_for_port" in turn3_tools
    )
    assert supplier_tool_found, (
        f"Turn 3 should call list_suppliers or match_suppliers_for_port, got: {turn3_tools}"
    )


# ---------------------------------------------------------------------------
# Test 4: Vessel -> Prediction flow (2 turns)
# ---------------------------------------------------------------------------
async def test_vessel_then_prediction(harness: LLMTestHarness):
    """Ask about a vessel, then predict consumption for it."""
    results = await harness.multi_turn_chat([
        "Tell me about vessel IMO 9876543",
        "Predict supplies needed for 25 crew on a 14 day voyage",
    ])

    # Turn 1: get_vessel_info
    vessel_call = assert_tool_called(results[0], "get_vessel_info", "Turn 1 should get vessel")
    assert "9876543" in str(vessel_call.arguments), (
        f"Should pass IMO 9876543, got: {vessel_call.arguments}"
    )

    # Turn 2: predict_consumption
    pred_call = assert_tool_called(results[1], "predict_consumption", "Turn 2 should predict")
    assert pred_call.arguments.get("crew_size") == 25, (
        f"Expected crew_size=25, got: {pred_call.arguments.get('crew_size')}"
    )
    assert pred_call.arguments.get("voyage_days") == 14, (
        f"Expected voyage_days=14, got: {pred_call.arguments.get('voyage_days')}"
    )


# ---------------------------------------------------------------------------
# Test 5: Intelligence gathering (3 turns)
# ---------------------------------------------------------------------------
async def test_intelligence_gathering(harness: LLMTestHarness):
    """Progressive intelligence gathering for Mumbai port."""
    results = await harness.multi_turn_chat([
        "I'm buying supplies for Mumbai port",
        "What are the risks?",
        "Who are the best suppliers there?",
    ])

    # Across the 3 turns, we expect intelligence and/or supplier tools
    all_tools = []
    for r in results:
        all_tools.extend(r.tool_names_used)

    intelligence_or_supplier = any(
        t in all_tools
        for t in ["get_intelligence", "match_suppliers_for_port", "list_suppliers"]
    )
    assert intelligence_or_supplier, (
        f"Expected intelligence or supplier tools across conversation, got: {all_tools}"
    )

    # Turn 3 specifically should find suppliers
    turn3_tools = results[2].tool_names_used
    supplier_found = (
        "list_suppliers" in turn3_tools
        or "match_suppliers_for_port" in turn3_tools
    )
    assert supplier_found, (
        f"Turn 3 should find suppliers, got: {turn3_tools}"
    )


# ---------------------------------------------------------------------------
# Test 6: Context switching (3 turns)
# ---------------------------------------------------------------------------
async def test_context_switching(harness: LLMTestHarness):
    """Switch from paint search to vessel info, then back to paint RFQ."""
    results = await harness.multi_turn_chat([
        "Search for paint",
        "Tell me about vessel IMO 9876543",
        "Back to paint - create an RFQ for those paint products for Mumbai port",
    ])

    # Turn 1: search_products
    assert_tool_called(results[0], "search_products", "Turn 1 should search paint")

    # Turn 2: get_vessel_info (context switch)
    assert_tool_called(results[1], "get_vessel_info", "Turn 2 should get vessel info")

    # Turn 3: create_rfq (returning to paint context)
    assert_tool_called(results[2], "create_rfq", "Turn 3 should create RFQ for paint")


# ---------------------------------------------------------------------------
# Test 7: Pronoun resolution (2 turns)
# ---------------------------------------------------------------------------
async def test_pronoun_resolution(harness: LLMTestHarness):
    """'Search for anti-fouling paint' -> 'How much of it for a 14-day voyage?'"""
    results = await harness.multi_turn_chat([
        "Search for anti-fouling paint",
        "How much of it should I order for a 14-day voyage with 20 crew?",
    ])

    # Turn 1: search_products
    assert_tool_called(results[0], "search_products", "Turn 1 should search")

    # Turn 2: should use predict_consumption or at least reference paint context
    turn2_tools = results[1].tool_names_used
    prediction_used = "predict_consumption" in turn2_tools

    # The LLM might respond conversationally using paint context, or use prediction.
    # Either way, the final content should reference paint or the search results.
    if not prediction_used:
        content = (results[1].final_content or "").lower()
        assert "paint" in content or "fouling" in content or "anti" in content, (
            f"Turn 2 should reference paint context, got: {content[:300]}"
        )


# ---------------------------------------------------------------------------
# Test 8: Correction handling (2 turns)
# ---------------------------------------------------------------------------
async def test_correction_handling(harness: LLMTestHarness):
    """Typo correction: 'marne pant' -> 'Sorry, I meant marine paint'"""
    results = await harness.multi_turn_chat([
        "Search for marne pant",
        "Sorry, I meant marine paint",
    ])

    # Both turns should call search_products
    assert_tool_called(results[0], "search_products", "Turn 1 should search even with typo")
    call2 = assert_tool_called(results[1], "search_products", "Turn 2 should search corrected")

    # Turn 2 query should be corrected
    query2 = call2.arguments.get("query", "").lower()
    assert "marine" in query2 or "paint" in query2, (
        f"Corrected query should contain 'marine' or 'paint', got: '{query2}'"
    )


# ---------------------------------------------------------------------------
# Test 9: Long conversation quality (5 turns)
# ---------------------------------------------------------------------------
async def test_long_conversation_quality(harness: LLMTestHarness):
    """5-turn extended dialogue to verify quality doesn't degrade."""
    results = await harness.multi_turn_chat([
        "Hello",
        "I need to provision my vessel",
        "It's a bulk carrier with 25 crew, IMO 9876543",
        "We're going from Chennai to Singapore, 14 days",
        "Create an RFQ for the predicted supplies for Chennai port delivery",
    ])

    # Turn 1: greeting - no tools or minimal tools
    # (the LLM may or may not use tools for a greeting)

    # Turn 3: should look up vessel info
    turn3_tools = results[2].tool_names_used
    vessel_found = "get_vessel_info" in turn3_tools
    assert vessel_found, (
        f"Turn 3 should get vessel info for IMO 9876543, got tools: {turn3_tools}"
    )

    # Turn 4: should predict consumption
    turn4_tools = results[3].tool_names_used
    prediction_found = "predict_consumption" in turn4_tools
    # The LLM might also defer prediction to turn 5. Check across turns 4-5.
    turn5_tools = results[4].tool_names_used
    all_late_tools = turn4_tools + turn5_tools
    assert "predict_consumption" in all_late_tools or "create_rfq" in all_late_tools, (
        f"Turns 4-5 should predict or create RFQ, got tools: {all_late_tools}"
    )

    # Turn 5: should create RFQ
    assert "create_rfq" in turn5_tools, (
        f"Turn 5 should create RFQ, got tools: {turn5_tools}"
    )

    # Final response should be coherent (non-empty)
    final = results[4].final_content or ""
    assert len(final) > 20, (
        f"Final response should be substantive, got length {len(final)}"
    )


# ---------------------------------------------------------------------------
# Test 10: Follow-up from intelligence (2 turns)
# ---------------------------------------------------------------------------
async def test_followup_from_intelligence(harness: LLMTestHarness):
    """Get intelligence, then create RFQ based on the analysis."""
    results = await harness.multi_turn_chat([
        "Get market intelligence for Chennai port, IMPA codes 232001, 450120",
        "Create an RFQ based on this analysis for Chennai port",
    ])

    # Turn 1: get_intelligence
    intel_call = assert_tool_called(results[0], "get_intelligence", "Turn 1 should get intelligence")
    args = intel_call.arguments
    # Should pass port and/or IMPA codes
    args_str = json.dumps(args).lower()
    assert "inmaa" in args_str or "chennai" in args_str or "232001" in args_str, (
        f"Intelligence call should include port or IMPA codes, got: {args}"
    )

    # Turn 2: create_rfq
    rfq_call = assert_tool_called(results[1], "create_rfq", "Turn 2 should create RFQ")
    rfq_args_str = json.dumps(rfq_call.arguments).lower()
    assert "chennai" in rfq_args_str or "inmaa" in rfq_args_str, (
        f"RFQ should target Chennai/INMAA, got: {rfq_call.arguments}"
    )


# ---------------------------------------------------------------------------
# Test 11: Status-filtered follow-up (2 turns)
# ---------------------------------------------------------------------------
async def test_status_filtered_followup(harness: LLMTestHarness):
    """'Show my open RFQs' -> 'Now show the draft ones'"""
    # Provide different mock results for different statuses
    results = await harness.multi_turn_chat([
        "Show my open RFQs",
        "Now show the draft ones",
    ])

    # Turn 1: list_rfqs — should filter by open status
    call1 = assert_tool_called(results[0], "list_rfqs", "Turn 1 should list RFQs")
    status1 = call1.arguments.get("status", "").upper()
    assert status1 in ("BIDDING_OPEN", "PUBLISHED", ""), (
        f"Turn 1 should filter by open status, got: '{status1}'"
    )

    # Turn 2: list_rfqs — should filter by DRAFT
    call2 = assert_tool_called(results[1], "list_rfqs", "Turn 2 should list RFQs again")
    status2 = call2.arguments.get("status", "").upper()
    assert status2 == "DRAFT", (
        f"Turn 2 should filter by DRAFT, got: '{status2}'"
    )


# ---------------------------------------------------------------------------
# Test 12: Greeting then work (2 turns)
# ---------------------------------------------------------------------------
async def test_greeting_then_work(harness: LLMTestHarness):
    """'Hi, I'm new here' -> 'I need to find suppliers for Chennai'"""
    results = await harness.multi_turn_chat([
        "Hi, I'm new here",
        "I need to find suppliers for Chennai",
    ])

    # Turn 1: greeting — no tool calls expected (or minimal)
    turn1_tools = results[0].tool_names_used
    # Greeting might trigger no tools or just a knowledge response
    assert len(turn1_tools) == 0 or all(
        t not in turn1_tools for t in ["create_rfq", "predict_consumption"]
    ), f"Turn 1 greeting should not create RFQs or predict, got tools: {turn1_tools}"

    # Turn 2: should find suppliers
    turn2_tools = results[1].tool_names_used
    supplier_found = (
        "list_suppliers" in turn2_tools
        or "match_suppliers_for_port" in turn2_tools
    )
    assert supplier_found, (
        f"Turn 2 should find suppliers, got tools: {turn2_tools}"
    )


# ---------------------------------------------------------------------------
# Test 13: Vessel context carries forward to prediction (2 turns)
# ---------------------------------------------------------------------------
async def test_vessel_context_in_prediction(harness: LLMTestHarness):
    """Verify vessel_id from Turn 1 is used in Turn 2 predict_consumption."""
    results = await harness.multi_turn_chat([
        "Look up vessel IMO 9876543",
        "Predict supply needs for that vessel, 30 crew, 10 day voyage",
    ])

    # Turn 1: get_vessel_info
    assert_tool_called(results[0], "get_vessel_info", "Turn 1 should get vessel")

    # Turn 2: predict_consumption with vessel context
    pred_call = assert_tool_called(results[1], "predict_consumption", "Turn 2 should predict")
    # The LLM should pass vessel_id (from mock: "vessel-001") or the IMO
    vessel_arg = pred_call.arguments.get("vessel_id", "")
    assert vessel_arg, (
        f"predict_consumption should have vessel_id, got args: {pred_call.arguments}"
    )
    assert pred_call.arguments.get("crew_size") == 30, (
        f"Expected crew_size=30, got: {pred_call.arguments.get('crew_size')}"
    )


# ---------------------------------------------------------------------------
# Test 14: Multi-tool single turn within conversation (2 turns)
# ---------------------------------------------------------------------------
async def test_multi_tool_in_conversation(harness: LLMTestHarness):
    """Ask for intelligence that requires multiple tools in one turn."""
    results = await harness.multi_turn_chat([
        "I have an RFQ for engine supplies at Chennai port",
        "Get me both market intelligence and matching suppliers for it",
    ])

    # Turn 2: should use intelligence and/or supplier matching
    turn2_tools = results[1].tool_names_used
    assert len(turn2_tools) >= 1, (
        f"Turn 2 should use at least one tool, got: {turn2_tools}"
    )
    intelligence_or_supplier = any(
        t in turn2_tools
        for t in ["get_intelligence", "match_suppliers_for_port", "list_suppliers"]
    )
    assert intelligence_or_supplier, (
        f"Turn 2 should use intelligence or supplier tools, got: {turn2_tools}"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    ("1. Search -> Create RFQ", test_search_then_create_rfq),
    ("2. Search refinement", test_search_refinement),
    ("3. RFQ exploration", test_rfq_exploration),
    ("4. Vessel -> Prediction", test_vessel_then_prediction),
    ("5. Intelligence gathering", test_intelligence_gathering),
    ("6. Context switching", test_context_switching),
    ("7. Pronoun resolution", test_pronoun_resolution),
    ("8. Correction handling", test_correction_handling),
    ("9. Long conversation quality (5 turns)", test_long_conversation_quality),
    ("10. Follow-up from intelligence", test_followup_from_intelligence),
    ("11. Status-filtered follow-up", test_status_filtered_followup),
    ("12. Greeting then work", test_greeting_then_work),
    ("13. Vessel context in prediction", test_vessel_context_in_prediction),
    ("14. Multi-tool in conversation", test_multi_tool_in_conversation),
]


async def main():
    global passed, failed

    print("=" * 70)
    print("PortiQ LLM Integration Tests: Multi-Turn Conversation Flows")
    print("=" * 70)
    print()

    harness = LLMTestHarness()

    overall_start = time.monotonic()

    for name, test_fn in ALL_TESTS:
        start = time.monotonic()
        try:
            await test_fn(harness)
            record_pass(name, time.monotonic() - start)
        except AssertionError as exc:
            record_fail(name, str(exc), time.monotonic() - start)
        except Exception as exc:
            record_fail(name, f"Unexpected error: {exc}", time.monotonic() - start)
            traceback.print_exc()

    total_time = time.monotonic() - overall_start

    print()
    print("=" * 70)
    print(f"Results: {passed}/{passed + failed} passed  ({total_time:.1f}s total)")
    if errors:
        print(f"\nFailures ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
    print("=" * 70)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
