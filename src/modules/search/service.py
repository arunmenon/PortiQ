"""VectorSearchService — pgvector-based product similarity search."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.search.constants import PRECISION_LEVELS
from src.modules.search.embedding import EmbeddingService
from src.modules.search.reranking import RerankingService
from src.modules.search.schemas import (
    MatchLineItemRequest,
    ProductMatchResult,
    SimilarProductResult,
)


class VectorSearchService:
    """Performs cosine-distance searches against the products embedding column."""

    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService) -> None:
        self._session = session
        self._embedding_service = embedding_service
        self._reranking_service = RerankingService()

    async def search_similar_products(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5,
        category_id: uuid.UUID | None = None,
        precision: str = "balanced",
    ) -> list[SimilarProductResult]:
        """Search products by cosine similarity to *query* embedding.

        Uses ``SET LOCAL hnsw.ef_search`` to control the precision/speed trade-off
        within the current transaction.
        """
        query_embedding = await self._embedding_service.generate_embedding(query)

        ef_search = PRECISION_LEVELS.get(precision, PRECISION_LEVELS["balanced"])

        # SET LOCAL scopes the parameter to the current transaction.
        # ef_search comes from PRECISION_LEVELS (a hardcoded int dict); cast to int
        # as a safety net since SET LOCAL does not support bind parameters.
        await self._session.execute(
            text("SET LOCAL hnsw.ef_search = :val"),
            {"val": int(ef_search)},
        )

        params: dict = {"embedding": str(query_embedding)}

        if category_id is not None:
            params["category_id"] = str(category_id)

        # Build SQL conditionally — avoids string interpolation in SQL
        base_sql = """
            SELECT * FROM (
                SELECT
                    p.id,
                    p.impa_code,
                    p.name,
                    p.description,
                    c.name AS category_name,
                    1 - (p.embedding <=> :embedding::vector) AS similarity
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE p.embedding IS NOT NULL
                {category_filter}
            ) sub
            WHERE sub.similarity >= :min_similarity
            ORDER BY sub.similarity DESC
            LIMIT :limit
        """
        if category_id is not None:
            search_sql = text(base_sql.replace("{category_filter}", "AND p.category_id = :category_id"))
        else:
            search_sql = text(base_sql.replace("{category_filter}", ""))

        result = await self._session.execute(search_sql, params | {"min_similarity": min_similarity, "limit": limit})
        rows = result.mappings().all()

        return [
            SimilarProductResult(
                id=row["id"],
                impa_code=row["impa_code"],
                name=row["name"],
                description=row["description"],
                category_name=row["category_name"],
                similarity=round(float(row["similarity"]), 4),
            )
            for row in rows
        ]

    async def find_matching_product(
        self,
        request: MatchLineItemRequest,
    ) -> tuple[ProductMatchResult | None, int]:
        """Search with a wider net, then rerank to find the best product match.

        Returns (best_match_or_None, candidates_evaluated).
        """
        # Build search text from the line-item fields
        search_parts = [request.product_name]
        if request.specifications:
            search_parts.append(request.specifications)
        if request.impa_code:
            search_parts.append(f"IMPA {request.impa_code}")
        search_text = " ".join(search_parts)

        # Wider search — fetch more candidates for reranking
        candidates = await self.search_similar_products(
            query=search_text,
            limit=20,
            min_similarity=0.3,
            precision="accurate",
        )

        if not candidates:
            return None, 0

        # Convert to dicts for reranking
        candidate_dicts = [
            {
                "id": str(c.id),
                "impa_code": c.impa_code,
                "name": c.name,
                "description": c.description,
                "category_name": c.category_name,
                "similarity": c.similarity,
            }
            for c in candidates
        ]

        reranked = self._reranking_service.rerank_candidates(
            candidate_dicts,
            impa_code=request.impa_code,
            unit=request.unit,
        )

        best = reranked[0]
        category_matches = (
            request.expected_category is None
            or (best.get("category_name") or "").lower() == request.expected_category.lower()
        )
        confidence = self._reranking_service.calculate_confidence(
            best["boosted_similarity"],
            extraction_confidence=request.confidence,
            category_matches=category_matches,
        )
        match_reason = self._reranking_service.explain_match(
            best,
            impa_code=request.impa_code,
            unit=request.unit,
        )

        product_result = SimilarProductResult(
            id=uuid.UUID(best["id"]),
            impa_code=best["impa_code"],
            name=best["name"],
            description=best["description"],
            category_name=best["category_name"],
            similarity=best["boosted_similarity"],
        )

        return (
            ProductMatchResult(
                product=product_result,
                confidence=confidence,
                match_reason=match_reason,
            ),
            len(reranked),
        )
