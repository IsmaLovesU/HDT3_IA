"""Generación de embeddings locales con sentence-transformers."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODELO_EMBEDDINGS = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSION = 384


@lru_cache(maxsize=1)
def _modelo() -> SentenceTransformer:
    # La primera llamada descarga el modelo (~90 MB); después queda en caché local.
    return SentenceTransformer(MODELO_EMBEDDINGS)


def vectorizar(textos: list[str]) -> list[list[float]]:
    """Convierte textos en vectores normalizados (similitud coseno = producto punto)."""
    vectores = _modelo().encode(textos, normalize_embeddings=True)
    return [vector.tolist() for vector in vectores]
