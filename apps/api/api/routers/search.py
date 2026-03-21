import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_vector_store
from api.models import (
    RankingExplanation,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from data.schemas import Property
from services.ranking_explainer import create_ranking_explainer
from utils.sanitization import sanitize_search_query
from vector_store.chroma_store import ChromaPropertyStore

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_explanation_to_response(
    explanation,
) -> RankingExplanation:
    """Convert RankingExplanation dataclass to Pydantic model."""
    from api.models import ScoreComponent

    components = [
        ScoreComponent(
            name=c.name,
            value=c.value,
            weight=c.weight,
            contribution=c.contribution,
            description=c.description,
        )
        for c in explanation.components
    ]

    return RankingExplanation(
        property_id=explanation.property_id,
        final_score=explanation.final_score,
        rank=explanation.rank,
        semantic_score=explanation.semantic_score,
        keyword_score=explanation.keyword_score,
        hybrid_score=explanation.hybrid_score,
        exact_match_boost=explanation.exact_match_boost,
        metadata_match_boost=explanation.metadata_match_boost,
        quality_boost=explanation.quality_boost,
        personalization_boost=explanation.personalization_boost,
        diversity_penalty=explanation.diversity_penalty,
        components=components,
    )


@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_properties(
    request: SearchRequest,
    store: Annotated[Optional[ChromaPropertyStore], Depends(get_vector_store)],
):
    """
    Search for properties using semantic search and metadata filters.
    """
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vector store is not available"
        )

    # Sanitize search query to prevent injection attacks
    try:
        sanitized_query = sanitize_search_query(request.query)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    try:
        # Perform hybrid search (Vector + Keyword)
        results = store.hybrid_search(
            query=sanitized_query,
            k=request.limit,
            filters=request.filters,
            alpha=request.alpha,
            lat=request.lat,
            lon=request.lon,
            radius_km=request.radius_km,
            min_lat=request.min_lat,
            max_lat=request.max_lat,
            min_lon=request.min_lon,
            max_lon=request.max_lon,
            polygon=request.polygon,
            sort_by=request.sort_by.value if request.sort_by else None,
            sort_order=request.sort_order.value if request.sort_order else None,
        )

        # Generate explanations if requested
        explanations = []
        if request.include_explanation:
            explainer = create_ranking_explainer()
            explanations = explainer.explain_results(
                results=results,
                query=sanitized_query,
                user_criteria=request.filters,
            )

        items = []
        for idx, (doc, score) in enumerate(results):
            try:
                # Document metadata contains property fields
                # We need to handle potential data inconsistencies
                metadata = doc.metadata.copy()

                # Ensure 'id' is present (sometimes stored as doc-id in Chroma)
                if "id" not in metadata:
                    metadata["id"] = "unknown"

                # 'rooms' might be stored as float in Chroma metadata
                # (no int type support sometimes)
                # Pydantic handles this conversion usually

                # Construct Property model
                # validation_error might occur if metadata is incomplete
                prop = Property.model_validate(metadata)

                # Include explanation if available
                explanation_model = None
                if request.include_explanation and idx < len(explanations):
                    explanation_model = _convert_explanation_to_response(explanations[idx])

                items.append(
                    SearchResultItem(
                        property=prop,
                        score=score,
                        explanation=explanation_model,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse property from search result: {e}")
                continue

        return SearchResponse(results=items, count=len(items))

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search operation failed: {str(e)}",
        ) from e
