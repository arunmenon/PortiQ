"""OpenAI function-calling tool definitions for PortiQ AI assistant."""

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search for marine products by name, description, or IMPA code. "
                "Returns matching products with IMPA codes, names, and categories."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — product name, description keywords, or IMPA code",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 10, max 50)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get detailed information about a specific product by its UUID or IMPA code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id_or_impa": {
                        "type": "string",
                        "description": "Product UUID or 6-digit IMPA code",
                    },
                },
                "required": ["product_id_or_impa"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_rfq",
            "description": (
                "Create a new Request for Quotation (RFQ) with a title, "
                "delivery port, and line items. Returns the created RFQ with reference number."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "RFQ title describing the procurement need",
                    },
                    "delivery_port": {
                        "type": "string",
                        "description": "Port code or name for delivery (e.g., INMAA, INBOM)",
                    },
                    "line_items": {
                        "type": "array",
                        "description": "List of items to include in the RFQ",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "Item description",
                                },
                                "quantity": {
                                    "type": "number",
                                    "description": "Required quantity",
                                },
                                "unit": {
                                    "type": "string",
                                    "description": "Unit of measure (e.g., PCS, KG, LTR)",
                                },
                                "impa_code": {
                                    "type": "string",
                                    "description": "IMPA code if known",
                                },
                            },
                            "required": ["description", "quantity", "unit"],
                        },
                    },
                },
                "required": ["title", "delivery_port", "line_items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_rfqs",
            "description": (
                "List the user's RFQs, optionally filtered by status. "
                "Returns reference numbers, titles, statuses, and dates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": (
                            "Filter by RFQ status: DRAFT, PUBLISHED, "
                            "BIDDING_OPEN, BIDDING_CLOSED, EVALUATION, "
                            "AWARDED, COMPLETED, CANCELLED"
                        ),
                        "enum": [
                            "DRAFT",
                            "PUBLISHED",
                            "BIDDING_OPEN",
                            "BIDDING_CLOSED",
                            "EVALUATION",
                            "AWARDED",
                            "COMPLETED",
                            "CANCELLED",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default 10)",
                        "default": 10,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rfq_details",
            "description": (
                "Get detailed information about a specific RFQ "
                "including line items, invitations, and status history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "rfq_id": {
                        "type": "string",
                        "description": "UUID of the RFQ",
                    },
                },
                "required": ["rfq_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_suppliers",
            "description": (
                "Find suppliers filtered by tier and/or port coverage. "
                "Returns supplier names, tiers, port coverage, and categories."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "string",
                        "description": "Minimum supplier tier: BASIC, VERIFIED, PREFERRED, PREMIUM",
                        "enum": ["BASIC", "VERIFIED", "PREFERRED", "PREMIUM"],
                    },
                    "port": {
                        "type": "string",
                        "description": "Filter by port coverage (port code or name)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_intelligence",
            "description": (
                "Get market intelligence including price benchmarks, "
                "supplier recommendations, risk analysis, and timing advice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "delivery_port": {
                        "type": "string",
                        "description": "Delivery port code",
                    },
                    "impa_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "IMPA codes to get intelligence for",
                    },
                    "vessel_id": {
                        "type": "string",
                        "description": "Vessel UUID for timing analysis",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_consumption",
            "description": (
                "Predict supply consumption quantities for a voyage "
                "based on vessel type, crew size, and voyage duration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_id": {
                        "type": "string",
                        "description": "UUID of the vessel",
                    },
                    "crew_size": {
                        "type": "integer",
                        "description": "Number of crew members",
                    },
                    "voyage_days": {
                        "type": "integer",
                        "description": "Expected duration of the voyage in days",
                    },
                },
                "required": ["vessel_id", "crew_size", "voyage_days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vessel_info",
            "description": (
                "Get vessel details including type, status, dimensions, "
                "and latest position. Accepts vessel UUID or IMO number."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "vessel_id_or_imo": {
                        "type": "string",
                        "description": "Vessel UUID or IMO number (7 digits)",
                    },
                },
                "required": ["vessel_id_or_imo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "match_suppliers_for_port",
            "description": (
                "Find and rank suppliers for a specific delivery port "
                "using the 6-stage matching pipeline. Returns scored and ranked suppliers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {
                        "type": "string",
                        "description": "Delivery port code (e.g., INMAA, INBOM)",
                    },
                    "impa_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "IMPA codes for category matching",
                    },
                },
                "required": ["port"],
            },
        },
    },
]
