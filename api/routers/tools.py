from typing import Annotated, List, Optional
import statistics

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import (
    get_crm_connector,
    get_data_enrichment_service,
    get_legal_check_service,
    get_valuation_provider,
    get_vector_store,
)
from api.models import (
    CRMContactRequest,
    CRMContactResponse,
    ComparePropertiesRequest,
    ComparePropertiesResponse,
    CompareSummary,
    ComparedProperty,
    DataEnrichmentRequest,
    DataEnrichmentResponse,
    LegalCheckRequest,
    LegalCheckResponse,
    LocationAnalysisRequest,
    LocationAnalysisResponse,
    PriceAnalysisRequest,
    PriceAnalysisResponse,
    ValuationRequest,
    ValuationResponse,
)
from tools.property_tools import (
    MortgageCalculatorTool,
    MortgageInput,
    MortgageResult,
    create_property_tools,
)
from vector_store.chroma_store import ChromaPropertyStore

router = APIRouter()


class ToolInfo(BaseModel):
    """Information about an available tool."""

    name: str
    description: str


@router.get("/tools", response_model=List[ToolInfo], tags=["Tools"])
async def list_tools():
    """List available tools."""
    tools = create_property_tools()
    items = [ToolInfo(name=tool.name, description=tool.description) for tool in tools]
    items.extend(
        [
            ToolInfo(
                name="valuation",
                description="Estimate property value from listing metadata (CE stub; may be disabled).",
            ),
            ToolInfo(
                name="legal_check",
                description="Basic contract text risk check (CE stub; may be disabled).",
            ),
            ToolInfo(
                name="enrich_address",
                description="Address enrichment (CE stub; gated by DATA_ENRICHMENT_ENABLED).",
            ),
            ToolInfo(
                name="crm_sync_contact",
                description="CRM contact sync via webhook (CE stub; gated by CRM_WEBHOOK_URL).",
            ),
        ]
    )
    return items


@router.post(
    "/tools/mortgage-calculator", response_model=MortgageResult, tags=["Tools"]
)
async def calculate_mortgage(input_data: MortgageInput):
    """
    Calculate mortgage payments.
    """
    try:
        return MortgageCalculatorTool.calculate(
            property_price=input_data.property_price,
            down_payment_percent=input_data.down_payment_percent,
            interest_rate=input_data.interest_rate,
            loan_years=input_data.loan_years,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}",
        ) from e


@router.post(
    "/tools/compare-properties",
    response_model=ComparePropertiesResponse,
    tags=["Tools"],
)
async def compare_properties(
    request: ComparePropertiesRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    property_ids = [pid.strip() for pid in request.property_ids if pid and pid.strip()]
    if not property_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one property_id is required",
        )

    docs = store.get_properties_by_ids(property_ids)
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No properties found for provided IDs",
        )

    properties = []
    prices: List[float] = []
    for doc in docs:
        md = doc.metadata or {}
        item = ComparedProperty(
            id=str(md.get("id")) if md.get("id") is not None else None,
            price=_to_float(md.get("price")),
            price_per_sqm=_to_float(md.get("price_per_sqm")),
            city=md.get("city"),
            rooms=_to_float(md.get("rooms")),
            bathrooms=_to_float(md.get("bathrooms")),
            area_sqm=_to_float(md.get("area_sqm")),
            year_built=_to_int(md.get("year_built")),
            property_type=md.get("property_type"),
        )
        if item.price is not None:
            prices.append(item.price)
        properties.append(item)

    summary = CompareSummary(
        count=len(properties),
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        price_difference=(max(prices) - min(prices)) if len(prices) >= 2 else None,
    )

    return ComparePropertiesResponse(properties=properties, summary=summary)


@router.post(
    "/tools/price-analysis", response_model=PriceAnalysisResponse, tags=["Tools"]
)
async def price_analysis(
    request: PriceAnalysisRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query is required",
        )

    results = store.search(query, k=20)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No properties found for analysis",
        )

    docs = [doc for doc, _score in results]
    prices: List[float] = []
    sqm_prices: List[float] = []
    distribution: dict[str, int] = {}

    for doc in docs:
        md = doc.metadata or {}
        raw_price = _to_float(md.get("price"))
        if raw_price is not None:
            prices.append(raw_price)
        raw_ppsqm = _to_float(md.get("price_per_sqm"))
        if raw_ppsqm is not None:
            sqm_prices.append(raw_ppsqm)

        ptype = md.get("property_type") or "Unknown"
        distribution[str(ptype)] = distribution.get(str(ptype), 0) + 1

    return PriceAnalysisResponse(
        query=query,
        count=len(docs),
        average_price=statistics.mean(prices) if prices else None,
        median_price=statistics.median(prices) if prices else None,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        average_price_per_sqm=statistics.mean(sqm_prices) if sqm_prices else None,
        median_price_per_sqm=statistics.median(sqm_prices) if sqm_prices else None,
        distribution_by_type=distribution,
    )


@router.post(
    "/tools/location-analysis", response_model=LocationAnalysisResponse, tags=["Tools"]
)
async def location_analysis(
    request: LocationAnalysisRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )

    property_id = request.property_id.strip()
    if not property_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )

    docs = store.get_properties_by_ids([property_id])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    md = docs[0].metadata or {}
    return LocationAnalysisResponse(
        property_id=property_id,
        city=md.get("city"),
        neighborhood=md.get("neighborhood"),
        lat=_to_float(md.get("lat")),
        lon=_to_float(md.get("lon")),
    )

@router.post(
    "/tools/valuation", response_model=ValuationResponse, tags=["Tools"]
)
async def valuation(
    request: ValuationRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
    provider=Depends(get_valuation_provider),
):
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store unavailable",
        )
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Valuation disabled",
        )
    pid = request.property_id.strip()
    if not pid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_id is required",
        )
    docs = store.get_properties_by_ids([pid])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    md = docs[0].metadata or {}
    area = md.get("area_sqm")
    price_per_sqm = md.get("price_per_sqm")
    value = provider.estimate_value({"area": area, "price_per_sqm": price_per_sqm})
    return ValuationResponse(property_id=pid, estimated_value=value)

@router.post(
    "/tools/legal-check", response_model=LegalCheckResponse, tags=["Tools"]
)
async def legal_check(
    request: LegalCheckRequest,
    service=Depends(get_legal_check_service),
):
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legal check disabled",
        )
    text = request.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text is required",
        )
    result = service.analyze_contract(text)
    return LegalCheckResponse(
        risks=result.get("risks", []),
        score=float(result.get("score", 0.0)),
    )

@router.post(
    "/tools/enrich-address", response_model=DataEnrichmentResponse, tags=["Tools"]
)
async def enrich_address(
    request: DataEnrichmentRequest,
    service=Depends(get_data_enrichment_service),
):
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data enrichment disabled",
        )
    address = request.address.strip()
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="address is required",
        )
    data = service.enrich(address)
    return DataEnrichmentResponse(address=address, data=data)

@router.post(
    "/tools/crm-sync-contact", response_model=CRMContactResponse, tags=["Tools"]
)
async def crm_sync_contact(
    request: CRMContactRequest,
    connector=Depends(get_crm_connector),
):
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM connector not configured",
        )
    payload = {"name": request.name, "phone": request.phone, "email": request.email}
    cid = connector.sync_contact(payload)
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="CRM sync failed",
        )
    return CRMContactResponse(id=cid)

def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
