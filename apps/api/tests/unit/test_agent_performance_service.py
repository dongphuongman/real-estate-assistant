"""Unit tests for AgentPerformanceService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.agent_performance import (
    AgentMetrics,
    AgentPerformanceService,
    PerformanceTrend,
    TeamComparison,
)


def _mock_scalar_result(value):
    """Create a mock DB result that returns a scalar value."""
    result = MagicMock()
    result.scalar.return_value = value
    result.fetchone.return_value = None
    result.fetchall.return_value = []
    result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    return result


def _mock_row_result(rows):
    """Create a mock DB result that returns fetched rows."""
    result = MagicMock()
    result.scalar.return_value = 0
    result.fetchone.return_value = rows[0] if rows else None
    result.fetchall.return_value = rows
    result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    return result


def _make_session(query_results=None):
    """Create a mock AsyncSession that returns preset results per query.

    Args:
        query_results: list of result objects, returned in order for each execute() call.
    """
    session = AsyncMock(spec=AsyncSession)
    if query_results:
        session.execute.side_effect = query_results
    else:
        session.execute.return_value = _mock_scalar_result(0)
    return session


class TestGetAgentMetrics:
    """Tests for get_agent_metrics method."""

    @pytest.mark.asyncio
    async def test_returns_default_metrics_with_no_data(self):
        """Returns AgentMetrics with default/zero values when agent has no data."""
        session = _make_session()
        # All scalar queries return 0
        session.execute.return_value = _mock_scalar_result(0)

        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert isinstance(metrics, AgentMetrics)
        assert metrics.total_leads == 0
        assert metrics.total_deals == 0
        assert metrics.closed_deals == 0

    @pytest.mark.asyncio
    async def test_uses_default_period_when_none(self):
        """Defaults to last 30 days when no period specified."""
        session = _make_session()
        session.execute.return_value = _mock_scalar_result(0)

        service = AgentPerformanceService(session)
        await service.get_agent_metrics("agent-001")

        # Verify session.execute was called (multiple queries for sub-metrics)
        assert session.execute.call_count > 0

    @pytest.mark.asyncio
    async def test_calculates_lead_metrics(self):
        """Calculates total_leads, active_leads, new_leads_week, high_value_leads."""
        # Order of scalar queries in _calculate_lead_metrics:
        # 1. total_leads, 2. active_leads, 3. new_leads_week, 4. high_value_leads, 5. avg_score
        results = [
            _mock_scalar_result(20),  # total leads
            _mock_scalar_result(8),  # active leads
            _mock_scalar_result(3),  # new leads week
            _mock_scalar_result(5),  # high value leads
            _mock_scalar_result(65.5),  # avg lead score
        ]
        # All remaining queries return 0
        results.extend([_mock_scalar_result(0)] * 50)

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert metrics.total_leads == 20
        assert metrics.active_leads == 8
        assert metrics.new_leads_week == 3
        assert metrics.high_value_leads == 5
        assert metrics.avg_lead_score == 65.5

    @pytest.mark.asyncio
    async def test_calculates_deal_metrics(self):
        """Calculates total_deals, active_deals, closed_deals, fell_through_deals."""
        # 5 lead queries, then deal queries
        results = [
            _mock_scalar_result(0),  # total leads
            _mock_scalar_result(0),  # active leads
            _mock_scalar_result(0),  # new leads week
            _mock_scalar_result(0),  # high value leads
            _mock_scalar_result(0),  # avg score
            _mock_scalar_result(10),  # total deals
            _mock_scalar_result(3),  # active deals
            _mock_scalar_result(5),  # closed deals
            _mock_scalar_result(2),  # fell through
        ]
        results.extend([_mock_scalar_result(0)] * 50)

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert metrics.total_deals == 10
        assert metrics.active_deals == 3
        assert metrics.closed_deals == 5
        assert metrics.fell_through_deals == 2


class TestGetTeamComparison:
    """Tests for get_team_comparison method."""

    @pytest.mark.asyncio
    async def test_returns_comparison_with_no_agents(self):
        """Returns empty comparison when no agents found."""
        session = _make_session()
        # Agent name query returns None
        agent_result = MagicMock()
        agent_result.fetchone.return_value = None
        session.execute.return_value = agent_result

        # _get_all_agents_stats returns empty
        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=[]):
            comparison = await service.get_team_comparison("agent-001")

        assert isinstance(comparison, TeamComparison)
        assert comparison.agent_id == "agent-001"
        assert comparison.total_agents == 0

    @pytest.mark.asyncio
    async def test_ranks_agent_by_deals(self):
        """Correctly ranks agents by deal count."""
        session = _make_session()

        # Agent name query
        agent_result = MagicMock()
        agent_row = MagicMock()
        agent_row.full_name = "Agent One"
        agent_result.fetchone.return_value = agent_row

        stats = [
            {
                "agent_id": "agent-001",
                "deals": 10,
                "revenue": 500000,
                "conversion_rate": 30.0,
                "avg_time_to_close": 20.0,
            },
            {
                "agent_id": "agent-002",
                "deals": 5,
                "revenue": 200000,
                "conversion_rate": 15.0,
                "avg_time_to_close": 30.0,
            },
            {
                "agent_id": "agent-003",
                "deals": 15,
                "revenue": 800000,
                "conversion_rate": 40.0,
                "avg_time_to_close": 15.0,
            },
        ]

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=stats):
            # Need to also mock the agent name query
            session.execute.return_value = agent_result
            comparison = await service.get_team_comparison("agent-001")

        assert comparison.total_agents == 3
        assert (
            comparison.rank_by_deals == 2
        )  # 3rd place: agent-003(15) > agent-001(10) > agent-002(5)
        assert comparison.team_avg_deals == 10.0

    @pytest.mark.asyncio
    async def test_calculates_vs_average_percentages(self):
        """Calculates percentage above/below team average."""
        session = _make_session()

        agent_result = MagicMock()
        agent_row = MagicMock()
        agent_row.full_name = "Top Agent"
        agent_result.fetchone.return_value = agent_row

        stats = [
            {
                "agent_id": "agent-001",
                "deals": 12,
                "revenue": 600000,
                "conversion_rate": 40.0,
                "avg_time_to_close": 20.0,
            },
            {
                "agent_id": "agent-002",
                "deals": 4,
                "revenue": 200000,
                "conversion_rate": 10.0,
                "avg_time_to_close": 40.0,
            },
        ]

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=stats):
            session.execute.return_value = agent_result
            comparison = await service.get_team_comparison("agent-001")

        # avg deals = 8.0, agent has 12 -> (12-8)/8 * 100 = 50.0%
        assert comparison.deals_vs_avg_percent == 50.0


class TestGetPerformanceTrends:
    """Tests for get_performance_trends method."""

    @pytest.mark.asyncio
    async def test_returns_trend_data_points(self):
        """Returns list of PerformanceTrend for requested periods."""
        session = _make_session()

        # Each period has 2 queries (leads + deals)
        # For 3 periods = 6 execute calls
        results = []
        for _ in range(3):
            # Leads query
            results.append(_mock_scalar_result(5))
            # Deals query
            deal_row = MagicMock()
            deal_row.count = 2
            deal_row.value = 100000
            results.append(_mock_row_result([deal_row]))

        session.execute.side_effect = results

        service = AgentPerformanceService(session)
        trends = await service.get_performance_trends("agent-001", interval="month", periods=3)

        assert len(trends) == 3
        assert all(isinstance(t, PerformanceTrend) for t in trends)
        # Verify ordering: oldest first
        assert trends[0].period_start < trends[1].period_start

    @pytest.mark.asyncio
    async def test_calculates_conversion_rate(self):
        """Calculates conversion rate from leads and deals."""
        session = _make_session()

        results = []
        for _ in range(1):
            results.append(_mock_scalar_result(10))  # 10 leads
            deal_row = MagicMock()
            deal_row.count = 3  # 3 deals
            deal_row.value = 300000
            results.append(_mock_row_result([deal_row]))

        session.execute.side_effect = results

        service = AgentPerformanceService(session)
        trends = await service.get_performance_trends("agent-001", interval="month", periods=1)

        assert trends[0].conversion_rate == 30.0  # 3/10 * 100

    @pytest.mark.asyncio
    async def test_handles_zero_leads(self):
        """Handles case where there are no leads (avoids division by zero)."""
        session = _make_session()

        results = []
        results.append(_mock_scalar_result(0))  # 0 leads
        deal_row = MagicMock()
        deal_row.count = 0
        deal_row.value = 0
        results.append(_mock_row_result([deal_row]))

        session.execute.side_effect = results

        service = AgentPerformanceService(session)
        trends = await service.get_performance_trends("agent-001", interval="month", periods=1)

        # With the default interval 'month' (not 'intervals')
        assert len(trends) == 1


class TestGetCoachingInsights:
    """Tests for get_coaching_insights method."""

    @pytest.mark.asyncio
    async def test_returns_strength_for_high_deal_count(self):
        """Generates 'Consistent Deal Closer' insight for >5 closed deals."""
        session = _make_session()
        session.execute.return_value = _mock_scalar_result(0)

        service = AgentPerformanceService(session)
        metrics = AgentMetrics(closed_deals=8, avg_lead_score=50)

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any(i.title == "Consistent Deal Closer" for i in insights)
        assert any(i.category == "strength" for i in insights)

    @pytest.mark.asyncio
    async def test_returns_improvement_for_slow_closing(self):
        """Generates 'Reduce Time to Close' insight when avg > 60 days."""
        session = _make_session()
        session.execute.return_value = _mock_scalar_result(0)

        service = AgentPerformanceService(session)
        metrics = AgentMetrics(
            avg_time_to_close_days=75,
            overall_conversion_rate=20,
            total_leads=5,
        )

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any(i.title == "Reduce Time to Close" for i in insights)

    @pytest.mark.asyncio
    async def test_returns_improvement_for_low_conversion(self):
        """Generates 'Improve Conversion Rate' insight when <10% and many leads."""
        session = _make_session()
        session.execute.return_value = _mock_scalar_result(0)

        service = AgentPerformanceService(session)
        metrics = AgentMetrics(
            overall_conversion_rate=5.0,
            total_leads=50,
        )

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any("Conversion Rate" in i.title for i in insights)

    @pytest.mark.asyncio
    async def test_returns_opportunity_for_high_value_leads(self):
        """Generates 'High-Value Leads Ready' insight when >30% of active are high value."""
        session = _make_session()
        session.execute.return_value = _mock_scalar_result(0)

        service = AgentPerformanceService(session)
        metrics = AgentMetrics(
            high_value_leads=5,
            active_leads=10,
        )

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any("High-Value" in i.title for i in insights)

    @pytest.mark.asyncio
    async def test_sorts_by_priority(self):
        """Insights are sorted by priority (1 = highest)."""
        session = _make_session()
        session.execute.return_value = _mock_scalar_result(0)

        service = AgentPerformanceService(session)
        metrics = AgentMetrics(
            closed_deals=8,
            avg_lead_score=50,
            avg_time_to_close_days=75,
            fell_through_deals=10,
            overall_conversion_rate=5.0,
            total_leads=50,
        )

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        if len(insights) > 1:
            priorities = [i.priority for i in insights]
            assert priorities == sorted(priorities)


class TestGetTopPerformers:
    """Tests for get_top_performers method."""

    @pytest.mark.asyncio
    async def test_returns_sorted_performers(self):
        """Returns agents sorted by requested metric."""
        session = _make_session()

        stats = [
            {
                "agent_id": "a1",
                "deals": 10,
                "revenue": 500000,
                "conversion_rate": 25.0,
                "avg_time_to_close": 20.0,
            },
            {
                "agent_id": "a2",
                "deals": 5,
                "revenue": 200000,
                "conversion_rate": 10.0,
                "avg_time_to_close": 30.0,
            },
        ]

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=stats):
            # Mock agent name lookups
            agent_row = MagicMock()
            agent_row.full_name = "Agent"
            agent_row.email = "agent@example.com"
            result = MagicMock()
            result.fetchone.return_value = agent_row
            session.execute.return_value = result

            performers = await service.get_top_performers(metric="deals", limit=5)

        assert len(performers) == 2
        assert performers[0]["rank"] == 1
        assert performers[0]["metric_value"] == 10

    @pytest.mark.asyncio
    async def test_sorts_by_revenue(self):
        """Correctly sorts by revenue metric."""
        session = _make_session()

        stats = [
            {
                "agent_id": "a1",
                "deals": 5,
                "revenue": 500000,
                "conversion_rate": 25.0,
                "avg_time_to_close": 20.0,
            },
            {
                "agent_id": "a2",
                "deals": 10,
                "revenue": 200000,
                "conversion_rate": 10.0,
                "avg_time_to_close": 30.0,
            },
        ]

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=stats):
            agent_row = MagicMock()
            agent_row.full_name = "Agent"
            agent_row.email = "agent@example.com"
            result = MagicMock()
            result.fetchone.return_value = agent_row
            session.execute.return_value = result

            performers = await service.get_top_performers(metric="revenue")

        assert performers[0]["metric_value"] == 500000

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        """Returns at most 'limit' results."""
        session = _make_session()

        stats = [
            {
                "agent_id": f"a{i}",
                "deals": 10 - i,
                "revenue": 100000,
                "conversion_rate": 20.0,
                "avg_time_to_close": 20.0,
            }
            for i in range(5)
        ]

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=stats):
            agent_row = MagicMock()
            agent_row.full_name = "Agent"
            agent_row.email = "a@b.c"
            result = MagicMock()
            result.fetchone.return_value = agent_row
            session.execute.return_value = result

            performers = await service.get_top_performers(metric="deals", limit=3)

        assert len(performers) == 3


class TestGetAgentsNeedingSupport:
    """Tests for get_agents_needing_support method."""

    @pytest.mark.asyncio
    async def test_flags_agent_with_no_deals(self):
        """Flags agents who have no closed deals in the period."""
        session = _make_session()

        # First query: all agents
        agent_row = MagicMock()
        agent_row.id = "agent-001"
        agent_row.full_name = "Struggling Agent"
        agent_row.email = "struggle@example.com"

        agents_result = MagicMock()
        agents_result.fetchall.return_value = [agent_row]

        # Subsequent queries for this agent
        no_deals_result = _mock_scalar_result(0)  # closed count
        last_deal_result = _mock_scalar_result(None)  # last deal date
        leads_result = _mock_scalar_result(5)  # active leads
        total_closed_result = _mock_scalar_result(0)  # total closed ever

        session.execute.side_effect = [
            agents_result,
            no_deals_result,
            last_deal_result,
            leads_result,
            total_closed_result,
        ]

        service = AgentPerformanceService(session)
        result = await service.get_agents_needing_support(threshold_days=30)

        assert len(result) == 1
        assert result[0]["agent_id"] == "agent-001"
        assert result[0]["days_without_deal"] == 999
        assert len(result[0]["suggested_actions"]) > 0

    @pytest.mark.asyncio
    async def test_does_not_flag_performing_agents(self):
        """Does not flag agents with closed deals in the period."""
        session = _make_session()

        agent_row = MagicMock()
        agent_row.id = "agent-002"
        agent_row.full_name = "Good Agent"
        agent_row.email = "good@example.com"

        agents_result = MagicMock()
        agents_result.fetchall.return_value = [agent_row]

        has_deals_result = _mock_scalar_result(3)  # 3 closed deals

        session.execute.side_effect = [agents_result, has_deals_result]

        service = AgentPerformanceService(session)
        result = await service.get_agents_needing_support()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_sorts_by_days_without_deal(self):
        """Sorts results with most days without deal first."""
        session = _make_session()

        agent1 = MagicMock()
        agent1.id = "a1"
        agent1.full_name = "Agent 1"
        agent1.email = "a1@example.com"

        agent2 = MagicMock()
        agent2.id = "a2"
        agent2.full_name = "Agent 2"
        agent2.email = "a2@example.com"

        agents_result = MagicMock()
        agents_result.fetchall.return_value = [agent1, agent2]

        # agent1: no deals, never closed
        # agent2: no deals, last deal 60 days ago
        last_deal_date = datetime.now(UTC) - timedelta(days=60)

        session.execute.side_effect = [
            agents_result,
            _mock_scalar_result(0),  # a1: closed_deals in period
            _mock_scalar_result(None),  # a1: last_deal_at (None = never closed)
            _mock_scalar_result(0),  # a1: active leads (0 → skip total_closed query)
            _mock_scalar_result(0),  # a2: closed_deals in period
            _mock_scalar_result(last_deal_date),  # a2: last_deal_at
            _mock_scalar_result(0),  # a2: active leads (0 → skip total_closed query)
        ]

        service = AgentPerformanceService(session)
        result = await service.get_agents_needing_support()

        assert len(result) == 2
        # a1 (never closed, 999 days) should come before a2 (60 days)
        assert result[0]["agent_id"] == "a1"
        assert result[0]["days_without_deal"] >= result[1]["days_without_deal"]


class TestGetGoalProgress:
    """Tests for get_goal_progress method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_active_goals(self):
        """Returns empty list when agent has no active goals."""
        session = _make_session()
        result = MagicMock()
        result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        session.execute.return_value = result

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert progress == []

    @pytest.mark.asyncio
    async def test_calculates_goal_progress(self):
        """Calculates progress percentage for active goals."""
        session = _make_session()

        goal = MagicMock()
        goal.id = "goal-001"
        goal.goal_type = "deals"
        goal.target_value = 10
        goal.period_type = "monthly"
        goal.period_start = datetime.now(UTC) - timedelta(days=15)
        goal.period_end = datetime.now(UTC) + timedelta(days=15)
        goal.is_active = True

        goals_result = MagicMock()
        goals_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[goal]))

        # _calculate_goal_current_value returns 7
        current_value_result = _mock_scalar_result(7)

        session.execute.side_effect = [goals_result, current_value_result]

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert len(progress) == 1
        assert progress[0]["current_value"] == 7.0
        assert progress[0]["target_value"] == 10
        assert progress[0]["progress_percent"] == 70.0
        assert progress[0]["is_achieved"] is False

    @pytest.mark.asyncio
    async def test_marks_achieved_when_100_percent(self):
        """Sets is_achieved when progress >= 100%."""
        session = _make_session()

        goal = MagicMock()
        goal.id = "goal-002"
        goal.goal_type = "leads"
        goal.target_value = 5
        goal.period_type = "weekly"
        goal.period_start = datetime.now(UTC) - timedelta(days=3)
        goal.period_end = datetime.now(UTC) + timedelta(days=4)
        goal.is_active = True

        goals_result = MagicMock()
        goals_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[goal]))
        current_value_result = _mock_scalar_result(6)  # exceeds target

        session.execute.side_effect = [goals_result, current_value_result]

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert progress[0]["progress_percent"] == 100.0  # min(100, 120)
        assert progress[0]["is_achieved"] is True

    @pytest.mark.asyncio
    async def test_handles_zero_target(self):
        """Handles goal with zero target_value gracefully."""
        session = _make_session()

        goal = MagicMock()
        goal.id = "goal-003"
        goal.goal_type = "revenue"
        goal.target_value = 0
        goal.period_type = "monthly"
        goal.period_start = datetime.now(UTC) - timedelta(days=15)
        goal.period_end = datetime.now(UTC) + timedelta(days=15)
        goal.is_active = True

        goals_result = MagicMock()
        goals_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[goal]))
        current_value_result = _mock_scalar_result(0)

        session.execute.side_effect = [goals_result, current_value_result]

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert progress[0]["progress_percent"] == 0.0
