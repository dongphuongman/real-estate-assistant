"""
Tests for Market Trends API endpoints.

Task #84: Market Trends Dashboard
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from api.routers import market
from data.schemas import Property, PropertyCollection, PropertyType
from db.database import get_db


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = "user-123"
    user.email = "user@example.com"
    user.role = "user"
    return user


@pytest.fixture
def sample_properties():
    """Create sample properties for testing."""
    return [
        Property(
            id="prop-1",
            city="Warsaw",
            price=500000,
            rooms=3,
            area_sqm=60,
            property_type=PropertyType.APARTMENT,
            latitude=52.23,
            longitude=21.01,
        ),
        Property(
            id="prop-2",
            city="Warsaw",
            price=600000,
            rooms=4,
            area_sqm=70,
            property_type=PropertyType.APARTMENT,
            latitude=52.24,
            longitude=21.02,
        ),
        Property(
            id="prop-3",
            city="Krakow",
            price=400000,
            rooms=2,
            area_sqm=50,
            property_type=PropertyType.APARTMENT,
            latitude=50.06,
            longitude=19.94,
        ),
        Property(
            id="prop-4",
            city="Krakow",
            price=450000,
            rooms=3,
            area_sqm=55,
            property_type=PropertyType.APARTMENT,
            latitude=50.07,
            longitude=19.95,
        ),
    ]


@pytest.fixture
def mock_property_collection(sample_properties):
    """Create a mock property collection."""
    return PropertyCollection(
        properties=sample_properties,
        total_count=len(sample_properties),
    )


@pytest.fixture(scope="function")
async def market_client(
    mock_user: MagicMock,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test client for market endpoints."""
    test_app = FastAPI()
    test_app.include_router(market.router, prefix="/api/v1")

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_current_active_user] = override_get_current_user
    test_app.dependency_overrides[get_db] = override_get_db

    # Add mock response cache to app state for cached_response decorator
    class MockResponseCache:
        async def get(self, request, body_hash=None):
            return None  # Always cache miss

        async def set(self, request, data, status_code=200, headers=None, body_hash=None):
            pass  # No-op

    test_app.state.response_cache = MockResponseCache()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


class TestGetMarketTrends:
    """Tests for market trends endpoint."""

    @pytest.mark.asyncio
    async def test_get_trends_no_data(self, market_client: AsyncClient):
        """Verify response when no property data is available."""
        with patch("api.routers.market.load_collection", return_value=None):
            response = await market_client.get("/api/v1/market/trends")

            assert response.status_code == 200
            data = response.json()
            assert data["trend_direction"] == "insufficient_data"
            assert data["data_points"] == []

    @pytest.mark.asyncio
    async def test_get_trends_with_city_filter(
        self,
        market_client: AsyncClient,
        mock_property_collection: PropertyCollection,
    ):
        """Verify trends endpoint with city filter."""
        with patch(
            "api.routers.market.load_collection",
            return_value=mock_property_collection,
        ):
            response = await market_client.get(
                "/api/v1/market/trends",
                params={"city": "Warsaw", "interval": "month"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "Warsaw"
            assert data["interval"] == "month"

    @pytest.mark.asyncio
    async def test_get_trends_invalid_interval(
        self,
        market_client: AsyncClient,
        mock_property_collection: PropertyCollection,
    ):
        """Verify response for invalid interval parameter."""
        with patch(
            "api.routers.market.load_collection",
            return_value=mock_property_collection,
        ):
            response = await market_client.get(
                "/api/v1/market/trends",
                params={"interval": "invalid"},
            )

            # Should return validation error
            assert response.status_code == 422


class TestGetMarketIndicators:
    """Tests for market indicators endpoint."""

    @pytest.mark.asyncio
    async def test_get_indicators_no_data(self, market_client: AsyncClient):
        """Verify response when no property data is available."""
        with patch("api.routers.market.load_collection", return_value=None):
            response = await market_client.get("/api/v1/market/indicators")

            assert response.status_code == 200
            data = response.json()
            assert data["overall_trend"] == "stable"
            assert data["total_listings"] == 0

    @pytest.mark.asyncio
    async def test_get_indicators_with_data(
        self,
        market_client: AsyncClient,
        mock_property_collection: PropertyCollection,
    ):
        """Verify indicators endpoint returns correct data."""
        mock_repo = MagicMock()
        mock_repo.get_properties_with_price_drops = MagicMock(return_value=[])

        with (
            patch("api.routers.market.load_collection", return_value=mock_property_collection),
            patch("api.routers.market.PriceSnapshotRepository", return_value=mock_repo),
        ):
            response = await market_client.get("/api/v1/market/indicators")

            assert response.status_code == 200
            data = response.json()
            assert data["total_listings"] == 4
            assert "hottest_districts" in data
            assert "coldest_districts" in data


class TestCompareAreas:
    """Tests for area comparison endpoint."""

    @pytest.mark.asyncio
    async def test_compare_areas_no_data(self, market_client: AsyncClient):
        """Verify response when no property data is available."""
        with patch("api.routers.market.load_collection", return_value=None):
            response = await market_client.get(
                "/api/v1/market/compare",
                params={"city1": "Warsaw", "city2": "Krakow"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["area1"]["city"] == "Warsaw"
            assert data["area2"]["city"] == "Krakow"
            assert data["area1"]["property_count"] == 0

    @pytest.mark.asyncio
    async def test_compare_areas_with_data(
        self,
        market_client: AsyncClient,
        mock_property_collection: PropertyCollection,
    ):
        """Verify comparison endpoint returns correct data."""
        with patch(
            "api.routers.market.load_collection",
            return_value=mock_property_collection,
        ):
            response = await market_client.get(
                "/api/v1/market/compare",
                params={"city1": "Warsaw", "city2": "Krakow"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["area1"]["city"] == "Warsaw"
            assert data["area2"]["city"] == "Krakow"
            assert data["area1"]["property_count"] == 2
            assert data["area2"]["property_count"] == 2
            assert "price_difference" in data
            assert "cheaper_area" in data

    @pytest.mark.asyncio
    async def test_compare_areas_missing_params(self, market_client: AsyncClient):
        """Verify error when required parameters are missing."""
        response = await market_client.get("/api/v1/market/compare")

        assert response.status_code == 422  # Validation error


class TestGetAreaInsights:
    """Tests for single area insights endpoint."""

    @pytest.mark.asyncio
    async def test_get_area_insights_no_data(self, market_client: AsyncClient):
        """Verify response when no property data is available."""
        with patch("api.routers.market.load_collection", return_value=None):
            response = await market_client.get("/api/v1/market/area/Warsaw")

            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "Warsaw"
            assert data["property_count"] == 0

    @pytest.mark.asyncio
    async def test_get_area_insights_with_data(
        self,
        market_client: AsyncClient,
        mock_property_collection: PropertyCollection,
    ):
        """Verify area insights endpoint returns correct data."""
        with patch(
            "api.routers.market.load_collection",
            return_value=mock_property_collection,
        ):
            response = await market_client.get("/api/v1/market/area/Warsaw")

            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "Warsaw"
            assert data["property_count"] == 2
            assert "avg_price" in data
            assert "median_price" in data

    @pytest.mark.asyncio
    async def test_get_area_insights_not_found(
        self,
        market_client: AsyncClient,
        mock_property_collection: PropertyCollection,
    ):
        """Verify response for non-existent city."""
        with patch(
            "api.routers.market.load_collection",
            return_value=mock_property_collection,
        ):
            response = await market_client.get("/api/v1/market/area/NonExistent")

            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "NonExistent"
            assert data["property_count"] == 0


class TestPriceHistory:
    """Tests for price history endpoint."""

    @pytest.mark.asyncio
    async def test_price_history_not_found(
        self, market_client: AsyncClient, db_session: AsyncSession
    ):
        """Verify response when property has no price history."""
        mock_repo = MagicMock()
        mock_repo.get_by_property = AsyncMock(return_value=[])
        mock_repo.count_for_property = AsyncMock(return_value=0)

        with patch(
            "api.routers.market.PriceSnapshotRepository",
            return_value=mock_repo,
        ):
            response = await market_client.get("/api/v1/market/price-history/prop-123")

            assert response.status_code == 200
            data = response.json()
            assert data["property_id"] == "prop-123"
            assert data["total"] == 0
            assert data["trend"] == "insufficient_data"
