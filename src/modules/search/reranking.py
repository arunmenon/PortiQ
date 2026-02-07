"""RerankingService — reranks vector search candidates using domain heuristics."""

from src.modules.search.constants import IMPA_CODE_MATCH_BOOST, UNIT_MATCH_BOOST

# Maps common unit abbreviations / synonyms to a canonical form.
UNIT_EQUIVALENCES: dict[str, str] = {
    # piece
    "piece": "PC",
    "pieces": "PC",
    "pc": "PC",
    "pcs": "PC",
    "ea": "PC",
    "each": "PC",
    # meter
    "meter": "MTR",
    "meters": "MTR",
    "metre": "MTR",
    "metres": "MTR",
    "mtr": "MTR",
    "m": "MTR",
    # kilogram
    "kilogram": "KG",
    "kilograms": "KG",
    "kg": "KG",
    "kgs": "KG",
    # liter
    "liter": "LTR",
    "liters": "LTR",
    "litre": "LTR",
    "litres": "LTR",
    "ltr": "LTR",
    "l": "LTR",
    # box
    "box": "BOX",
    "boxes": "BOX",
    "bx": "BOX",
    # pack
    "pack": "PK",
    "packs": "PK",
    "pk": "PK",
    "pkt": "PK",
    "packet": "PK",
    # set
    "set": "SET",
    "sets": "SET",
    # roll
    "roll": "RL",
    "rolls": "RL",
    "rl": "RL",
    # pair
    "pair": "PR",
    "pairs": "PR",
    "pr": "PR",
    # dozen
    "dozen": "DZ",
    "dozens": "DZ",
    "dz": "DZ",
    "doz": "DZ",
    # can
    "can": "CAN",
    "cans": "CAN",
    "tin": "CAN",
    # drum
    "drum": "DRM",
    "drums": "DRM",
    "drm": "DRM",
    # carton
    "carton": "CTN",
    "cartons": "CTN",
    "ctn": "CTN",
    # bottle
    "bottle": "BTL",
    "bottles": "BTL",
    "btl": "BTL",
}


def _normalise_unit(unit: str | None) -> str | None:
    """Normalise a unit string to its canonical abbreviation."""
    if unit is None:
        return None
    return UNIT_EQUIVALENCES.get(unit.strip().lower(), unit.strip().upper())


class RerankingService:
    """Reranks vector-search candidates using IMPA-code and unit-match heuristics."""

    def rerank_candidates(
        self,
        candidates: list[dict],
        impa_code: str | None = None,
        unit: str | None = None,
    ) -> list[dict]:
        """Boost similarity scores for IMPA code and unit matches, then re-sort."""
        normalised_unit = _normalise_unit(unit)

        for candidate in candidates:
            boosted_score = candidate["similarity"]

            if impa_code and candidate.get("impa_code") == impa_code:
                boosted_score += IMPA_CODE_MATCH_BOOST

            if normalised_unit and _normalise_unit(candidate.get("unit_of_measure")) == normalised_unit:
                boosted_score += UNIT_MATCH_BOOST

            candidate["boosted_similarity"] = min(boosted_score, 1.0)

        candidates.sort(key=lambda c: c["boosted_similarity"], reverse=True)
        return candidates

    def calculate_confidence(
        self,
        similarity: float,
        extraction_confidence: float = 1.0,
        category_matches: bool = True,
    ) -> float:
        """Calculate final match confidence from similarity, extraction confidence, and category match."""
        confidence = similarity * extraction_confidence
        if not category_matches:
            confidence *= 0.8
        return round(min(confidence, 1.0), 4)

    def explain_match(
        self,
        candidate: dict,
        impa_code: str | None = None,
        unit: str | None = None,
    ) -> str:
        """Return a human-readable explanation for why a candidate matched."""
        reasons: list[str] = []
        reasons.append(f"Vector similarity: {candidate['similarity']:.3f}")

        if impa_code and candidate.get("impa_code") == impa_code:
            reasons.append(f"IMPA code exact match ({impa_code})")

        normalised_unit = _normalise_unit(unit)
        if normalised_unit and _normalise_unit(candidate.get("unit_of_measure")) == normalised_unit:
            reasons.append(f"Unit match ({normalised_unit})")

        boosted = candidate.get("boosted_similarity")
        if boosted is not None and boosted != candidate["similarity"]:
            reasons.append(f"Boosted similarity: {boosted:.3f}")

        return "; ".join(reasons)
