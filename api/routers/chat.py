import json
import logging
import inspect
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain.memory import ConversationBufferMemory
from langchain_core.language_models import BaseChatModel

from agents.hybrid_agent import create_hybrid_agent
from ai.memory import get_session_history
from api.chat_sources import serialize_chat_sources
from api.dependencies import get_llm, get_vector_store
from api.models import ChatRequest, ChatResponse
from config.settings import get_settings

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: ChatRequest,
    llm: Annotated[BaseChatModel, Depends(get_llm)],
    store: Annotated[Optional["ChromaPropertyStore"], Depends(get_vector_store)],
):
    """
    Process a chat message using the hybrid agent with session persistence.
    """
    try:
        if not store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector store unavailable"
            )

        settings = get_settings()
        sources_max_items = max(0, int(settings.chat_sources_max_items))
        sources_max_content_chars = max(0, int(settings.chat_source_content_max_chars))
        sources_max_total_bytes = max(0, int(settings.chat_sources_max_total_bytes))

        # Handle Session ID
        session_id = request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Initialize Memory with Persistence
        chat_history = get_session_history(session_id)
        memory = ConversationBufferMemory(
            chat_memory=chat_history,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Create Agent
        agent_kwargs = {
            "llm": llm,
            "retriever": store.get_retriever(),
            "memory": memory,
            "internet_enabled": bool(getattr(settings, "internet_enabled", False)),
            "searxng_url": getattr(settings, "searxng_url", None),
            "web_search_max_results": int(getattr(settings, "web_search_max_results", 5)),
            "web_fetch_timeout_seconds": float(getattr(settings, "web_fetch_timeout_seconds", 10)),
            "web_fetch_max_bytes": int(getattr(settings, "web_fetch_max_bytes", 300_000)),
            "web_allowlist_domains": list(getattr(settings, "web_allowlist_domains", []) or []),
        }
        sig = inspect.signature(create_hybrid_agent)
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            filtered_kwargs = agent_kwargs
        else:
            filtered_kwargs = {k: v for k, v in agent_kwargs.items() if k in sig.parameters}
        agent = create_hybrid_agent(**filtered_kwargs)

        if request.stream:
            async def event_generator():
                async for chunk in agent.astream_query(request.message):
                    yield f"data: {chunk}\n\n"
                sources_payload = {"sources": [], "sources_truncated": False, "session_id": session_id}
                if hasattr(agent, "get_sources_for_query"):
                    try:
                        docs = agent.get_sources_for_query(request.message)
                        sources, sources_truncated = serialize_chat_sources(
                            docs,
                            max_items=sources_max_items,
                            max_content_chars=sources_max_content_chars,
                            max_total_bytes=sources_max_total_bytes,
                        )
                        sources_payload["sources"] = sources
                        sources_payload["sources_truncated"] = sources_truncated
                    except Exception:
                        sources_payload["sources"] = []
                        sources_payload["sources_truncated"] = False
                yield "event: meta\n"
                yield f"data: {json.dumps(sources_payload)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"
            )

        result = agent.process_query(request.message)
        
        answer = result.get("answer", "")
        if "sources" in result and isinstance(result.get("sources"), list):
            sources = result.get("sources") or []
            sources_truncated = False
        else:
            sources, sources_truncated = serialize_chat_sources(
                result.get("source_documents") or [],
                max_items=sources_max_items,
                max_content_chars=sources_max_content_chars,
                max_total_bytes=sources_max_total_bytes,
            )
        
        return ChatResponse(
            response=answer,
            sources=sources,
            sources_truncated=sources_truncated,
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        ) from e
