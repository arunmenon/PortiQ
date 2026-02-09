"""ImpaMatcher — 3-stage IMPA code matching pipeline (regex, semantic, LLM)."""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.product import Product
from src.modules.document_ai.normalizer import Normalizer
from src.modules.document_ai.schemas import MatchAlternative, MatchResult

logger = logging.getLogger(__name__)

# Pattern for 6-digit IMPA codes
_IMPA_PATTERN = re.compile(r"\b(\d{6})\b")


class ImpaMatcher:
    """Three-stage IMPA matching pipeline.

    Stage 1: Regex IMPA detection (fast, high-confidence)
    Stage 2: Semantic search via pgvector embeddings
    Stage 3: LLM disambiguation for ambiguous cases
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._normalizer = Normalizer()

    async def match_item(
        self,
        raw_text: str,
        detected_impa_code: str | None = None,
    ) -> MatchResult:
        """Run the 3-stage matching pipeline for a single item.

        Stage 1: Regex IMPA Detection
        Stage 2: Semantic Search (pgvector) — requires OpenAI key
        Stage 3: LLM Disambiguation — requires OpenAI key
        """
        # Stage 1: Regex-based matching
        stage1_result = await self._match_by_regex(raw_text, detected_impa_code)
        if stage1_result is not None and stage1_result.confidence >= 0.95:
            return stage1_result

        # For MVP: if OpenAI key is not configured, skip stages 2 & 3
        if not settings.openai_api_key:
            if stage1_result is not None:
                return stage1_result
            return MatchResult(confidence=0.0, method="none")

        # Stage 2: Semantic search via pgvector
        stage2_result = await self._match_by_semantic(raw_text)
        if stage2_result is not None and stage2_result.confidence >= 0.85:
            return stage2_result

        # Stage 3: LLM disambiguation
        candidates = []
        if stage2_result is not None:
            candidates = stage2_result.alternatives
        stage3_result = await self._match_by_llm(raw_text, candidates)
        if stage3_result is not None:
            return stage3_result

        # Fallback: best available result
        if stage2_result is not None:
            return stage2_result
        if stage1_result is not None:
            return stage1_result
        return MatchResult(confidence=0.0, method="none")

    async def match_batch(
        self,
        items: list[dict],
    ) -> list[MatchResult]:
        """Match a batch of items.

        Each item dict should have 'raw_text' and optionally 'detected_impa_code'.
        Stage 1 runs on all items, then stages 2-3 for unmatched.
        """
        results: list[MatchResult] = []
        for item in items:
            result = await self.match_item(
                raw_text=item["raw_text"],
                detected_impa_code=item.get("detected_impa_code"),
            )
            results.append(result)
        return results

    # ── Stage 1: Regex matching ───────────────────────────────────────────

    async def _match_by_regex(
        self,
        raw_text: str,
        detected_impa_code: str | None = None,
    ) -> MatchResult | None:
        """Look for IMPA codes in text and validate against the products table."""
        candidates: list[str] = []

        # Priority 1: explicitly detected IMPA code
        if detected_impa_code:
            candidates.append(detected_impa_code)

        # Priority 2: scan raw text for 6-digit patterns
        text_matches = _IMPA_PATTERN.findall(raw_text)
        for match in text_matches:
            code_int = int(match)
            if 100000 <= code_int <= 999999 and match not in candidates:
                candidates.append(match)

        if not candidates:
            return None

        # Validate candidates against products table
        for candidate in candidates:
            result = await self.db.execute(
                select(Product).where(Product.impa_code == candidate)
            )
            product = result.scalar_one_or_none()
            if product is not None:
                return MatchResult(
                    impa_code=product.impa_code,
                    product_id=product.id,
                    product_name=product.name,
                    confidence=0.98 if candidate == detected_impa_code else 0.95,
                    method="regex",
                )

        # Code found in text but not in product catalog
        return MatchResult(
            impa_code=candidates[0],
            product_id=None,
            product_name=None,
            confidence=0.5,
            method="regex",
        )

    # ── Stage 2: Semantic search (pgvector) ──────────────────────────────

    async def _match_by_semantic(
        self,
        raw_text: str,
    ) -> MatchResult | None:
        """Embed the description and search for similar products via pgvector."""
        try:
            from src.modules.search.embedding import EmbeddingService

            embedding_service = EmbeddingService()
            normalized_text = self._normalizer.normalize_description(raw_text)
            query_embedding = await embedding_service.generate_embedding(normalized_text)
        except Exception:
            logger.warning("Failed to generate embedding for semantic matching", exc_info=True)
            return None

        # Query pgvector for similar products
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        query = text("""
            SELECT id, impa_code, name,
                   1 - (embedding <=> :query_embedding::vector) as similarity
            FROM products
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> :query_embedding::vector) > 0.6
            ORDER BY embedding <=> :query_embedding::vector
            LIMIT 5
        """)

        result = await self.db.execute(
            query, {"query_embedding": embedding_str}
        )
        rows = result.fetchall()

        if not rows:
            return None

        top_match = rows[0]
        alternatives = [
            MatchAlternative(
                impa_code=row.impa_code,
                product_name=row.name,
                confidence=float(row.similarity),
            )
            for row in rows[1:4]  # Up to 3 alternatives
        ]

        top_confidence = float(top_match.similarity)

        # Check if top matches are ambiguous (within 0.05 of each other)
        is_ambiguous = (
            len(rows) >= 2
            and abs(float(rows[0].similarity) - float(rows[1].similarity)) < 0.05
        )

        if top_confidence >= 0.85 and not is_ambiguous:
            return MatchResult(
                impa_code=top_match.impa_code,
                product_id=uuid.UUID(str(top_match.id)),
                product_name=top_match.name,
                confidence=top_confidence,
                method="semantic",
                alternatives=alternatives,
            )

        # Return with lower confidence — will trigger stage 3
        return MatchResult(
            impa_code=top_match.impa_code,
            product_id=uuid.UUID(str(top_match.id)),
            product_name=top_match.name,
            confidence=top_confidence,
            method="semantic",
            alternatives=alternatives,
        )

    # ── Stage 3: LLM disambiguation ─────────────────────────────────────

    async def _match_by_llm(
        self,
        raw_text: str,
        candidates: list[MatchAlternative],
    ) -> MatchResult | None:
        """Use OpenAI to disambiguate between similar product candidates."""
        if not candidates:
            return None

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

            candidate_descriptions = "\n".join(
                f"- IMPA {c.impa_code}: {c.product_name} (similarity: {c.confidence:.2f})"
                for c in candidates
            )

            prompt = (
                "You are an expert in maritime ship chandlery products. "
                "Given the following line item description from a procurement document, "
                "determine which IMPA product code is the best match.\n\n"
                f"Line item: {raw_text}\n\n"
                f"Candidate products:\n{candidate_descriptions}\n\n"
                "Respond with ONLY a JSON object: "
                '{"impa_code": "XXXXXX", "confidence": 0.XX, "reasoning": "..."}'
            )

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )

            import json

            content = response.choices[0].message.content or ""
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                selected_impa = parsed.get("impa_code")
                llm_confidence = max(0.0, min(0.90, float(parsed.get("confidence", 0.7))))

                # Find the matching candidate
                for candidate in candidates:
                    if candidate.impa_code == selected_impa:
                        # Look up product
                        result = await self.db.execute(
                            select(Product).where(
                                Product.impa_code == selected_impa
                            )
                        )
                        product = result.scalar_one_or_none()

                        return MatchResult(
                            impa_code=selected_impa,
                            product_id=product.id if product else None,
                            product_name=product.name if product else candidate.product_name,
                            confidence=llm_confidence,
                            method="llm",
                            alternatives=[
                                c for c in candidates if c.impa_code != selected_impa
                            ][:3],
                        )

        except Exception:
            logger.warning("LLM disambiguation failed", exc_info=True)

        return None
