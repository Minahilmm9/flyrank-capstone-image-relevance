"""
Embedding generation + cosine similarity. Both image captions and post text
are embedded into the same space with task_type="SEMANTIC_SIMILARITY" so
they're directly comparable — this is what lets "red rose" and
"a rose in bloom" rank as related despite differing wording.

Uses the newer `google-genai` SDK — see app/vision.py for why.
"""
import logging

from google import genai
from google.genai import types
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def embed_text(text: str) -> list[float] | None:
    try:
        client = _get_client()
        result = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
        )
        return list(result.embeddings[0].values)
    except Exception as exc:
        logger.warning("Embedding call failed: %s", exc)
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)