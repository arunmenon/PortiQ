"""Centralized v1 API router — all module routers are included here."""

from fastapi import APIRouter

from src.modules.product.router import category_router, product_router, unit_router
from src.modules.search.router import router as search_router
from src.modules.supplier.router import router as supplier_router
from src.modules.tenancy.router import router as tenancy_router
from src.modules.rfq.router import router as rfq_router
from src.modules.vessel.router import router as vessel_router
from src.modules.prediction.router import router as prediction_router
from src.modules.intelligence.router import router as intelligence_router
from src.modules.document_ai.router import router as document_ai_router
from src.modules.tco.router import router as tco_router
from src.modules.portiq.router import router as portiq_router
from src.modules.order.router import router as order_router
from src.modules.delivery.router import router as delivery_router
from src.modules.delivery.router import sla_router as delivery_sla_router
from src.modules.dispute.router import router as dispute_router
from src.modules.invoice.router import router as invoice_router
from src.modules.invoice.router import settlement_router
from src.modules.export.router import router as export_router
from src.modules.port_call_requirement.router import router as requirement_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(search_router)
v1_router.include_router(tenancy_router)
v1_router.include_router(product_router)
v1_router.include_router(category_router)
v1_router.include_router(unit_router)
v1_router.include_router(supplier_router)
v1_router.include_router(vessel_router)
v1_router.include_router(rfq_router)
v1_router.include_router(prediction_router)
v1_router.include_router(intelligence_router)
v1_router.include_router(document_ai_router)
v1_router.include_router(tco_router)
v1_router.include_router(portiq_router)
v1_router.include_router(order_router)
v1_router.include_router(delivery_router)
v1_router.include_router(delivery_sla_router)
v1_router.include_router(dispute_router)
v1_router.include_router(invoice_router)
v1_router.include_router(settlement_router)
v1_router.include_router(export_router)
v1_router.include_router(requirement_router)
