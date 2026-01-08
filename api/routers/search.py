from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from api.dependencies import get_vector_store
from api.models import SearchRequest, SearchResponse, SearchResultItem
from vector_store.chroma_store import ChromaPropertyStore
from data.schemas import Property
import logging

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_properties(
    request: SearchRequest,
    store: Optional[ChromaPropertyStore] = Depends(get_vector_store)
):
    """
    Search for properties using semantic search and metadata filters.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not available"
        )

    try:
        # Perform search
        results = store.search(
            query=request.query,
            k=request.limit,
            filter=request.filters
        )
        
        items = []
        for doc, score in results:
            try:
                # Document metadata contains property fields
                # We need to handle potential data inconsistencies
                metadata = doc.metadata.copy()
                
                # Ensure 'id' is present (sometimes stored as doc-id in Chroma)
                if "id" not in metadata:
                    metadata["id"] = "unknown"
                
                # 'rooms' might be stored as float in Chroma metadata (no int type support sometimes)
                # Pydantic handles this conversion usually
                
                # Construct Property model
                # validation_error might occur if metadata is incomplete
                prop = Property.model_validate(metadata)
                
                items.append(SearchResultItem(property=prop, score=score))
            except Exception as e:
                logger.warning(f"Failed to parse property from search result: {e}")
                continue
                
        return SearchResponse(results=items, count=len(items))

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search operation failed: {str(e)}"
        )
