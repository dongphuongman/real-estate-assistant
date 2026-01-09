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
    Uses settings to determine provider and model.
    """
    provider_name = settings.default_provider
    model_id = settings.default_model
    
    try:
        factory_provider = ModelProviderFactory.get_provider(provider_name)
        
        # If no specific model configured, pick the first available one from the provider
        if not model_id:
            models = factory_provider.list_models()
            if not models:
                raise RuntimeError(f"No models available for provider '{provider_name}'")
            # Prefer a model marked as recommended if available, otherwise first
            # We don't have a structured "is_default" flag, but recommended_for list exists.
            # For now, just pick the first one as they are usually ordered by relevance/recency in implementation
            model_id = models[0].id
            
        return factory_provider.create_model(
            model_id=model_id,
            provider_name=provider_name,
            temperature=settings.default_temperature,
            max_tokens=settings.default_max_tokens
        )
    except Exception as e:
        # Fallback for tests or when no keys configured
        raise RuntimeError(f"Could not initialize LLM with provider '{provider_name}': {e}")

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
