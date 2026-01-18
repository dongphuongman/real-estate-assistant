import logging
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain.memory import ConversationBufferMemory
from langchain_core.language_models import BaseChatModel

from agents.hybrid_agent import create_hybrid_agent
from ai.memory import get_session_history
from api.dependencies import get_llm, get_vector_store
from api.models import ChatRequest, ChatResponse
from vector_store.chroma_store import ChromaPropertyStore

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: ChatRequest,
    llm: Annotated[BaseChatModel, Depends(get_llm)],
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
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
            output_key="output" 
        )
        
        # Create Agent
        agent = create_hybrid_agent(
            llm=llm, 
            retriever=store.get_retriever(), 
            memory=memory
        )

        if request.stream:
            async def event_generator():
                async for chunk in agent.astream_query(request.message):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"
            )

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
            session_id=session_id
        )

    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        ) from e
