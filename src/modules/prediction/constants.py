"""Consumption rates, vessel-type multipliers, and template definitions (ADR-FN-021)."""

from __future__ import annotations

# IMPA category prefix -> base consumption rate configuration
# base_rate: quantity consumed per unit (person or vessel) per day
# unit: measurement unit (KG, PIECE, L, M)
# per: "person/day" or "vessel/day" — determines whether crew_size factors in
# min_days: minimum days of supply to always carry
# buffer: safety buffer multiplier (e.g. 1.2 = 20% extra)
CONSUMPTION_RATES: dict[str, dict] = {
    "00": {"base_rate": 3.5, "unit": "KG", "per": "person/day", "min_days": 7, "buffer": 1.2},
    "11": {"base_rate": 0.05, "unit": "PIECE", "per": "person/day", "min_days": 30, "buffer": 1.1},
    "17": {"base_rate": 0.02, "unit": "L", "per": "person/day", "min_days": 30, "buffer": 1.1},
    "21": {"base_rate": 0.5, "unit": "M", "per": "vessel/day", "min_days": 90, "buffer": 1.3},
    "25": {"base_rate": 0.3, "unit": "L", "per": "vessel/day", "min_days": 90, "buffer": 1.2},
    "31": {"base_rate": 0.02, "unit": "PIECE", "per": "person/day", "min_days": 90, "buffer": 1.3},
    "33": {"base_rate": 0.01, "unit": "PIECE", "per": "person/day", "min_days": 180, "buffer": 1.5},
    "37": {"base_rate": 0.001, "unit": "PIECE", "per": "vessel/day", "min_days": 365, "buffer": 1.1},
    "39": {"base_rate": 0.005, "unit": "PIECE", "per": "person/day", "min_days": 180, "buffer": 1.5},
    "45": {"base_rate": 0.1, "unit": "L", "per": "vessel/day", "min_days": 90, "buffer": 1.2},
    "55": {"base_rate": 0.1, "unit": "L", "per": "person/day", "min_days": 30, "buffer": 1.1},
    "61": {"base_rate": 0.005, "unit": "PIECE", "per": "vessel/day", "min_days": 180, "buffer": 1.2},
    "71": {"base_rate": 0.01, "unit": "PIECE", "per": "vessel/day", "min_days": 180, "buffer": 1.3},
    "85": {"base_rate": 0.02, "unit": "KG", "per": "vessel/day", "min_days": 180, "buffer": 1.2},
}

# Vessel type -> per-category multiplier overrides.  "DEFAULT" is the fallback.
VESSEL_TYPE_MULTIPLIERS: dict[str, dict[str, float]] = {
    "TANKER": {"31": 1.5, "33": 1.5, "45": 1.3, "DEFAULT": 1.0},
    "PASSENGER": {"00": 2.5, "11": 2.0, "17": 2.0, "55": 1.5, "DEFAULT": 1.0},
    "BULK_CARRIER": {"25": 1.3, "61": 1.2, "21": 1.1, "DEFAULT": 1.0},
    "CONTAINER": {"21": 1.2, "23": 1.3, "DEFAULT": 1.0},
    "OFFSHORE": {"31": 1.5, "33": 1.5, "85": 1.4, "71": 1.3, "DEFAULT": 1.1},
    "RO_RO": {"25": 1.2, "31": 1.1, "DEFAULT": 1.0},
    "FISHING": {"21": 1.3, "31": 1.2, "00": 1.3, "DEFAULT": 1.0},
    "TUG": {"45": 1.3, "71": 1.2, "DEFAULT": 1.0},
    "GENERAL_CARGO": {"DEFAULT": 1.0},
    "OTHER": {"DEFAULT": 1.0},
}

# ---------------------------------------------------------------------------
# Template definitions — keyed by vessel type
# ---------------------------------------------------------------------------

VESSEL_TYPE_TEMPLATES: dict[str, dict] = {
    "TANKER": {
        "name": "Tanker Safety Package",
        "categories": ["31", "33", "45"],
        "description": "Safety-focused for tanker operations",
    },
    "BULK_CARRIER": {
        "name": "Bulk Carrier Deck Package",
        "categories": ["21", "25", "61"],
        "description": "Deck maintenance focus",
    },
    "CONTAINER": {
        "name": "Container Ship Essentials",
        "categories": ["21", "23", "37"],
        "description": "Rigging and lashing gear",
    },
    "PASSENGER": {
        "name": "Passenger Vessel Provisions",
        "categories": ["00", "11", "17", "55"],
        "description": "Crew and guest provisions",
    },
    "OFFSHORE": {
        "name": "Offshore Support Package",
        "categories": ["31", "33", "71", "85"],
        "description": "Heavy-duty safety and engine",
    },
}

# ---------------------------------------------------------------------------
# Voyage type templates — keyed by voyage classification
# ---------------------------------------------------------------------------

VOYAGE_TYPE_TEMPLATES: dict[str, dict] = {
    "COASTAL": {
        "name": "Coastal Run",
        "max_days": 7,
        "adjustments": {"provisions_multiplier": 0.5, "deck_priority": True},
    },
    "SHORT_SEA": {
        "name": "Short Sea Voyage",
        "max_days": 21,
        "adjustments": {"provisions_multiplier": 1.0},
    },
    "DEEP_SEA": {
        "name": "Ocean Crossing",
        "max_days": 999,
        "adjustments": {"provisions_multiplier": 1.5, "safety_buffer": 1.3},
    },
}

# ---------------------------------------------------------------------------
# Event-based templates — keyed by event type
# ---------------------------------------------------------------------------

EVENT_TEMPLATES: dict[str, dict] = {
    "DRYDOCK": {
        "name": "Dry-Docking Prep",
        "categories": ["71", "25", "45"],
        "description": "Engine overhaul spares, hull paint",
    },
    "CREW_CHANGE": {
        "name": "Crew Change",
        "categories": ["00", "11", "55"],
        "description": "Fresh provisions, cabin stores",
    },
    "PSC_INSPECTION": {
        "name": "PSC Inspection Prep",
        "categories": ["33", "39"],
        "description": "Safety equipment service kits",
    },
}

# Threshold for blending historical data with rule-based predictions
HISTORY_BLEND_THRESHOLD = 5  # number of past RFQs needed
RULES_WEIGHT = 0.3
HISTORY_WEIGHT = 0.7

# Confidence scores
RULES_ONLY_CONFIDENCE = 0.55
BLENDED_CONFIDENCE = 0.78
