from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from data.schemas import Property

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class SortField(str, Enum):
    RELEVANCE = "relevance"
    PRICE = "price"
    PRICE_PER_SQM = "price_per_sqm"
    AREA = "area_sqm"
    YEAR_BUILT = "year_built"

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str

class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    alpha: float = 0.7
    
    # Geospatial
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude for geo-search")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitude for geo-search")
    radius_km: Optional[float] = Field(None, gt=0, description="Radius in kilometers")
    
    # Sorting
    sort_by: Optional[SortField] = SortField.RELEVANCE
    sort_order: Optional[SortOrder] = SortOrder.DESC

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

class IngestRequest(BaseModel):
    """Request model for data ingestion."""
    file_urls: Optional[List[str]] = None
    force: bool = False

class IngestResponse(BaseModel):
    """Response model for data ingestion."""
    message: str
    properties_processed: int
    errors: List[str] = []

class ReindexRequest(BaseModel):
    """Request model for reindexing."""
    clear_existing: bool = False

class ReindexResponse(BaseModel):
    """Response model for reindexing."""
    message: str
    count: int
