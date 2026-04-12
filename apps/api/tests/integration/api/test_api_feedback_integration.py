"""Integration tests for feedback router."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routers import feedback
from db.database import get_db


@pytest.fixture
def test_app(db_session):
    """Create test app with feedback router and mocked dependencies."""
    app = FastAPI()
    app.include_router(feedback.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestFeedbackAPI:
    """Integration tests for feedback endpoints."""

    @pytest.mark.asyncio
    async def test_submit_rating(self, client):
        """Submit a thumbs-up rating for a search result."""
        resp = await client.post(
            "/api/v1/feedback/rating",
            json={
                "query": "apartments in Krakow",
                "property_id": "prop-001",
                "rating": 5,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["query"] == "apartments in Krakow"
        assert data["property_id"] == "prop-001"
        assert data["rating"] == 5
        assert "id" in data

    @pytest.mark.asyncio
    async def test_submit_thumbs_down_rating(self, client):
        """Submit a low rating."""
        resp = await client.post(
            "/api/v1/feedback/rating",
            json={
                "query": "cheap houses",
                "property_id": "prop-002",
                "rating": 1,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["rating"] == 1

    @pytest.mark.asyncio
    async def test_get_relevance_metrics_empty(self, client):
        """Returns zeroed metrics when no ratings exist."""
        resp = await client.get("/api/v1/feedback/metrics/relevance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_ratings"] == 0
        assert data["avg_rating"] == 0.0
        assert data["positive_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_get_relevance_metrics_with_ratings(self, client):
        """Returns aggregated metrics after submitting ratings."""
        # Submit several ratings
        for rating in [5, 4, 3, 5, 2]:
            await client.post(
                "/api/v1/feedback/rating",
                json={
                    "query": "test query",
                    "property_id": f"prop-{rating}",
                    "rating": rating,
                },
            )

        resp = await client.get("/api/v1/feedback/metrics/relevance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_ratings"] == 5
        assert data["avg_rating"] > 0
        assert data["positive_pct"] > 0

    @pytest.mark.asyncio
    async def test_get_relevance_metrics_with_since_filter(self, client):
        """Filters metrics by date using 'since' parameter."""
        # Submit a rating
        await client.post(
            "/api/v1/feedback/rating",
            json={
                "query": "test",
                "property_id": "prop-100",
                "rating": 4,
            },
        )

        # Use a far-future date — should return zero
        resp = await client.get(
            "/api/v1/feedback/metrics/relevance",
            params={"since": "2099-01-01T00:00:00Z"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_ratings"] == 0

    @pytest.mark.asyncio
    async def test_invalid_since_date(self, client):
        """Returns 400 for invalid 'since' date format."""
        resp = await client.get(
            "/api/v1/feedback/metrics/relevance",
            params={"since": "not-a-date"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_rating_missing_fields(self, client):
        """Returns 422 when required fields are missing."""
        resp = await client.post(
            "/api/v1/feedback/rating",
            json={"query": "test"},
        )
        assert resp.status_code == 422
