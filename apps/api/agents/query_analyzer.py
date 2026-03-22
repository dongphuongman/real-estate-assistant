"""
Query analyzer for classifying user intent and complexity.

This module analyzes user queries to determine:
- Query intent (property_search, market_analysis, comparison, mortgage, etc.)
- Complexity level (simple, medium, complex)
- Required tools
- Optimal routing strategy
- Confidence score for classification quality
- Multi-intent detection for complex queries

Enhanced with:
- Expanded intent taxonomy (7 intents)
- Confidence scoring based on keyword overlap and ambiguity
- Multi-intent detection for complex queries
- Intent modifiers for nuanced classification
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# INTENT TAXONOMY (Enhanced)
# =============================================================================


class QueryIntent(str, Enum):
    """
    Types of query intents.

    New taxonomy (Task #66):
    - PROPERTY_SEARCH: Finding/showing properties (merged simple_retrieval + filtered_search)
    - MARKET_ANALYSIS: Price trends, statistics, averages
    - COMPARISON: Comparing properties or areas
    - MORTGAGE: Mortgage/loan calculations
    - LOCATION: Neighborhood/area questions
    - DOCUMENT_QA: Questions about specific properties (context-based)
    - GENERAL: General real estate questions or out-of-domain
    """

    PROPERTY_SEARCH = "property_search"  # "Show me apartments in Krakow"
    MARKET_ANALYSIS = "market_analysis"  # "What's the average price per sqm?"
    COMPARISON = "comparison"  # "Compare properties in Warsaw vs Krakow"
    MORTGAGE = "mortgage"  # "Calculate mortgage for $200k property"
    LOCATION = "location"  # "Tell me about the Warsaw district"
    DOCUMENT_QA = "document_qa"  # "Tell me more about that property"
    GENERAL = "general"  # "How does the rental market work?"

    # Legacy aliases for backward compatibility
    # These map to new intents via INTENT_ALIASES dict below
    SIMPLE_RETRIEVAL = "simple_retrieval"  # Alias for PROPERTY_SEARCH
    FILTERED_SEARCH = "filtered_search"  # Alias for PROPERTY_SEARCH
    ANALYSIS = "analysis"  # Alias for MARKET_ANALYSIS
    CALCULATION = "calculation"  # Alias for MORTGAGE
    RECOMMENDATION = "recommendation"  # Alias with modifier
    CONVERSATION = "conversation"  # Alias for DOCUMENT_QA
    GENERAL_QUESTION = "general_question"  # Alias for GENERAL


# Backward compatibility mapping
INTENT_ALIASES: Dict[QueryIntent, QueryIntent] = {
    QueryIntent.SIMPLE_RETRIEVAL: QueryIntent.PROPERTY_SEARCH,
    QueryIntent.FILTERED_SEARCH: QueryIntent.PROPERTY_SEARCH,
    QueryIntent.ANALYSIS: QueryIntent.MARKET_ANALYSIS,
    QueryIntent.CALCULATION: QueryIntent.MORTGAGE,
    QueryIntent.RECOMMENDATION: QueryIntent.PROPERTY_SEARCH,  # With is_recommendation modifier
    QueryIntent.CONVERSATION: QueryIntent.DOCUMENT_QA,
    QueryIntent.GENERAL_QUESTION: QueryIntent.GENERAL,
}


@dataclass
class IntentModifiers:
    """
    Modifier flags that add nuance to intent classification.

    These are orthogonal to the primary intent and affect processing.
    """

    is_recommendation: bool = False  # Query asks for "best", "top", "ideal"
    is_follow_up: bool = False  # Query references previous context
    is_urgent: bool = False  # Query has urgency signals
    requires_visualization: bool = False  # Query may benefit from charts

    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary for serialization."""
        return {
            "is_recommendation": self.is_recommendation,
            "is_follow_up": self.is_follow_up,
            "is_urgent": self.is_urgent,
            "requires_visualization": self.requires_visualization,
        }


class Complexity(str, Enum):
    """Query complexity levels."""

    SIMPLE = "simple"  # Direct retrieval, can use RAG only
    MEDIUM = "medium"  # Some filtering or simple computation
    COMPLEX = "complex"  # Requires multiple steps, tools, or reasoning


class Tool(str, Enum):
    """Available tools for query processing."""

    RAG_RETRIEVAL = "rag_retrieval"
    PYTHON_CODE = "python_code"
    CALCULATOR = "calculator"
    COMPARATOR = "comparator"
    WEB_SEARCH = "web_search"
    MORTGAGE_CALC = "mortgage_calculator"


class ProcessingStrategy(str, Enum):
    """Strategy for processing multi-intent queries."""

    SINGLE_ROUTE = "single_route"  # One dominant intent, direct routing
    SEQUENTIAL = "sequential"  # Process intents in order of weight
    HYBRID = "hybrid"  # Combine RAG + tools
    CLARIFICATION = "clarification"  # Low confidence, needs disambiguation


# Confidence thresholds for routing decisions
class RoutingThresholds:
    """Thresholds for routing decisions based on confidence."""

    HIGH_CONFIDENCE = 0.8  # Use classified route directly
    MEDIUM_CONFIDENCE = 0.5  # Use hybrid approach
    LOW_CONFIDENCE = 0.3  # Use LLM fallback or clarification


class QueryAnalysis(BaseModel):
    """
    Enhanced analysis result for a query.

    Includes multi-intent detection, confidence scoring, and intent modifiers.
    """

    query: str
    intent: QueryIntent  # Primary intent (backward compatible)
    complexity: Complexity
    requires_computation: bool = False
    requires_comparison: bool = False
    requires_external_data: bool = False
    tools_needed: List[Tool] = Field(default_factory=list)
    extracted_filters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: Optional[str] = None

    # New fields for enhanced classification
    primary_intent: Optional[QueryIntent] = None  # Explicit primary (same as intent for compat)
    secondary_intents: List[QueryIntent] = Field(default_factory=list)
    intent_weights: Dict[str, float] = Field(default_factory=dict)  # intent_value -> weight
    modifiers: Dict[str, bool] = Field(default_factory=dict)  # IntentModifiers serialized
    processing_strategy: ProcessingStrategy = ProcessingStrategy.SINGLE_ROUTE
    language_detected: str = "en"  # Detected language: en, ru, tr
    ambiguity_signals: List[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        """Set primary_intent to match intent for backward compatibility."""
        if self.primary_intent is None:
            # Use canonical intent (resolve aliases)
            self.primary_intent = INTENT_ALIASES.get(self.intent, self.intent)

    def should_use_agent(self) -> bool:
        """Determine if query needs agent-based processing."""
        return (
            self.complexity == Complexity.COMPLEX
            or self.requires_computation
            or self.requires_comparison
            or len(self.tools_needed) > 1
            or self.processing_strategy == ProcessingStrategy.SEQUENTIAL
        )

    def should_use_rag_only(self) -> bool:
        """Determine if query can be handled by RAG alone."""
        return (
            self.complexity == Complexity.SIMPLE
            and not self.requires_computation
            and not self.requires_comparison
            and Tool.RAG_RETRIEVAL in self.tools_needed
            and len(self.tools_needed) == 1
            and self.confidence >= RoutingThresholds.HIGH_CONFIDENCE
        )

    def needs_clarification(self) -> bool:
        """Check if query needs clarification due to low confidence."""
        return self.confidence < RoutingThresholds.LOW_CONFIDENCE

    def get_canonical_intent(self) -> QueryIntent:
        """Get the canonical intent (resolves aliases)."""
        return INTENT_ALIASES.get(self.intent, self.intent)


class QueryAnalyzer:
    """
    Analyzer for classifying queries and determining optimal processing strategy.

    This uses pattern matching and heuristics to classify queries without
    requiring an LLM call (fast and cost-effective).

    Enhanced with:
    - Confidence scoring based on keyword overlap and ambiguity
    - Multi-intent detection for complex queries
    - Intent modifiers for nuanced classification
    """

    # =========================================================================
    # KEYWORDS FOR INTENT CLASSIFICATION (Multilingual: EN, RU, TR)
    # =========================================================================

    # Property search keywords (merged retrieval + filtered search)
    PROPERTY_SEARCH_KEYWORDS = [
        "show",
        "find",
        "list",
        "search",
        "get",
        "display",
        "want",
        "need",
        "looking for",
        "give me",
        "apartments",
        "houses",
        "properties",
        "listings",
        "показать",
        "найти",
        "список",
        "поиск",
        "дать",
        "квартиры",
        "дома",
        "недвижимость",  # RU
        "göster",
        "bul",
        "listele",
        "ara",
        "ver",
        "istiyorum",
        "daireler",
        "evler",
        "emlak",  # TR
    ]

    COMPARISON_KEYWORDS = [
        "compare",
        "versus",
        "vs",
        "difference",
        "between",
        "better",
        "cheaper",
        "more expensive",
        "bigger",
        "smaller",
        "which is",
        "or",
        "сравнить",
        "против",
        "разница",
        "между",
        "лучше",
        "дешевле",
        "или",  # RU
        "karşılaştır",
        "fark",
        "arasında",
        "daha iyi",
        "daha ucuz",
        "mi",
        "mı",  # TR
    ]

    # Strong comparison indicators (require explicit comparison context)
    COMPARISON_STRONG_KEYWORDS = [
        "compare",
        "versus",
        "vs",
        "difference between",
        "between x and",
        "or",
        "which is better",
        "сравнить",
        "против",
        "или",
        "karşılaştır",
    ]

    MORTGAGE_KEYWORDS = [
        "calculate",
        "compute",
        "how much",
        "total cost",
        "monthly payment",
        "mortgage",
        "interest",
        "loan",
        "down payment",
        "apr",
        "rate",
        "amortization",
        "рассчитать",
        "посчитать",
        "сколько",
        "ипотека",
        "кредит",
        "процент",
        "взнос",  # RU
        "hesapla",
        "ne kadar",
        "toplam",
        "kredi",
        "ipotek",
        "faiz",
        "peşinat",  # TR
    ]

    MARKET_ANALYSIS_KEYWORDS = [
        "average",
        "mean",
        "median",
        "statistics",
        "trend",
        "distribution",
        "analyze",
        "analysis",
        "insights",
        "market",
        "price per",
        "per sqm",
        "per square",
        "средняя",
        "медиана",
        "статистика",
        "тренд",
        "анализ",
        "рынок",
        "за квадрат",  # RU
        "ortalama",
        "medyan",
        "istatistik",
        "trend",
        "analiz",
        "piyasa",
        "metrekare",  # TR
    ]

    LOCATION_KEYWORDS = [
        "neighborhood",
        "district",
        "area",
        "location",
        "region",
        "zone",
        "near",
        "nearby",
        "around",
        "close to",
        "distance from",
        "commute",
        "transport",
        "amenities",
        "schools",
        "safety",
        "crime",
        "район",
        "районе",
        "локация",
        "рядом",
        "близко",
        "транспорт",
        "школы",
        "безопасность",  # RU
        "mahalle",
        "bölge",
        "konum",
        "yakın",
        "yakınında",
        "ulaşım",
        "okullar",
        "güvenlik",  # TR
    ]

    DOCUMENT_QA_KEYWORDS = [
        "this property",
        "that property",
        "the property",
        "this listing",
        "that one",
        "the one",
        "previous property",
        "last property",
        "last one",
        "above property",
        "mentioned property",
        "tell me more about",
        "more about it",
        "more about that",
        "more about this",
        "tell me about",
        "tell me more",
        "эта квартира",
        "этот дом",
        "та квартира",
        "предыдущ",
        "последн",
        "упомянут",
        "подробнее",  # RU
        "bu daire",
        "bu ev",
        "o daire",
        "önceki",
        "son",
        "bahsedilen",
        "daha fazla",  # TR
    ]

    # Weak document QA indicators (need context to be meaningful)
    DOCUMENT_QA_WEAK_KEYWORDS = [
        "it",
        "this",
        "that",
    ]

    RECOMMENDATION_KEYWORDS = [
        "recommend",
        "suggest",
        "best",
        "optimal",
        "top",
        "ideal",
        "perfect",
        "most suitable",
        "good",
        "great",
        "value for money",
        "порекомендуй",
        "лучший",
        "топ",
        "идеальный",
        "хороший",
        "выгодный",  # RU
        "öner",
        "tavsiye",
        "en iyi",
        "ideal",
        "mükemmel",
        "iyi",  # TR
    ]

    # Urgency keywords
    URGENCY_KEYWORDS = [
        "asap",
        "urgent",
        "immediately",
        "right now",
        "quickly",
        "soon",
        "fast",
        "срочно",
        "немедленно",
        "быстро",
        "скоро",  # RU
        "acil",
        "hemen",
        "çabuk",
        "yakında",  # TR
    ]

    # Visualization keywords
    VISUALIZATION_KEYWORDS = [
        "chart",
        "graph",
        "plot",
        "visualize",
        "trend",
        "over time",
        "comparison table",
        "график",
        "диаграмм",
        "таблиц",
        "сравнен",  # RU
        "grafik",
        "tablo",
        "çizelge",  # TR
    ]

    # Filter extraction patterns
    # Price: match currency symbols or explicitly "price"/"cost" context if just number
    # For now, keeping simple but avoiding 4-digit years in specific ranges if possible?
    # Actually, let's keep the pattern but filter results later.
    PRICE_PATTERN = re.compile(r"\$?\d{1,5}(?:,\d{3})*(?:\.\d{2})?")
    ROOMS_PATTERN = re.compile(r"(\d+)[- ](?:bed(?:room)?|room|комнат|odalı)")
    CITY_PATTERN = re.compile(
        r"\b(warsaw|krakow|gdansk|wroclaw|poznan|warszawa|kraków|gdańsk|wrocław|poznań|варшав|краков|гданьск|вроцлав|познан|varşova)\w*",
        re.IGNORECASE,
    )
    # Added 'построен' (built) and 'yapı' (building/built) stems
    YEAR_PATTERN = re.compile(
        r"(?:built|year|год|yıl|построен|yapı)[\D]{0,10}(\d{4})", re.IGNORECASE
    )
    # Allow suffixes on class/rating words (e.g. sınıf-ı, класс-а)
    ENERGY_PATTERN = re.compile(
        r"(?:energy|epc|энергия|enerji)(?:\s+(?:class|rating|класс|sınıf)\w*)?\s+([A-G])\b",
        re.IGNORECASE,
    )

    # City normalization map
    CITY_VARIANTS = {
        "Warsaw": ["warsaw", "warszawa", "варшав", "varşova"],
        "Krakow": ["krakow", "kraków", "краков"],
        "Gdansk": ["gdansk", "gdańsk", "гданьск"],
        "Wroclaw": ["wroclaw", "wrocław", "вроцлав"],
        "Poznan": ["poznan", "poznań", "познан"],
    }

    # Multilingual Amenities - using stems for better matching
    PARKING_KEYWORDS = {
        "parking",
        "garage",
        "парковк",
        "гараж",
        "otopark",
        "garaj",
    }  # парковк(а/и/ой)
    GARDEN_KEYWORDS = {"garden", "yard", "сад", "двор", "bahçe"}
    POOL_KEYWORDS = {"pool", "бассейн", "havuz"}
    FURNISHED_KEYWORDS = {"furnished", "мебель", "меблир", "eşyalı", "mobilyalı"}  # меблир(ованная)
    ELEVATOR_KEYWORDS = {"elevator", "lift", "лифт", "asansör", "winda"}

    def analyze(self, query: str) -> QueryAnalysis:
        """
        Analyze a query and return enhanced classification.

        Enhanced features:
        - Confidence scoring based on keyword overlap and ambiguity
        - Multi-intent detection for complex queries
        - Intent modifiers for nuanced classification

        Args:
            query: User query string

        Returns:
            QueryAnalysis with intent, complexity, tools, confidence, and modifiers
        """
        query_lower = query.lower()

        # Detect language
        language = self._detect_language(query_lower)

        # Detect multi-intent with scores
        intent_scores, matched_keywords = self._score_all_intents(query_lower)

        # Get primary and secondary intents
        primary_intent, secondary_intents, intent_weights = self._get_multi_intent(intent_scores)

        # Extract filters (needed for legacy intent mapping)
        filters = self._extract_filters(query)

        # Extract intent modifiers (needed for legacy intent mapping)
        modifiers = self._extract_modifiers(query_lower)

        # For backward compatibility, map to legacy intent
        legacy_intent = self._to_legacy_intent(primary_intent, filters, modifiers)

        # Detect ambiguity signals
        ambiguity_signals = self._detect_ambiguity(
            query_lower, intent_scores, matched_keywords, primary_intent
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            query_lower,
            primary_intent,
            matched_keywords.get(primary_intent, []),
            intent_scores.get(primary_intent, 0.0),
            ambiguity_signals,
        )

        # Determine complexity
        complexity = self._determine_complexity_enhanced(
            query_lower, primary_intent, secondary_intents, filters
        )

        # Determine required tools
        tools = self._determine_tools_enhanced(
            primary_intent, secondary_intents, complexity, query_lower
        )

        # Determine processing strategy
        processing_strategy = self._determine_processing_strategy(
            confidence, secondary_intents, complexity
        )

        # Check for special requirements
        requires_computation = self._requires_computation(query_lower, primary_intent)
        requires_comparison = primary_intent == QueryIntent.COMPARISON
        requires_external_data = self._requires_external_data(query_lower)

        # Build enhanced analysis
        analysis = QueryAnalysis(
            query=query,
            intent=legacy_intent,  # Backward compatible
            complexity=complexity,
            requires_computation=requires_computation,
            requires_comparison=requires_comparison,
            requires_external_data=requires_external_data,
            tools_needed=tools,
            extracted_filters=filters,
            confidence=confidence,
            reasoning=self._generate_reasoning_enhanced(
                primary_intent,
                legacy_intent,
                secondary_intents,
                complexity,
                tools,
                confidence,
            ),
            # New enhanced fields
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            intent_weights=intent_weights,
            modifiers=modifiers,
            processing_strategy=processing_strategy,
            language_detected=language,
            ambiguity_signals=ambiguity_signals,
        )

        return analysis

    def _detect_language(self, query_lower: str) -> str:
        """Detect the language of the query (en, ru, tr)."""
        # Cyrillic characters indicate Russian
        if any("\u0400" <= c <= "\u04ff" for c in query_lower):
            return "ru"
        # Turkish-specific characters
        if any(c in "çğıöşü" for c in query_lower):
            return "tr"
        return "en"

    def _score_all_intents(
        self, query_lower: str
    ) -> tuple[Dict[QueryIntent, float], Dict[QueryIntent, List[str]]]:
        """
        Score all intents based on keyword matching.

        Uses priority weighting: specific intents (COMPARISON, MORTGAGE, etc.)
        get higher base scores than generic intents (PROPERTY_SEARCH).

        Returns:
            Tuple of (intent_scores, matched_keywords_by_intent)
        """
        intent_keyword_map = {
            QueryIntent.PROPERTY_SEARCH: self.PROPERTY_SEARCH_KEYWORDS,
            QueryIntent.COMPARISON: self.COMPARISON_KEYWORDS,
            QueryIntent.MORTGAGE: self.MORTGAGE_KEYWORDS,
            QueryIntent.MARKET_ANALYSIS: self.MARKET_ANALYSIS_KEYWORDS,
            QueryIntent.LOCATION: self.LOCATION_KEYWORDS,
            QueryIntent.DOCUMENT_QA: self.DOCUMENT_QA_KEYWORDS,
        }

        # Priority boost for specific intents (higher = more specific)
        intent_priority = {
            QueryIntent.COMPARISON: 2.0,  # Most specific
            QueryIntent.MORTGAGE: 1.8,
            QueryIntent.MARKET_ANALYSIS: 1.6,
            QueryIntent.DOCUMENT_QA: 1.4,
            QueryIntent.LOCATION: 1.2,
            QueryIntent.PROPERTY_SEARCH: 1.0,  # Least specific (fallback)
        }

        scores: Dict[QueryIntent, float] = {}
        matched: Dict[QueryIntent, List[str]] = {}

        for intent, keywords in intent_keyword_map.items():
            matches = [kw for kw in keywords if kw in query_lower]
            if matches:
                # Score based on number of matches and keyword specificity
                # Longer keywords get more weight (more specific)
                total_weight = sum(len(kw.split()) for kw in matches)
                max_possible = sum(len(kw.split()) for kw in keywords[:20])
                base_score = min(total_weight / max(max_possible, 1), 1.0)

                # Apply priority boost
                priority = intent_priority.get(intent, 1.0)
                scores[intent] = base_score * priority
                matched[intent] = matches
            else:
                scores[intent] = 0.0
                matched[intent] = []

        return scores, matched

    def _get_multi_intent(
        self, intent_scores: Dict[QueryIntent, float]
    ) -> tuple[QueryIntent, List[QueryIntent], Dict[str, float]]:
        """
        Determine primary and secondary intents from scores.

        Returns:
            Tuple of (primary_intent, secondary_intents, intent_weights)
        """
        # Sort intents by score
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)

        # Filter to non-zero scores
        non_zero = [(intent, score) for intent, score in sorted_intents if score > 0.0]

        if not non_zero:
            return QueryIntent.GENERAL, [], {}

        primary = non_zero[0][0]

        # Secondary intents have score > 0.2 and < primary score
        secondary = [
            intent
            for intent, score in non_zero[1:4]  # Top 3 secondary
            if score > 0.15
        ]

        # Build weights dict (normalized)
        total_score = sum(score for _, score in non_zero[:4]) or 1.0
        weights = {
            intent.value: round(score / total_score, 2)
            for intent, score in non_zero[:4]
            if score > 0.1
        }

        return primary, secondary, weights

    def _to_legacy_intent(
        self,
        intent: QueryIntent,
        filters: Dict[str, Any] | None = None,
        modifiers: Dict[str, bool] | None = None,
    ) -> QueryIntent:
        """Map new intent to legacy intent for backward compatibility."""
        # Check modifiers FIRST - they override intent classification
        if modifiers and modifiers.get("is_recommendation"):
            return QueryIntent.RECOMMENDATION

        # If intent is already a legacy one, return as-is
        legacy_intents = {
            QueryIntent.SIMPLE_RETRIEVAL,
            QueryIntent.FILTERED_SEARCH,
            QueryIntent.COMPARISON,
            QueryIntent.ANALYSIS,
            QueryIntent.CALCULATION,
            QueryIntent.RECOMMENDATION,
            QueryIntent.CONVERSATION,
            QueryIntent.GENERAL_QUESTION,
        }
        if intent in legacy_intents:
            return intent

        # Map new intents to legacy with context
        if intent == QueryIntent.PROPERTY_SEARCH:
            # Only certain filters make it FILTERED_SEARCH
            # Location alone is still simple retrieval
            filter_keys = set(filters.keys()) if filters else set()
            # These filters make it a "filtered search"
            complex_filters = {
                "min_price",
                "max_price",
                "rooms",
                "has_parking",
                "has_garden",
                "has_pool",
                "is_furnished",
                "has_elevator",
                "energy_ratings",
                "must_have_parking",
                "must_have_elevator",
            }
            if filter_keys & complex_filters:
                return QueryIntent.FILTERED_SEARCH
            return QueryIntent.SIMPLE_RETRIEVAL

        if intent == QueryIntent.DOCUMENT_QA:
            return QueryIntent.CONVERSATION

        mapping = {
            QueryIntent.MARKET_ANALYSIS: QueryIntent.ANALYSIS,
            QueryIntent.MORTGAGE: QueryIntent.CALCULATION,
            QueryIntent.LOCATION: QueryIntent.GENERAL_QUESTION,
            QueryIntent.GENERAL: QueryIntent.GENERAL_QUESTION,
        }
        return mapping.get(intent, QueryIntent.GENERAL_QUESTION)

    def _detect_ambiguity(
        self,
        query_lower: str,
        intent_scores: Dict[QueryIntent, float],
        matched_keywords: Dict[QueryIntent, List[str]],
        primary_intent: QueryIntent,
    ) -> List[str]:
        """Detect ambiguity signals that reduce classification confidence."""
        signals = []

        # Multiple strong intents (competing classifications)
        strong_intents = [i for i, s in intent_scores.items() if s > 0.3]
        if len(strong_intents) > 1:
            signals.append("multiple_strong_intents")

        # Short query (harder to classify)
        word_count = len(query_lower.split())
        if word_count < 3:
            signals.append("short_query")
        elif word_count < 5:
            signals.append("brief_query")

        # Pronouns without clear referent
        pronoun_patterns = [r"\bit\b", r"\bthis\b", r"\bthat\b", r"\bthe one\b"]
        if any(re.search(p, query_lower) for p in pronoun_patterns):
            # Check if there's context (property-related keywords nearby)
            if primary_intent != QueryIntent.DOCUMENT_QA:
                signals.append("unresolved_pronoun")

        # Negation words
        negation_words = ["not", "don't", "dont", "no", "neither", "nor", "excluding", "without"]
        if any(word in query_lower for word in negation_words):
            signals.append("negation_present")

        # No clear action verb
        action_verbs = (
            self.PROPERTY_SEARCH_KEYWORDS[:15]
            + self.COMPARISON_KEYWORDS[:5]
            + self.MORTGAGE_KEYWORDS[:5]
        )
        if not any(verb in query_lower for verb in action_verbs):
            signals.append("no_action_verb")

        # Low keyword coverage
        primary_matches = len(matched_keywords.get(primary_intent, []))
        if primary_matches == 0:
            signals.append("no_keyword_match")

        return signals

    def _calculate_confidence(
        self,
        query_lower: str,
        intent: QueryIntent,
        matched_keywords: List[str],
        pattern_strength: float,
        ambiguity_signals: List[str],
    ) -> float:
        """
        Calculate confidence score for classification.

        Formula:
            confidence = keyword_score * 0.4 + pattern_score * 0.3 - ambiguity_penalty * 0.3

        Returns:
            Float between 0.0 and 1.0
        """
        # Keyword overlap score
        keyword_count = len(matched_keywords)
        keyword_score = min(keyword_count / 3.0, 1.0)  # Cap at 3 keywords

        # Pattern strength (from scoring)
        pattern_score = pattern_strength

        # Ambiguity penalty
        ambiguity_penalty = len(ambiguity_signals) * 0.15

        # Calculate final confidence
        confidence = (
            keyword_score * 0.4
            + pattern_score * 0.3
            + 0.3  # Base confidence for reaching classification
            - ambiguity_penalty
        )

        return max(0.0, min(1.0, round(confidence, 2)))

    def _extract_modifiers(self, query_lower: str) -> Dict[str, bool]:
        """Extract intent modifier flags."""
        return {
            "is_recommendation": any(kw in query_lower for kw in self.RECOMMENDATION_KEYWORDS),
            "is_follow_up": any(kw in query_lower for kw in self.DOCUMENT_QA_KEYWORDS),
            "is_urgent": any(kw in query_lower for kw in self.URGENCY_KEYWORDS),
            "requires_visualization": any(kw in query_lower for kw in self.VISUALIZATION_KEYWORDS),
        }

    def _determine_processing_strategy(
        self,
        confidence: float,
        secondary_intents: List[QueryIntent],
        complexity: Complexity,
    ) -> ProcessingStrategy:
        """Determine the processing strategy based on confidence and intents."""
        if confidence < RoutingThresholds.LOW_CONFIDENCE:
            return ProcessingStrategy.CLARIFICATION

        if len(secondary_intents) == 0:
            return ProcessingStrategy.SINGLE_ROUTE

        if len(secondary_intents) >= 2 or complexity == Complexity.COMPLEX:
            return ProcessingStrategy.SEQUENTIAL

        return ProcessingStrategy.HYBRID

    def _determine_complexity_enhanced(
        self,
        query_lower: str,
        primary_intent: QueryIntent,
        secondary_intents: List[QueryIntent],
        filters: Dict[str, Any],
    ) -> Complexity:
        """Determine query complexity level (enhanced version)."""

        # Complex intents
        if primary_intent in [
            QueryIntent.MARKET_ANALYSIS,
            QueryIntent.COMPARISON,
            QueryIntent.MORTGAGE,
        ]:
            return Complexity.COMPLEX

        # Multi-intent queries are at least medium
        if len(secondary_intents) >= 2:
            return Complexity.COMPLEX
        if len(secondary_intents) == 1:
            return Complexity.MEDIUM

        # Multiple filters = medium complexity
        if len(filters) >= 3:
            return Complexity.MEDIUM

        # Recommendation needs reasoning
        if "is_recommendation" in query_lower or any(
            kw in query_lower for kw in self.RECOMMENDATION_KEYWORDS[:5]
        ):
            return Complexity.COMPLEX

        # Questions requiring explanation
        question_patterns = [r"\bwhy\b", r"\bhow\b", r"\bexplain\b", r"\bwhat is\b"]
        if any(re.search(pattern, query_lower) for pattern in question_patterns):
            return Complexity.MEDIUM

        return Complexity.SIMPLE

    def _determine_tools_enhanced(
        self,
        primary_intent: QueryIntent,
        secondary_intents: List[QueryIntent],
        complexity: Complexity,
        query_lower: str,
    ) -> List[Tool]:
        """Determine which tools are needed (enhanced version)."""
        tools = []

        # Property search needs RAG
        if primary_intent == QueryIntent.PROPERTY_SEARCH:
            tools.append(Tool.RAG_RETRIEVAL)

        # Comparison tool
        if primary_intent == QueryIntent.COMPARISON or QueryIntent.COMPARISON in secondary_intents:
            tools.extend([Tool.RAG_RETRIEVAL, Tool.COMPARATOR])

        # Mortgage calculation
        if primary_intent == QueryIntent.MORTGAGE or QueryIntent.MORTGAGE in secondary_intents:
            tools.append(Tool.MORTGAGE_CALC)

        # Market analysis
        if primary_intent == QueryIntent.MARKET_ANALYSIS:
            tools.extend([Tool.RAG_RETRIEVAL, Tool.PYTHON_CODE])

        # Location queries need RAG
        if primary_intent == QueryIntent.LOCATION:
            tools.append(Tool.RAG_RETRIEVAL)

        # Document QA needs RAG
        if primary_intent == QueryIntent.DOCUMENT_QA:
            tools.append(Tool.RAG_RETRIEVAL)

        # Web search for external data
        if self._requires_external_data(query_lower):
            tools.append(Tool.WEB_SEARCH)

        # Default to RAG if no tools determined
        if not tools:
            tools.append(Tool.RAG_RETRIEVAL)

        # Remove duplicates while preserving order
        seen = set()
        unique_tools = []
        for tool in tools:
            if tool not in seen:
                seen.add(tool)
                unique_tools.append(tool)

        return unique_tools

    def _generate_reasoning_enhanced(
        self,
        primary_intent: QueryIntent,
        legacy_intent: QueryIntent,
        secondary_intents: List[QueryIntent],
        complexity: Complexity,
        tools: List[Tool],
        confidence: float,
    ) -> str:
        """Generate human-readable reasoning for the enhanced classification."""
        reasoning_parts = [
            f"Classified as {legacy_intent.value}",
            f"Complexity: {complexity.value}",
            f"Confidence: {confidence:.0%}",
        ]

        if secondary_intents:
            secondary_names = [i.value for i in secondary_intents]
            reasoning_parts.append(f"Secondary intents: {', '.join(secondary_names)}")

        if tools:
            tool_names = [t.value for t in tools]
            reasoning_parts.append(f"Tools: {', '.join(tool_names)}")

        return ". ".join(reasoning_parts)

    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract structured filters from query."""
        filters: Dict[str, Any] = {}

        # Extract year
        year_match = self.YEAR_PATTERN.search(query)
        year_val = None
        if year_match:
            year_val = int(year_match.group(1))
            filters["year_built_min"] = year_val

        # Extract price
        prices = self.PRICE_PATTERN.findall(query)
        if prices:
            # Clean and convert
            price_values = []
            for p in prices:
                try:
                    val = float(p.replace("$", "").replace(",", ""))
                    # Filter out the year value if it was captured as a price
                    if year_val and abs(val - year_val) < 0.1:
                        continue
                    price_values.append(val)
                except ValueError:
                    continue

            if len(price_values) == 1:
                filters["max_price"] = price_values[0]
            elif len(price_values) >= 2:
                filters["min_price"] = min(price_values)
                filters["max_price"] = max(price_values)

        # Extract number of rooms
        rooms_match = self.ROOMS_PATTERN.search(query)
        if rooms_match:
            filters["rooms"] = int(rooms_match.group(1))

        # Extract city
        city_match = self.CITY_PATTERN.search(query)
        if city_match:
            city_str = city_match.group(0).lower()
            found_city = None
            for canonical, variants in self.CITY_VARIANTS.items():
                if any(v in city_str for v in variants):
                    found_city = canonical
                    break

            if found_city:
                filters["city"] = found_city
            else:
                filters["city"] = city_match.group(1).title()

        # Extract amenities
        query_lower = query.lower()
        if any(kw in query_lower for kw in self.PARKING_KEYWORDS):
            filters["has_parking"] = True
            filters["must_have_parking"] = True
        if any(kw in query_lower for kw in self.GARDEN_KEYWORDS):
            filters["has_garden"] = True
        if any(kw in query_lower for kw in self.POOL_KEYWORDS):
            filters["has_pool"] = True
        if any(kw in query_lower for kw in self.FURNISHED_KEYWORDS):
            filters["is_furnished"] = True
        if any(kw in query_lower for kw in self.ELEVATOR_KEYWORDS):
            filters["must_have_elevator"] = True
            filters["has_elevator"] = True

        # Extract energy
        energy_match = self.ENERGY_PATTERN.search(query)
        if energy_match:
            filters["energy_ratings"] = [energy_match.group(1).upper()]

        return filters

    def _determine_complexity(
        self, query_lower: str, intent: QueryIntent, filters: Dict[str, Any]
    ) -> Complexity:
        """Determine query complexity level."""

        # Complex intents
        if intent in [QueryIntent.ANALYSIS, QueryIntent.COMPARISON, QueryIntent.CALCULATION]:
            return Complexity.COMPLEX

        # Multiple filters = medium complexity
        if len(filters) >= 3:
            return Complexity.MEDIUM

        # Recommendation needs reasoning
        if intent == QueryIntent.RECOMMENDATION:
            return Complexity.COMPLEX

        # Questions requiring explanation (use word boundaries to avoid false matches like "show" matching "how")
        question_patterns = [r"\bwhy\b", r"\bhow\b", r"\bexplain\b", r"\bwhat is\b"]
        if any(re.search(pattern, query_lower) for pattern in question_patterns):
            return Complexity.MEDIUM

        # Simple retrieval
        return Complexity.SIMPLE

    def _determine_tools(
        self, intent: QueryIntent, complexity: Complexity, query_lower: str
    ) -> List[Tool]:
        """Determine which tools are needed."""
        tools = []

        # RAG is almost always needed
        if intent in [
            QueryIntent.SIMPLE_RETRIEVAL,
            QueryIntent.FILTERED_SEARCH,
            QueryIntent.CONVERSATION,
            QueryIntent.RECOMMENDATION,
        ]:
            tools.append(Tool.RAG_RETRIEVAL)

        # Comparison tool
        if intent == QueryIntent.COMPARISON:
            tools.extend([Tool.RAG_RETRIEVAL, Tool.COMPARATOR])

        # Calculation tools
        if intent == QueryIntent.CALCULATION:
            if "mortgage" in query_lower:
                tools.append(Tool.MORTGAGE_CALC)
            else:
                tools.append(Tool.CALCULATOR)

        # Analysis requires Python code execution
        if intent == QueryIntent.ANALYSIS:
            tools.extend([Tool.RAG_RETRIEVAL, Tool.PYTHON_CODE])

        # Web search for external data
        if any(
            kw in query_lower
            for kw in [
                "current",
                "currently",
                "latest",
                "market",
                "today",
                "news",
                "right now",
                "at the moment",
                "сейчас",
                "сегодня",
                "прямо сейчас",
                "актуал",
                "новост",
                "текущ",
                "рынок",
                "ставк",
            ]
        ):
            tools.append(Tool.WEB_SEARCH)

        # Default to RAG if no tools determined
        if not tools:
            tools.append(Tool.RAG_RETRIEVAL)

        return tools

    def _requires_computation(self, query_lower: str, intent: QueryIntent) -> bool:
        """Check if query requires numerical computation."""
        # Check for computation-heavy intents (both new and legacy)
        computation_intents = [
            QueryIntent.CALCULATION,
            QueryIntent.ANALYSIS,
            QueryIntent.MORTGAGE,
            QueryIntent.MARKET_ANALYSIS,
        ]
        return intent in computation_intents or any(
            word in query_lower
            for word in [
                "average",
                "mean",
                "sum",
                "total",
                "calculate",
                "compute",
                "percentage",
                "ratio",
            ]
        )

    def _requires_external_data(self, query_lower: str) -> bool:
        """Check if query needs external/current data."""
        return any(
            word in query_lower
            for word in [
                "current",
                "currently",
                "latest",
                "recent",
                "today",
                "market rate",
                "interest rate",
                "news",
                "right now",
                "at the moment",
                "сейчас",
                "сегодня",
                "прямо сейчас",
                "последн",
                "актуал",
                "новост",
                "текущ",
                "рынок",
                "ставк",
            ]
        )

    def _generate_reasoning(
        self, intent: QueryIntent, complexity: Complexity, tools: List[Tool]
    ) -> str:
        """Generate human-readable reasoning for the classification."""
        reasoning_parts = [
            f"Classified as {intent.value}",
            f"Complexity: {complexity.value}",
        ]

        if len(tools) > 0:
            tool_names = [t.value for t in tools]
            reasoning_parts.append(f"Tools: {', '.join(tool_names)}")

        return ". ".join(reasoning_parts)

    def analyze_with_context(
        self,
        query: str,
        session_history: Optional[List[Any]] = None,
        max_history_messages: int = 5,
    ) -> QueryAnalysis:
        """
        Analyze query with conversation context for enhanced classification.

        This method uses recent conversation history to:
        1. Resolve pronoun references ("it", "that property")
        2. Boost confidence when query aligns with conversation flow
        3. Detect follow-up questions and context-dependent intents

        Args:
            query: User query string
            session_history: List of recent chat messages (optional)
            max_history_messages: Maximum history messages to consider

        Returns:
            QueryAnalysis with context-enhanced classification
        """
        # First, do standard analysis
        analysis = self.analyze(query)

        # If no history, return standard analysis
        if not session_history:
            return analysis

        # Extract context signals from recent messages
        context = self._extract_context_signals(session_history[-max_history_messages:])

        # Apply context enhancements
        analysis = self._apply_context(analysis, context, query.lower())

        return analysis

    def _extract_context_signals(self, messages: List[Any]) -> Dict[str, Any]:
        """Extract context signals from recent messages."""
        signals: Dict[str, Any] = {
            "mentioned_properties": [],
            "mentioned_locations": [],
            "last_intent": None,
            "last_price_range": None,
            "has_property_context": False,
        }

        for msg in messages:
            content = ""
            if hasattr(msg, "content"):
                content = msg.content.lower()
            elif isinstance(msg, dict):
                content = msg.get("content", "").lower()

            if not content:
                continue

            # Check for property references
            if any(kw in content for kw in ["property", "apartment", "house", "listing"]):
                signals["has_property_context"] = True

            # Check for city references
            city_match = self.CITY_PATTERN.search(content)
            if city_match:
                city_str = city_match.group(0).lower()
                for canonical, variants in self.CITY_VARIANTS.items():
                    if any(v in city_str for v in variants):
                        signals["mentioned_locations"].append(canonical)
                        break

            # Check for price mentions
            prices = self.PRICE_PATTERN.findall(content)
            if prices:
                try:
                    price_vals = [float(p.replace("$", "").replace(",", "")) for p in prices]
                    if price_vals:
                        signals["last_price_range"] = (
                            min(price_vals),
                            max(price_vals),
                        )
                except ValueError:
                    pass

        return signals

    def _apply_context(
        self,
        analysis: QueryAnalysis,
        context: Dict[str, Any],
        query_lower: str,
    ) -> QueryAnalysis:
        """Apply context to enhance analysis."""

        # Check for pronoun references that need context
        pronoun_patterns = [
            r"\bit\b",
            r"\bthis\b",
            r"\bthat\b",
            r"\bthe one\b",
            r"\bthe property\b",
        ]
        has_pronoun = any(re.search(p, query_lower) for p in pronoun_patterns)

        # If query has pronouns and context has properties, boost DOCUMENT_QA
        if has_pronoun and context.get("has_property_context"):
            # Update to DOCUMENT_QA intent
            if analysis.primary_intent == QueryIntent.PROPERTY_SEARCH:
                analysis.primary_intent = QueryIntent.DOCUMENT_QA
                analysis.intent = QueryIntent.CONVERSATION
                analysis.confidence = min(analysis.confidence + 0.2, 1.0)
                if "context_resolved" not in analysis.ambiguity_signals:
                    analysis.ambiguity_signals.append("context_resolved")

        # If query mentions location and context has location, boost confidence
        if context.get("mentioned_locations"):
            city_match = self.CITY_PATTERN.search(query_lower)
            if city_match:
                analysis.confidence = min(analysis.confidence + 0.1, 1.0)

        return analysis


# Singleton instance
_analyzer = None


def get_query_analyzer() -> QueryAnalyzer:
    """Get or create query analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = QueryAnalyzer()
    return _analyzer


def analyze_query(query: str) -> QueryAnalysis:
    """
    Convenience function to analyze a query.

    Args:
        query: User query string

    Returns:
        QueryAnalysis result
    """
    analyzer = get_query_analyzer()
    return analyzer.analyze(query)
