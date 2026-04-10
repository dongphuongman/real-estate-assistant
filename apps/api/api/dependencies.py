from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, Any, Optional

from fastapi import Body, Depends, Header, HTTPException, Query, status
from langchain_core.language_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models.user_model_preferences as user_model_preferences
from agents.hybrid_agent import HybridPropertyAgent, SimpleRAGAgent, create_hybrid_agent
from agents.services.crm_connector import CRMConnector, WebhookCRMConnector
from agents.services.data_enrichment import BasicDataEnrichmentService, DataEnrichmentService
from agents.services.legal_check import BasicLegalCheckService, LegalCheckService
from agents.services.valuation import SimpleValuationProvider, ValuationProvider
from api.models import RagQaRequest
from config.settings import settings
from db.models import User
from models.provider_factory import ModelProviderFactory
from services.model_preference_service import SYSTEM_DEFAULTS, ModelPreferenceService

if TYPE_CHECKING:
    from data.enrichment.pipeline import EnrichmentPipeline
    from services.esignature_service import ESignatureService
    from services.template_service import TemplateService
    from vector_store.chroma_store import ChromaPropertyStore
    from vector_store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)

try:
    from vector_store.chroma_store import ChromaPropertyStore  # type: ignore
except Exception as e:
    logger.warning("ChromaPropertyStore not available, vector search disabled: %s", e)
    ChromaPropertyStore = None  # type: ignore

try:
    from vector_store.knowledge_store import KnowledgeStore  # type: ignore
except Exception as e:
    logger.warning("KnowledgeStore not available, knowledge RAG disabled: %s", e)
    KnowledgeStore = None  # type: ignore


@lru_cache()
def get_vector_store() -> Optional[ChromaPropertyStore]:
    """
    Get cached vector store instance for API.
    Returns None if embeddings are not available.
    """
    if ChromaPropertyStore is None:
        return None
    try:
        store = ChromaPropertyStore(
            persist_directory=str(settings.chroma_dir),
            collection_name="properties",
            embedding_model=settings.embedding_model,
        )
        return store
    except Exception as e:
        logger.warning("Vector store initialization failed: %s", e)
        return None


def _create_llm(provider_name: str, model_id: Optional[str]) -> BaseChatModel:
    llm, _resolved_model_id = _create_llm_with_resolved_model_id(
        provider_name=provider_name, model_id=model_id
    )
    return llm


@lru_cache(maxsize=16)
def _create_llm_with_resolved_model_id(
    provider_name: str, model_id: Optional[str]
) -> tuple[BaseChatModel, str]:
    factory_provider = ModelProviderFactory.get_provider(provider_name)
    resolved_model_id = model_id

    if not resolved_model_id:
        if provider_name == "ollama" and getattr(settings, "ollama_default_model", None):
            resolved_model_id = settings.ollama_default_model
        else:
            models = factory_provider.list_models()
            if not models:
                raise RuntimeError(f"No models available for provider '{provider_name}'")
            resolved_model_id = models[0].id

    # Add Sentry breadcrumb for LLM creation (Task #56)
    try:
        from api.sentry_init import add_llm_breadcrumb

        add_llm_breadcrumb(provider=provider_name, model=resolved_model_id)
    except Exception as e:
        logger.debug("Sentry breadcrumb skipped: %s", e)

    llm = factory_provider.create_model(
        model_id=resolved_model_id,
        temperature=settings.default_temperature,
        max_tokens=settings.default_max_tokens,
    )
    return llm, resolved_model_id


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
            except Exception as fallback_err:
                logger.warning("Default provider fallback also failed: %s", fallback_err)
        if primary_provider != "ollama":
            try:
                ollama_provider = ModelProviderFactory.get_provider("ollama")
                runtime_ok, _runtime_error = ollama_provider.validate_connection()
                if runtime_ok:
                    return _create_llm("ollama", settings.ollama_default_model)
            except Exception as ollama_err:
                logger.warning("Ollama fallback failed: %s", ollama_err)
        raise RuntimeError(
            f"Could not initialize LLM with provider '{primary_provider}': {e}"
        ) from e


def get_optional_llm(
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> Optional[BaseChatModel]:
    try:
        return get_llm(x_user_email=x_user_email)
    except Exception as e:
        logger.warning("LLM unavailable: %s", e)
        return None


# =============================================================================
# Task-Specific Model Preferences (Task #87)
# =============================================================================


async def get_llm_for_task(
    task_type: str,
    x_user_email: str | None = None,
    session: AsyncSession | None = None,
) -> BaseChatModel:
    """
    Get Language Model instance configured for a specific task type.

    Priority order:
    1. User's task-specific preference (from DB via ModelPreferenceService)
    2. User's global preference (from legacy UserModelPreferencesManager)
    3. System default for task type
    4. Settings default
    5. Fallback to Ollama

    Args:
        task_type: Task type (chat, search, tools, analysis, embedding)
        x_user_email: User email for preference lookup
        session: Database session for preference queries

    Returns:
        Configured LLM instance
    """
    primary_provider: Optional[str] = None
    primary_model: Optional[str] = None

    # 1. Try task-specific preference from database
    if x_user_email and x_user_email.strip() and session:
        try:
            user_query = select(User.id).where(User.email == x_user_email.strip())
            user_result = await session.execute(user_query)
            user_id = user_result.scalar_one_or_none()

            if user_id:
                service = ModelPreferenceService(session)
                preference = await service.get_preference_by_task(user_id, task_type)
                if preference and preference.is_active:
                    primary_provider = preference.provider
                    primary_model = preference.model_name
                    logger.debug(
                        "Using task-specific preference for %s: %s/%s",
                        task_type,
                        primary_provider,
                        primary_model,
                    )
        except Exception as e:
            logger.warning("Failed to load task-specific model preferences: %s", e)

    # 2. Fall back to legacy global preferences
    if not primary_provider and x_user_email and x_user_email.strip():
        try:
            prefs = user_model_preferences.MODEL_PREFS_MANAGER.get_preferences(x_user_email.strip())
            if prefs.preferred_provider:
                primary_provider = prefs.preferred_provider
                primary_model = prefs.preferred_model
                logger.debug(
                    "Using global preference for %s: %s/%s",
                    task_type,
                    primary_provider,
                    primary_model,
                )
        except Exception as e:
            logger.warning("Failed to load legacy model preferences: %s", e)

    # 3. Fall back to system default for task type
    if not primary_provider:
        task_default = SYSTEM_DEFAULTS.get(task_type)
        if task_default:
            primary_provider = task_default["provider"]
            primary_model = task_default["model_name"]
            logger.debug(
                "Using system default for %s: %s/%s",
                task_type,
                primary_provider,
                primary_model,
            )

    # 4. Final fallback to settings default
    if not primary_provider:
        primary_provider = settings.default_provider
        primary_model = settings.default_model

    try:
        return _create_llm(primary_provider, primary_model)
    except Exception as e:
        # Try settings default if we had a preference
        if primary_provider != settings.default_provider:
            try:
                return _create_llm(settings.default_provider, settings.default_model)
            except Exception as fallback_err:
                logger.warning(
                    "Default provider fallback for task %s failed: %s", task_type, fallback_err
                )

        # 5. Fallback to Ollama if configured
        if primary_provider != "ollama":
            try:
                ollama_provider = ModelProviderFactory.get_provider("ollama")
                runtime_ok, _runtime_error = ollama_provider.validate_connection()
                if runtime_ok:
                    logger.info("Falling back to Ollama for task %s", task_type)
                    return _create_llm("ollama", settings.ollama_default_model)
            except Exception as ollama_err:
                logger.warning("Ollama fallback for task %s failed: %s", task_type, ollama_err)

        raise RuntimeError(
            f"Could not initialize LLM for task '{task_type}' with provider '{primary_provider}': {e}"
        ) from e


async def get_optional_llm_for_task(
    task_type: str,
    x_user_email: str | None = None,
    session: AsyncSession | None = None,
) -> Optional[BaseChatModel]:
    """Get LLM for task, returning None if unavailable."""
    try:
        return await get_llm_for_task(task_type, x_user_email, session)
    except Exception as e:
        logger.warning("LLM unavailable for task %s: %s", task_type, e)
        return None


def get_optional_llm_with_details(
    *,
    x_user_email: str | None,
    provider_override: str | None,
    model_override: str | None,
) -> tuple[Optional[BaseChatModel], Optional[str], Optional[str]]:
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

    has_overrides = bool(
        (provider_override and provider_override.strip())
        or (model_override and model_override.strip())
    )

    if provider_override and provider_override.strip():
        primary_provider = provider_override.strip()
        primary_model = (
            model_override.strip() if model_override and model_override.strip() else None
        )
    elif model_override and model_override.strip():
        primary_provider = preferred_provider or default_provider_name
        primary_model = model_override.strip()
    else:
        primary_provider = preferred_provider or default_provider_name
        primary_model = (
            preferred_model if preferred_provider else (preferred_model or default_model_id)
        )

    try:
        llm, resolved_model_id = _create_llm_with_resolved_model_id(primary_provider, primary_model)
        return llm, primary_provider, resolved_model_id
    except Exception as e:
        if has_overrides:
            logger.warning(
                "LLM unavailable for explicit selection (provider=%s, model=%s): %s",
                primary_provider,
                primary_model,
                e,
            )
            return None, primary_provider, primary_model

        if preferred_provider or preferred_model:
            try:
                llm, resolved_model_id = _create_llm_with_resolved_model_id(
                    default_provider_name,
                    default_model_id,
                )
                return llm, default_provider_name, resolved_model_id
            except Exception as fallback_err:
                logger.warning("Default provider fallback failed: %s", fallback_err)
        if primary_provider != "ollama":
            try:
                ollama_provider = ModelProviderFactory.get_provider("ollama")
                runtime_ok, _runtime_error = ollama_provider.validate_connection()
                if runtime_ok:
                    llm, resolved_model_id = _create_llm_with_resolved_model_id(
                        "ollama",
                        settings.ollama_default_model,
                    )
                    return llm, "ollama", resolved_model_id
            except Exception as ollama_err:
                logger.warning("Ollama fallback failed: %s", ollama_err)

        logger.warning("LLM unavailable: %s", e)
        return None, primary_provider, primary_model


def parse_rag_qa_request(
    payload: Annotated[Optional[RagQaRequest], Body()] = None,
    question: Annotated[Optional[str], Query()] = None,
    top_k: Annotated[int, Query(ge=1, le=50)] = 5,
    provider: Annotated[Optional[str], Query()] = None,
    model: Annotated[Optional[str], Query()] = None,
) -> RagQaRequest:
    if payload is not None:
        return payload

    if question is None or not question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Question must not be empty"
        )

    return RagQaRequest(
        question=question,
        top_k=top_k,
        provider=provider,
        model=model,
    )


def get_rag_qa_llm_details(
    rag_request: Annotated[RagQaRequest, Depends(parse_rag_qa_request)],
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> tuple[Optional[BaseChatModel], Optional[str], Optional[str]]:
    return get_optional_llm_with_details(
        x_user_email=x_user_email,
        provider_override=rag_request.provider,
        model_override=rag_request.model,
    )


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
    if KnowledgeStore is None:
        return None
    try:
        store = KnowledgeStore(
            persist_directory=str(settings.chroma_dir),
            collection_name="knowledge",
        )
        return store
    except Exception as e:
        logger.warning("Knowledge store initialization failed: %s", e)
        return None


def get_data_enrichment_service() -> Optional[DataEnrichmentService]:
    if not settings.data_enrichment_enabled:
        return None
    return BasicDataEnrichmentService()


# =============================================================================
# Property Enrichment Dependencies (Task #78)
# =============================================================================

_enrichment_pipeline: Optional[EnrichmentPipeline] = None


def get_enrichment_pipeline() -> Optional[EnrichmentPipeline]:
    """
    Get enrichment pipeline instance.

    Returns None if enrichment is disabled.
    """
    from data.enrichment.pipeline import PipelineConfig
    from data.enrichment.pipeline import get_enrichment_pipeline as _get_impl

    if not settings.enrichment_enabled:
        return None

    config = PipelineConfig(
        enabled=settings.enrichment_enabled,
        parallel_execution=settings.enrichment_parallel_execution,
        max_concurrent=settings.enrichment_max_concurrent,
        default_timeout=settings.enrichment_timeout_seconds,
        cache_enabled=settings.enrichment_cache_enabled,
        fallback_on_error=settings.enrichment_fallback_on_error,
        sources=settings.enrichment_sources if settings.enrichment_sources else None,
    )
    return _get_impl(config)


def get_enrichment_status(property_id: str) -> dict[str, Any]:
    """
    Get enrichment status for a property.

    Args:
        property_id: Property identifier

    Returns:
        Status dictionary
    """
    from data.enrichment.status import get_status_tracker

    return get_status_tracker().get_status(property_id)


def get_legal_check_service() -> Optional[LegalCheckService]:
    if settings.legal_check_mode != "basic":
        return None
    return BasicLegalCheckService()


# =============================================================================
# E-Signature Dependencies
# =============================================================================

_esignature_service: Optional[ESignatureService] = None
_template_service: Optional[TemplateService] = None


def get_esignature_service() -> Optional[ESignatureService]:
    """
    Get e-signature service instance.

    Returns None if not configured.
    """
    from services.esignature_service import get_esignature_service as _get_esignature_service_impl

    return _get_esignature_service_impl()


def get_template_service() -> Optional[TemplateService]:
    """
    Get template service instance.

    Returns None if not configured.
    """
    from services.template_service import get_template_service as _get_template_service_impl

    return _get_template_service_impl()


def get_agent(
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
    llm: Annotated[BaseChatModel, Depends(get_llm)],
) -> HybridPropertyAgent | SimpleRAGAgent:
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
