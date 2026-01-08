from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any
from api.dependencies import get_agent
from api.models import ChatRequest, ChatResponse
import logging

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: ChatRequest,
    agent: Any = Depends(get_agent)
):
    """
    Process a chat message using the hybrid agent.
    """
    try:
        # For now, we don't persist sessions in this simple endpoint, 
        # but the agent has memory. To truly support sessions across requests,
        # we'd need to load/save memory based on session_id.
        # This implementation assumes a stateless request or single-turn for now,
        # or relies on the agent being re-instantiated (which wipes memory).
        # TODO: Implement persistent session storage (Redis/DB).
        
        result = agent.process_query(request.message)
        
        # HybridPropertyAgent returns dict with 'answer', 'source_documents', etc.
        answer = result.get("answer", "")
        sources = []
        if "source_documents" in result:
            for doc in result["source_documents"]:
                # Convert Document to dict source
                sources.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
        
        return ChatResponse(
            response=answer,
            sources=sources,
            session_id=request.session_id # Echo back for now
        )

    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )
