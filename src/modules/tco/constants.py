"""TCO engine constants — industry templates, scoring maps, and tier mappings."""

from __future__ import annotations

from decimal import Decimal

from src.models.enums import SupplierTier, TcoTemplateType

# ── Industry weight templates ────────────────────────────────────────────────
# Each template maps factor names to their weight (must sum to 1.0).

INDUSTRY_TEMPLATES: dict[TcoTemplateType, dict[str, Decimal]] = {
    TcoTemplateType.COMMODITY: {
        "weight_unit_price": Decimal("0.5000"),
        "weight_shipping": Decimal("0.1500"),
        "weight_lead_time": Decimal("0.1000"),
        "weight_quality": Decimal("0.1000"),
        "weight_payment_terms": Decimal("0.1000"),
        "weight_supplier_rating": Decimal("0.0500"),
    },
    TcoTemplateType.TECHNICAL: {
        "weight_unit_price": Decimal("0.2000"),
        "weight_shipping": Decimal("0.1000"),
        "weight_lead_time": Decimal("0.1500"),
        "weight_quality": Decimal("0.3000"),
        "weight_payment_terms": Decimal("0.1000"),
        "weight_supplier_rating": Decimal("0.1500"),
    },
    TcoTemplateType.URGENT: {
        "weight_unit_price": Decimal("0.2000"),
        "weight_shipping": Decimal("0.1500"),
        "weight_lead_time": Decimal("0.3500"),
        "weight_quality": Decimal("0.1000"),
        "weight_payment_terms": Decimal("0.0500"),
        "weight_supplier_rating": Decimal("0.1500"),
    },
    TcoTemplateType.STRATEGIC: {
        "weight_unit_price": Decimal("0.2000"),
        "weight_shipping": Decimal("0.1500"),
        "weight_lead_time": Decimal("0.1500"),
        "weight_quality": Decimal("0.2000"),
        "weight_payment_terms": Decimal("0.1500"),
        "weight_supplier_rating": Decimal("0.1500"),
    },
    TcoTemplateType.QUALITY_CRITICAL: {
        "weight_unit_price": Decimal("0.1500"),
        "weight_shipping": Decimal("0.0500"),
        "weight_lead_time": Decimal("0.1000"),
        "weight_quality": Decimal("0.4000"),
        "weight_payment_terms": Decimal("0.1000"),
        "weight_supplier_rating": Decimal("0.2000"),
    },
}

# ── Incoterms scoring (0-100, higher = better for buyer) ────────────────────
INCOTERMS_SCORE: dict[str, int] = {
    "DDP": 100,
    "CIF": 85,
    "CFR": 75,
    "FOB": 50,
    "FCA": 40,
    "EXW": 20,
}

# ── Payment terms scoring (0-100, higher = more favorable for buyer) ────────
PAYMENT_TERMS_SCORE: dict[str, int] = {
    "NET90": 100,
    "NET60": 80,
    "NET45": 70,
    "NET30": 60,
    "NET15": 40,
    "COD": 25,
    "CIA": 10,
}

# ── Supplier tier → quality score mapping ────────────────────────────────────
SUPPLIER_TIER_QUALITY_SCORE: dict[SupplierTier, int] = {
    SupplierTier.PREMIUM: 95,
    SupplierTier.PREFERRED: 80,
    SupplierTier.VERIFIED: 65,
    SupplierTier.BASIC: 40,
    SupplierTier.PENDING: 20,
}

# ── Re-export TIER_CAPABILITIES for convenience ─────────────────────────────
from src.modules.supplier.constants import TIER_CAPABILITIES  # noqa: E402

__all__ = [
    "INDUSTRY_TEMPLATES",
    "INCOTERMS_SCORE",
    "PAYMENT_TERMS_SCORE",
    "SUPPLIER_TIER_QUALITY_SCORE",
    "TIER_CAPABILITIES",
]
