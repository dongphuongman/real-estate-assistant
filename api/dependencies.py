import logging
from functools import lru_cache
from typing import Annotated, Any, Optional

from fastapi import Depends, Header
from langchain_core.language_models import BaseChatModel

import models.user_model_preferences as user_model_preferences
from agents.hybrid_agent import create_hybrid_agent
from agents.services.crm_connector import CRMConnector, WebhookCRMConnector
from agents.services.data_enrichment import BasicDataEnrichmentService, DataEnrichmentService
from agents.services.legal_check import BasicLegalCheckService, LegalCheckService
from agents.services.valuation import SimpleValuationProvider, ValuationProvider
from config.settings import settings
from models.provider_factory import ModelProviderFactory
from vector_store.chroma_store import ChromaPropertyStore
from vector_store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


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

def _create_llm(provider_name: str, model_id: Optional[str]) -> BaseChatModel:
    factory_provider = ModelProviderFactory.get_provider(provider_name)
    resolved_model_id = model_id

    if not resolved_model_id:
        models = factory_provider.list_models()
        if not models:
            raise RuntimeError(f"No models available for provider '{provider_name}'")
        resolved_model_id = models[0].id

    return factory_provider.create_model(
        model_id=resolved_model_id,
        provider_name=provider_name,
        temperature=settings.default_temperature,
        max_tokens=settings.default_max_tokens,
    )


def get_llm(
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> BaseChatModel:
    """
    Get Language Model instance.
    Uses settings to determine provider and model.
    """
    default_provider_name = settings.default_provider
    default_model_id = settings.default_model

    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    if x_user_email and x_user_email.strip():
        try:
            prefs = user_model_preferences.MODEL_PREFS_MANAGER.get_preferences(x_user_email.strip())
            preferred_provider = prefs.preferred_provider
            preferred_model = prefs.preferred_model
        except Exception as e:
            logger.warning("Failed to load model preferences: %s", e)

    primary_provider = preferred_provider or default_provider_name
    primary_model = preferred_model if preferred_provider else (preferred_model or default_model_id)

    try:
        return _create_llm(primary_provider, primary_model)
    except Exception as e:
        if preferred_provider or preferred_model:
            try:
                return _create_llm(default_provider_name, default_model_id)
            except Exception:
                pass
        raise RuntimeError(f"Could not initialize LLM with provider '{primary_provider}': {e}") from e

def get_valuation_provider() -> Optional[ValuationProvider]:
    if settings.valuation_mode != "simple":
        return None
    return SimpleValuationProvider()

def get_crm_connector() -> Optional[CRMConnector]:
    url = settings.crm_webhook_url
    if not url:
        return None
    return WebhookCRMConnector(url)

@lru_cache()
def get_knowledge_store() -> Optional[KnowledgeStore]:
    """
    Get cached knowledge store instance for RAG uploads (CE-safe).
    Returns None if embeddings are not available.
    """
    try:
        store = KnowledgeStore(
            persist_directory=str(settings.chroma_dir),
            collection_name="knowledge",
        )
        return store
    except Exception:
        return None

def get_data_enrichment_service() -> Optional[DataEnrichmentService]:
    if not settings.data_enrichment_enabled:
        return None
    return BasicDataEnrichmentService()

def get_legal_check_service() -> Optional[LegalCheckService]:
    if settings.legal_check_mode != "basic":
        return None
    return BasicLegalCheckService()

def get_agent(
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
    llm: Annotated[BaseChatModel, Depends(get_llm)]
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
