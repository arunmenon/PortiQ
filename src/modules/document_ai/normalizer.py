"""Text normalization utilities for Document AI extraction pipeline."""

from __future__ import annotations

import re

UNIT_NORMALIZATION: dict[str, str] = {
    "pcs": "pcs",
    "pce": "pcs",
    "pieces": "pcs",
    "ea": "pcs",
    "each": "pcs",
    "nos": "pcs",
    "kg": "kg",
    "kgs": "kg",
    "kilos": "kg",
    "kilogram": "kg",
    "m": "m",
    "mtr": "m",
    "mtrs": "m",
    "meters": "m",
    "metres": "m",
    "l": "L",
    "ltr": "L",
    "ltrs": "L",
    "liters": "L",
    "litres": "L",
    "sets": "set",
    "set": "set",
    "rolls": "roll",
    "roll": "roll",
    "rls": "roll",
    "drums": "drum",
    "drum": "drum",
    "drm": "drum",
    "boxes": "box",
    "box": "box",
    "bx": "box",
    "tins": "tin",
    "tin": "tin",
    "cans": "tin",
    "can": "tin",
    "bottles": "bottle",
    "bottle": "bottle",
    "btl": "bottle",
}

# Pattern for quantity + unit: "50kg", "200 meters", "12 units", "3.5 L"
_QUANTITY_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)",
)

# Pattern for standalone IMPA 6-digit code
_IMPA_PATTERN = re.compile(r"\b(\d{6})\b")

# Pattern for line-number prefixes like "1.", "01.", "1)", "1 -"
_LINE_NUMBER_PREFIX = re.compile(r"^\s*\d+[\.\)\-\s]+")


class Normalizer:
    """Normalizes extracted text from maritime procurement documents."""

    def normalize_unit(self, raw_unit: str) -> str:
        """Normalize unit string.

        Returns the canonical form from UNIT_NORMALIZATION or the original
        string lowercased if no mapping is found.
        """
        lookup = raw_unit.strip().lower()
        return UNIT_NORMALIZATION.get(lookup, lookup)

    def parse_quantity(self, raw_text: str) -> tuple[float | None, str | None]:
        """Extract quantity and unit from text like '50kg', '200 meters', '12 units'.

        Returns (quantity, normalized_unit). Returns (None, None) for ambiguous
        phrases like 'as required' or 'TBD'.
        """
        text = raw_text.strip().lower()

        # Check for ambiguous / non-numeric quantities
        ambiguous_markers = {"as required", "tbd", "as needed", "lot", "assorted"}
        if text in ambiguous_markers:
            return None, None

        match = _QUANTITY_PATTERN.search(raw_text)
        if match:
            quantity = float(match.group(1))
            unit = self.normalize_unit(match.group(2))
            return quantity, unit

        # Try to find a bare number (no unit)
        bare_number = re.search(r"(\d+(?:\.\d+)?)", raw_text)
        if bare_number:
            return float(bare_number.group(1)), None

        return None, None

    def normalize_description(self, raw_text: str) -> str:
        """Clean description text.

        - Strip leading line numbers (e.g. "1. ", "01) ")
        - Normalize whitespace (collapse multiple spaces/newlines)
        - Truncate to 500 characters
        """
        text = raw_text.strip()

        # Remove line-number prefix
        text = _LINE_NUMBER_PREFIX.sub("", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Truncate to 500 chars
        if len(text) > 500:
            text = text[:497] + "..."

        return text

    def detect_impa_in_text(self, text: str) -> str | None:
        """Find 6-digit IMPA code pattern in text.

        Returns first valid match (6-digit number) or None.
        IMPA codes are 6 digits in the range 100000-999999.
        """
        matches = _IMPA_PATTERN.findall(text)
        for match in matches:
            code = int(match)
            if 100000 <= code <= 999999:
                return match
        return None
