from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from data.schemas import Property
from pydantic import model_validator

from utils.exporters import ExportFormat


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
    lat: Optional[float] = Field(
        None, ge=-90, le=90, description="Latitude for geo-search"
    )
    lon: Optional[float] = Field(
        None, ge=-180, le=180, description="Longitude for geo-search"
    )
    radius_km: Optional[float] = Field(None, gt=0, description="Radius in kilometers")
    min_lat: Optional[float] = Field(
        None, ge=-90, le=90, description="Bounding box min latitude"
    )
    max_lat: Optional[float] = Field(
        None, ge=-90, le=90, description="Bounding box max latitude"
    )
    min_lon: Optional[float] = Field(
        None, ge=-180, le=180, description="Bounding box min longitude"
    )
    max_lon: Optional[float] = Field(
        None, ge=-180, le=180, description="Bounding box max longitude"
    )

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


class NotificationSettings(BaseModel):
    """User notification settings."""

    email_digest: bool = True
    frequency: str = "weekly"
    expert_mode: bool = False
    marketing_emails: bool = False


class ComparePropertiesRequest(BaseModel):
    property_ids: List[str]


class ComparedProperty(BaseModel):
    id: Optional[str] = None
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    city: Optional[str] = None
    rooms: Optional[float] = None
    bathrooms: Optional[float] = None
    area_sqm: Optional[float] = None
    year_built: Optional[int] = None
    property_type: Optional[str] = None


class CompareSummary(BaseModel):
    count: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    price_difference: Optional[float] = None


class ComparePropertiesResponse(BaseModel):
    properties: List[ComparedProperty]
    summary: CompareSummary


class PriceAnalysisRequest(BaseModel):
    query: str


class PriceAnalysisResponse(BaseModel):
    query: str
    count: int
    average_price: Optional[float] = None
    median_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    average_price_per_sqm: Optional[float] = None
    median_price_per_sqm: Optional[float] = None
    distribution_by_type: Dict[str, int] = {}


class LocationAnalysisRequest(BaseModel):
    property_id: str


class LocationAnalysisResponse(BaseModel):
    property_id: str
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class ExportPropertiesRequest(BaseModel):
    format: ExportFormat
    property_ids: Optional[List[str]] = None
    search: Optional[SearchRequest] = None

    columns: Optional[List[str]] = None
    include_header: bool = True

    include_summary: bool = True
    include_statistics: bool = True
    include_metadata: bool = True
    pretty: bool = True
    max_properties: Optional[int] = None

    @model_validator(mode="after")
    def validate_input(self) -> "ExportPropertiesRequest":
        if not self.property_ids and self.search is None:
            raise ValueError("Either property_ids or search must be provided")
        return self
