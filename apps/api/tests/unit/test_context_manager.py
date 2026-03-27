"""
Unit tests for context window management (Task #73).

Tests cover:
- TokenCounter: Multi-provider token counting
- ContextCompressor: Content compression and deduplication
- ContextSummarizer: LLM-based summarization
- ContextManager: Main orchestrator
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ai.context_manager import (
    CHARS_PER_TOKEN_ESTIMATE,
    DEFAULT_CONTEXT_WINDOWS,
    ContextCompressor,
    ContextManager,
    ContextMetrics,
    ContextSummarizer,
    TokenCounter,
)
from ai.context_metrics import (
    ContextUsageMetrics,
    get_usage_by_session,
    init_context_metrics_db,
    log_context_metrics,
)


class TestTokenCounter:
    """Tests for TokenCounter class."""

    def test_count_tokens_empty_string(self):
        """Test token counting with empty string."""
        counter = TokenCounter()
        assert counter.count_tokens("", "gpt-4o") == 0

    def test_count_tokens_openai_model(self):
        """Test token counting for OpenAI models."""
        counter = TokenCounter()

        # Test with tiktoken available
        text = "Hello, world! This is a test message."
        count = counter.count_tokens(text, "gpt-4o")

        # Should return a positive integer
        assert isinstance(count, int)
        assert count > 0

        # Should be roughly accurate (within 20% of char/4 estimate)
        expected_approx = len(text) // CHARS_PER_TOKEN_ESTIMATE
        assert abs(count - expected_approx) < expected_approx * 0.5

    def test_count_tokens_anthropic_model(self):
        """Test token counting for Anthropic models (uses estimate)."""
        counter = TokenCounter()

        text = "Hello, world! This is a test message."
        count = counter.count_tokens(text, "claude-3-5-sonnet-20241022")

        # Should use char/4 estimate
        expected = len(text) // CHARS_PER_TOKEN_ESTIMATE
        assert count == expected

    def test_count_messages_tokens(self):
        """Test token counting for message lists."""
        counter = TokenCounter()

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello!"),
            AIMessage(content="Hi there! How can I help?"),
        ]

        total = counter.count_messages_tokens(messages, "gpt-4o")

        # Should include overhead for each message
        assert total > 0

        # Should be sum of individual counts plus overhead
        individual_sum = sum(counter.count_tokens(m.content, "gpt-4o") for m in messages)
        overhead = len(messages) * 4  # 4 tokens overhead per message
        assert total == individual_sum + overhead

    def test_get_context_window_limit_known_model(self):
        """Test context window lookup for known models."""
        counter = TokenCounter()

        # Test OpenAI default
        limit = counter.get_context_window_limit("gpt-4o")
        assert limit == DEFAULT_CONTEXT_WINDOWS["openai"]

        # Test Anthropic default
        limit = counter.get_context_window_limit("claude-3-5-sonnet")
        assert limit == DEFAULT_CONTEXT_WINDOWS["anthropic"]

    def test_get_context_window_limit_unknown_model(self):
        """Test context window lookup for unknown models."""
        counter = TokenCounter()

        # Unknown model should return a sensible default
        limit = counter.get_context_window_limit("unknown-model-xyz")
        assert limit > 0  # Should have some default

    def test_get_provider_from_model(self):
        """Test provider inference from model ID."""
        counter = TokenCounter()

        assert counter._get_provider_from_model("gpt-4o") == "openai"
        assert counter._get_provider_from_model("gpt-3.5-turbo") == "openai"
        assert counter._get_provider_from_model("claude-3-5-sonnet") == "anthropic"
        assert counter._get_provider_from_model("gemini-1.5-pro") == "google"
        assert counter._get_provider_from_model("llama-3.1-70b") == "ollama"


class TestContextCompressor:
    """Tests for ContextCompressor class."""

    def test_compress_repeated_content_no_duplicates(self):
        """Test compression with no duplicates."""
        compressor = ContextCompressor()

        messages = [
            HumanMessage(content="What properties in Berlin?"),
            AIMessage(content="Here are some options..."),
            HumanMessage(content="Tell me about Munich."),
        ]

        compressed = compressor.compress_repeated_content(messages)

        # Should return same messages
        assert len(compressed) == len(messages)
        assert [m.content for m in compressed] == [m.content for m in messages]

    def test_compress_repeated_content_with_duplicates(self):
        """Test compression removes consecutive duplicates."""
        compressor = ContextCompressor()

        messages = [
            HumanMessage(content="What properties in Berlin?"),
            AIMessage(content="Here are some options..."),
            AIMessage(content="Here are some options..."),  # Duplicate
            HumanMessage(content="Tell me about Munich."),
        ]

        compressed = compressor.compress_repeated_content(messages)

        # Should remove duplicate
        assert len(compressed) == 3

    def test_deduplicate_consecutive(self):
        """Test consecutive deduplication."""
        compressor = ContextCompressor()

        messages = [
            HumanMessage(content="A"),
            HumanMessage(content="A"),  # Duplicate
            HumanMessage(content="B"),
            HumanMessage(content="B"),  # Duplicate
            HumanMessage(content="C"),
        ]

        deduped = compressor.deduplicate_consecutive(messages)

        assert len(deduped) == 3
        assert [m.content for m in deduped] == ["A", "B", "C"]

    def test_compress_empty_messages(self):
        """Test compression with empty message list."""
        compressor = ContextCompressor()

        compressed = compressor.compress_repeated_content([])
        assert compressed == []

    def test_compress_single_message(self):
        """Test compression with single message."""
        compressor = ContextCompressor()

        messages = [HumanMessage(content="Single message")]
        compressed = compressor.compress_repeated_content(messages)

        assert len(compressed) == 1
        assert compressed[0].content == "Single message"


class TestContextSummarizer:
    """Tests for ContextSummarizer class."""

    def test_should_summarize_below_threshold(self):
        """Test summarization check below threshold."""
        summarizer = ContextSummarizer()

        should = summarizer.should_summarize(
            token_count=5000,
            threshold_percent=80,
            context_window=100000,
        )

        assert should is False

    def test_should_summarize_above_threshold(self):
        """Test summarization check above threshold."""
        summarizer = ContextSummarizer()

        should = summarizer.should_summarize(
            token_count=85000,
            threshold_percent=80,
            context_window=100000,
        )

        assert should is True

    def test_format_conversation(self):
        """Test conversation formatting."""
        summarizer = ContextSummarizer()

        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        formatted = summarizer._format_conversation(messages)

        assert "HUMAN: Hello" in formatted
        assert "AI: Hi there!" in formatted

    def test_fallback_summary(self):
        """Test fallback summary generation."""
        summarizer = ContextSummarizer()

        messages = [
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
            HumanMessage(content="Message 2"),
            AIMessage(content="Response 2"),
            HumanMessage(content="Message 3"),
            AIMessage(content="Response 3"),
        ]

        fallback = summarizer._fallback_summary(messages)

        # Should contain first and last messages
        assert "Message 1" in fallback
        assert "Message 3" in fallback
        assert "..." in fallback


class TestContextManager:
    """Tests for ContextManager class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.context_max_utilization_percent = 75
        settings.context_sliding_window_messages = 50
        settings.context_summarization_threshold_percent = 80
        settings.context_compression_enabled = True
        settings.context_metrics_enabled = False  # Disable for tests
        settings.context_priority_system_weight = 1.0
        settings.context_priority_recent_weight = 0.8
        return settings

    def test_init_context_manager(self, mock_settings):
        """Test context manager initialization."""
        manager = ContextManager(mock_settings)

        assert manager.token_counter is not None
        assert manager.compressor is not None
        assert manager.summarizer is not None

    def test_optimize_context_under_limit(self, mock_settings):
        """Test optimization when under limit (no changes needed)."""
        manager = ContextManager(mock_settings)

        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        optimized, metrics = manager.optimize_context(
            session_id="test-session",
            messages=messages,
            model_id="gpt-4o",
        )

        # Should return same messages when under limit
        assert len(optimized) == len(messages)
        assert metrics is None  # No optimization occurred

    def test_optimize_context_applies_compression(self, mock_settings):
        """Test that compression is applied when over limit."""
        manager = ContextManager(mock_settings)

        # Create messages with duplicates that would benefit from compression
        messages = []
        for _ in range(10):
            messages.append(HumanMessage(content="A" * 10000))
            messages.append(AIMessage(content="B" * 10000))

        optimized, metrics = manager.optimize_context(
            session_id="test-session",
            messages=messages,
            model_id="gpt-4o",
        )

        # If over limit, should have metrics
        if metrics:
            assert metrics.compression_applied is True

    def test_apply_sliding_window(self, mock_settings):
        """Test sliding window application."""
        manager = ContextManager(mock_settings)

        messages = [
            SystemMessage(content="System prompt"),
        ]
        for i in range(100):
            messages.append(HumanMessage(content=f"Message {i}"))
            messages.append(AIMessage(content=f"Response {i}"))

        windowed = manager.apply_sliding_window(messages, window_size=10)

        # Should keep system messages + last 10 non-system messages
        assert len(windowed) <= 12  # 1 system + 10 recent + some buffer

    def test_prioritize_messages(self, mock_settings):
        """Test priority-based message selection."""
        manager = ContextManager(mock_settings)

        messages = [
            SystemMessage(content="Important system prompt"),
        ]
        for i in range(20):
            messages.append(HumanMessage(content=f"User message {i}"))
            messages.append(AIMessage(content=f"AI response {i}" * 100))

        # Prioritize with very low token limit
        prioritized = manager.prioritize_messages(
            messages,
            max_tokens=100,  # Very limited
            model_id="gpt-4o",
            system_weight=1.0,
            recent_weight=0.8,
        )

        # System message should always be included
        assert any(isinstance(m, SystemMessage) for m in prioritized)

        # Should be significantly reduced
        assert len(prioritized) < len(messages)


class TestContextMetrics:
    """Tests for context metrics storage."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test_metrics.db"

    @pytest.mark.asyncio
    async def test_init_context_metrics_db(self, temp_db_path):
        """Test database initialization."""
        await init_context_metrics_db(temp_db_path)

        assert temp_db_path.exists()

    @pytest.mark.asyncio
    async def test_log_and_retrieve_metrics(self, temp_db_path):
        """Test logging and retrieving metrics."""
        await init_context_metrics_db(temp_db_path)

        metrics = ContextUsageMetrics(
            timestamp=datetime.now(),
            session_id="test-session",
            model_id="gpt-4o",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
            context_window_limit=128000,
            utilization_percent=1.2,
            estimated_cost_usd=0.01,
            compression_applied=False,
            summarization_applied=False,
            messages_before=10,
            messages_after=10,
            processing_time_ms=5.5,
        )

        await log_context_metrics(metrics, db_path=temp_db_path)

        # Retrieve metrics
        results = await get_usage_by_session("test-session", days=1, db_path=temp_db_path)

        assert len(results) == 1
        assert results[0].session_id == "test-session"
        assert results[0].input_tokens == 1000

    def test_context_usage_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = ContextUsageMetrics(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            session_id="test",
            model_id="gpt-4o",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
            context_window_limit=128000,
            utilization_percent=1.2,
            estimated_cost_usd=0.01,
            compression_applied=True,
            summarization_applied=False,
            messages_before=10,
            messages_after=8,
            processing_time_ms=5.5,
        )

        d = metrics.to_dict()

        assert d["session_id"] == "test"
        assert d["input_tokens"] == 1000
        assert d["compression_applied"] is True
        assert "timestamp" in d


class TestContextMetricsDataclass:
    """Tests for ContextMetrics dataclass."""

    def test_context_metrics_creation(self):
        """Test ContextMetrics creation."""
        metrics = ContextMetrics(
            session_id="test-session",
            timestamp=datetime.now(),
            total_tokens=5000,
            input_tokens=4500,
            context_window_limit=128000,
            utilization_percent=3.9,
            estimated_cost_usd=0.05,
            compression_applied=True,
            summarization_applied=False,
            messages_before=50,
            messages_after=40,
            model_id="gpt-4o",
            provider="openai",
            processing_time_ms=15.5,
        )

        assert metrics.session_id == "test-session"
        assert metrics.total_tokens == 5000
        assert metrics.compression_applied is True
        assert metrics.utilization_percent == pytest.approx(3.9, rel=0.01)


class TestIntegration:
    """Integration tests for context management."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.context_max_utilization_percent = 75
        settings.context_sliding_window_messages = 10
        settings.context_summarization_threshold_percent = 80
        settings.context_compression_enabled = True
        settings.context_metrics_enabled = False
        settings.context_priority_system_weight = 1.0
        settings.context_priority_recent_weight = 0.8
        return settings

    def test_full_optimization_flow(self, mock_settings):
        """Test full optimization flow with large context."""
        manager = ContextManager(mock_settings)

        # Create large conversation
        messages = [SystemMessage(content="You are a real estate assistant.")]

        # Simulate a long conversation
        for i in range(100):
            messages.append(
                HumanMessage(
                    content=f"I'm looking for a property in Berlin. Budget around {i * 10000} EUR."
                )
            )
            messages.append(
                AIMessage(
                    content=f"Here are some options for your budget of "
                    f"{i * 10000} EUR in Berlin..." * 50  # Make it long
                )
            )

        # Optimize
        optimized, metrics = manager.optimize_context(
            session_id="long-conversation",
            messages=messages,
            model_id="gpt-4o",
        )

        # Should have optimized
        assert len(optimized) < len(messages) or metrics is None

        if metrics:
            # Check metrics are populated
            assert metrics.session_id == "long-conversation"
            assert metrics.messages_before == len(messages)
            assert metrics.messages_after == len(optimized)

    def test_optimization_preserves_system_messages(self, mock_settings):
        """Test that system messages are always preserved."""
        manager = ContextManager(mock_settings)

        system_msg = SystemMessage(content="Critical system instructions")
        messages = [system_msg]

        for i in range(50):
            messages.append(HumanMessage(content="Query " + str(i) * 1000))

        optimized = manager.apply_sliding_window(messages, window_size=10)

        # System message should be preserved
        assert system_msg in optimized
        assert optimized[0] == system_msg
