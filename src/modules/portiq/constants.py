"""PortiQ AI constants — model config, intent types, limits."""

# Intent classification types
INTENT_SEARCH = "search"
INTENT_RFQ = "rfq"
INTENT_INTELLIGENCE = "intelligence"
INTENT_VESSEL = "vessel"
INTENT_PREDICTION = "prediction"
INTENT_GENERAL = "general"

# OpenAI model configuration (actual values from Settings)
DEFAULT_MODEL = "gpt-4o"
DEFAULT_MAX_TOKENS = 4096

# Chat loop limits
MAX_TOOL_CALL_ITERATIONS = 5

# Session defaults
MAX_SESSION_HISTORY_MESSAGES = 50

# Card types matching frontend CardType
CARD_TYPE_PRODUCT_LIST = "product_list"
CARD_TYPE_RFQ_SUMMARY = "rfq_summary"
CARD_TYPE_QUOTE_COMPARISON = "quote_comparison"
CARD_TYPE_VESSEL_INFO = "vessel_info"
CARD_TYPE_SUGGESTION = "suggestion"

# Action variants matching frontend AIAction
ACTION_VARIANT_PRIMARY = "primary"
ACTION_VARIANT_OUTLINE = "outline"
