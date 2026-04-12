"""Integration tests for agent analytics router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import agent_analytics
from db.database import get_db
from db.schemas import UserResponse


def _make_user_response(**overrides):
    """Create a UserResponse for dependency override."""
    return UserResponse(
        id=overrides.get("id", "test-user-123"),
        email=overrides.get("email", "agent@example.com"),
        role=overrides.get("role", "agent"),
        created_at=overrides.get("created_at", "2024-01-01T00:00:00Z"),
    )


@pytest.fixture
def test_app(db_session):
    """Create test app with agent_analytics router and mocked dependencies."""
    app = FastAPI()
    app.include_router(agent_analytics.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return _make_user_response(role="agent")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_metrics_mock():
    """Create a mock agent metrics result."""
    m = MagicMock()
    m.total_leads = 50
    m.active_leads = 20
    m.new_leads_week = 5
    m.high_value_leads = 10
    m.total_deals = 15
    m.active_deals = 8
    m.closed_deals = 5
    m.fell_through_deals = 2
    m.lead_to_qualified_rate = 0.4
    m.qualified_to_deal_rate = 0.5
    m.overall_conversion_rate = 0.2
    m.avg_time_to_first_contact_hours = 2.5
    m.avg_time_to_qualify_days = 7.0
    m.avg_time_to_close_days = 30.0
    m.total_deal_value = 5000000.0
    m.avg_deal_value = 333333.33
    m.total_commission = 75000.0
    m.pending_commission = 25000.0
    m.top_property_types = [{"type": "apartment", "count": 10}]
    m.top_locations = [{"city": "Krakow", "count": 8}]
    m.avg_lead_score = 7.5
    m.deals_change_percent = 15.0
    m.revenue_change_percent = 20.0
    return m


def _make_comparison_mock():
    """Create a mock team comparison result."""
    m = MagicMock()
    m.agent_id = "test-user-123"
    m.agent_name = "Test Agent"
    m.rank_by_deals = 3
    m.rank_by_revenue = 5
    m.rank_by_conversion = 2
    m.total_agents = 15
    m.deals_vs_avg_percent = 25.0
    m.revenue_vs_avg_percent = 10.0
    m.conversion_vs_avg_percent = 30.0
    m.time_to_close_vs_avg_percent = -5.0
    m.team_avg_deals = 12.0
    m.team_avg_revenue = 4500000.0
    m.team_avg_conversion = 0.15
    m.team_avg_time_to_close_days = 35.0
    return m


class TestAgentAnalyticsAPI:
    """Integration tests for agent analytics endpoints."""

    @pytest.mark.asyncio
    async def test_get_my_metrics(self, client):
        """Gets agent's own performance metrics."""
        mock_service = AsyncMock()
        mock_service.get_agent_metrics.return_value = _make_metrics_mock()

        with patch(
            "api.routers.agent_analytics.AgentPerformanceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/agent-analytics/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_leads"] == 50
        assert data["total_deals"] == 15

    @pytest.mark.asyncio
    async def test_get_my_team_comparison(self, client):
        """Gets team comparison for the agent."""
        mock_service = AsyncMock()
        mock_service.get_team_comparison.return_value = _make_comparison_mock()

        with patch(
            "api.routers.agent_analytics.AgentPerformanceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/agent-analytics/me/comparison")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rank_by_deals"] == 3
        assert data["total_agents"] == 15

    @pytest.mark.asyncio
    async def test_get_my_trends(self, client):
        """Gets performance trends."""
        mock_service = AsyncMock()
        mock_trend = MagicMock()
        mock_trend.period = "2025-01"
        mock_trend.period_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mock_trend.period_end = datetime(2025, 1, 31, tzinfo=timezone.utc)
        mock_trend.leads = 10
        mock_trend.deals_closed = 3
        mock_trend.revenue = 500000.0
        mock_trend.conversion_rate = 0.3
        mock_trend.avg_deal_value = 166666.67
        mock_service.get_performance_trends.return_value = [mock_trend]

        with patch(
            "api.routers.agent_analytics.AgentPerformanceService",
            return_value=mock_service,
        ):
            resp = await client.get(
                "/api/v1/agent-analytics/me/trends",
                params={"interval": "month", "periods": 6},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["trends"]) == 1
        assert data["interval"] == "month"

    @pytest.mark.asyncio
    async def test_get_my_insights(self, client):
        """Gets coaching insights."""
        mock_service = AsyncMock()
        mock_insight = MagicMock()
        mock_insight.category = "conversion"
        mock_insight.title = "Improve follow-up timing"
        mock_insight.description = "Follow up within 1 hour for better results"
        mock_insight.actionable_recommendation = "Set up auto-reminders"
        mock_insight.priority = 1
        mock_service.get_coaching_insights.return_value = [mock_insight]

        with patch(
            "api.routers.agent_analytics.AgentPerformanceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/agent-analytics/me/insights")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["insights"]) == 1
        assert data["insights"][0]["category"] == "conversion"

    @pytest.mark.asyncio
    async def test_get_my_goals(self, client):
        """Gets goal progress."""
        mock_service = AsyncMock()
        mock_service.get_goal_progress.return_value = [
            {
                "id": "goal-001",
                "goal_type": "deals",
                "target_value": 20,
                "current_value": 15,
                "progress_percent": 75.0,
                "period_type": "quarterly",
                "period_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "period_end": datetime(2025, 3, 31, tzinfo=timezone.utc),
                "is_achieved": False,
                "days_remaining": 45,
            }
        ]

        with patch(
            "api.routers.agent_analytics.AgentPerformanceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/agent-analytics/me/goals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["goals"]) == 1
        assert data["goals"][0]["progress_percent"] == 75.0
