"""Tool executor — dispatches AI tool calls to existing platform services."""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enums import OnboardingStatus, RfqStatus, SupplierTier
from src.models.supplier_profile import SupplierProfile
from src.modules.tenancy.auth import AuthenticatedUser

logger = logging.getLogger(__name__)

# Matches 7-digit IMO numbers
_IMO_RE = re.compile(r"^\d{7}$")
# Matches 6-digit IMPA codes
_IMPA_RE = re.compile(r"^\d{6}$")


class ToolExecutor:
    """Executes PortiQ AI tool calls by delegating to existing platform services."""

    def __init__(self, db: AsyncSession, user: AuthenticatedUser) -> None:
        self.db = db
        self.user = user

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Dispatch a tool call to the appropriate handler.

        Returns a serializable dict. Errors are returned as {"error": message}
        rather than raising exceptions, so the LLM can handle them gracefully.
        """
        handler = getattr(self, f"_handle_{tool_name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return await handler(arguments)
        except Exception as exc:
            logger.warning("Tool %s failed: %s", tool_name, exc, exc_info=True)
            return {"error": f"Tool execution failed: {str(exc)}"}

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _handle_search_products(self, args: dict) -> dict:
        from src.modules.search.embedding import EmbeddingService
        from src.modules.search.text_search import TextSearchService

        query = args.get("query", "")
        limit = min(args.get("limit", 10), 50)

        embedding_svc = EmbeddingService(self.db)
        search_svc = TextSearchService(self.db, embedding_svc)
        results, total = await search_svc.keyword_search(query=query, limit=limit)

        items = [
            {
                "id": str(r.id),
                "impa_code": r.impa_code,
                "name": r.name,
                "description": r.description,
                "category": r.category_name,
                "score": round(r.score, 3) if r.score else None,
            }
            for r in results
        ]
        return {"items": items, "total": total, "query": query}

    async def _handle_get_product_details(self, args: dict) -> dict:
        from src.modules.product.service import ProductService

        identifier = args.get("product_id_or_impa", "")
        svc = ProductService(self.db)

        if _IMPA_RE.match(identifier):
            product = await svc.get_product_by_impa(identifier)
        else:
            product = await svc.get_product_detail(uuid.UUID(identifier))

        return {
            "id": str(product.id),
            "impa_code": product.impa_code,
            "name": product.name,
            "description": product.description,
            "unit_of_measure": product.unit_of_measure,
            "category_id": str(product.category_id) if product.category_id else None,
            "specifications": product.specifications,
        }

    async def _handle_create_rfq(self, args: dict) -> dict:
        from src.modules.rfq.rfq_service import RfqService

        title = args.get("title", "")
        delivery_port = args.get("delivery_port", "")
        line_items_data = args.get("line_items", [])

        svc = RfqService(self.db)
        rfq = await svc.create_rfq(
            buyer_organization_id=self.user.organization_id,
            created_by=self.user.id,
            title=title,
            delivery_port=delivery_port,
        )

        for idx, item in enumerate(line_items_data, start=1):
            await svc.add_line_item(
                rfq_id=rfq.id,
                line_number=idx,
                description=item.get("description", ""),
                quantity=float(item.get("quantity", 1)),
                unit_of_measure=item.get("unit", "PCS"),
                impa_code=item.get("impa_code"),
            )

        return {
            "id": str(rfq.id),
            "reference_number": rfq.reference_number,
            "title": rfq.title,
            "status": rfq.status.value,
            "delivery_port": rfq.delivery_port,
            "line_item_count": len(line_items_data),
        }

    async def _handle_list_rfqs(self, args: dict) -> dict:
        from src.modules.rfq.rfq_service import RfqService

        status_str = args.get("status")
        limit = min(args.get("limit", 10), 50)

        status_filter = RfqStatus(status_str) if status_str else None

        svc = RfqService(self.db)
        rfqs, total = await svc.list_rfqs(
            organization_id=self.user.organization_id,
            organization_type=self.user.organization_type,
            status=status_filter,
            limit=limit,
        )

        items = [
            {
                "id": str(rfq.id),
                "reference_number": rfq.reference_number,
                "title": rfq.title,
                "status": rfq.status.value,
                "delivery_port": rfq.delivery_port,
                "created_at": rfq.created_at.isoformat() if rfq.created_at else None,
            }
            for rfq in rfqs
        ]
        return {"items": items, "total": total}

    async def _handle_get_rfq_details(self, args: dict) -> dict:
        from src.modules.rfq.rfq_service import RfqService

        rfq_id = uuid.UUID(args.get("rfq_id", ""))

        svc = RfqService(self.db)
        rfq = await svc.get_rfq(rfq_id)

        line_items = [
            {
                "line_number": li.line_number,
                "description": li.description,
                "quantity": float(li.quantity) if li.quantity else None,
                "unit_of_measure": li.unit_of_measure,
                "impa_code": li.impa_code,
            }
            for li in (rfq.line_items or [])
        ]

        invitations = [
            {
                "supplier_organization_id": str(inv.supplier_organization_id),
                "status": inv.status.value,
            }
            for inv in (rfq.invitations or [])
        ]

        return {
            "id": str(rfq.id),
            "reference_number": rfq.reference_number,
            "title": rfq.title,
            "description": rfq.description,
            "status": rfq.status.value,
            "delivery_port": rfq.delivery_port,
            "delivery_date": rfq.delivery_date.isoformat() if rfq.delivery_date else None,
            "bidding_deadline": rfq.bidding_deadline.isoformat() if rfq.bidding_deadline else None,
            "currency": rfq.currency,
            "line_items": line_items,
            "invitations": invitations,
            "created_at": rfq.created_at.isoformat() if rfq.created_at else None,
        }

    async def _handle_list_suppliers(self, args: dict) -> dict:
        tier_str = args.get("tier")
        port = args.get("port")

        query = select(SupplierProfile).where(
            SupplierProfile.onboarding_status == OnboardingStatus.APPROVED
        )

        if tier_str:
            tier_enum = SupplierTier(tier_str)
            query = query.where(SupplierProfile.tier >= tier_enum)

        if port:
            query = query.where(
                SupplierProfile.port_coverage.contains([port])
            )

        result = await self.db.execute(query.limit(20))
        profiles = result.scalars().all()

        items = [
            {
                "id": str(p.id),
                "company_name": p.company_name,
                "tier": p.tier.value,
                "categories": p.categories,
                "port_coverage": p.port_coverage,
                "city": p.city,
                "country": p.country,
            }
            for p in profiles
        ]
        return {"items": items, "total": len(items)}

    async def _handle_get_intelligence(self, args: dict) -> dict:
        from src.modules.intelligence.price_benchmark_service import PriceBenchmarkService
        from src.modules.intelligence.risk_analyzer import RiskAnalyzer
        from src.modules.intelligence.supplier_matching import SupplierMatchingService
        from src.modules.intelligence.timing_advisor import TimingAdvisor

        delivery_port = args.get("delivery_port")
        impa_codes = args.get("impa_codes", [])
        vessel_id_str = args.get("vessel_id")
        vessel_id = uuid.UUID(vessel_id_str) if vessel_id_str else None

        result: dict = {}

        if impa_codes:
            benchmark_svc = PriceBenchmarkService(self.db)
            benchmarks = await benchmark_svc.get_price_benchmarks(
                impa_codes=impa_codes,
                delivery_port=delivery_port,
            )
            result["price_benchmarks"] = [
                {
                    "impa_code": b.impa_code,
                    "p25": float(b.p25) if b.p25 else None,
                    "p50": float(b.p50) if b.p50 else None,
                    "p75": float(b.p75) if b.p75 else None,
                    "sample_count": b.sample_count,
                    "currency": b.currency,
                }
                for b in benchmarks
            ]

        if delivery_port:
            matching_svc = SupplierMatchingService(self.db)
            match_result = await matching_svc.match_suppliers(
                delivery_port=delivery_port,
                impa_codes=impa_codes or None,
                buyer_organization_id=self.user.organization_id,
            )
            result["suppliers"] = {
                "ranked": [
                    {
                        "supplier_id": str(s.supplier_id),
                        "company_name": s.company_name,
                        "tier": s.tier,
                        "score": round(s.score, 3),
                    }
                    for s in match_result.ranked_suppliers
                ],
                "total": match_result.total_candidates,
            }

        if delivery_port or impa_codes:
            risk_svc = RiskAnalyzer(self.db)
            risks = await risk_svc.analyze_risks(
                delivery_port=delivery_port,
                vessel_id=vessel_id,
                impa_codes=impa_codes or None,
                buyer_organization_id=self.user.organization_id,
            )
            result["risks"] = [
                {
                    "type": r.risk_type,
                    "severity": r.severity,
                    "message": r.message,
                }
                for r in risks
            ]

        if delivery_port or vessel_id:
            timing_svc = TimingAdvisor(self.db)
            timing = await timing_svc.get_timing_advice(
                delivery_port=delivery_port,
                vessel_id=vessel_id,
            )
            result["timing"] = {
                "assessment": timing.assessment,
                "recommended_bidding_window_days": timing.recommended_bidding_window_days,
                "vessel_eta": timing.vessel_eta.isoformat() if timing.vessel_eta else None,
                "avg_response_days": timing.avg_response_days,
            }

        return result

    async def _handle_predict_consumption(self, args: dict) -> dict:
        from src.modules.prediction.consumption_engine import ConsumptionEngine

        vessel_id = uuid.UUID(args.get("vessel_id", ""))
        crew_size = int(args.get("crew_size", 20))
        voyage_days = int(args.get("voyage_days", 14))

        engine = ConsumptionEngine(self.db)
        predictions = await engine.predict_quantities(
            vessel_id=vessel_id,
            voyage_days=voyage_days,
            crew_size=crew_size,
        )

        items = [
            {
                "category": p.category,
                "product_name": p.product_name,
                "impa_code": p.impa_code,
                "predicted_quantity": float(p.predicted_quantity),
                "unit": p.unit,
                "confidence": round(p.confidence, 2),
            }
            for p in predictions
        ]
        return {"items": items, "vessel_id": str(vessel_id), "voyage_days": voyage_days}

    async def _handle_get_vessel_info(self, args: dict) -> dict:
        from src.modules.vessel.vessel_service import VesselService

        identifier = args.get("vessel_id_or_imo", "")
        svc = VesselService(self.db)

        if _IMO_RE.match(identifier):
            vessel = await svc.get_vessel_by_imo(identifier)
        else:
            vessel = await svc.get_vessel(uuid.UUID(identifier))

        result = {
            "id": str(vessel.id),
            "name": vessel.name,
            "imo_number": vessel.imo_number,
            "mmsi": vessel.mmsi,
            "vessel_type": vessel.vessel_type.value if vessel.vessel_type else None,
            "status": vessel.status.value if vessel.status else None,
            "flag_state": vessel.flag_state,
            "gross_tonnage": float(vessel.gross_tonnage) if vessel.gross_tonnage else None,
            "deadweight_tonnage": float(vessel.deadweight_tonnage) if vessel.deadweight_tonnage else None,
            "year_built": vessel.year_built,
        }

        # Try to get latest position
        try:
            from src.models.vessel_position import VesselPosition

            pos_result = await self.db.execute(
                select(VesselPosition)
                .where(VesselPosition.vessel_id == vessel.id)
                .order_by(VesselPosition.recorded_at.desc())
                .limit(1)
            )
            latest_pos = pos_result.scalar_one_or_none()
            if latest_pos:
                result["latest_position"] = {
                    "latitude": float(latest_pos.latitude),
                    "longitude": float(latest_pos.longitude),
                    "speed_knots": float(latest_pos.speed_knots) if latest_pos.speed_knots else None,
                    "recorded_at": latest_pos.recorded_at.isoformat() if latest_pos.recorded_at else None,
                }
        except Exception:
            pass

        return result

    async def _handle_match_suppliers_for_port(self, args: dict) -> dict:
        from src.modules.intelligence.supplier_matching import SupplierMatchingService

        port = args.get("port", "")
        impa_codes = args.get("impa_codes")

        svc = SupplierMatchingService(self.db)
        match_result = await svc.match_suppliers(
            delivery_port=port,
            impa_codes=impa_codes,
            buyer_organization_id=self.user.organization_id,
        )

        ranked = [
            {
                "supplier_id": str(s.supplier_id),
                "company_name": s.company_name,
                "tier": s.tier,
                "score": round(s.score, 3),
                "port_coverage": s.port_coverage,
                "category_match_ratio": round(s.category_match_ratio, 2) if s.category_match_ratio else None,
            }
            for s in match_result.ranked_suppliers
        ]

        return {
            "port": port,
            "ranked_suppliers": ranked,
            "total_candidates": match_result.total_candidates,
        }
