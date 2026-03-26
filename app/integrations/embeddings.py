"""Embedding service — wraps sentence-transformers for vector generation."""

import structlog

from app.config import settings

logger = structlog.get_logger()

_embedding_service = None


class EmbeddingService:
    """Generate embeddings using sentence-transformers (self-hosted)."""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("loading_embedding_model", model=self.model_name)
                self._model = SentenceTransformer(self.model_name)
                logger.info("embedding_model_loaded", model=self.model_name)
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        self._load_model()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single search query (with instruction prefix for BGE models)."""
        self._load_model()
        # BGE models perform better with instruction prefix for queries
        instruction = "Represent this sentence for searching relevant passages: "
        embedding = self._model.encode(
            instruction + query,
            normalize_embeddings=True,
        )
        return embedding.tolist()


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name=settings.embedding_model)
    return _embedding_service
