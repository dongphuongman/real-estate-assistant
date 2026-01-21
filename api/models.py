from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from data.schemas import Property
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


class RagCitation(BaseModel):
    source: Optional[str] = None
    chunk_index: Optional[int] = None


class RagQaRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    provider: Optional[str] = None
    model: Optional[str] = None


class RagQaResponse(BaseModel):
    answer: str
    citations: List[RagCitation] = Field(default_factory=list)
    llm_used: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None


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


class ModelPricing(BaseModel):
    input_price_per_1m: float
    output_price_per_1m: float
    currency: str = "USD"


class ModelCatalogItem(BaseModel):
    id: str
    display_name: str
    provider_name: str
    context_window: int
    pricing: Optional[ModelPricing] = None
    capabilities: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    recommended_for: List[str] = Field(default_factory=list)


class ModelProviderCatalog(BaseModel):
    name: str
    display_name: str
    is_local: bool
    requires_api_key: bool
    models: List[ModelCatalogItem]
    runtime_available: Optional[bool] = None
    available_models: Optional[List[str]] = None


class ModelPreferences(BaseModel):
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class ModelPreferencesUpdate(BaseModel):
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "ModelPreferencesUpdate":
        if self.preferred_provider is None and self.preferred_model is None:
            raise ValueError("At least one of preferred_provider or preferred_model must be provided")
        return self


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

class ValuationRequest(BaseModel):
    property_id: str

class ValuationResponse(BaseModel):
    property_id: str
    estimated_value: float

class LegalCheckRequest(BaseModel):
    text: str

class LegalCheckResponse(BaseModel):
    risks: List[Dict[str, Any]] = []
    score: float = 0.0

class DataEnrichmentRequest(BaseModel):
    address: str

class DataEnrichmentResponse(BaseModel):
    address: str
    data: Dict[str, Any] = {}

class CRMContactRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class CRMContactResponse(BaseModel):
    id: str


class ExportPropertiesRequest(BaseModel):
    format: ExportFormat
    property_ids: Optional[List[str]] = None
    search: Optional[SearchRequest] = None

    columns: Optional[List[str]] = None
    include_header: bool = True
    csv_delimiter: str = ","
    csv_decimal: str = "."

    include_summary: bool = True
    include_statistics: bool = True
    include_metadata: bool = True
    pretty: bool = True
    max_properties: Optional[int] = None

    @model_validator(mode="after")
    def validate_input(self) -> "ExportPropertiesRequest":
        if not self.property_ids and self.search is None:
            raise ValueError("Either property_ids or search must be provided")
        if len(self.csv_delimiter) != 1 or self.csv_delimiter in ("\n", "\r"):
            raise ValueError("csv_delimiter must be a single non-newline character")
        if len(self.csv_decimal) != 1 or self.csv_decimal in ("\n", "\r"):
            raise ValueError("csv_decimal must be a single non-newline character")
        return self


class PromptTemplateVariableInfo(BaseModel):
    name: str
    description: str
    required: bool = True
    example: Optional[str] = None


class PromptTemplateInfo(BaseModel):
    id: str
    title: str
    category: str
    description: str
    template_text: str
    variables: List[PromptTemplateVariableInfo]


class PromptTemplateApplyRequest(BaseModel):
    template_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)


class PromptTemplateApplyResponse(BaseModel):
    template_id: str
    rendered_text: str
