"""Centralized v1 API router — all module routers are included here."""

from fastapi import APIRouter

from src.modules.product.router import category_router, product_router, unit_router
from src.modules.search.router import router as search_router
from src.modules.supplier.router import router as supplier_router
from src.modules.tenancy.router import router as tenancy_router
from src.modules.vessel.router import router as vessel_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(search_router)
v1_router.include_router(tenancy_router)
v1_router.include_router(product_router)
v1_router.include_router(category_router)
v1_router.include_router(unit_router)
v1_router.include_router(supplier_router)
v1_router.include_router(vessel_router)
