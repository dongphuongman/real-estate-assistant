from functools import lru_cache
from typing import Optional, Any
from fastapi import Depends
from langchain_core.language_models import BaseChatModel
from vector_store.chroma_store import ChromaPropertyStore
from config.settings import settings
from models.provider_factory import ModelProviderFactory
from agents.hybrid_agent import create_hybrid_agent

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

def get_llm() -> BaseChatModel:
    """
    Get Language Model instance.
    Defaults to OpenAI if available, otherwise tries others or raises error.
    """
    # Simple logic: prefer OpenAI, then Anthropic, then fallback
    provider = "openai"
    if not settings.openai_api_key:
        if settings.anthropic_api_key:
            provider = "anthropic"
        # Add more fallbacks if needed
    
    try:
        factory_provider = ModelProviderFactory.get_provider(provider)
        # Get default model for provider
        models = factory_provider.list_models()
        model_id = models[0].id if models else None
        return factory_provider.create_model(model_id=model_id)
    except Exception as e:
        # Fallback for tests or when no keys configured (might mock in tests)
        # raising error so endpoint knows service is unavailable
        raise RuntimeError(f"Could not initialize LLM: {e}")

def get_agent(
    store: Optional[ChromaPropertyStore] = Depends(get_vector_store),
    llm: BaseChatModel = Depends(get_llm)
) -> Any:
    """
    Get initialized Hybrid Agent.
    """
    if not store:
        # If store is missing, we might want a simple agent or raise error
        # For now, let's assume we need the store for the full hybrid agent
        # But we can try to create it with a dummy retriever or fail
        # HybridPropertyAgent needs a retriever.
        raise RuntimeError("Vector Store unavailable, cannot create Hybrid Agent")
    
    retriever = store.get_retriever()
    return create_hybrid_agent(llm=llm, retriever=retriever)
