from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from data.schemas import Property

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str

class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None

class SearchResultItem(BaseModel):
    """Search result item with score."""
    property: Property
    score: float

class SearchResponse(BaseModel):
    """Search response model."""
    results: List[SearchResultItem]
    count: int

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    sources: List[Dict[str, Any]] = []
    session_id: Optional[str] = None
