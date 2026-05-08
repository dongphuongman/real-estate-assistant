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

    @pytest.mark.asyncio
    async def test_goal_days_remaining_capped_at_zero(self):
        """Days remaining is max(0, ...) even when period_end is in the past."""
        session = _make_session()

        goal = MagicMock()
        goal.id = "goal-004"
        goal.goal_type = "deals"
        goal.target_value = 10
        goal.period_type = "monthly"
        goal.period_start = datetime.now(UTC) - timedelta(days=45)
        goal.period_end = datetime.now(UTC) - timedelta(days=15)  # already ended
        goal.is_active = True

        goals_result = MagicMock()
        goals_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[goal]))
        current_value_result = _mock_scalar_result(5)

        session.execute.side_effect = [goals_result, current_value_result]

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert progress[0]["days_remaining"] == 0


class TestConversionMetrics:
    """Tests for _calculate_conversion_metrics edge cases."""

    @pytest.mark.asyncio
    async def test_qualified_to_deal_rate(self):
        """Calculates qualified_to_deal_rate when there are qualified leads and closed deals."""
        session = _make_session()

        # Lead queries: total=20, active=0, new=0, high_value=0, avg_score=0
        results = [
            _mock_scalar_result(20),  # total leads
            _mock_scalar_result(0),  # active leads
            _mock_scalar_result(0),  # new leads week
            _mock_scalar_result(0),  # high value leads
            _mock_scalar_result(0),  # avg score
            _mock_scalar_result(0),  # total deals
            _mock_scalar_result(0),  # active deals
            _mock_scalar_result(5),  # closed deals  <-- needed for qualified_to_deal_rate
            _mock_scalar_result(0),  # fell through
            _mock_scalar_result(10),  # qualified count (lead to qualified)
        ]
        # Remaining: time metrics (0), financial metrics (all 0), strengths (0), period comparison (0)
        results.extend([_mock_scalar_result(0)] * 50)

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert metrics.lead_to_qualified_rate == 50.0  # 10/20 * 100
        assert metrics.qualified_to_deal_rate == 50.0  # 5/10 * 100
        assert metrics.overall_conversion_rate == 25.0  # 5/20 * 100

    @pytest.mark.asyncio
    async def test_no_conversion_when_no_closed_deals(self):
        """qualified_to_deal_rate stays 0 when closed_deals is 0."""
        session = _make_session()
        results = [
            _mock_scalar_result(10),  # total leads
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),  # closed deals = 0
            _mock_scalar_result(0),
            _mock_scalar_result(8),  # qualified count > 0
        ]
        results.extend([_mock_scalar_result(0)] * 50)

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert metrics.lead_to_qualified_rate == 80.0  # 8/10 * 100
        assert metrics.qualified_to_deal_rate == 0.0  # no closed deals
        assert metrics.overall_conversion_rate == 0.0


class TestTimeMetrics:
    """Tests for _calculate_time_metrics with actual deal data."""

    @pytest.mark.asyncio
    async def test_avg_time_to_close_with_deals(self):
        """Calculates avg_time_to_close_days from closed deal timestamps."""
        session = _make_session()

        now = datetime.now(UTC)

        # Create mock deal rows with closed_at and offer_submitted_at
        deal1 = MagicMock()
        deal1.closed_at = now
        deal1.offer_submitted_at = now - timedelta(days=30)

        deal2 = MagicMock()
        deal2.closed_at = now
        deal2.offer_submitted_at = now - timedelta(days=50)

        deal_rows_result = MagicMock()
        deal_rows_result.fetchall.return_value = [deal1, deal2]
        deal_rows_result.scalar.return_value = 0
        deal_rows_result.fetchone.return_value = None
        deal_rows_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))

        # Build query results:
        # 5 lead metric queries (all 0)
        # 4 deal metric queries (all 0)
        # 1 conversion metric query (qualified_count = 0)
        # 1 time metric query (closed deals query returning deal rows)
        results = [
            _mock_scalar_result(0),  # total leads
            _mock_scalar_result(0),  # active leads
            _mock_scalar_result(0),  # new leads week
            _mock_scalar_result(0),  # high value leads
            _mock_scalar_result(0),  # avg score
            _mock_scalar_result(0),  # total deals
            _mock_scalar_result(0),  # active deals
            _mock_scalar_result(0),  # closed deals
            _mock_scalar_result(0),  # fell through
            _mock_scalar_result(0),  # qualified count (conversion)
            deal_rows_result,  # closed deals rows (time metrics)
        ]
        # Financial metrics: deal_value=0, total_commission=0, pending_commission=0
        results.extend([_mock_scalar_result(0)] * 3)
        # Strengths: property types, locations
        results.extend([_mock_scalar_result(0)] * 2)
        # Period comparison: prev_deals=0, prev_revenue=0
        results.extend([_mock_scalar_result(0)] * 2)

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        # (30 + 50) / 2 = 40.0
        assert metrics.avg_time_to_close_days == 40.0

    @pytest.mark.asyncio
    async def test_time_to_close_ignores_deals_without_timestamps(self):
        """Deals where closed_at or offer_submitted_at is None are skipped."""
        session = _make_session()

        deal1 = MagicMock()
        deal1.closed_at = datetime.now(UTC)
        deal1.offer_submitted_at = None  # missing timestamp

        deal2 = MagicMock()
        deal2.closed_at = None  # missing timestamp
        deal2.offer_submitted_at = datetime.now(UTC) - timedelta(days=20)

        deal_rows_result = MagicMock()
        deal_rows_result.fetchall.return_value = [deal1, deal2]
        deal_rows_result.scalar.return_value = 0
        deal_rows_result.fetchone.return_value = None
        deal_rows_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))

        results = [
            _mock_scalar_result(0),  # total leads
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),  # conversion
            deal_rows_result,  # time metrics
        ]
        results.extend([_mock_scalar_result(0)] * 7)

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert metrics.avg_time_to_close_days == 0.0


class TestPeriodComparison:
    """Tests for _calculate_period_comparison."""

    @pytest.mark.asyncio
    async def test_period_comparison_with_previous_data(self):
        """Calculates deals_change_percent and revenue_change_percent vs previous period."""
        session = _make_session()

        # Need to set up metrics where closed_deals > 0 and total_deal_value > 0
        # Lead metrics: 5 queries
        # Deal metrics: 4 queries (closed_deals = 5)
        # Conversion metrics: 1 query (qualified = 0)
        # Time metrics: 1 query (no deals)
        # Financial metrics: 3 queries (total_deal_value = 500000)
        # Strengths: 2 queries
        # Period comparison: 2 queries (prev_deals = 3, prev_revenue = 300000)

        results = [
            _mock_scalar_result(10),  # total leads
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),  # avg score
            _mock_scalar_result(0),  # total deals
            _mock_scalar_result(0),  # active deals
            _mock_scalar_result(5),  # closed deals <-- needed for conversion + period comparison
            _mock_scalar_result(0),  # fell through
            _mock_scalar_result(0),  # qualified count (conversion)
            _mock_scalar_result(0),  # time metrics (no deal rows)
            _mock_scalar_result(500000),  # total deal value
            _mock_scalar_result(0),  # total commission
            _mock_scalar_result(0),  # pending commission
            _mock_scalar_result(0),  # property types (fetchall returns [])
            _mock_scalar_result(0),  # locations (fetchall returns [])
            _mock_scalar_result(3),  # prev period closed deals
            _mock_scalar_result(300000),  # prev period revenue
        ]

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        # deals change: (5 - 3) / 3 * 100 = 66.7%
        assert metrics.deals_change_percent == 66.7
        # revenue change: (500000 - 300000) / 300000 * 100 = 66.7%
        assert metrics.revenue_change_percent == 66.7

    @pytest.mark.asyncio
    async def test_period_comparison_no_previous(self):
        """Period comparison stays None when previous period has no data."""
        session = _make_session()

        results = [
            _mock_scalar_result(0),  # total leads
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),  # prev period deals = 0
            _mock_scalar_result(0),  # prev period revenue = 0
        ]

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert metrics.deals_change_percent is None
        assert metrics.revenue_change_percent is None


class TestStrengths:
    """Tests for _calculate_strengths."""

    @pytest.mark.asyncio
    async def test_calculates_top_property_types_and_locations(self):
        """Calculates property type and location breakdowns."""
        session = _make_session()

        # Property type rows
        pt_row1 = MagicMock()
        pt_row1.property_type = "apartment"
        pt_row1.count = 6
        pt_row2 = MagicMock()
        pt_row2.property_type = "house"
        pt_row2.count = 4

        pt_result = MagicMock()
        pt_result.fetchall.return_value = [pt_row1, pt_row2]
        pt_result.scalar.return_value = 0
        pt_result.fetchone.return_value = None

        # Location rows
        loc_row1 = MagicMock()
        loc_row1.property_city = "Berlin"
        loc_row1.count = 7
        loc_row2 = MagicMock()
        loc_row2.property_city = "Munich"
        loc_row2.count = 3

        loc_result = MagicMock()
        loc_result.fetchall.return_value = [loc_row1, loc_row2]
        loc_result.scalar.return_value = 0
        loc_result.fetchone.return_value = None

        results = [
            _mock_scalar_result(0),  # total leads
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            _mock_scalar_result(0),  # time metrics
            _mock_scalar_result(0),  # financial
            _mock_scalar_result(0),
            _mock_scalar_result(0),
            pt_result,  # property types
            loc_result,  # locations
            _mock_scalar_result(0),  # period comparison
            _mock_scalar_result(0),
        ]

        session = _make_session(results)
        service = AgentPerformanceService(session)
        metrics = await service.get_agent_metrics("agent-001")

        assert len(metrics.top_property_types) == 2
        assert metrics.top_property_types[0]["type"] == "apartment"
        assert metrics.top_property_types[0]["percentage"] == 60.0  # 6/10 * 100
        assert metrics.top_property_types[1]["type"] == "house"
        assert metrics.top_property_types[1]["percentage"] == 40.0

        assert len(metrics.top_locations) == 2
        assert metrics.top_locations[0]["location"] == "Berlin"
        assert metrics.top_locations[0]["percentage"] == 70.0


class TestGetAllAgentsStats:
    """Tests for _get_all_agents_stats method."""

    @pytest.mark.asyncio
    async def test_returns_stats_for_all_agents(self):
        """Queries and returns aggregated stats per agent."""
        session = _make_session()

        # Main stats query row
        agent_row = MagicMock()
        agent_row.agent_id = "agent-001"
        agent_row.deals = 5
        agent_row.revenue = 250000

        stats_result = MagicMock()
        stats_result.fetchall.return_value = [agent_row]
        stats_result.scalar.return_value = 0
        stats_result.fetchone.return_value = None

        # Per-agent sub-queries: leads count, avg time to close
        leads_result = _mock_scalar_result(20)  # leads count
        time_result = _mock_scalar_result(25.5)  # avg time to close in days

        session.execute.side_effect = [stats_result, leads_result, time_result]

        service = AgentPerformanceService(session)
        now = datetime.now(UTC)
        stats = await service._get_all_agents_stats(now - timedelta(days=30), now)

        assert len(stats) == 1
        assert stats[0]["agent_id"] == "agent-001"
        assert stats[0]["deals"] == 5
        assert stats[0]["revenue"] == 250000.0
        assert stats[0]["conversion_rate"] == 25.0  # 5/20 * 100
        assert stats[0]["avg_time_to_close"] == 25.5

    @pytest.mark.asyncio
    async def test_handles_zero_leads(self):
        """Returns 0 conversion_rate when agent has no leads."""
        session = _make_session()

        agent_row = MagicMock()
        agent_row.agent_id = "agent-002"
        agent_row.deals = 0
        agent_row.revenue = 0

        stats_result = MagicMock()
        stats_result.fetchall.return_value = [agent_row]
        stats_result.scalar.return_value = 0
        stats_result.fetchone.return_value = None

        leads_result = _mock_scalar_result(0)
        time_result = _mock_scalar_result(None)

        session.execute.side_effect = [stats_result, leads_result, time_result]

        service = AgentPerformanceService(session)
        now = datetime.now(UTC)
        stats = await service._get_all_agents_stats(now - timedelta(days=30), now)

        assert stats[0]["conversion_rate"] == 0.0
        assert stats[0]["avg_time_to_close"] is None


class TestTeamComparisonEdgeCases:
    """Tests for team comparison edge cases."""

    @pytest.mark.asyncio
    async def test_agent_not_in_stats(self):
        """Returns empty comparison when agent is not found in stats."""
        session = _make_session()

        agent_result = MagicMock()
        agent_row = MagicMock()
        agent_row.full_name = "Agent One"
        agent_result.fetchone.return_value = agent_row

        stats = [
            {
                "agent_id": "other-agent",
                "deals": 10,
                "revenue": 500000,
                "conversion_rate": 30.0,
                "avg_time_to_close": 20.0,
            },
        ]

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=stats):
            session.execute.return_value = agent_result
            comparison = await service.get_team_comparison("agent-001")

        assert comparison.rank_by_deals == 0
        assert comparison.rank_by_revenue == 0
        assert comparison.rank_by_conversion == 0

    @pytest.mark.asyncio
    async def test_team_avg_conversion_and_time(self):
        """Calculates team average conversion rate and time to close."""
        session = _make_session()

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
                "avg_time_to_close": 40.0,
            },
            {
                "agent_id": "agent-003",
                "deals": 0,
                "revenue": 0,
                "conversion_rate": 0.0,  # excluded from avg conversion
                "avg_time_to_close": None,  # excluded from avg time
            },
        ]

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=stats):
            session.execute.return_value = agent_result
            comparison = await service.get_team_comparison("agent-001")

        # Only agents with conversion > 0: (30 + 15) / 2 = 22.5
        assert comparison.team_avg_conversion == 22.5
        # Only agents with avg_time: (20 + 40) / 2 = 30.0
        assert comparison.team_avg_time_to_close_days == 30.0

        # time_to_close_vs_avg: (20 - 30) / 30 * 100 = -33.3%
        assert comparison.time_to_close_vs_avg_percent == -33.3

    @pytest.mark.asyncio
    async def test_unknown_agent_name(self):
        """Uses 'Unknown' when agent row is not found."""
        session = _make_session()

        agent_result = MagicMock()
        agent_result.fetchone.return_value = None  # agent not in DB

        service = AgentPerformanceService(session)
        with patch.object(service, "_get_all_agents_stats", return_value=[]):
            session.execute.return_value = agent_result
            comparison = await service.get_team_comparison("agent-001")

        assert comparison.agent_name == "Unknown"


class TestPerformanceTrendsIntervals:
    """Tests for different trend intervals."""

    @pytest.mark.asyncio
    async def test_week_interval(self):
        """Generates weekly trend periods."""
        session = _make_session()

        results = []
        for _ in range(2):
            results.append(_mock_scalar_result(5))
            deal_row = MagicMock()
            deal_row.count = 1
            deal_row.value = 50000
            results.append(_mock_row_result([deal_row]))

        session.execute.side_effect = results
        service = AgentPerformanceService(session)
        trends = await service.get_performance_trends("agent-001", interval="week", periods=2)

        assert len(trends) == 2
        assert "W" in trends[0].period  # weekly format: YYYY-W%W

    @pytest.mark.asyncio
    async def test_day_interval(self):
        """Generates daily trend periods."""
        session = _make_session()

        results = []
        for _ in range(2):
            results.append(_mock_scalar_result(3))
            deal_row = MagicMock()
            deal_row.count = 1
            deal_row.value = 25000
            results.append(_mock_row_result([deal_row]))

        session.execute.side_effect = results
        service = AgentPerformanceService(session)
        trends = await service.get_performance_trends("agent-001", interval="day", periods=2)

        assert len(trends) == 2
        # Daily format: YYYY-MM-DD
        assert len(trends[0].period) == 10

    @pytest.mark.asyncio
    async def test_quarter_interval(self):
        """Generates quarterly trend periods."""
        session = _make_session()

        results = []
        for _ in range(2):
            results.append(_mock_scalar_result(10))
            deal_row = MagicMock()
            deal_row.count = 2
            deal_row.value = 100000
            results.append(_mock_row_result([deal_row]))

        session.execute.side_effect = results
        service = AgentPerformanceService(session)
        trends = await service.get_performance_trends("agent-001", interval="quarter", periods=2)

        assert len(trends) == 2
        assert "Q" in trends[0].period  # quarterly format: YYYY-QN

    @pytest.mark.asyncio
    async def test_avg_deal_value_per_period(self):
        """Calculates avg_deal_value when deals are present."""
        session = _make_session()

        results = []
        leads_result = _mock_scalar_result(4)
        deal_row = MagicMock()
        deal_row.count = 2
        deal_row.value = 200000
        deals_result = _mock_row_result([deal_row])
        results.extend([leads_result, deals_result])

        session.execute.side_effect = results
        service = AgentPerformanceService(session)
        trends = await service.get_performance_trends("agent-001", interval="month", periods=1)

        assert trends[0].avg_deal_value == 100000.0  # 200000 / 2
        assert trends[0].revenue == 200000.0
        assert trends[0].deals_closed == 2


class TestCoachingInsightsComprehensive:
    """Additional coaching insight tests for missing coverage."""

    @pytest.mark.asyncio
    async def test_quality_lead_pipeline_insight(self):
        """Generates 'Quality Lead Pipeline' when avg_lead_score > 60."""
        session = _make_session()
        service = AgentPerformanceService(session)
        metrics = AgentMetrics(avg_lead_score=75.0, closed_deals=3)

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any("Quality Lead Pipeline" in i.title for i in insights)

    @pytest.mark.asyncio
    async def test_property_type_specialist_insight(self):
        """Generates property type specialist insight when top_property_types exist."""
        session = _make_session()
        service = AgentPerformanceService(session)
        metrics = AgentMetrics(
            top_property_types=[{"type": "apartment", "count": 8, "percentage": 80.0}],
        )

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any("Specialist" in i.title for i in insights)
        assert any("apartment" in i.title.lower() for i in insights)

    @pytest.mark.asyncio
    async def test_pending_commission_insight(self):
        """Generates 'Pending Commission' insight when pending_commission > 0."""
        session = _make_session()
        service = AgentPerformanceService(session)
        metrics = AgentMetrics(pending_commission=5000.0)

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any("Pending Commission" in i.title for i in insights)

    @pytest.mark.asyncio
    async def test_strong_lead_inflow_insight(self):
        """Generates 'Strong Lead Inflow' when new_leads_week > 5."""
        session = _make_session()
        service = AgentPerformanceService(session)
        metrics = AgentMetrics(new_leads_week=8)

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any("Strong Lead Inflow" in i.title for i in insights)

    @pytest.mark.asyncio
    async def test_deal_fell_through_insight(self):
        """Generates 'Reduce Deal Fall-Through' when fell_through > closed."""
        session = _make_session()
        service = AgentPerformanceService(session)
        metrics = AgentMetrics(fell_through_deals=6, closed_deals=3)

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        assert any("Fall-Through" in i.title for i in insights)

    @pytest.mark.asyncio
    async def test_no_insights_for_average_agent(self):
        """Returns empty list for agent with unremarkable metrics."""
        session = _make_session()
        service = AgentPerformanceService(session)
        metrics = AgentMetrics(
            closed_deals=2,
            avg_lead_score=40.0,
            total_leads=5,
            overall_conversion_rate=15.0,
        )

        with patch.object(service, "get_agent_metrics", return_value=metrics):
            insights = await service.get_coaching_insights("agent-001")

        # No insights triggered: deals <= 5, score <= 60, no property types,
        # time not > 60, conversion not < 10 or leads not > 10, etc.
        assert len(insights) == 0


class TestGetTopPerformersConversion:
    """Tests for top performers with conversion metric."""

    @pytest.mark.asyncio
    async def test_sorts_by_conversion(self):
        """Correctly sorts by conversion_rate metric."""
        session = _make_session()

        stats = [
            {
                "agent_id": "a1",
                "deals": 5,
                "revenue": 200000,
                "conversion_rate": 15.0,
                "avg_time_to_close": 20.0,
            },
            {
                "agent_id": "a2",
                "deals": 3,
                "revenue": 100000,
                "conversion_rate": 45.0,
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

            performers = await service.get_top_performers(metric="conversion")

        assert performers[0]["metric_value"] == 45.0
        assert performers[0]["rank"] == 1


class TestAgentsNeedingSupportEdgeCases:
    """Additional tests for agents needing support."""

    @pytest.mark.asyncio
    async def test_agent_with_many_leads_low_conversion(self):
        """Suggests coaching review when agent has >10 leads but <5% conversion."""
        session = _make_session()

        agent_row = MagicMock()
        agent_row.id = "agent-001"
        agent_row.full_name = "Low Conv Agent"
        agent_row.email = "low@example.com"

        agents_result = MagicMock()
        agents_result.fetchall.return_value = [agent_row]

        last_deal_date = datetime.now(UTC) - timedelta(days=45)

        session.execute.side_effect = [
            agents_result,
            _mock_scalar_result(0),  # closed in period = 0
            _mock_scalar_result(last_deal_date),  # last_deal_at
            _mock_scalar_result(15),  # active leads > 10
            _mock_scalar_result(0),  # total closed ever -> conversion = 0%
        ]

        service = AgentPerformanceService(session)
        result = await service.get_agents_needing_support()

        assert len(result) == 1
        assert "Review lead qualification process" in result[0]["suggested_actions"]
        assert "Schedule one-on-one coaching" in result[0]["suggested_actions"]


class TestGoalCurrentValues:
    """Tests for _calculate_goal_current_value with different goal types."""

    @pytest.mark.asyncio
    async def test_revenue_goal_type(self):
        """Calculates current value for revenue goal type."""
        session = _make_session()

        goal = MagicMock()
        goal.id = "goal-rev"
        goal.goal_type = "revenue"
        goal.target_value = 500000
        goal.period_type = "monthly"
        goal.period_start = datetime.now(UTC) - timedelta(days=15)
        goal.period_end = datetime.now(UTC) + timedelta(days=15)
        goal.is_active = True

        goals_result = MagicMock()
        goals_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[goal]))
        current_value_result = _mock_scalar_result(350000)

        session.execute.side_effect = [goals_result, current_value_result]

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert progress[0]["current_value"] == 350000.0
        assert progress[0]["progress_percent"] == 70.0

    @pytest.mark.asyncio
    async def test_gci_goal_type(self):
        """Calculates current value for gci (gross commission income) goal type."""
        session = _make_session()

        goal = MagicMock()
        goal.id = "goal-gci"
        goal.goal_type = "gci"
        goal.target_value = 20000
        goal.period_type = "monthly"
        goal.period_start = datetime.now(UTC) - timedelta(days=15)
        goal.period_end = datetime.now(UTC) + timedelta(days=15)
        goal.is_active = True

        goals_result = MagicMock()
        goals_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[goal]))
        current_value_result = _mock_scalar_result(12000)

        session.execute.side_effect = [goals_result, current_value_result]

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert progress[0]["current_value"] == 12000.0
        assert progress[0]["progress_percent"] == 60.0

    @pytest.mark.asyncio
    async def test_unknown_goal_type_returns_zero(self):
        """Returns 0.0 for unrecognized goal types."""
        session = _make_session()

        goal = MagicMock()
        goal.id = "goal-unknown"
        goal.goal_type = "mystery_metric"
        goal.target_value = 100
        goal.period_type = "monthly"
        goal.period_start = datetime.now(UTC) - timedelta(days=15)
        goal.period_end = datetime.now(UTC) + timedelta(days=15)
        goal.is_active = True

        goals_result = MagicMock()
        goals_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[goal]))

        session.execute.side_effect = [goals_result]

        service = AgentPerformanceService(session)
        progress = await service.get_goal_progress("agent-001")

        assert progress[0]["current_value"] == 0.0
        assert progress[0]["progress_percent"] == 0.0
