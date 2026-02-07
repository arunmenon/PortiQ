"""Vessel module constants — quality thresholds, port lists, event types."""

# Quality thresholds (also in config, these are code-level constants)
MAX_POSITION_AGE_SECONDS = 3600
MAX_SPEED_KNOTS = 50.0
MIN_SIGNAL_CONFIDENCE = 0.7

# PCS1x Indian ports (UN/LOCODE) — aligned with ADR-FN-020
PCS1X_PORTS = [
    "INMAA", "INBOM", "INCOK", "INKOL", "INMUN", "INPAV",
    "INNSA", "INVIS", "INTUT", "INKRI", "INENG", "INPBD",
]

# Port maturity levels for PCS1x (per ADR-FN-020)
PORT_MATURITY = {
    "INMAA": "FULL", "INBOM": "FULL", "INCOK": "FULL", "INNSA": "FULL",
    "INKOL": "PARTIAL", "INMUN": "PARTIAL",
    "INPAV": "BASIC", "INVIS": "BASIC", "INTUT": "BASIC",
    "INKRI": "BASIC", "INENG": "BASIC", "INPBD": "BASIC",
}

# PCS1x retry policies: {http_status: {strategy, delay_seconds, max_retries}}
PCS1X_RETRY_POLICIES = {
    408: {"strategy": "exponential", "delay_seconds": 5, "max_retries": 5},
    429: {"strategy": "linear", "delay_seconds": 60, "max_retries": 3},
    503: {"strategy": "fixed", "delay_seconds": 300, "max_retries": 12},
}

# Event type constants
VESSEL_EVENT_TYPES = {
    "position_updated": "vessel.position.updated",
    "approaching": "vessel.approaching",
    "arrived": "vessel.arrived",
    "departed": "vessel.departed",
}
