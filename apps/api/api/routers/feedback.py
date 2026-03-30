"""Feedback and relevance rating endpoints (Task #118)."""

import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import SearchFeedback
from db.schemas import FeedbackCreate, FeedbackResponse, RelevanceMetrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "/rating",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a relevance rating for a search result",
)
async def submit_rating(
    body: FeedbackCreate,
    session: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """
    Submit a thumbs-up/down rating for a search result.
    Ratings are stored anonymously — no user authentication required.
    """
    feedback = SearchFeedback(
        id=str(uuid4()),
        search_query=body.query,
        property_id=body.property_id,
        rating=body.rating,
        created_at=datetime.now(UTC),
    )
    session.add(feedback)
    await session.flush()

    return FeedbackResponse(
        id=feedback.id,
        query=feedback.search_query,
        property_id=feedback.property_id,
        rating=feedback.rating,
        created_at=feedback.created_at,
    )


@router.get(
    "/metrics/relevance",
    response_model=RelevanceMetrics,
    summary="Get aggregated relevance metrics",
    tags=["Admin"],
)
async def get_relevance_metrics(
    since: Optional[str] = Query(None, description="ISO date to filter ratings from"),
    session: AsyncSession = Depends(get_db),
) -> RelevanceMetrics:
    """
    Return aggregated search relevance metrics for admin monitoring.
    Measures user-rated match accuracy against the ≥80% target.
    """
    # Base query
    base = select(SearchFeedback)
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 'since' date format. Use ISO 8601.",
            ) from None
        base = base.where(SearchFeedback.created_at >= since_dt)

    # Total and average
    total_q = select(func.count()).select_from(base.subquery())
    avg_q = select(func.avg(SearchFeedback.rating)).select_from(base.subquery())

    total_result = await session.execute(total_q)
    avg_result = await session.execute(avg_q)

    total_ratings = total_result.scalar() or 0
    avg_rating = avg_result.scalar() or 0.0

    # Positive ratings (4-5)
    positive_q = select(func.count()).select_from(base.where(SearchFeedback.rating >= 4).subquery())
    positive_result = await session.execute(positive_q)
    positive_count = positive_result.scalar() or 0

    positive_pct = (positive_count / total_ratings * 100) if total_ratings > 0 else 0.0

    # Breakdown by score
    ratings_by_score: dict[str, int] = {}
    for score in range(1, 6):
        score_q = select(func.count()).select_from(
            base.where(SearchFeedback.rating == score).subquery()
        )
        score_result = await session.execute(score_q)
        ratings_by_score[str(score)] = score_result.scalar() or 0

    return RelevanceMetrics(
        avg_rating=round(avg_rating, 2),
        total_ratings=total_ratings,
        positive_pct=round(positive_pct, 1),
        ratings_by_score=ratings_by_score,
    )
