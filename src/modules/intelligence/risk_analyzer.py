"""Risk analyzer — identifies procurement risks for RFQ intelligence."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.enums import (
    OnboardingStatus,
    QuoteStatus,
    SupplierTier,
)
from src.models.quote import Quote
from src.models.quote_line_item import QuoteLineItem
from src.models.rfq import Rfq
from src.models.rfq_invitation import RfqInvitation
from src.models.rfq_line_item import RfqLineItem
from src.models.supplier_profile import SupplierProfile
from src.modules.intelligence.schemas import RiskFlag

logger = logging.getLogger(__name__)

# Average lead time assumption (days) when no historical data
_DEFAULT_LEAD_TIME_DAYS = 14
# Threshold for low-response port (quote-to-invite ratio)
_LOW_RESPONSE_RATIO = 0.5
# Threshold for unusual quantity (multiplier of stddev)
_UNUSUAL_QTY_STDDEV_MULTIPLIER = 3.0
# Threshold for no-price-history fraction
_NO_PRICE_HISTORY_THRESHOLD = 0.5


class RiskAnalyzer:
    """Identifies procurement risks for a given delivery context."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze_risks(
        self,
        delivery_port: str | None = None,
        delivery_date: datetime | None = None,
        vessel_id: uuid.UUID | None = None,
        impa_codes: list[str] | None = None,
        bidding_deadline: datetime | None = None,
        buyer_organization_id: uuid.UUID | None = None,
    ) -> list[RiskFlag]:
        """Check 7 risk types and return any that apply.

        Risk types:
            1. SINGLE_SOURCE — only 1 supplier covers all items at port
            2. TIGHT_TIMELINE — insufficient time before delivery
            3. NO_PRICE_HISTORY — >50% of items lack historical pricing
            4. QUANTITY_REFERENCE — historical quantity reference ranges for buyer
            5. NEW_CATEGORY — buyer never ordered this IMPA category before
            6. SUSPENDED_SUPPLIERS — previously used suppliers now suspended
            7. LOW_RESPONSE_PORT — historical quote-to-invite ratio < 50%
        """
        flags: list[RiskFlag] = []

        # Run all risk checks concurrently-ish (sequentially to avoid session issues)
        if delivery_port and impa_codes:
            flag = await self._check_single_source(delivery_port, impa_codes)
            if flag:
                flags.append(flag)

        if delivery_date:
            flag = self._check_tight_timeline(delivery_date, bidding_deadline)
            if flag:
                flags.append(flag)

        if impa_codes:
            flag = await self._check_no_price_history(impa_codes, delivery_port)
            if flag:
                flags.append(flag)

        if impa_codes and buyer_organization_id:
            unusual_flags = await self._check_unusual_quantity(
                impa_codes, buyer_organization_id
            )
            flags.extend(unusual_flags)

        if impa_codes and buyer_organization_id:
            flag = await self._check_new_category(impa_codes, buyer_organization_id)
            if flag:
                flags.append(flag)

        if buyer_organization_id:
            flag = await self._check_suspended_suppliers(buyer_organization_id)
            if flag:
                flags.append(flag)

        if delivery_port:
            flag = await self._check_low_response_port(delivery_port)
            if flag:
                flags.append(flag)

        return flags

    # ------------------------------------------------------------------
    # Individual risk checks
    # ------------------------------------------------------------------

    async def _check_single_source(
        self,
        delivery_port: str,
        impa_codes: list[str],
    ) -> RiskFlag | None:
        """Risk 1: Only one approved supplier covers the port."""
        stmt = (
            select(func.count(SupplierProfile.id))
            .where(
                SupplierProfile.onboarding_status == OnboardingStatus.APPROVED,
                SupplierProfile.tier.in_([
                    SupplierTier.VERIFIED,
                    SupplierTier.PREFERRED,
                    SupplierTier.PREMIUM,
                ]),
            )
        )
        result = await self.db.execute(stmt)
        total_approved = result.scalar() or 0

        # Check how many of those cover this port (JSONB array check)
        all_stmt = (
            select(SupplierProfile.port_coverage)
            .where(
                SupplierProfile.onboarding_status == OnboardingStatus.APPROVED,
                SupplierProfile.tier.in_([
                    SupplierTier.VERIFIED,
                    SupplierTier.PREFERRED,
                    SupplierTier.PREMIUM,
                ]),
            )
        )
        all_result = await self.db.execute(all_stmt)
        port_suppliers = 0
        for row in all_result.all():
            port_coverage = row[0] or []
            if delivery_port in port_coverage or delivery_port.upper() in [
                p.upper() for p in port_coverage
            ]:
                port_suppliers += 1

        if port_suppliers <= 1:
            return RiskFlag(
                risk_type="SINGLE_SOURCE",
                severity="HIGH",
                message=(
                    f"Only {port_suppliers} verified+ supplier(s) cover port {delivery_port}. "
                    "Consider expanding supplier network."
                ),
                details={
                    "delivery_port": delivery_port,
                    "supplier_count": port_suppliers,
                    "total_approved": total_approved,
                },
            )
        return None

    def _check_tight_timeline(
        self,
        delivery_date: datetime,
        bidding_deadline: datetime | None = None,
    ) -> RiskFlag | None:
        """Risk 2: Delivery date is too close for comfortable procurement."""
        now = datetime.now(tz=UTC)
        days_until_delivery = (delivery_date - now).days

        if days_until_delivery < _DEFAULT_LEAD_TIME_DAYS:
            severity = "HIGH" if days_until_delivery < 7 else "MEDIUM"
            return RiskFlag(
                risk_type="TIGHT_TIMELINE",
                severity=severity,
                message=(
                    f"Only {days_until_delivery} day(s) until delivery. "
                    f"Typical lead time is {_DEFAULT_LEAD_TIME_DAYS} days."
                ),
                details={
                    "days_until_delivery": days_until_delivery,
                    "default_lead_time": _DEFAULT_LEAD_TIME_DAYS,
                    "delivery_date": delivery_date.isoformat(),
                },
            )
        return None

    async def _check_no_price_history(
        self,
        impa_codes: list[str],
        delivery_port: str | None,
    ) -> RiskFlag | None:
        """Risk 3: >50% of items have no historical pricing data."""
        cutoff = datetime.now(tz=UTC) - timedelta(
            days=settings.intelligence_price_benchmark_days
        )
        min_quotes = settings.intelligence_min_quotes_for_benchmark

        items_without_data = 0
        for impa_code in impa_codes:
            stmt = (
                select(func.count(QuoteLineItem.id))
                .join(Quote, QuoteLineItem.quote_id == Quote.id)
                .join(RfqLineItem, QuoteLineItem.rfq_line_item_id == RfqLineItem.id)
                .where(
                    RfqLineItem.impa_code == impa_code,
                    Quote.status.in_((QuoteStatus.SUBMITTED, QuoteStatus.AWARDED)),
                    Quote.submitted_at >= cutoff,
                    Quote.submitted_at.isnot(None),
                )
            )
            result = await self.db.execute(stmt)
            count = result.scalar() or 0
            if count < min_quotes:
                items_without_data += 1

        ratio = items_without_data / len(impa_codes) if impa_codes else 0
        if ratio > _NO_PRICE_HISTORY_THRESHOLD:
            return RiskFlag(
                risk_type="NO_PRICE_HISTORY",
                severity="MEDIUM",
                message=(
                    f"{items_without_data}/{len(impa_codes)} items lack sufficient "
                    "historical pricing data for accurate benchmarking."
                ),
                details={
                    "items_without_data": items_without_data,
                    "total_items": len(impa_codes),
                    "ratio": round(ratio, 2),
                },
            )
        return None

    async def _check_unusual_quantity(
        self,
        impa_codes: list[str],
        buyer_organization_id: uuid.UUID,
    ) -> list[RiskFlag]:
        """Risk 4: Provide quantity reference ranges from historical data."""
        flags = []
        for impa_code in impa_codes:
            # Get historical quantities for this buyer + IMPA code
            stmt = (
                select(
                    func.avg(RfqLineItem.quantity).label("avg_qty"),
                    func.stddev(RfqLineItem.quantity).label("stddev_qty"),
                )
                .join(Rfq, RfqLineItem.rfq_id == Rfq.id)
                .where(
                    RfqLineItem.impa_code == impa_code,
                    Rfq.buyer_organization_id == buyer_organization_id,
                )
            )
            result = await self.db.execute(stmt)
            row = result.first()

            if row and row.avg_qty and row.stddev_qty and float(row.stddev_qty) > 0:
                avg = float(row.avg_qty)
                stddev = float(row.stddev_qty)
                low = max(0, avg - _UNUSUAL_QTY_STDDEV_MULTIPLIER * stddev)
                high = avg + _UNUSUAL_QTY_STDDEV_MULTIPLIER * stddev
                flags.append(
                    RiskFlag(
                        risk_type="QUANTITY_REFERENCE",
                        severity="LOW",
                        message=(
                            f"IMPA {impa_code}: historical avg is {avg:.1f} "
                            f"(\u00b1{stddev:.1f}), typical range is {low:.1f}\u2013{high:.1f}."
                        ),
                        details={
                            "impa_code": impa_code,
                            "avg_quantity": avg,
                            "stddev": stddev,
                            "typical_low": round(low, 2),
                            "typical_high": round(high, 2),
                        },
                    )
                )
                if len(flags) > 5:
                    break

        return flags

    async def _check_new_category(
        self,
        impa_codes: list[str],
        buyer_organization_id: uuid.UUID,
    ) -> RiskFlag | None:
        """Risk 5: Buyer has never ordered from this IMPA category."""
        # Get IMPA category prefixes requested
        requested_prefixes = {code[:2] for code in impa_codes if len(code) >= 2}
        if not requested_prefixes:
            return None

        # Get all IMPA prefixes the buyer has previously ordered
        stmt = (
            select(RfqLineItem.impa_code)
            .join(Rfq, RfqLineItem.rfq_id == Rfq.id)
            .where(
                Rfq.buyer_organization_id == buyer_organization_id,
                RfqLineItem.impa_code.isnot(None),
            )
        )
        result = await self.db.execute(stmt)
        historical_prefixes = {
            row[0][:2] for row in result.all() if row[0] and len(row[0]) >= 2
        }

        new_categories = requested_prefixes - historical_prefixes
        if new_categories:
            return RiskFlag(
                risk_type="NEW_CATEGORY",
                severity="LOW",
                message=(
                    f"Buyer has not previously ordered from IMPA categor{'y' if len(new_categories) == 1 else 'ies'} "
                    f"{', '.join(sorted(new_categories))}. Verify specifications carefully."
                ),
                details={
                    "new_category_prefixes": sorted(new_categories),
                    "known_category_prefixes": sorted(historical_prefixes),
                },
            )
        return None

    async def _check_suspended_suppliers(
        self,
        buyer_organization_id: uuid.UUID,
    ) -> RiskFlag | None:
        """Risk 6: Previously used suppliers are now suspended."""
        # Find supplier orgs that were previously invited by this buyer
        invited_stmt = (
            select(RfqInvitation.supplier_organization_id)
            .join(Rfq, RfqInvitation.rfq_id == Rfq.id)
            .where(Rfq.buyer_organization_id == buyer_organization_id)
            .distinct()
        )
        invited_result = await self.db.execute(invited_stmt)
        invited_org_ids = [row[0] for row in invited_result.all()]

        if not invited_org_ids:
            return None

        # Check which of those are now suspended
        suspended_stmt = (
            select(func.count(SupplierProfile.id))
            .where(
                SupplierProfile.organization_id.in_(invited_org_ids),
                SupplierProfile.onboarding_status == OnboardingStatus.SUSPENDED,
            )
        )
        suspended_result = await self.db.execute(suspended_stmt)
        suspended_count = suspended_result.scalar() or 0

        if suspended_count > 0:
            return RiskFlag(
                risk_type="SUSPENDED_SUPPLIERS",
                severity="MEDIUM",
                message=(
                    f"{suspended_count} previously used supplier(s) are now suspended. "
                    "Consider finding replacement suppliers."
                ),
                details={
                    "suspended_count": suspended_count,
                    "total_historical_suppliers": len(invited_org_ids),
                },
            )
        return None

    async def _check_low_response_port(
        self,
        delivery_port: str,
    ) -> RiskFlag | None:
        """Risk 7: Historical quote-to-invite ratio at this port < 50%."""
        # Count invitations for RFQs at this port
        invite_stmt = (
            select(func.count(RfqInvitation.id))
            .join(Rfq, RfqInvitation.rfq_id == Rfq.id)
            .where(Rfq.delivery_port == delivery_port)
        )
        invite_result = await self.db.execute(invite_stmt)
        total_invitations = invite_result.scalar() or 0

        if total_invitations == 0:
            return None

        # Count quotes for RFQs at this port
        quote_stmt = (
            select(func.count(Quote.id))
            .join(Rfq, Quote.rfq_id == Rfq.id)
            .where(
                Rfq.delivery_port == delivery_port,
                Quote.status.in_((QuoteStatus.SUBMITTED, QuoteStatus.AWARDED)),
            )
        )
        quote_result = await self.db.execute(quote_stmt)
        total_quotes = quote_result.scalar() or 0

        response_ratio = total_quotes / total_invitations
        if response_ratio < _LOW_RESPONSE_RATIO:
            return RiskFlag(
                risk_type="LOW_RESPONSE_PORT",
                severity="MEDIUM",
                message=(
                    f"Port {delivery_port} has a {response_ratio:.0%} quote-to-invite ratio. "
                    "Consider inviting more suppliers or extending the bidding window."
                ),
                details={
                    "delivery_port": delivery_port,
                    "total_invitations": total_invitations,
                    "total_quotes": total_quotes,
                    "response_ratio": round(response_ratio, 2),
                },
            )
        return None
