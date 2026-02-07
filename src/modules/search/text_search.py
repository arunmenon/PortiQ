"""TextSearchService — PostgreSQL-native hybrid search (FTS + pg_trgm + pgvector)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.search.embedding import EmbeddingService
from src.modules.search.schemas import TextSearchResult

# Matches 1-6 digit strings (potential IMPA codes)
_IMPA_CODE_RE = re.compile(r"^\d{1,6}$")

# Queries with 3+ words are worth embedding for semantic search
_MIN_WORDS_FOR_VECTOR = 3


class TextSearchService:
    """Provides keyword, fuzzy, and hybrid search over the products table.

    Leverages PostgreSQL full-text search (tsvector/tsquery), pg_trgm
    trigram similarity, and pgvector embeddings — all in-database with
    zero external dependencies.
    """

    # Configurable scoring weights for hybrid search
    FTS_WEIGHT: float = 0.4
    TRIGRAM_WEIGHT: float = 0.3
    VECTOR_WEIGHT: float = 0.3

    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService) -> None:
        self._session = session
        self._embedding_service = embedding_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def keyword_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_id: uuid.UUID | None = None,
    ) -> tuple[list[TextSearchResult], int]:
        """Full-text search using tsvector with cover-density ranking."""
        category_filter = "AND p.category_id = :category_id" if category_id else ""
        params: dict = {"query": query, "limit": limit, "offset": offset}
        if category_id:
            params["category_id"] = str(category_id)

        sql = text(f"""
            WITH ranked AS (
                SELECT
                    p.id,
                    p.impa_code,
                    p.name,
                    p.description,
                    c.name AS category_name,
                    ts_rank_cd(p.search_vector, websearch_to_tsquery('english', :query)) AS score,
                    ts_headline(
                        'english',
                        coalesce(p.name, '') || ' ' || coalesce(p.description, ''),
                        websearch_to_tsquery('english', :query),
                        'StartSel=<b>, StopSel=</b>, MaxFragments=2, MaxWords=30'
                    ) AS highlight,
                    count(*) OVER() AS total_count
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE p.search_vector @@ websearch_to_tsquery('english', :query)
                {category_filter}
            )
            SELECT * FROM ranked
            ORDER BY score DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await self._session.execute(sql, params)
        rows = result.mappings().all()

        total = int(rows[0]["total_count"]) if rows else 0
        results = [self._row_to_result(row) for row in rows]
        return results, total

    async def fuzzy_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_id: uuid.UUID | None = None,
        threshold: float = 0.3,
    ) -> tuple[list[TextSearchResult], int]:
        """Trigram-based fuzzy search for typo tolerance."""
        category_filter = "AND p.category_id = :category_id" if category_id else ""
        params: dict = {
            "query": query,
            "threshold": threshold,
            "limit": limit,
            "offset": offset,
        }
        if category_id:
            params["category_id"] = str(category_id)

        sql = text(f"""
            WITH ranked AS (
                SELECT
                    p.id,
                    p.impa_code,
                    p.name,
                    p.description,
                    c.name AS category_name,
                    similarity(p.name, :query) AS score,
                    NULL AS highlight,
                    count(*) OVER() AS total_count
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE similarity(p.name, :query) >= :threshold
                {category_filter}
            )
            SELECT * FROM ranked
            ORDER BY score DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await self._session.execute(sql, params)
        rows = result.mappings().all()

        total = int(rows[0]["total_count"]) if rows else 0
        results = [self._row_to_result(row) for row in rows]
        return results, total

    async def _expand_synonyms(self, query: str) -> str:
        """Look up query terms in the search_synonyms table and expand the query.

        For each word in the query that has a synonym entry, the synonyms are
        appended to produce a broader recall query.  The original query terms
        are always preserved.
        """
        words = query.lower().split()
        if not words:
            return query

        result = await self._session.execute(
            text(
                "SELECT term, synonyms FROM search_synonyms "
                "WHERE term = ANY(:terms)"
            ),
            {"terms": words},
        )
        synonym_map: dict[str, list[str]] = {}
        for row in result.mappings().all():
            synonym_map[row["term"]] = row["synonyms"]

        if not synonym_map:
            return query

        expanded_parts = [query]
        for word in words:
            if word in synonym_map:
                expanded_parts.extend(synonym_map[word])

        return " ".join(expanded_parts)

    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        category_id: uuid.UUID | None = None,
    ) -> tuple[list[TextSearchResult], int]:
        """Combine FTS keyword, trigram fuzzy, and vector semantic search.

        Scoring weights are controlled by class-level constants:
        - Exact IMPA code match: score = 1.0
        - FTS keyword: ts_rank_cd * FTS_WEIGHT
        - Trigram fuzzy: similarity * TRIGRAM_WEIGHT
        - Vector semantic: (1 - cosine_distance) * VECTOR_WEIGHT  (only for 3+ word queries)
        """
        # Expand query with synonyms for broader recall
        expanded_query = await self._expand_synonyms(query)

        is_impa_query = bool(_IMPA_CODE_RE.match(query.strip()))
        use_vector = len(query.split()) >= _MIN_WORDS_FOR_VECTOR

        category_filter = "AND p.category_id = :category_id" if category_id else ""
        params: dict = {"query": expanded_query, "limit": limit, "offset": offset}
        if category_id:
            params["category_id"] = str(category_id)

        fts_w = self.FTS_WEIGHT
        tri_w = self.TRIGRAM_WEIGHT
        vec_w = self.VECTOR_WEIGHT

        # Build score components
        score_parts = []

        if is_impa_query:
            # Exact IMPA code match gets maximum score (use original query for exact match)
            params["original_query"] = query
            score_parts.append(
                "CASE WHEN p.impa_code = :original_query THEN 1.0 ELSE 0.0 END"
            )

        # FTS component
        score_parts.append(
            f"coalesce(ts_rank_cd(p.search_vector, websearch_to_tsquery('english', :query)), 0) * {fts_w}"
        )

        # Trigram component
        score_parts.append(
            f"coalesce(similarity(p.name, :query), 0) * {tri_w}"
        )

        # Vector component (only if query is long enough)
        if use_vector:
            query_embedding = await self._embedding_service.generate_embedding(query)
            params["embedding"] = str(query_embedding)
            score_parts.append(
                "CASE WHEN p.embedding IS NOT NULL "
                f"THEN (1 - (p.embedding <=> :embedding::vector)) * {vec_w} "
                "ELSE 0.0 END"
            )

        combined_score = "GREATEST(" + ", ".join(score_parts) + ")"

        # Use OR conditions to match via any strategy
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

        where_clause = "(" + " OR ".join(where_conditions) + ")"

        sql = text(f"""
            WITH ranked AS (
                SELECT
                    p.id,
                    p.impa_code,
                    p.name,
                    p.description,
                    c.name AS category_name,
                    {combined_score} AS score,
                    ts_headline(
                        'english',
                        coalesce(p.name, '') || ' ' || coalesce(p.description, ''),
                        websearch_to_tsquery('english', :query),
                        'StartSel=<b>, StopSel=</b>, MaxFragments=2, MaxWords=30'
                    ) AS highlight,
                    count(*) OVER() AS total_count
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE {where_clause}
                {category_filter}
            )
            SELECT * FROM ranked
            ORDER BY score DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await self._session.execute(sql, params)
        rows = result.mappings().all()

        total = int(rows[0]["total_count"]) if rows else 0
        results = [self._row_to_result(row) for row in rows]
        return results, total

    async def suggest(
        self,
        prefix: str,
        limit: int = 5,
    ) -> list[TextSearchResult]:
        """Autocomplete / prefix suggestions combining FTS prefix and ILIKE."""
        params: dict = {
            "prefix_tsquery": prefix + ":*",
            "prefix_ilike": prefix + "%",
            "prefix": prefix,
            "limit": limit,
        }

        sql = text("""
            SELECT DISTINCT ON (p.id)
                p.id,
                p.impa_code,
                p.name,
                p.description,
                c.name AS category_name,
                GREATEST(
                    coalesce(ts_rank_cd(p.search_vector, to_tsquery('english', :prefix_tsquery)), 0),
                    coalesce(similarity(p.name, :prefix), 0)
                ) AS score,
                NULL AS highlight
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.search_vector @@ to_tsquery('english', :prefix_tsquery)
               OR p.name ILIKE :prefix_ilike
               OR p.impa_code LIKE :prefix_ilike
            ORDER BY p.id, score DESC
        """)

        # Wrap to get top-N ordered by score
        wrapped_sql = text(f"""
            SELECT * FROM (
                SELECT DISTINCT ON (sub.id)
                    sub.id,
                    sub.impa_code,
                    sub.name,
                    sub.description,
                    sub.category_name,
                    sub.score,
                    sub.highlight
                FROM ({sql.text}) sub
            ) deduped
            ORDER BY deduped.score DESC
            LIMIT :limit
        """)

        result = await self._session.execute(wrapped_sql, params)
        rows = result.mappings().all()
        return [self._row_to_result(row) for row in rows]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 20,
        offset: int = 0,
        category_id: uuid.UUID | None = None,
    ) -> tuple[list[TextSearchResult], int]:
        """Dispatch to the requested search mode."""
        if mode == "keyword":
            return await self.keyword_search(query, limit, offset, category_id)
        elif mode == "fuzzy":
            return await self.fuzzy_search(query, limit, offset, category_id)
        else:
            return await self.hybrid_search(query, limit, offset, category_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_result(row) -> TextSearchResult:
        return TextSearchResult(
            id=row["id"],
            impa_code=row["impa_code"],
            name=row["name"],
            description=row["description"],
            category_name=row["category_name"],
            score=round(float(row["score"]), 4),
            highlight=row["highlight"],
        )
