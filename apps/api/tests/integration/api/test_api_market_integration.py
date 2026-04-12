"""Integration tests for market analytics router."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import market
from data.schemas import Property, PropertyCollection, PropertyType
from db.database import get_db
from db.schemas import UserResponse


def _make_collection():
    """Create a mock property collection for market tests."""
    properties = [
        Property(
            id=f"prop{i}",
            city="Krakow",
            rooms=2 + i,
            bathrooms=1,
            price=1000 + i * 100,
            area_sqm=50 + i * 10,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT,
            source_url=f"http://example.com/{i}",
        )
        for i in range(5)
    ]
    return PropertyCollection(properties=properties, total_count=5)


@pytest.fixture
def test_app(db_session):
    """Create test app with market router and mocked dependencies."""
    app = FastAPI()
    app.include_router(market.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
            roles=["user"],
            created_at="2024-01-01T00:00:00Z",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestMarketAPI:
    """Integration tests for market analytics endpoints."""

    @pytest.mark.asyncio
    async def test_get_price_history_empty(self, client):
        """Returns price history with empty snapshots for unknown property."""
        with patch("api.routers.market.PriceSnapshotRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_property = AsyncMock(return_value=[])
            mock_repo.count_for_property = AsyncMock(return_value=0)

            resp = await client.get("/api/v1/market/price-history/prop-unknown")
            assert resp.status_code == 200
            data = resp.json()
            assert data["property_id"] == "prop-unknown"
            assert data["total"] == 0
            assert data["snapshots"] == []

    @pytest.mark.asyncio
    async def test_get_trends_no_data(self, client):
        """Returns trends response with no data when cache is empty."""
        with patch("api.routers.market.load_collection", return_value=None):
            resp = await client.get("/api/v1/market/trends")
            assert resp.status_code == 200
            data = resp.json()
            assert data["data_points"] == []
            assert data["trend_direction"] == "insufficient_data"

    @pytest.mark.asyncio
    async def test_get_trends_with_city_filter(self, client):
        """Filters trends by city."""
        with patch("api.routers.market.load_collection", return_value=_make_collection()):
            resp = await client.get(
                "/api/v1/market/trends",
                params={"city": "Krakow"},
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_indicators_no_data(self, client):
        """Returns indicators with zero listings when cache is empty."""
        with (
            patch("api.routers.market.load_collection", return_value=None),
            patch("api.routers.market.PriceSnapshotRepository") as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_properties_with_price_drops = AsyncMock(return_value=[])

            resp = await client.get("/api/v1/market/indicators")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_listings"] == 0

    @pytest.mark.asyncio
    async def test_compare_areas_no_data(self, client):
        """Returns comparison with zeroed values when cache is empty."""
        with patch("api.routers.market.load_collection", return_value=None):
            resp = await client.get(
                "/api/v1/market/compare",
                params={"city1": "Krakow", "city2": "Warsaw"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["area1"]["city"] == "Krakow"
            assert data["area2"]["city"] == "Warsaw"
            assert data["price_difference"] == 0

    @pytest.mark.asyncio
    async def test_get_area_insights_no_data(self, client):
        """Returns insights with zeroed values when cache is empty."""
        with patch("api.routers.market.load_collection", return_value=None):
            resp = await client.get("/api/v1/market/area/Krakow")
            assert resp.status_code == 200
            data = resp.json()
            assert data["city"] == "Krakow"
            assert data["property_count"] == 0

    @pytest.mark.asyncio
    async def test_get_area_insights_with_data(self, client):
        """Returns area insights when properties exist."""
        with patch("api.routers.market.load_collection", return_value=_make_collection()):
            resp = await client.get("/api/v1/market/area/Krakow")
            assert resp.status_code == 200
            data = resp.json()
            assert data["city"] == "Krakow"
            assert data["property_count"] > 0
