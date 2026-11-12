"""Text embeddings with gemini-embedding-001.

768 dimensions instead of the default 3,072: pgvector's HNSW index caps at
2,000 dimensions, and 768 is plenty for a few thousand textbook chunks.
Documents and queries use different task types, which the model is trained
for (asymmetric retrieval).
"""

from __future__ import annotations

import math

from google import genai
from google.genai import types

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
# USD per 1M input tokens (online, non-batch). Re-check the pricing page.
EMBED_PRICE_PER_M = 0.15
MAX_BATCH = 100


def _normalize(v: list[float]) -> list[float]:
    # Truncated (non-3072) outputs are not unit length.
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed_documents(client: genai.Client, texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), MAX_BATCH):
        resp = client.models.embed_content(
            model=EMBED_MODEL,
            contents=texts[i:i + MAX_BATCH],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT", output_dimensionality=EMBED_DIM
            ),
        )
        out.extend(_normalize(e.values) for e in resp.embeddings)
    return out


async def embed_query(client: genai.Client, text: str) -> list[float]:
    resp = await client.aio.models.embed_content(
        model=EMBED_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY", output_dimensionality=EMBED_DIM
        ),
    )
    return _normalize(resp.embeddings[0].values)
