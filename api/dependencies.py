from functools import lru_cache
from typing import Optional
from vector_store.chroma_store import ChromaPropertyStore
from config.settings import settings

@lru_cache()
def get_vector_store() -> Optional[ChromaPropertyStore]:
    """
    Get cached vector store instance for API.
    Returns None if embeddings are not available.
    """
    try:
        store = ChromaPropertyStore(
            persist_directory=str(settings.chroma_dir),
            collection_name="properties",
            embedding_model=settings.embedding_model
        )
        return store
    except Exception:
        return None
