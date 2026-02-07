"""EmbeddingService — generates vector embeddings via OpenAI."""

import json

import openai

from src.config import settings
from src.modules.search.constants import EMBEDDING_BATCH_SIZE, EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


class EmbeddingService:
    """Wraps the OpenAI embeddings API for product text vectorisation."""

    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a single embedding vector for *text*."""
        response = await self._client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts, batching in groups of EMBEDDING_BATCH_SIZE."""
        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + EMBEDDING_BATCH_SIZE]
            response = await self._client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            # Ensure results are in the same order as the input batch
            sorted_data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend(d.embedding for d in sorted_data)
        return all_embeddings

    @staticmethod
    def build_product_text(product) -> str:
        """Build a searchable text representation of a product.

        Combines the product's name, description, IMPA code, category name,
        and specification values into a single string suitable for embedding.
        """
        parts: list[str] = [product.name]
        if product.description:
            parts.append(product.description)
        parts.append(f"IMPA {product.impa_code}")
        if hasattr(product, "category") and product.category is not None:
            parts.append(product.category.name)
        if product.specifications:
            specs = product.specifications
            if isinstance(specs, str):
                specs = json.loads(specs)
            if isinstance(specs, dict):
                parts.extend(f"{k}: {v}" for k, v in specs.items())
        return " | ".join(parts)
