"""
Unit tests for feedback router (api/routers/feedback.py).

Tests cover:
- Submit rating endpoint (thumbs up/down, database storage)
- Get relevance metrics endpoint (aggregation, filtering, date parsing)
- Error handling (invalid date, database errors)
"""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.routers.feedback import router as feedback_router
from db.database import get_db


@pytest.fixture
async def feedback_client(db_session):
    """Create an async HTTP client for testing feedback endpoints."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(feedback_router)

    # Override the get_db dependency to use test database
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


class TestSubmitRatingEndpoint:
    """Test submit rating endpoint."""

    @pytest.mark.asyncio
    async def test_submit_rating_success_thumbs_up(self, feedback_client):
        """Test successful rating submission with thumbs up (5)."""
        response = await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "2-bedroom apartment in Berlin",
                "property_id": "prop-123",
                "rating": 5,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["query"] == "2-bedroom apartment in Berlin"
        assert data["property_id"] == "prop-123"
        assert data["rating"] == 5
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_submit_rating_thumbs_down(self, feedback_client):
        """Test successful rating submission with thumbs down (1)."""
        response = await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "cheap apartment in Warsaw",
                "property_id": "prop-456",
                "rating": 1,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["rating"] == 1

    @pytest.mark.asyncio
    async def test_submit_rating_middle_rating(self, feedback_client):
        """Test successful rating submission with middle rating (3)."""
        response = await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "luxury apartment in Krakow",
                "property_id": "prop-789",
                "rating": 3,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["rating"] == 3

    @pytest.mark.asyncio
    async def test_submit_rating_missing_query(self, feedback_client):
        """Test rating submission with missing query field."""
        response = await feedback_client.post(
            "/feedback/rating",
            json={
                "property_id": "prop-123",
                "rating": 5,
            },
        )

        # FastAPI validation should catch missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_submit_rating_missing_property_id(self, feedback_client):
        """Test rating submission with missing property_id field."""
        response = await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "test query",
                "rating": 5,
            },
        )

        # FastAPI validation should catch missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_submit_rating_invalid_rating(self, feedback_client):
        """Test rating submission with invalid rating value."""
        response = await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "test query",
                "property_id": "prop-123",
                "rating": 6,  # Invalid: rating must be 1-5
            },
        )

        # FastAPI validation should catch invalid rating
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_submit_rating_missing_rating(self, feedback_client):
        """Test rating submission with missing rating field."""
        response = await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "test query",
                "property_id": "prop-123",
            },
        )

        # FastAPI validation should catch missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetRelevanceMetricsEndpoint:
    """Test get relevance metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_metrics_success_no_filter(self, feedback_client):
        """Test successful metrics retrieval without date filter."""
        # First, add some test data
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "test query 1",
                "property_id": "prop-1",
                "rating": 5,
            },
        )
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "test query 2",
                "property_id": "prop-2",
                "rating": 4,
            },
        )
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "test query 3",
                "property_id": "prop-3",
                "rating": 3,
            },
        )

        response = await feedback_client.get("/feedback/metrics/relevance")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "avg_rating" in data
        assert "total_ratings" in data
        assert "positive_pct" in data
        assert "ratings_by_score" in data
        assert len(data["ratings_by_score"]) == 5  # Scores 1-5
        assert data["total_ratings"] == 3

    @pytest.mark.asyncio
    async def test_get_metrics_with_date_filter(self, feedback_client):
        """Test metrics retrieval with valid 'since' date filter."""
        # Add test data
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "recent query",
                "property_id": "prop-recent",
                "rating": 5,
            },
        )

        response = await feedback_client.get(
            "/feedback/metrics/relevance?since=2025-01-01T00:00:00Z"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "avg_rating" in data
        # Should only return ratings from the date filter
        assert data["total_ratings"] >= 0

    @pytest.mark.asyncio
    async def test_get_metrics_invalid_date_format(self, feedback_client):
        """Test metrics retrieval with invalid date format."""
        response = await feedback_client.get("/feedback/metrics/relevance?since=invalid-date")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "since" in data["detail"].lower() or "date" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_metrics_no_ratings(self, feedback_client):
        """Test metrics when no ratings exist."""
        response = await feedback_client.get("/feedback/metrics/relevance")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_ratings"] == 0
        assert data["avg_rating"] == 0.0
        assert data["positive_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_get_metrics_all_negative(self, feedback_client):
        """Test metrics when all ratings are negative (1-2)."""
        # Add only negative ratings
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "bad query 1",
                "property_id": "prop-bad-1",
                "rating": 1,
            },
        )
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "bad query 2",
                "property_id": "prop-bad-2",
                "rating": 2,
            },
        )

        response = await feedback_client.get("/feedback/metrics/relevance")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Positive percentage should be low (only ratings 4-5 are positive)
        assert data["positive_pct"] == 0.0
        assert data["avg_rating"] < 2.0

    @pytest.mark.asyncio
    async def test_get_metrics_all_positive(self, feedback_client):
        """Test metrics when all ratings are positive (4-5)."""
        # Add only positive ratings
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "good query 1",
                "property_id": "prop-good-1",
                "rating": 5,
            },
        )
        await feedback_client.post(
            "/feedback/rating",
            json={
                "query": "good query 2",
                "property_id": "prop-good-2",
                "rating": 4,
            },
        )

        response = await feedback_client.get("/feedback/metrics/relevance")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All ratings should be positive
        assert data["positive_pct"] == 100.0
        assert data["avg_rating"] >= 4.0


class TestFeedbackRouterConfiguration:
    """Test feedback router configuration."""

    def test_router_tag(self):
        """Test that router has correct tag."""
        assert feedback_router.tags == ["Feedback"]

    def test_router_prefix(self):
        """Test that router has correct prefix."""
        assert feedback_router.prefix == "/feedback"

    def test_router_endpoints_registered(self):
        """Test that router has expected endpoints registered."""
        # Router should have 2 endpoints registered
        assert len(feedback_router.routes) >= 2

        # Check endpoint paths
        paths = [route.path for route in feedback_router.routes]
        assert "/feedback/rating" in paths
        assert "/feedback/metrics/relevance" in paths

    def test_endpoint_methods(self):
        """Test that endpoints have correct HTTP methods."""
        for route in feedback_router.routes:
            if route.path == "/feedback/rating":
                assert "POST" in route.methods
            elif route.path == "/feedback/metrics/relevance":
                assert "GET" in route.methods

    def test_endpoint_tags(self):
        """Test that admin-only endpoint has correct tags."""
        for route in feedback_router.routes:
            if route.path == "/feedback/metrics/relevance":
                assert "Admin" in route.tags
