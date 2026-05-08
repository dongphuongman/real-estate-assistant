"""Tests for agent_analytics router endpoints.

Covers:
- GET /agent-analytics/me — agent metrics
- GET /agent-analytics/me/comparison — team comparison
- GET /agent-analytics/me/trends — performance trends
- GET /agent-analytics/me/insights — coaching insights
- GET /agent-analytics/me/goals — goal progress
- GET /agent-analytics/top-performers — admin top performers
- GET /agent-analytics/needs-support — admin agents needing support
- POST /agent-analytics/deals — create deal
- GET /agent-analytics/deals — list deals
- GET /agent-analytics/deals/{deal_id} — get deal
- PATCH /agent-analytics/deals/{deal_id} — update deal
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import agent_analytics
from db.database import get_db as get_db_dep

# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------

_test_app = FastAPI()
_test_app.include_router(agent_analytics.router)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_user(role="agent", user_id="agent-1", is_active=True):
    """Create a mock User with configurable role and id."""
    user = MagicMock()
    user.id = user_id
    user.role = role
    user.email = f"{user_id}@test.com"
    user.is_active = is_active
    return user


def _make_deal(
    deal_id="deal-1",
    agent_id="agent-1",
    lead_id="lead-1",
    status="offer_submitted",
    deal_type="sale",
    deal_value=300000.0,
):
    """Create a mock Deal object mimicking the ORM model."""
    deal = MagicMock()
    deal.id = deal_id
    deal.lead_id = lead_id
    deal.agent_id = agent_id
    deal.property_id = "prop-1"
    deal.deal_type = deal_type
    deal.deal_value = deal_value
    deal.currency = "EUR"
    deal.status = status
    deal.property_type = "apartment"
    deal.property_city = "Krakow"
    deal.property_district = "Centrum"
    deal.offer_submitted_at = datetime(2025, 1, 1, tzinfo=UTC)
    deal.offer_accepted_at = None
    deal.contract_signed_at = None
    deal.closed_at = None
    deal.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    return deal


# ---------------------------------------------------------------------------
# Fixtures — auth overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_agent():
    """Override auth to return an agent user."""
    user = _make_user(role="agent", user_id="agent-1")

    async def _override():
        return user

    _test_app.dependency_overrides[get_current_active_user] = _override
    yield user
    _test_app.dependency_overrides.clear()


@pytest.fixture
def auth_admin():
    """Override auth to return an admin user."""
    user = _make_user(role="admin", user_id="admin-1")

    async def _override():
        return user

    _test_app.dependency_overrides[get_current_active_user] = _override
    yield user
    _test_app.dependency_overrides.clear()


@pytest.fixture
def auth_superuser():
    """Override auth to return a superuser."""
    user = _make_user(role="superuser", user_id="super-1")

    async def _override():
        return user

    _test_app.dependency_overrides[get_current_active_user] = _override
    yield user
    _test_app.dependency_overrides.clear()


@pytest.fixture
def auth_unauthorized():
    """Override auth to return a plain user (no analytics access)."""
    user = _make_user(role="user", user_id="user-1")

    async def _override():
        return user

    _test_app.dependency_overrides[get_current_active_user] = _override
    yield user
    _test_app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Provide a mock async session and override the get_db dependency."""
    mock_session = AsyncMock()

    async def _get_db():
        yield mock_session

    _test_app.dependency_overrides[get_db_dep] = _get_db
    yield mock_session
    _test_app.dependency_overrides.pop(get_db_dep, None)


# ---------------------------------------------------------------------------
# GET /agent-analytics/me
# ---------------------------------------------------------------------------


class TestGetMyMetrics:
    """Tests for GET /agent-analytics/me."""

    @pytest.mark.asyncio
    async def test_agent_can_get_metrics(self, auth_agent, mock_db):
        metrics = MagicMock()
        metrics.total_leads = 20
        metrics.active_leads = 10
        metrics.new_leads_week = 5
        metrics.high_value_leads = 3
        metrics.total_deals = 8
        metrics.active_deals = 4
        metrics.closed_deals = 3
        metrics.fell_through_deals = 1
        metrics.lead_to_qualified_rate = 40.0
        metrics.qualified_to_deal_rate = 30.0
        metrics.overall_conversion_rate = 15.0
        metrics.avg_time_to_first_contact_hours = 2.5
        metrics.avg_time_to_qualify_days = 5.0
        metrics.avg_time_to_close_days = 30.0
        metrics.total_deal_value = 900000.0
        metrics.avg_deal_value = 300000.0
        metrics.total_commission = 27000.0
        metrics.pending_commission = 9000.0
        metrics.top_property_types = [{"type": "apartment", "count": 3, "percentage": 100.0}]
        metrics.top_locations = [{"location": "Krakow", "count": 3, "percentage": 100.0}]
        metrics.avg_lead_score = 65.0
        metrics.deals_change_percent = 10.0
        metrics.revenue_change_percent = 5.0

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_agent_metrics = AsyncMock(return_value=metrics)
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me")

        assert response.status_code == 200
        data = response.json()
        assert data["total_leads"] == 20
        assert data["active_leads"] == 10
        assert data["closed_deals"] == 3
        assert data["overall_conversion_rate"] == 15.0
        assert data["total_deal_value"] == 900000.0
        assert data["avg_lead_score"] == 65.0
        assert data["deals_change_percent"] == 10.0

    @pytest.mark.asyncio
    async def test_admin_can_get_metrics(self, auth_admin, mock_db):
        metrics = MagicMock()
        metrics.total_leads = 0
        metrics.active_leads = 0
        metrics.new_leads_week = 0
        metrics.high_value_leads = 0
        metrics.total_deals = 0
        metrics.active_deals = 0
        metrics.closed_deals = 0
        metrics.fell_through_deals = 0
        metrics.lead_to_qualified_rate = 0.0
        metrics.qualified_to_deal_rate = 0.0
        metrics.overall_conversion_rate = 0.0
        metrics.avg_time_to_first_contact_hours = None
        metrics.avg_time_to_qualify_days = None
        metrics.avg_time_to_close_days = None
        metrics.total_deal_value = 0.0
        metrics.avg_deal_value = 0.0
        metrics.total_commission = 0.0
        metrics.pending_commission = 0.0
        metrics.top_property_types = []
        metrics.top_locations = []
        metrics.avg_lead_score = 0.0
        metrics.deals_change_percent = None
        metrics.revenue_change_percent = None

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_agent_metrics = AsyncMock(return_value=metrics)
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthorized_role_rejected(self, auth_unauthorized, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/me")

        assert response.status_code == 403
        assert "Only agents and admins" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_metrics_with_date_params(self, auth_agent, mock_db):
        metrics = MagicMock()
        for attr in (
            "total_leads",
            "active_leads",
            "new_leads_week",
            "high_value_leads",
            "total_deals",
            "active_deals",
            "closed_deals",
            "fell_through_deals",
        ):
            setattr(metrics, attr, 0)
        for attr in (
            "lead_to_qualified_rate",
            "qualified_to_deal_rate",
            "overall_conversion_rate",
            "total_deal_value",
            "avg_deal_value",
            "total_commission",
            "pending_commission",
            "avg_lead_score",
        ):
            setattr(metrics, attr, 0.0)
        metrics.avg_time_to_first_contact_hours = None
        metrics.avg_time_to_qualify_days = None
        metrics.avg_time_to_close_days = None
        metrics.top_property_types = []
        metrics.top_locations = []
        metrics.deals_change_percent = None
        metrics.revenue_change_percent = None

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_agent_metrics = AsyncMock(return_value=metrics)
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/agent-analytics/me",
                    params={
                        "period_start": "2025-01-01T00:00:00Z",
                        "period_end": "2025-02-01T00:00:00Z",
                    },
                )

        assert response.status_code == 200
        mock_svc.get_agent_metrics.assert_awaited_once()
        call_kwargs = mock_svc.get_agent_metrics.call_args
        assert call_kwargs.kwargs["period_start"] is not None
        assert call_kwargs.kwargs["period_end"] is not None


# ---------------------------------------------------------------------------
# GET /agent-analytics/me/comparison
# ---------------------------------------------------------------------------


class TestGetTeamComparison:
    """Tests for GET /agent-analytics/me/comparison."""

    @pytest.mark.asyncio
    async def test_agent_can_get_comparison(self, auth_agent, mock_db):
        comparison = MagicMock()
        comparison.agent_id = "agent-1"
        comparison.agent_name = "Test Agent"
        comparison.rank_by_deals = 2
        comparison.rank_by_revenue = 1
        comparison.rank_by_conversion = 3
        comparison.total_agents = 10
        comparison.deals_vs_avg_percent = 15.0
        comparison.revenue_vs_avg_percent = 25.0
        comparison.conversion_vs_avg_percent = -5.0
        comparison.time_to_close_vs_avg_percent = 0.0
        comparison.team_avg_deals = 5.0
        comparison.team_avg_revenue = 200000.0
        comparison.team_avg_conversion = 12.0
        comparison.team_avg_time_to_close_days = 30.0

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_team_comparison = AsyncMock(return_value=comparison)
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me/comparison")

        assert response.status_code == 200
        data = response.json()
        assert data["rank_by_deals"] == 2
        assert data["total_agents"] == 10
        assert data["deals_vs_avg_percent"] == 15.0

    @pytest.mark.asyncio
    async def test_unauthorized_role_rejected(self, auth_unauthorized, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/me/comparison")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /agent-analytics/me/trends
# ---------------------------------------------------------------------------


class TestGetMyTrends:
    """Tests for GET /agent-analytics/me/trends."""

    @pytest.mark.asyncio
    async def test_default_monthly_trends(self, auth_agent, mock_db):
        trend = MagicMock()
        trend.period = "2025-01"
        trend.period_start = datetime(2025, 1, 1, tzinfo=UTC)
        trend.period_end = datetime(2025, 2, 1, tzinfo=UTC)
        trend.leads = 15
        trend.deals_closed = 3
        trend.revenue = 900000.0
        trend.conversion_rate = 20.0
        trend.avg_deal_value = 300000.0

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_performance_trends = AsyncMock(return_value=[trend])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["interval"] == "month"
        assert len(data["trends"]) == 1
        assert data["trends"][0]["period"] == "2025-01"
        assert data["trends"][0]["leads"] == 15

    @pytest.mark.asyncio
    async def test_weekly_interval(self, auth_agent, mock_db):
        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_performance_trends = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/agent-analytics/me/trends",
                    params={"interval": "week", "periods": 4},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["interval"] == "week"
        mock_svc.get_performance_trends.assert_awaited_once_with(
            agent_id="agent-1", interval="week", periods=4
        )

    @pytest.mark.asyncio
    async def test_unauthorized_role_rejected(self, auth_unauthorized, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/me/trends")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /agent-analytics/me/insights
# ---------------------------------------------------------------------------


class TestGetMyInsights:
    """Tests for GET /agent-analytics/me/insights."""

    @pytest.mark.asyncio
    async def test_returns_coaching_insights(self, auth_agent, mock_db):
        insight = MagicMock()
        insight.category = "strength"
        insight.title = "Consistent Deal Closer"
        insight.description = "You've closed 6 deals."
        insight.actionable_recommendation = "Continue your current approach."
        insight.priority = 3

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_coaching_insights = AsyncMock(return_value=[insight])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me/insights")

        assert response.status_code == 200
        data = response.json()
        assert len(data["insights"]) == 1
        assert data["insights"][0]["category"] == "strength"
        assert data["insights"][0]["priority"] == 3

    @pytest.mark.asyncio
    async def test_empty_insights(self, auth_agent, mock_db):
        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_coaching_insights = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me/insights")

        assert response.status_code == 200
        assert response.json()["insights"] == []

    @pytest.mark.asyncio
    async def test_unauthorized_role_rejected(self, auth_unauthorized, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/me/insights")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /agent-analytics/me/goals
# ---------------------------------------------------------------------------


class TestGetMyGoals:
    """Tests for GET /agent-analytics/me/goals."""

    @pytest.mark.asyncio
    async def test_returns_goal_progress(self, auth_agent, mock_db):
        goal = {
            "id": "goal-1",
            "goal_type": "deals",
            "target_value": 10.0,
            "current_value": 6.0,
            "progress_percent": 60.0,
            "period_type": "monthly",
            "period_start": "2025-01-01T00:00:00Z",
            "period_end": "2025-01-31T00:00:00Z",
            "is_achieved": False,
            "days_remaining": 15,
        }

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_goal_progress = AsyncMock(return_value=[goal])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me/goals")

        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 1
        assert data["goals"][0]["goal_type"] == "deals"
        assert data["goals"][0]["progress_percent"] == 60.0
        assert data["goals"][0]["is_achieved"] is False

    @pytest.mark.asyncio
    async def test_empty_goals(self, auth_agent, mock_db):
        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_goal_progress = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/me/goals")

        assert response.status_code == 200
        assert response.json()["goals"] == []

    @pytest.mark.asyncio
    async def test_unauthorized_role_rejected(self, auth_unauthorized, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/me/goals")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /agent-analytics/top-performers (admin only)
# ---------------------------------------------------------------------------


class TestGetTopPerformers:
    """Tests for GET /agent-analytics/top-performers."""

    @pytest.mark.asyncio
    async def test_admin_can_get_top_performers(self, auth_admin, mock_db):
        performer = {
            "agent_id": "agent-1",
            "agent_name": "Top Agent",
            "agent_email": "top@test.com",
            "metric_value": 15.0,
            "rank": 1,
        }

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_top_performers = AsyncMock(return_value=[performer])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/top-performers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["performers"]) == 1
        assert data["performers"][0]["rank"] == 1
        assert data["metric"] == "deals"
        assert data["period_days"] == 30

    @pytest.mark.asyncio
    async def test_superuser_can_access(self, auth_superuser, mock_db):
        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_top_performers = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/top-performers")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_revenue_metric(self, auth_admin, mock_db):
        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_top_performers = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/agent-analytics/top-performers",
                    params={"metric": "revenue", "limit": 5, "period_days": 90},
                )

        assert response.status_code == 200
        mock_svc.get_top_performers.assert_awaited_once_with(
            metric="revenue", limit=5, period_days=90
        )

    @pytest.mark.asyncio
    async def test_agent_forbidden(self, auth_agent, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/top-performers")

        assert response.status_code == 403
        assert "Only admins" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /agent-analytics/needs-support (admin only)
# ---------------------------------------------------------------------------


class TestGetAgentsNeedingSupport:
    """Tests for GET /agent-analytics/needs-support."""

    @pytest.mark.asyncio
    async def test_admin_can_get_agents_needing_support(self, auth_admin, mock_db):
        agent_data = {
            "agent_id": "agent-2",
            "agent_name": "Struggling Agent",
            "agent_email": "struggle@test.com",
            "days_without_deal": 45,
            "total_leads": 12,
            "conversion_rate": 0.0,
            "last_deal_at": None,
            "suggested_actions": ["Assign leads to this agent"],
        }

        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_agents_needing_support = AsyncMock(return_value=[agent_data])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/agent-analytics/needs-support")

        assert response.status_code == 200
        data = response.json()
        assert len(data["agents"]) == 1
        assert data["agents"][0]["days_without_deal"] == 45
        assert data["threshold_days"] == 30

    @pytest.mark.asyncio
    async def test_custom_threshold(self, auth_admin, mock_db):
        with patch("api.routers.agent_analytics.AgentPerformanceService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.get_agents_needing_support = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/agent-analytics/needs-support",
                    params={"threshold_days": 60},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["threshold_days"] == 60
        mock_svc.get_agents_needing_support.assert_awaited_once_with(threshold_days=60)

    @pytest.mark.asyncio
    async def test_agent_forbidden(self, auth_agent, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/needs-support")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /agent-analytics/deals
# ---------------------------------------------------------------------------


class TestCreateDeal:
    """Tests for POST /agent-analytics/deals.

    The create_deal endpoint instantiates Deal(...) directly.
    Since SQLAlchemy column defaults are DB-level (not Python-level),
    we must patch the Deal class to return a fully-populated mock.
    """

    @pytest.mark.asyncio
    async def test_create_deal_success(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")

        with patch("api.routers.agent_analytics.Deal", return_value=deal):
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.refresh = AsyncMock()

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/agent-analytics/deals",
                    json={
                        "lead_id": "lead-1",
                        "deal_type": "sale",
                        "deal_value": 300000.0,
                        "property_type": "apartment",
                        "property_city": "Krakow",
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert data["lead_id"] == "lead-1"
        assert data["deal_type"] == "sale"
        assert data["deal_value"] == 300000.0
        assert data["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_create_deal_rent(self, auth_agent, mock_db):
        deal = _make_deal(deal_type="rent", deal_value=1500.0, agent_id="agent-1")

        with patch("api.routers.agent_analytics.Deal", return_value=deal):
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.refresh = AsyncMock()

            transport = ASGITransport(app=_test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/agent-analytics/deals",
                    json={
                        "lead_id": "lead-2",
                        "deal_type": "rent",
                        "deal_value": 1500.0,
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert data["deal_type"] == "rent"
        assert data["deal_value"] == 1500.0

    @pytest.mark.asyncio
    async def test_unauthorized_role_rejected(self, auth_unauthorized, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agent-analytics/deals",
                json={
                    "lead_id": "lead-1",
                    "deal_type": "sale",
                    "deal_value": 100000.0,
                },
            )

        assert response.status_code == 403
        assert "Only agents" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_payload_rejected(self, auth_agent, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agent-analytics/deals",
                json={"deal_type": "sale"},  # missing required lead_id, deal_value
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_deal_value_rejected(self, auth_agent, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/agent-analytics/deals",
                json={
                    "lead_id": "lead-1",
                    "deal_type": "sale",
                    "deal_value": -500.0,
                },
            )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /agent-analytics/deals
# ---------------------------------------------------------------------------


class TestListMyDeals:
    """Tests for GET /agent-analytics/deals."""

    @pytest.mark.asyncio
    async def test_list_deals_success(self, auth_agent, mock_db):
        deal = _make_deal()

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        # Mock select query
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [deal]
        select_result = MagicMock()
        select_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(side_effect=[count_result, select_result])

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_deals_with_status_filter(self, auth_agent, mock_db):
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        select_result = MagicMock()
        select_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(side_effect=[count_result, select_result])

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/agent-analytics/deals",
                params={"status": "closed"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_deals_pagination(self, auth_agent, mock_db):
        count_result = MagicMock()
        count_result.scalar.return_value = 50
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        select_result = MagicMock()
        select_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(side_effect=[count_result, select_result])

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/agent-analytics/deals",
                params={"page": 3, "page_size": 10},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 50
        assert data["page"] == 3
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_deals_empty(self, auth_agent, mock_db):
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        select_result = MagicMock()
        select_result.scalars.return_value = scalars_mock

        mock_db.execute = AsyncMock(side_effect=[count_result, select_result])

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals")

        assert response.status_code == 200
        assert response.json()["items"] == []

    @pytest.mark.asyncio
    async def test_unauthorized_role_rejected(self, auth_unauthorized, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /agent-analytics/deals/{deal_id}
# ---------------------------------------------------------------------------


class TestGetDeal:
    """Tests for GET /agent-analytics/deals/{deal_id}."""

    @pytest.mark.asyncio
    async def test_get_own_deal(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")
        result = MagicMock()
        result.scalar_one_or_none.return_value = deal
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals/deal-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "deal-1"
        assert data["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_admin_can_get_any_deal(self, auth_admin, mock_db):
        deal = _make_deal(agent_id="agent-2")
        result = MagicMock()
        result.scalar_one_or_none.return_value = deal
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals/deal-1")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_deal_not_found(self, auth_agent, mock_db):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals/nonexistent")

        assert response.status_code == 404
        assert "Deal not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_agent_cannot_view_others_deal(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-999")
        result = MagicMock()
        result.scalar_one_or_none.return_value = deal
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals/deal-1")

        assert response.status_code == 403
        assert "your own deals" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_superuser_can_get_any_deal(self, auth_superuser, mock_db):
        deal = _make_deal(agent_id="other-agent")
        result = MagicMock()
        result.scalar_one_or_none.return_value = deal
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals/deal-1")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /agent-analytics/deals/{deal_id}
# ---------------------------------------------------------------------------


class TestUpdateDeal:
    """Tests for PATCH /agent-analytics/deals/{deal_id}."""

    @pytest.mark.asyncio
    async def test_update_deal_notes(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal

        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/deal-1",
                json={"notes": "Updated notes"},
            )

        assert response.status_code == 200
        assert deal.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_deal_status_to_offer_accepted(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")
        deal.offer_accepted_at = None
        # Use naive datetime to match what datetime.now() produces in the endpoint
        deal.offer_submitted_at = datetime(2025, 1, 1)

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal

        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/deal-1",
                json={"status": "offer_accepted"},
            )

        assert response.status_code == 200
        assert deal.offer_accepted_at is not None

    @pytest.mark.asyncio
    async def test_update_deal_status_to_contract_signed(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")
        deal.contract_signed_at = None
        deal.offer_submitted_at = datetime(2025, 1, 1)

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal

        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/deal-1",
                json={"status": "contract_signed"},
            )

        assert response.status_code == 200
        assert deal.contract_signed_at is not None

    @pytest.mark.asyncio
    async def test_update_deal_status_to_closed(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")
        deal.closed_at = None
        # Use naive datetime to match what datetime.now() produces in the endpoint
        deal.offer_submitted_at = datetime(2025, 1, 1)

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal

        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/deal-1",
                json={"status": "closed"},
            )

        assert response.status_code == 200
        assert deal.closed_at is not None

    @pytest.mark.asyncio
    async def test_deal_not_found(self, auth_agent, mock_db):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/nonexistent",
                json={"status": "closed"},
            )

        assert response.status_code == 404
        assert "Deal not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_agent_cannot_update_others_deal(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-999")

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/deal-1",
                json={"notes": "hacked"},
            )

        assert response.status_code == 403
        assert "your own deals" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_can_update_any_deal(self, auth_admin, mock_db):
        deal = _make_deal(agent_id="agent-2")

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal

        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/deal-1",
                json={"deal_value": 500000.0},
            )

        assert response.status_code == 200
        assert deal.deal_value == 500000.0

    @pytest.mark.asyncio
    async def test_update_deal_value(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal

        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/agent-analytics/deals/deal-1",
                json={"deal_value": 350000.0},
            )

        assert response.status_code == 200
        assert deal.deal_value == 350000.0


# ---------------------------------------------------------------------------
# _deal_to_response helper (indirect via deal with closed_at set)
# ---------------------------------------------------------------------------


class TestDealToResponseHelper:
    """Tests that _deal_to_response correctly computes days_to_close."""

    @pytest.mark.asyncio
    async def test_days_to_close_calculated(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")
        deal.closed_at = datetime(2025, 2, 1, tzinfo=UTC)
        deal.offer_submitted_at = datetime(2025, 1, 1, tzinfo=UTC)

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals/deal-1")

        assert response.status_code == 200
        data = response.json()
        assert data["days_to_close"] == 31

    @pytest.mark.asyncio
    async def test_days_to_close_none_when_not_closed(self, auth_agent, mock_db):
        deal = _make_deal(agent_id="agent-1")
        deal.closed_at = None
        deal.offer_submitted_at = datetime(2025, 1, 1, tzinfo=UTC)

        result = MagicMock()
        result.scalar_one_or_none.return_value = deal
        mock_db.execute = AsyncMock(return_value=result)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agent-analytics/deals/deal-1")

        assert response.status_code == 200
        assert response.json()["days_to_close"] is None
