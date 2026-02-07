"""FacetedSearchService — Hybrid search with PostgreSQL-native facet aggregation."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.search.embedding import EmbeddingService
from src.modules.search.schemas import FacetCount, TextSearchResult

_IMPA_CODE_RE = re.compile(r"^\d{1,6}$")
_MIN_WORDS_FOR_VECTOR = 3


class FacetedSearchService:
    """Provides hybrid search with category, ihm_relevant, and hazmat_class facets."""

    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService) -> None:
        self._session = session
        self._embedding_service = embedding_service

    async def search_with_facets(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TextSearchResult], int, dict[str, list[FacetCount]]]:
        """Execute hybrid search and return (results, total_count, facets).

        Facets are computed over the *unfiltered* result set (before applying
        category/ihm/hazmat filters) so the UI can show valid counts for
        narrowing.  Results are returned with filters applied.
        """
        filters = filters or {}
        is_impa_query = bool(_IMPA_CODE_RE.match(query.strip()))
        use_vector = len(query.split()) >= _MIN_WORDS_FOR_VECTOR

        params: dict = {"query": query, "limit": limit, "offset": offset}

        # Score components
        score_parts: list[str] = []
        if is_impa_query:
            score_parts.append("CASE WHEN p.impa_code = :query THEN 1.0 ELSE 0.0 END")

        score_parts.append(
            "coalesce(ts_rank_cd(p.search_vector, websearch_to_tsquery('english', :query)), 0) * 0.4"
        )
        score_parts.append("coalesce(similarity(p.name, :query), 0) * 0.3")

        if use_vector:
            query_embedding = await self._embedding_service.generate_embedding(query)
            params["embedding"] = str(query_embedding)
            score_parts.append(
                "CASE WHEN p.embedding IS NOT NULL "
                "THEN (1 - (p.embedding <=> :embedding::vector)) * 0.3 "
                "ELSE 0.0 END"
            )

        combined_score = "GREATEST(" + ", ".join(score_parts) + ")"

        # Match conditions (OR — any strategy)
        where_conditions = [
            "p.search_vector @@ websearch_to_tsquery('english', :query)",
            "similarity(p.name, :query) >= 0.2",
        ]
        if is_impa_query:
            where_conditions.append("p.impa_code = :query")
        if use_vector:
            where_conditions.append(
                "(p.embedding IS NOT NULL AND (1 - (p.embedding <=> :embedding::vector)) >= 0.3)"
            )

        base_where = "(" + " OR ".join(where_conditions) + ")"

        # Build optional filter clauses
        filter_clauses: list[str] = []
        if filters.get("category_id"):
            filter_clauses.append("p.category_id = :filter_category_id")
            params["filter_category_id"] = str(filters["category_id"])
        if filters.get("ihm_relevant") is not None:
            filter_clauses.append("p.ihm_relevant = :filter_ihm")
            params["filter_ihm"] = filters["ihm_relevant"]
        if filters.get("hazmat_class"):
            filter_clauses.append("p.hazmat_class = :filter_hazmat")
            params["filter_hazmat"] = filters["hazmat_class"]

        filter_where = (" AND " + " AND ".join(filter_clauses)) if filter_clauses else ""

        # Single query: CTE for base matches, then facets + filtered results
        sql = text(f"""
            WITH base_matches AS (
                SELECT
                    p.id,
                    p.impa_code,
                    p.name,
                    p.description,
                    p.category_id,
                    p.ihm_relevant,
                    p.hazmat_class,
                    c.name AS category_name,
                    {combined_score} AS score,
                    ts_headline(
                        'english',
                        coalesce(p.name, '') || ' ' || coalesce(p.description, ''),
                        websearch_to_tsquery('english', :query),
                        'StartSel=<b>, StopSel=</b>, MaxFragments=2, MaxWords=30'
                    ) AS highlight
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE {base_where}
            ),
            facet_category AS (
                SELECT category_name AS value, count(*) AS cnt
                FROM base_matches
                WHERE category_name IS NOT NULL
                GROUP BY category_name
                ORDER BY cnt DESC
            ),
            facet_ihm AS (
                SELECT
                    CASE WHEN ihm_relevant THEN 'true' ELSE 'false' END AS value,
                    count(*) AS cnt
                FROM base_matches
                GROUP BY ihm_relevant
                ORDER BY cnt DESC
            ),
            facet_hazmat AS (
                SELECT hazmat_class AS value, count(*) AS cnt
                FROM base_matches
                WHERE hazmat_class IS NOT NULL
                GROUP BY hazmat_class
                ORDER BY cnt DESC
            ),
            filtered AS (
                SELECT *, count(*) OVER() AS total_count
                FROM base_matches
                WHERE 1=1 {filter_where}
            )
            SELECT
                'result' AS _type,
                f.id, f.impa_code, f.name, f.description, f.category_name,
                f.score, f.highlight, f.total_count,
                NULL AS facet_kind, NULL AS facet_value, NULL AS facet_count
            FROM filtered f
            ORDER BY f.score DESC
            LIMIT :limit OFFSET :offset
        """)

        # Facet queries (separate for clarity and to avoid Cartesian product)
        facet_sql = text(f"""
            WITH base_matches AS (
                SELECT
                    p.id,
                    p.impa_code,
                    p.name,
                    p.ihm_relevant,
                    p.hazmat_class,
                    c.name AS category_name,
                    {combined_score} AS score
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE {base_where}
            )
            SELECT 'category' AS facet_kind, category_name AS facet_value, count(*)::int AS facet_count
            FROM base_matches WHERE category_name IS NOT NULL GROUP BY category_name
            UNION ALL
            SELECT 'ihm_relevant', CASE WHEN ihm_relevant THEN 'true' ELSE 'false' END, count(*)::int
            FROM base_matches GROUP BY ihm_relevant
            UNION ALL
            SELECT 'hazmat_class', hazmat_class, count(*)::int
            FROM base_matches WHERE hazmat_class IS NOT NULL GROUP BY hazmat_class
        """)

        # Execute both queries
        result_rows = (await self._session.execute(sql, params)).mappings().all()
        facet_rows = (await self._session.execute(facet_sql, params)).mappings().all()

        # Parse results
        total = int(result_rows[0]["total_count"]) if result_rows else 0
        results = [
            TextSearchResult(
                id=row["id"],
                impa_code=row["impa_code"],
                name=row["name"],
                description=row["description"],
                category_name=row["category_name"],
                score=round(float(row["score"]), 4),
                highlight=row["highlight"],
            )
            for row in result_rows
        ]

        # Parse facets
        facets: dict[str, list[FacetCount]] = {
            "category": [],
            "ihm_relevant": [],
            "hazmat_class": [],
        }
        for row in facet_rows:
            kind = row["facet_kind"]
            if kind in facets:
                facets[kind].append(FacetCount(value=row["facet_value"], count=row["facet_count"]))

        # Sort facets by count descending
        for key in facets:
            facets[key].sort(key=lambda fc: fc.count, reverse=True)

        return results, total, facets
