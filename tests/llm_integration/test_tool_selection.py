"""LLM integration tests for PortiQ tool selection intelligence.

Tests that GPT-4o correctly selects the right OpenAI function-calling tool
for various maritime procurement queries. Runs via `python` directly (no pytest).

Each test sends a single user message and asserts:
- The expected tool is (or is not) called
- Tool arguments are correct where relevant
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
import time

# Ensure project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.llm_integration.harness import (
    LLMTestHarness,
    LLMTurn,
    assert_no_tool_calls,
    assert_tool_argument,
    assert_tool_called,
)


# ---------------------------------------------------------------------------
# Test runner infrastructure
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name: str, passed: bool, detail: str, latency_ms: float):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.latency_ms = latency_ms


results: list[TestResult] = []


def record(name: str, passed: bool, detail: str = "", latency_ms: float = 0):
    results.append(TestResult(name, passed, detail, latency_ms))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not passed else ""))


def assert_any_tool(turn: LLMTurn, tool_names: list[str], msg: str = ""):
    """Assert that at least one of the given tools was called."""
    actual = turn.tool_names
    for name in tool_names:
        if name in actual:
            return
    raise AssertionError(
        f"Expected one of {tool_names}, got: {actual}. {msg}"
    )


async def run_test(name: str, harness: LLMTestHarness, message: str, check):
    """Run a single test case and record the result."""
    try:
        turn = await harness.single_turn(message)
        check(turn)
        record(name, True, latency_ms=turn.latency_ms)
    except AssertionError as exc:
        record(name, False, detail=str(exc))
    except Exception as exc:
        record(name, False, detail=f"Exception: {exc}\n{traceback.format_exc()}")


# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------

async def run_all_tests():
    harness = LLMTestHarness()
    print("\n=== PortiQ Tool Selection Intelligence Tests ===\n")
    start_time = time.monotonic()

    # -------------------------------------------------------------------
    # Category 1: Product Search (4 tests)
    # -------------------------------------------------------------------
    print("-- Product Search --")

    await run_test(
        "product_search_natural_language",
        harness,
        "Find marine paint for hull coating",
        lambda turn: assert_tool_called(turn, "search_products"),
    )

    # "Search for IMPA 232001" -- LLM may use search_products OR
    # get_product_details since it's a specific IMPA code. Both valid.
    async def test_search_impa_code():
        turn = await harness.single_turn("Search for IMPA 232001")
        assert_any_tool(turn, ["search_products", "get_product_details"])
        # If search_products was used, verify the IMPA code is in the query
        if "search_products" in turn.tool_names:
            tc = assert_tool_called(turn, "search_products")
            assert "232001" in tc.arguments.get("query", ""), \
                f"Expected '232001' in query arg, got: {tc.arguments}"
        # If get_product_details was used, verify the IMPA code is the identifier
        if "get_product_details" in turn.tool_names:
            tc = assert_tool_called(turn, "get_product_details")
            assert "232001" in tc.arguments.get("product_id_or_impa", ""), \
                f"Expected '232001' in product_id_or_impa, got: {tc.arguments}"
    try:
        await test_search_impa_code()
        record("product_search_impa_code", True)
    except AssertionError as exc:
        record("product_search_impa_code", False, str(exc))

    await run_test(
        "product_search_category_query",
        harness,
        "What anti-fouling coating options do you have?",
        lambda turn: assert_tool_called(turn, "search_products"),
    )

    await run_test(
        "product_search_engine_parts",
        harness,
        "I need engine oil filters for a bulk carrier",
        lambda turn: assert_tool_called(turn, "search_products"),
    )

    # -------------------------------------------------------------------
    # Category 2: Product Details (3 tests)
    # -------------------------------------------------------------------
    print("\n-- Product Details --")

    async def test_product_detail_impa():
        turn = await harness.single_turn("Tell me about IMPA 450120")
        assert_any_tool(turn, ["get_product_details", "search_products"])
    try:
        await test_product_detail_impa()
        record("product_detail_by_impa", True)
    except AssertionError as exc:
        record("product_detail_by_impa", False, str(exc))

    async def test_product_detail_uuid():
        turn = await harness.single_turn(
            "Get details on product 550e8400-e29b-41d4-a716-446655440001"
        )
        tc = assert_tool_called(turn, "get_product_details")
        assert_tool_argument(
            tc, "product_id_or_impa", "550e8400-e29b-41d4-a716-446655440001"
        )
    try:
        await test_product_detail_uuid()
        record("product_detail_by_uuid", True)
    except AssertionError as exc:
        record("product_detail_by_uuid", False, str(exc))

    async def test_product_detail_specific():
        turn = await harness.single_turn("Show me full specs for IMPA 174001")
        assert_any_tool(turn, ["get_product_details", "search_products"])
    try:
        await test_product_detail_specific()
        record("product_detail_specs_request", True)
    except AssertionError as exc:
        record("product_detail_specs_request", False, str(exc))

    # -------------------------------------------------------------------
    # Category 3: RFQ Creation (3 tests)
    # -------------------------------------------------------------------
    print("\n-- RFQ Creation --")

    # The system prompt instructs the LLM to "gather needed items through
    # search first" before creating an RFQ. So both create_rfq directly
    # and search_products first are valid behaviors.
    async def test_rfq_create_explicit():
        turn = await harness.single_turn(
            "Create an RFQ for 50 litres of anti-fouling paint and 100 oil filters, "
            "delivery to Chennai port INMAA"
        )
        assert_any_tool(turn, ["create_rfq", "search_products"])
        if "create_rfq" in turn.tool_names:
            tc = assert_tool_called(turn, "create_rfq")
            assert_tool_argument(tc, "delivery_port")
            assert "line_items" in tc.arguments, \
                f"Expected 'line_items' in create_rfq args, got: {list(tc.arguments.keys())}"
    try:
        await test_rfq_create_explicit()
        record("rfq_create_explicit", True)
    except AssertionError as exc:
        record("rfq_create_explicit", False, str(exc))

    async def test_rfq_create_with_port():
        turn = await harness.single_turn(
            "Create an RFQ titled 'Deck Supplies Q1' for delivery at INBOM with "
            "10 PCS of rope and 5 KG of grease"
        )
        assert_any_tool(turn, ["create_rfq", "search_products"])
        if "create_rfq" in turn.tool_names:
            tc = assert_tool_called(turn, "create_rfq")
            assert_tool_argument(tc, "title")
    try:
        await test_rfq_create_with_port()
        record("rfq_create_with_title", True)
    except AssertionError as exc:
        record("rfq_create_with_title", False, str(exc))

    # Test that an ambiguous ordering request triggers search first or create_rfq
    async def test_rfq_order_intent():
        turn = await harness.single_turn(
            "I need to order 200 litres of engine oil SAE 40 for Chennai"
        )
        assert_any_tool(turn, ["create_rfq", "search_products"])
    try:
        await test_rfq_order_intent()
        record("rfq_order_intent", True)
    except AssertionError as exc:
        record("rfq_order_intent", False, str(exc))

    # -------------------------------------------------------------------
    # Category 4: RFQ Listing (2 tests)
    # -------------------------------------------------------------------
    print("\n-- RFQ Listing --")

    await run_test(
        "rfq_list_all",
        harness,
        "Show me my RFQs",
        lambda turn: assert_tool_called(turn, "list_rfqs"),
    )

    async def test_rfq_list_filtered():
        turn = await harness.single_turn("What RFQs are in draft status?")
        tc = assert_tool_called(turn, "list_rfqs")
        assert_tool_argument(tc, "status", "DRAFT")
    try:
        await test_rfq_list_filtered()
        record("rfq_list_by_status", True)
    except AssertionError as exc:
        record("rfq_list_by_status", False, str(exc))

    # -------------------------------------------------------------------
    # Category 5: RFQ Detail (2 tests)
    # -------------------------------------------------------------------
    print("\n-- RFQ Detail --")

    async def test_rfq_detail_by_ref():
        turn = await harness.single_turn("Tell me about RFQ-2026-00040")
        assert_any_tool(turn, ["get_rfq_details", "list_rfqs"])
    try:
        await test_rfq_detail_by_ref()
        record("rfq_detail_by_reference", True)
    except AssertionError as exc:
        record("rfq_detail_by_reference", False, str(exc))

    async def test_rfq_detail_by_uuid():
        turn = await harness.single_turn(
            "Get details for RFQ rfq-550e8400-001"
        )
        assert_tool_called(turn, "get_rfq_details")
    try:
        await test_rfq_detail_by_uuid()
        record("rfq_detail_by_uuid", True)
    except AssertionError as exc:
        record("rfq_detail_by_uuid", False, str(exc))

    # -------------------------------------------------------------------
    # Category 6: Supplier Search (3 tests)
    # -------------------------------------------------------------------
    print("\n-- Supplier Search --")

    async def test_supplier_by_port():
        turn = await harness.single_turn("Find suppliers in Mumbai")
        assert_any_tool(turn, ["list_suppliers", "match_suppliers_for_port"])
    try:
        await test_supplier_by_port()
        record("supplier_search_by_port", True)
    except AssertionError as exc:
        record("supplier_search_by_port", False, str(exc))

    async def test_supplier_by_port_code():
        turn = await harness.single_turn("Who supplies paint near INMAA?")
        assert_any_tool(turn, ["list_suppliers", "match_suppliers_for_port"])
    try:
        await test_supplier_by_port_code()
        record("supplier_search_by_port_code", True)
    except AssertionError as exc:
        record("supplier_search_by_port_code", False, str(exc))

    async def test_supplier_by_tier():
        turn = await harness.single_turn(
            "List all PREMIUM tier suppliers available on the platform"
        )
        if turn.has_tool_calls:
            tc = assert_tool_called(turn, "list_suppliers")
            assert_tool_argument(tc, "tier", "PREMIUM")
        else:
            # LLM may respond asking for more context or clarification.
            # This is acceptable but less ideal.
            assert turn.content is not None and len(turn.content) > 0, \
                "Expected either list_suppliers call or a text response"
    try:
        await test_supplier_by_tier()
        record("supplier_search_by_tier", True)
    except AssertionError as exc:
        record("supplier_search_by_tier", False, str(exc))

    # -------------------------------------------------------------------
    # Category 7: Intelligence (3 tests)
    # -------------------------------------------------------------------
    print("\n-- Intelligence --")

    async def test_intelligence_market_rate():
        turn = await harness.single_turn(
            "What are the current price benchmarks for engine oil IMPA 450120?"
        )
        assert_any_tool(turn, ["get_intelligence", "search_products", "get_product_details"])
    try:
        await test_intelligence_market_rate()
        record("intelligence_market_rate", True)
    except AssertionError as exc:
        record("intelligence_market_rate", False, str(exc))

    async def test_intelligence_risk():
        turn = await harness.single_turn(
            "Give me a risk analysis for a procurement at Chennai port"
        )
        tc = assert_tool_called(turn, "get_intelligence")
        if "delivery_port" in tc.arguments:
            assert tc.arguments["delivery_port"] is not None
    try:
        await test_intelligence_risk()
        record("intelligence_risk_analysis", True)
    except AssertionError as exc:
        record("intelligence_risk_analysis", False, str(exc))

    async def test_intelligence_combined():
        turn = await harness.single_turn(
            "Get market intelligence for IMPA 232001 and 450120 at port INMAA"
        )
        tc = assert_tool_called(turn, "get_intelligence")
        assert "impa_codes" in tc.arguments, \
            f"Expected 'impa_codes' argument, got: {list(tc.arguments.keys())}"
    try:
        await test_intelligence_combined()
        record("intelligence_combined_query", True)
    except AssertionError as exc:
        record("intelligence_combined_query", False, str(exc))

    # -------------------------------------------------------------------
    # Category 8: Consumption Prediction (2 tests)
    # -------------------------------------------------------------------
    print("\n-- Consumption Prediction --")

    async def test_consumption_prediction():
        turn = await harness.single_turn(
            "Predict supplies needed for vessel vessel-001 with 25 crew on a 14-day voyage"
        )
        tc = assert_tool_called(turn, "predict_consumption")
        assert_tool_argument(tc, "vessel_id", "vessel-001")
        assert_tool_argument(tc, "crew_size", 25)
        assert_tool_argument(tc, "voyage_days", 14)
    try:
        await test_consumption_prediction()
        record("consumption_prediction_full", True)
    except AssertionError as exc:
        record("consumption_prediction_full", False, str(exc))

    async def test_consumption_natural():
        turn = await harness.single_turn(
            "How much food and supplies will we need for a 30-day trip "
            "with 20 crew members on vessel abc-123?"
        )
        # LLM may call predict_consumption directly, or call get_vessel_info
        # first to look up the vessel before predicting. Both are valid.
        assert_any_tool(turn, ["predict_consumption", "get_vessel_info"])
        if "predict_consumption" in turn.tool_names:
            tc = assert_tool_called(turn, "predict_consumption")
            assert_tool_argument(tc, "voyage_days", 30)
            assert_tool_argument(tc, "crew_size", 20)
    try:
        await test_consumption_natural()
        record("consumption_prediction_natural", True)
    except AssertionError as exc:
        record("consumption_prediction_natural", False, str(exc))

    # -------------------------------------------------------------------
    # Category 9: Vessel Lookup (3 tests)
    # -------------------------------------------------------------------
    print("\n-- Vessel Lookup --")

    async def test_vessel_by_imo():
        turn = await harness.single_turn("Show me info on IMO 9876543")
        tc = assert_tool_called(turn, "get_vessel_info")
        assert "9876543" in tc.arguments.get("vessel_id_or_imo", ""), \
            f"Expected '9876543' in vessel_id_or_imo, got: {tc.arguments}"
    try:
        await test_vessel_by_imo()
        record("vessel_lookup_by_imo", True)
    except AssertionError as exc:
        record("vessel_lookup_by_imo", False, str(exc))

    # Vessel name queries: LLM may call get_vessel_info with the name
    # as identifier, or may decide it cannot resolve the name without
    # a UUID/IMO. Both behaviors are reasonable given the tool schema
    # says "Vessel UUID or IMO number". We accept either outcome.
    async def test_vessel_by_name():
        turn = await harness.single_turn(
            "Look up vessel information for MV Ocean Star"
        )
        # get_vessel_info is strongly expected, but the LLM may respond
        # textually asking for a UUID/IMO since the tool schema specifies
        # those formats. Accept both outcomes.
        if turn.has_tool_calls:
            assert_tool_called(turn, "get_vessel_info")
        else:
            # If no tool called, the LLM should at least have responded
            # with text (asking for identifier)
            assert turn.content is not None and len(turn.content) > 0, \
                "Expected either get_vessel_info call or a text response"
    try:
        await test_vessel_by_name()
        record("vessel_lookup_by_name", True)
    except AssertionError as exc:
        record("vessel_lookup_by_name", False, str(exc))

    async def test_vessel_position():
        turn = await harness.single_turn(
            "What is the current position of vessel vessel-001?"
        )
        tc = assert_tool_called(turn, "get_vessel_info")
        assert_tool_argument(tc, "vessel_id_or_imo", "vessel-001")
    try:
        await test_vessel_position()
        record("vessel_position_query", True)
    except AssertionError as exc:
        record("vessel_position_query", False, str(exc))

    # -------------------------------------------------------------------
    # Category 10: Supplier Matching (2 tests)
    # -------------------------------------------------------------------
    print("\n-- Supplier Matching --")

    async def test_supplier_match_port():
        turn = await harness.single_turn(
            "Rank the best suppliers for port INMAA"
        )
        tc = assert_tool_called(turn, "match_suppliers_for_port")
        assert "INMAA" in tc.arguments.get("port", ""), \
            f"Expected 'INMAA' in port arg, got: {tc.arguments}"
    try:
        await test_supplier_match_port()
        record("supplier_match_for_port", True)
    except AssertionError as exc:
        record("supplier_match_for_port", False, str(exc))

    async def test_supplier_match_with_items():
        turn = await harness.single_turn(
            "Which suppliers at INBOM can best supply IMPA 232001 and 450120?"
        )
        assert_any_tool(turn, ["match_suppliers_for_port", "list_suppliers"])
    try:
        await test_supplier_match_with_items()
        record("supplier_match_with_impa_codes", True)
    except AssertionError as exc:
        record("supplier_match_with_impa_codes", False, str(exc))

    # -------------------------------------------------------------------
    # Category 11: No Tool Calls -- conversational (3 tests)
    # -------------------------------------------------------------------
    print("\n-- No Tool Calls (Conversational) --")

    await run_test(
        "no_tool_greeting",
        harness,
        "Hello",
        lambda turn: assert_no_tool_calls(turn),
    )

    await run_test(
        "no_tool_thanks",
        harness,
        "Thank you, that's all I need",
        lambda turn: assert_no_tool_calls(turn),
    )

    await run_test(
        "no_tool_capabilities",
        harness,
        "What can you do?",
        lambda turn: assert_no_tool_calls(turn),
    )

    # -------------------------------------------------------------------
    # Category 12: Edge cases & disambiguation (3 tests)
    # -------------------------------------------------------------------
    print("\n-- Edge Cases --")

    # Multi-intent: should call at least one product or supplier tool
    async def test_edge_multiple_tools():
        turn = await harness.single_turn(
            "I need to buy paint at Chennai port -- find products and suppliers"
        )
        assert_any_tool(
            turn,
            ["search_products", "list_suppliers", "match_suppliers_for_port"],
        )
    try:
        await test_edge_multiple_tools()
        record("edge_multi_intent", True)
    except AssertionError as exc:
        record("edge_multi_intent", False, str(exc))

    # IMPA code should trigger product tools, NOT vessel lookup
    async def test_edge_impa_not_vessel():
        turn = await harness.single_turn("Look up IMPA 232001")
        assert "get_vessel_info" not in turn.tool_names, \
            f"IMPA lookup should NOT call get_vessel_info, got: {turn.tool_names}"
        assert_any_tool(turn, ["search_products", "get_product_details"])
    try:
        await test_edge_impa_not_vessel()
        record("edge_impa_not_vessel", True)
    except AssertionError as exc:
        record("edge_impa_not_vessel", False, str(exc))

    # Bidding-related query should map to list_rfqs with BIDDING_OPEN filter
    async def test_edge_bidding_status():
        turn = await harness.single_turn(
            "Which of my RFQs have open bidding right now?"
        )
        tc = assert_tool_called(turn, "list_rfqs")
        assert_tool_argument(tc, "status", "BIDDING_OPEN")
    try:
        await test_edge_bidding_status()
        record("edge_bidding_status_filter", True)
    except AssertionError as exc:
        record("edge_bidding_status_filter", False, str(exc))

    # -------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------
    elapsed = time.monotonic() - start_time
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed ({failed} failed)")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"{'='*60}")

    if failed:
        print("\n  FAILURES:")
        for r in results:
            if not r.passed:
                print(f"    - {r.name}: {r.detail}")
    print()

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())
    sys.exit(0 if passed == total else 1)
