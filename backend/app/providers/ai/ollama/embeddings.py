# backend/app/providers/ai/ollama/embeddings.py
"""
Optional fastembed-based similarity fallback for account interpretation.

Builds a cosine-similarity index from the known service domains in
lookup_table._KNOWN_DOMAINS. At query time the sender domain string is
embedded and compared against all indexed service vectors; the best match
is returned when it exceeds the minimum similarity threshold.

This module is entirely optional:
- If fastembed is not installed, every public function silently returns None.
- If OLLAMA_EMBED_ENABLED is False (default), interpretation.py never calls
  into this module so no model is loaded at all.

No network requests are made. The embedding model runs entirely on CPU.
"""

from __future__ import annotations

from backend.app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum cosine similarity (0-1) required to accept a match.
_MIN_SIMILARITY: float = 0.80

# Populated lazily on first call to query_embedding().
_index: _EmbeddingIndex | None = None
_fastembed_unavailable: bool = False


class _EmbeddingIndex:
    """
    Cosine similarity index over the static domain service list.

    Built once per process; thread-safe for reads after construction.
    """

    def __init__(self) -> None:
        try:
            from fastembed import TextEmbedding  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError("fastembed is not installed") from exc

        from backend.app.providers.ai.ollama import lookup_table
        from backend.app.providers.ai.ollama.schemas import OllamaAccountInterpretation

        # Deduplicate: multiple domains may map to the same service slug.
        seen: dict[str, tuple[str, str]] = {}
        for _domain, (slug, display) in lookup_table._KNOWN_DOMAINS.items():
            if slug not in seen:
                seen[slug] = (slug, display)

        self._slugs: list[str] = []
        self._displays: list[str] = []
        self._corpus: list[str] = []

        for slug, display in seen.values():
            self._slugs.append(slug)
            self._displays.append(display)
            # Text fed to the embedder: slug + display name for richer signal.
            self._corpus.append(f"{slug} {display.lower()}")

        model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        import numpy as np  # type: ignore[import-untyped]

        raw = list(model.embed(self._corpus))
        mat = np.array(raw, dtype=np.float32)
        # L2-normalise so dot product == cosine similarity.
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        self._vectors: np.ndarray[object, np.dtype[np.float32]] = mat / norms
        self._model = model
        self._np = np
        self._OllamaAccountInterpretation = OllamaAccountInterpretation

    def query(self, sender_domain: str) -> OllamaAccountInterpretation | None:  # type: ignore[name-defined]
        import numpy as np  # type: ignore[import-untyped]

        query_text = sender_domain.strip().lower()
        if not query_text:
            return None

        raw_q = list(self._model.embed([query_text]))
        q_vec = np.array(raw_q[0], dtype=np.float32)
        norm = np.linalg.norm(q_vec)
        if norm == 0:
            return None
        q_vec = q_vec / norm

        scores = self._vectors @ q_vec
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])

        if best_score < _MIN_SIMILARITY:
            return None

        result: OllamaAccountInterpretation = {  # type: ignore[assignment]
            "service_name": self._slugs[best_idx],
            "display_name": self._displays[best_idx],
            "confidence": min(100, int(best_score * 100)),
            "reason": f"embedding-similarity:{best_score:.3f}",
        }
        return result


def _get_index() -> _EmbeddingIndex | None:
    global _index, _fastembed_unavailable  # noqa: PLW0603
    if _fastembed_unavailable:
        return None
    if _index is not None:
        return _index
    try:
        _index = _EmbeddingIndex()
        logger.info("ollama.embeddings.index_built", services=len(_index._slugs))
    except ImportError:
        _fastembed_unavailable = True
        logger.debug("ollama.embeddings.fastembed_unavailable")
        return None
    except Exception as exc:  # noqa: BLE001
        _fastembed_unavailable = True
        logger.warning("ollama.embeddings.build_failed", error=str(exc))
        return None
    return _index


def query_embedding(sender_domain: str) -> OllamaAccountInterpretation | None:
    """
    Return a high-confidence interpretation for sender_domain using
    cosine similarity against the known-service embedding index.

    Returns None when:
    - fastembed is not installed
    - similarity is below _MIN_SIMILARITY
    - any internal error occurs (fail-open)
    """
    try:
        idx = _get_index()
        if idx is None:
            return None
        return idx.query(sender_domain)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ollama.embeddings.query_failed", error=str(exc))
        return None


__all__ = ["query_embedding"]
