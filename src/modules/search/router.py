"""FastAPI router for search endpoints."""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.modules.search.embedding import EmbeddingService
from src.modules.search.faceted_search import FacetedSearchService
from src.modules.search.schemas import (
    FacetedSearchResponse,
    GenerateEmbeddingsRequest,
    GenerateEmbeddingsResponse,
    MatchLineItemRequest,
    MatchResponse,
    SearchProductsRequest,
    SearchResponse,
    SynonymEntry,
    TextSearchResponse,
    TextSearchResult,
)
from src.modules.search.service import VectorSearchService
from src.modules.search.tasks import generate_embeddings
from src.modules.search.text_search import TextSearchService
from src.modules.tenancy.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/search", tags=["search"])
limiter = Limiter(key_func=get_remote_address)


def _get_search_service(session: AsyncSession = Depends(get_db)) -> VectorSearchService:
    return VectorSearchService(session=session, embedding_service=EmbeddingService())


def _get_text_search_service(session: AsyncSession = Depends(get_db)) -> TextSearchService:
    return TextSearchService(session=session, embedding_service=EmbeddingService())


@router.post("/products", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search_products(
    request_obj: Request,
    request: SearchProductsRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: VectorSearchService = Depends(_get_search_service),
) -> SearchResponse:
    """Search for similar products using pgvector cosine similarity."""
    results = await service.search_similar_products(
        query=request.query,
        limit=request.limit,
        min_similarity=request.min_similarity,
        category_id=request.category_id,
        precision=request.precision,
    )
    return SearchResponse(results=results, query=request.query, total=len(results))


@router.post("/match", response_model=MatchResponse)
@limiter.limit("20/minute")
async def match_line_item(
    request_obj: Request,
    request: MatchLineItemRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: VectorSearchService = Depends(_get_search_service),
) -> MatchResponse:
    """Match a line item description to the closest product in the catalogue."""
    match_result, candidates_evaluated = await service.find_matching_product(request)
    return MatchResponse(match=match_result, candidates_evaluated=candidates_evaluated)


@router.post("/embeddings/generate", response_model=GenerateEmbeddingsResponse)
@limiter.limit("5/minute")
async def queue_embedding_generation(
    request_obj: Request,
    request: GenerateEmbeddingsRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> GenerateEmbeddingsResponse:
    """Queue asynchronous embedding generation for the given product IDs."""
    task = generate_embeddings.delay([str(pid) for pid in request.product_ids])
    return GenerateEmbeddingsResponse(
        task_id=task.id,
        product_count=len(request.product_ids),
        message=f"Embedding generation queued for {len(request.product_ids)} products",
    )


# ---------------------------------------------------------------------------
# Text search endpoints (FTS + trigram + hybrid)
# ---------------------------------------------------------------------------


@router.get("/products/text", response_model=TextSearchResponse)
@limiter.limit("60/minute")
async def text_search_products(
    request: Request,
    query: str = Query(max_length=1000),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    category_id: UUID | None = Query(default=None),
    mode: str = Query(default="hybrid", pattern="^(keyword|fuzzy|hybrid)$"),
    _user: AuthenticatedUser = Depends(get_current_user),
    service: TextSearchService = Depends(_get_text_search_service),
) -> TextSearchResponse:
    """Search products using PostgreSQL full-text, trigram fuzzy, or hybrid mode."""
    offset = (page - 1) * limit
    results, total = await service.search(
        query=query,
        mode=mode,
        limit=limit,
        offset=offset,
        category_id=category_id,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 0
    return TextSearchResponse(
        results=results,
        query=query,
        total=total,
        page=page,
        total_pages=total_pages,
    )


@router.get("/suggest", response_model=list[TextSearchResult])
@limiter.limit("120/minute")
async def suggest_products(
    request: Request,
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
    _user: AuthenticatedUser = Depends(get_current_user),
    service: TextSearchService = Depends(_get_text_search_service),
) -> list[TextSearchResult]:
    """Autocomplete / prefix suggestions for the search bar."""
    return await service.suggest(prefix=q, limit=limit)


# ---------------------------------------------------------------------------
# Faceted search & synonyms
# ---------------------------------------------------------------------------


def _get_faceted_search_service(session: AsyncSession = Depends(get_db)) -> FacetedSearchService:
    return FacetedSearchService(session=session, embedding_service=EmbeddingService())


@router.get("/products/faceted", response_model=FacetedSearchResponse)
@limiter.limit("60/minute")
async def faceted_search_products(
    request: Request,
    query: str = Query(max_length=1000),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    category_id: UUID | None = Query(default=None),
    ihm_relevant: bool | None = Query(default=None),
    hazmat_class: str | None = Query(default=None),
    _user: AuthenticatedUser = Depends(get_current_user),
    service: FacetedSearchService = Depends(_get_faceted_search_service),
) -> FacetedSearchResponse:
    """Search products with faceted filtering and aggregation."""
    offset = (page - 1) * limit
    filters: dict = {}
    if category_id is not None:
        filters["category_id"] = category_id
    if ihm_relevant is not None:
        filters["ihm_relevant"] = ihm_relevant
    if hazmat_class is not None:
        filters["hazmat_class"] = hazmat_class

    results, total, facets = await service.search_with_facets(
        query=query, filters=filters, limit=limit, offset=offset,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 0
    return FacetedSearchResponse(
        results=results,
        query=query,
        total=total,
        page=page,
        total_pages=total_pages,
        facets=facets,
    )


@router.get("/synonyms", response_model=list[SynonymEntry])
@limiter.limit("60/minute")
async def list_synonyms(
    request: Request,
    term: str | None = Query(default=None, max_length=100),
    _user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[SynonymEntry]:
    """Get known search synonyms, optionally filtered by term."""
    if term:
        result = await session.execute(
            text("SELECT term, synonyms, domain FROM search_synonyms WHERE term ILIKE :term ORDER BY term"),
            {"term": f"%{term}%"},
        )
    else:
        result = await session.execute(
            text("SELECT term, synonyms, domain FROM search_synonyms ORDER BY term")
        )
    rows = result.mappings().all()
    return [SynonymEntry(term=row["term"], synonyms=row["synonyms"], domain=row["domain"]) for row in rows]
