"""
Unit tests for Query Analyzer.

Tests intent classification, complexity detection, filter extraction,
tool selection, confidence scoring, multi-intent detection,
context-aware classification, and metrics logging.
"""

import pytest

from agents.query_analyzer import (
    Complexity,
    QueryIntent,
    RoutingThresholds,
    Tool,
    analyze_query,
)


class TestQueryAnalyzer:
    """Test suite for QueryAnalyzer."""

    def test_simple_retrieval_intent(self, query_analyzer):
        """Test simple retrieval intent classification."""
        query = "Show me apartments in Krakow"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.SIMPLE_RETRIEVAL
        assert analysis.complexity == Complexity.SIMPLE
        assert Tool.RAG_RETRIEVAL in analysis.tools_needed
        assert not analysis.requires_computation
        assert not analysis.should_use_agent()

    def test_filtered_search_intent(self, query_analyzer):
        """Test filtered search intent classification."""
        query = "Find 2-bedroom apartments under $1000 with parking"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.FILTERED_SEARCH
        assert analysis.complexity in [Complexity.MEDIUM, Complexity.SIMPLE]
        assert Tool.RAG_RETRIEVAL in analysis.tools_needed

    def test_calculation_intent(self, query_analyzer):
        """Test calculation intent classification."""
        query = "Calculate mortgage for $150,000 property"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.CALCULATION
        assert analysis.complexity == Complexity.COMPLEX
        assert analysis.requires_computation
        assert analysis.should_use_agent()

    def test_comparison_intent(self, query_analyzer):
        """Test comparison intent classification."""
        query = "Compare apartments in Warsaw vs Krakow"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.COMPARISON
        assert analysis.complexity == Complexity.COMPLEX
        assert analysis.requires_comparison
        assert analysis.should_use_agent()

    def test_analysis_intent(self, query_analyzer):
        """Test analysis intent classification."""
        query = "What's the average price per square meter in Krakow?"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.ANALYSIS
        assert analysis.complexity == Complexity.COMPLEX
        assert analysis.requires_computation
        assert Tool.PYTHON_CODE in analysis.tools_needed

    def test_recommendation_intent(self, query_analyzer):
        """Test recommendation intent classification."""
        query = "What's the best value apartment for $1000?"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.RECOMMENDATION
        assert analysis.complexity == Complexity.COMPLEX

    def test_conversation_intent(self, query_analyzer):
        """Test conversation intent classification."""
        query = "Tell me more about the last property"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.CONVERSATION

    def test_filter_extraction_price(self, query_analyzer):
        """Test price filter extraction."""
        query = "Find apartments under $1000"
        analysis = query_analyzer.analyze(query)

        assert "max_price" in analysis.extracted_filters
        assert analysis.extracted_filters["max_price"] == 1000.0

    def test_filter_extraction_rooms(self, query_analyzer):
        """Test rooms filter extraction."""
        query = "Find 2-bedroom apartments"
        analysis = query_analyzer.analyze(query)

        assert "rooms" in analysis.extracted_filters
        assert analysis.extracted_filters["rooms"] == 2

    def test_filter_extraction_city(self, query_analyzer):
        """Test city filter extraction."""
        query = "Show me apartments in Krakow"
        analysis = query_analyzer.analyze(query)

        assert "city" in analysis.extracted_filters
        assert analysis.extracted_filters["city"] == "Krakow"

    def test_filter_extraction_amenities(self, query_analyzer):
        """Test amenities filter extraction."""
        query = "Find apartments with parking and garden"
        analysis = query_analyzer.analyze(query)

        assert "has_parking" in analysis.extracted_filters
        assert "has_garden" in analysis.extracted_filters
        assert analysis.extracted_filters["has_parking"] is True
        assert analysis.extracted_filters["has_garden"] is True

    def test_multi_filter_extraction(self, query_analyzer):
        """Test multiple filter extraction."""
        query = "Find 2-bedroom apartments in Krakow under $1000 with parking"
        analysis = query_analyzer.analyze(query)

        assert "rooms" in analysis.extracted_filters
        assert "city" in analysis.extracted_filters
        assert "max_price" in analysis.extracted_filters
        assert "has_parking" in analysis.extracted_filters

        assert analysis.extracted_filters["rooms"] == 2
        assert analysis.extracted_filters["city"] == "Krakow"
        assert analysis.extracted_filters["max_price"] == 1000.0
        assert analysis.extracted_filters["has_parking"] is True

    def test_price_range_extraction(self, query_analyzer):
        """Test price range extraction."""
        query = "Find apartments between $800 and $1200"
        analysis = query_analyzer.analyze(query)

        assert "min_price" in analysis.extracted_filters
        assert "max_price" in analysis.extracted_filters
        assert analysis.extracted_filters["min_price"] == 800.0
        assert analysis.extracted_filters["max_price"] == 1200.0

    def test_mortgage_tool_selection(self, query_analyzer):
        """Test mortgage calculator tool selection."""
        query = "Calculate mortgage for property"
        analysis = query_analyzer.analyze(query)

        assert Tool.MORTGAGE_CALC in analysis.tools_needed

    def test_comparator_tool_selection(self, query_analyzer):
        """Test comparator tool selection."""
        query = "Compare properties in different cities"
        analysis = query_analyzer.analyze(query)

        assert Tool.COMPARATOR in analysis.tools_needed

    def test_complexity_detection_simple(self, query_analyzer):
        """Test simple complexity detection."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze(query)

        assert analysis.complexity == Complexity.SIMPLE

    def test_complexity_detection_complex(self, query_analyzer):
        """Test complex complexity detection."""
        query = "Calculate the average price and compare"
        analysis = query_analyzer.analyze(query)

        assert analysis.complexity == Complexity.COMPLEX

    def test_should_use_agent_for_complex(self, query_analyzer):
        """Test agent usage for complex queries."""
        query = "Calculate mortgage and compare properties"
        analysis = query_analyzer.analyze(query)

        assert analysis.should_use_agent()

    def test_should_not_use_agent_for_simple(self, query_analyzer):
        """Test no agent for simple queries."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze(query)

        assert not analysis.should_use_agent()

    def test_reasoning_generation(self, query_analyzer):
        """Test reasoning text generation."""
        query = "Calculate mortgage"
        analysis = query_analyzer.analyze(query)

        assert analysis.reasoning is not None
        assert len(analysis.reasoning) > 0
        assert "calculation" in analysis.reasoning.lower()

    def test_confidence_score(self, query_analyzer):
        """Test confidence score is valid."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze(query)

        assert 0.0 <= analysis.confidence <= 1.0

    def test_analyze_query_function(self):
        """Test convenience function."""
        query = "Show me apartments in Krakow"
        analysis = analyze_query(query)

        assert analysis.intent == QueryIntent.SIMPLE_RETRIEVAL
        assert isinstance(analysis.extracted_filters, dict)

    def test_empty_query(self, query_analyzer):
        """Test empty query handling."""
        query = ""
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.GENERAL_QUESTION
        assert len(analysis.extracted_filters) == 0

    def test_complex_multi_criteria_query(self, query_analyzer):
        """Test complex query with many criteria."""
        query = (
            "Find 2-3 bedroom apartments in Krakow between $800-$1200 "
            "with parking and garden near schools"
        )
        analysis = query_analyzer.analyze(query)

        assert analysis.complexity in [Complexity.MEDIUM, Complexity.COMPLEX]
        assert len(analysis.extracted_filters) >= 3
        assert "city" in analysis.extracted_filters
        assert "has_parking" in analysis.extracted_filters


class TestQueryIntentClassification:
    """Test intent classification accuracy."""

    @pytest.mark.parametrize(
        "query,expected_intent",
        [
            ("Show me apartments", QueryIntent.SIMPLE_RETRIEVAL),
            ("Find properties in Warsaw", QueryIntent.SIMPLE_RETRIEVAL),
            ("List available apartments", QueryIntent.SIMPLE_RETRIEVAL),
            ("Find 2-bed under $1000", QueryIntent.FILTERED_SEARCH),
            ("Search apartments with parking", QueryIntent.FILTERED_SEARCH),
            ("Calculate mortgage", QueryIntent.CALCULATION),
            ("How much is monthly payment", QueryIntent.CALCULATION),
            ("Compare Warsaw vs Krakow", QueryIntent.COMPARISON),
            ("What's the difference between", QueryIntent.COMPARISON),
            ("Average price analysis", QueryIntent.ANALYSIS),
            ("What's the mean price", QueryIntent.ANALYSIS),
            ("Recommend best value", QueryIntent.RECOMMENDATION),
            ("What's the best apartment", QueryIntent.RECOMMENDATION),
        ],
    )
    def test_intent_classification(self, query_analyzer, query, expected_intent):
        """Test various query intents."""
        analysis = query_analyzer.analyze(query)
        assert analysis.intent == expected_intent


class TestFilterExtraction:
    """Test filter extraction accuracy."""

    @pytest.mark.parametrize(
        "query,expected_filters",
        [
            ("Find apartments in Krakow", {"city": "Krakow"}),
            ("2-bedroom apartments", {"rooms": 2}),
            ("Under $1000", {"max_price": 1000.0}),
            ("With parking", {"has_parking": True}),
            ("With garden", {"has_garden": True}),
            ("Furnished apartment", {"is_furnished": True}),
        ],
    )
    def test_filter_extraction(self, query_analyzer, query, expected_filters):
        """Test filter extraction for various queries."""
        analysis = query_analyzer.analyze(query)

        for key, value in expected_filters.items():
            assert key in analysis.extracted_filters
            assert analysis.extracted_filters[key] == value


class TestConfidenceScoring:
    """Test confidence scoring for classification quality."""

    @pytest.mark.parametrize(
        "query,min_confidence,max_confidence",
        [
            # Clear intent keywords - medium to high confidence
            ("Calculate my mortgage payment", 0.3, 1.0),
            ("Compare apartments in Warsaw and Krakow", 0.3, 1.0),
            ("Show me all apartments", 0.3, 1.0),
            # Ambiguous queries - lower confidence
            ("What about the apartment?", 0.0, 0.5),
            ("Is it good?", 0.0, 0.5),
            # Very ambiguous - low confidence
            ("Tell me more", 0.0, 0.5),
        ],
    )
    def test_confidence_range(self, query_analyzer, query, min_confidence, max_confidence):
        """Test confidence falls within expected ranges."""
        analysis = query_analyzer.analyze(query)
        assert min_confidence <= analysis.confidence <= max_confidence, (
            f"Confidence {analysis.confidence} not in range [{min_confidence}, {max_confidence}]"
        )

    def test_clear_intent_has_higher_confidence(self, query_analyzer):
        """Clear intent queries should have higher confidence than ambiguous ones."""
        clear_query = "Calculate mortgage for $500000 at 5% interest"
        ambiguous_query = "What about it?"

        clear_analysis = query_analyzer.analyze(clear_query)
        ambiguous_analysis = query_analyzer.analyze(ambiguous_query)

        assert clear_analysis.confidence > ambiguous_analysis.confidence

    def test_multi_keyword_matches_increase_confidence(self, query_analyzer):
        """More keyword matches should increase confidence."""
        simple_query = "mortgage"
        detailed_query = "Calculate monthly mortgage payment for $300000 loan"

        simple_analysis = query_analyzer.analyze(simple_query)
        detailed_analysis = query_analyzer.analyze(detailed_query)

        assert detailed_analysis.confidence >= simple_analysis.confidence

    def test_confidence_affects_routing_decision(self, query_analyzer):
        """High confidence should lead to direct routing."""
        high_confidence_query = "Calculate my mortgage monthly payment"
        analysis = query_analyzer.analyze(high_confidence_query)

        if analysis.confidence >= RoutingThresholds.HIGH_CONFIDENCE:
            # Should have a clear route
            assert analysis.should_use_agent() or analysis.should_use_rag_only()


class TestMultiIntentDetection:
    """Test multi-intent detection for complex queries."""

    def test_single_intent_detection(self, query_analyzer):
        """Simple queries should have single dominant intent."""
        query = "Show me apartments in Krakow"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent is not None
        # Secondary intents may be empty or have low weights
        if analysis.secondary_intents:
            total_secondary_weight = sum(
                analysis.intent_weights.get(i.value, 0) for i in analysis.secondary_intents
            )
            primary_weight = analysis.intent_weights.get(analysis.intent.value, 1.0)
            assert primary_weight >= total_secondary_weight

    def test_multi_intent_query_detection(self, query_analyzer):
        """Complex queries may have multiple intents."""
        query = "Compare mortgage options for 3 properties in different cities"
        analysis = query_analyzer.analyze(query)

        # Should detect COMPARISON intent at minimum
        assert analysis.intent in [QueryIntent.COMPARISON, QueryIntent.MORTGAGE]

    def test_intent_weights_sum_reasonable(self, query_analyzer):
        """Intent weights should be normalized reasonably."""
        query = "Find and compare apartments"
        analysis = query_analyzer.analyze(query)

        if analysis.intent_weights:
            total_weight = sum(analysis.intent_weights.values())
            # Weights should be positive and not exceed 2.0 total
            assert 0 < total_weight <= 2.0

    def test_processing_strategy_selection(self, query_analyzer):
        """Processing strategy should match query complexity."""
        # Simple query
        simple_query = "Show me apartments"
        _ = query_analyzer.analyze(simple_query)
        # Processing strategy may be None for simple queries

        # Complex multi-intent query
        complex_query = "Compare mortgage calculations for two properties"
        _ = query_analyzer.analyze(complex_query)
        # Should handle complex queries appropriately


class TestContextAwareClassification:
    """Test context-aware classification using session history."""

    def test_analyze_with_context_no_history(self, query_analyzer):
        """Should work without session history."""
        query = "Tell me more about it"
        analysis = query_analyzer.analyze_with_context(query, session_history=None)

        assert analysis is not None
        assert analysis.query == query

    def test_analyze_with_empty_history(self, query_analyzer):
        """Should work with empty history."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze_with_context(query, session_history=[])

        assert analysis is not None
        assert analysis.intent is not None

    def test_pronoun_resolution_with_context(self, query_analyzer):
        """Should resolve pronouns with context."""
        query = "What about that property?"

        # Create mock session history with property context
        mock_history = [
            type("Message", (), {"content": "Property at Main Street, 2 bedrooms"})(),
        ]

        analysis = query_analyzer.analyze_with_context(query, session_history=mock_history)

        # With context, should classify as DOCUMENT_QA or similar
        assert analysis.intent is not None

    def test_context_boosts_confidence(self, query_analyzer):
        """Context should potentially boost confidence for follow-up queries."""
        query = "How much is it?"

        # Without context
        analysis_no_context = query_analyzer.analyze(query)

        # With relevant context
        mock_history = [
            type("Message", (), {"content": "Property at Oak Street, $500000"})(),
        ]
        analysis_with_context = query_analyzer.analyze_with_context(
            query, session_history=mock_history
        )

        # Both should have valid analysis
        assert analysis_no_context.intent is not None
        assert analysis_with_context.intent is not None

    def test_max_history_messages_respected(self, query_analyzer):
        """Should only use last N messages from history."""
        query = "Tell me more"

        # Create 10 mock messages
        mock_history = [type("Message", (), {"content": f"Message {i}"})() for i in range(10)]

        # Should not fail even with more messages than max
        analysis = query_analyzer.analyze_with_context(
            query, session_history=mock_history, max_history_messages=3
        )

        assert analysis is not None


class TestIntentSpecificPrompts:
    """Test intent-specific prompt selection."""

    def test_intent_prompts_module_imports(self):
        """Intent prompts module should be importable."""
        from agents.intent_prompts import INTENT_SYSTEM_PROMPTS, get_system_prompt_for_intent

        assert INTENT_SYSTEM_PROMPTS is not None
        assert callable(get_system_prompt_for_intent)

    def test_all_intents_have_prompts(self):
        """All query intents should have corresponding prompts."""
        from agents.intent_prompts import get_system_prompt_for_intent

        for intent in QueryIntent:
            prompt = get_system_prompt_for_intent(intent)
            assert prompt is not None
            assert len(prompt) > 0

    def test_prompt_content_relevance(self):
        """Prompts should contain relevant context for their intent."""
        from agents.intent_prompts import INTENT_SYSTEM_PROMPTS

        # PROPERTY_SEARCH should mention properties
        assert any(
            kw in INTENT_SYSTEM_PROMPTS[QueryIntent.PROPERTY_SEARCH].lower()
            for kw in ["property", "search", "find"]
        )

        # MORTGAGE should mention mortgage/financial terms
        assert any(
            kw in INTENT_SYSTEM_PROMPTS[QueryIntent.MORTGAGE].lower()
            for kw in ["mortgage", "payment", "loan", "financial"]
        )

        # COMPARISON should mention comparing
        assert any(
            kw in INTENT_SYSTEM_PROMPTS[QueryIntent.COMPARISON].lower()
            for kw in ["comparison", "compare", "side-by-side"]
        )

    def test_general_intent_is_fallback(self):
        """GENERAL intent prompt should be used as fallback."""
        from agents.intent_prompts import get_system_prompt_for_intent

        general_prompt = get_system_prompt_for_intent(QueryIntent.GENERAL)
        # Should return a valid prompt for any intent
        assert general_prompt is not None


class TestMetricsLogging:
    """Test classification metrics logging."""

    def test_metrics_module_imports(self):
        """Metrics module should be importable."""
        from agents.classification_metrics import (
            ClassificationMetrics,
            init_metrics_db,
            log_classification_metrics,
        )

        assert ClassificationMetrics is not None
        assert callable(init_metrics_db)
        assert callable(log_classification_metrics)

    def test_classification_metrics_dataclass(self):
        """ClassificationMetrics should have required fields."""
        from datetime import datetime

        from agents.classification_metrics import ClassificationMetrics

        metrics = ClassificationMetrics(
            timestamp=datetime.now(),
            session_id="test-session",
            query="test query",
            query_length=11,
            primary_intent=QueryIntent.SIMPLE_RETRIEVAL,
            secondary_intents=[],
            confidence=0.9,
            complexity=Complexity.SIMPLE,
            processing_time_ms=10.5,
            route_taken="rag",
            tools_used=[],
            user_feedback=None,
            language_detected="en",
            ambiguity_signals=[],
        )

        assert metrics.session_id == "test-session"
        assert metrics.confidence == 0.9
        assert metrics.route_taken == "rag"

    def test_metrics_to_dict(self):
        """ClassificationMetrics should serialize to dict."""
        from datetime import datetime

        from agents.classification_metrics import ClassificationMetrics

        metrics = ClassificationMetrics(
            timestamp=datetime.now(),
            session_id="test",
            query="test",
            query_length=4,
            primary_intent=QueryIntent.SIMPLE_RETRIEVAL,
            secondary_intents=[],
            confidence=0.8,
            complexity=Complexity.SIMPLE,
            processing_time_ms=5.0,
            route_taken="rag",
            tools_used=[],
            user_feedback=None,
            language_detected="en",
            ambiguity_signals=[],
        )

        result = metrics.to_dict()
        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "query" in result
        assert "confidence" in result

    def test_init_metrics_db_creates_table(self, tmp_path):
        """init_metrics_db should create the database table."""
        from agents.classification_metrics import init_metrics_db

        db_path = tmp_path / "test_metrics.db"
        init_metrics_db(db_path)

        assert db_path.exists()

    def test_log_and_retrieve_metrics(self, tmp_path):
        """Should log metrics and retrieve summaries."""
        from datetime import datetime

        from agents.classification_metrics import (
            ClassificationMetrics,
            get_metrics_summary,
            init_metrics_db,
            log_classification_metrics,
        )

        db_path = tmp_path / "test_metrics.db"
        init_metrics_db(db_path)

        metrics = ClassificationMetrics(
            timestamp=datetime.now(),
            session_id="test-session",
            query="test query",
            query_length=10,
            primary_intent=QueryIntent.SIMPLE_RETRIEVAL,
            secondary_intents=[],
            confidence=0.9,
            complexity=Complexity.SIMPLE,
            processing_time_ms=15.0,
            route_taken="rag",
            tools_used=[],
            user_feedback=None,
            language_detected="en",
            ambiguity_signals=[],
        )

        log_classification_metrics(metrics, db_path)

        summary = get_metrics_summary(db_path, days=1)
        assert "counts_by_intent" in summary
        assert "avg_confidence_by_intent" in summary


class TestRoutingThresholds:
    """Test routing threshold constants."""

    def test_threshold_values(self):
        """Thresholds should be in valid range."""
        assert 0 < RoutingThresholds.LOW_CONFIDENCE < RoutingThresholds.MEDIUM_CONFIDENCE
        assert RoutingThresholds.MEDIUM_CONFIDENCE < RoutingThresholds.HIGH_CONFIDENCE <= 1.0

    def test_threshold_values_expected(self):
        """Thresholds should match plan values."""
        assert RoutingThresholds.HIGH_CONFIDENCE == 0.8
        assert RoutingThresholds.MEDIUM_CONFIDENCE == 0.5
        assert RoutingThresholds.LOW_CONFIDENCE == 0.3


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_legacy_intents_still_work(self, query_analyzer):
        """Legacy intent values should still be recognized."""
        # These queries should classify to legacy intents
        legacy_queries = [
            ("Show me apartments", QueryIntent.SIMPLE_RETRIEVAL),
            ("Find 2-bed under $1000", QueryIntent.FILTERED_SEARCH),
            ("Calculate mortgage", QueryIntent.CALCULATION),
            ("Compare Warsaw vs Krakow", QueryIntent.COMPARISON),
        ]

        for query, expected_intent in legacy_queries:
            analysis = query_analyzer.analyze(query)
            assert analysis.intent == expected_intent, (
                f"Query '{query}' classified as {analysis.intent}, expected {expected_intent}"
            )

    def test_should_use_agent_method_exists(self, query_analyzer):
        """should_use_agent method should still work."""
        query = "Calculate mortgage for property"
        analysis = query_analyzer.analyze(query)

        # Method should exist and return boolean
        assert hasattr(analysis, "should_use_agent")
        result = analysis.should_use_agent()
        assert isinstance(result, bool)

    def test_should_use_rag_only_method_exists(self, query_analyzer):
        """should_use_rag_only method should still work."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze(query)

        # Method should exist and return boolean
        assert hasattr(analysis, "should_use_rag_only")
        result = analysis.should_use_rag_only()
        assert isinstance(result, bool)

    def test_extracted_filters_dict(self, query_analyzer):
        """extracted_filters should be a dict."""
        query = "Find 2-bedroom apartments in Krakow under $1000"
        analysis = query_analyzer.analyze(query)

        assert isinstance(analysis.extracted_filters, dict)

    def test_tools_needed_list(self, query_analyzer):
        """tools_needed should be a list."""
        query = "Calculate mortgage"
        analysis = query_analyzer.analyze(query)

        assert isinstance(analysis.tools_needed, list)
