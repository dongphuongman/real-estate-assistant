"""
LLM-based fallback classifier for low-confidence queries.

When the rule-based classifier has low confidence, this module uses an LLM
to provide more accurate intent classification.

Task #66: Query Intent Classification Enhancement
"""

import json
from typing import Tuple

from langchain_core.language_models import BaseChatModel

from agents.query_analyzer import (
    Complexity,
    QueryAnalysis,
    QueryIntent,
    RoutingThresholds,
)

# Prompt template for LLM classification
CLASSIFICATION_PROMPT = """You are a query intent classifier for a real estate assistant.

Classify the following user query into one of these intent categories:

1. property_search - Finding, showing, or searching for properties
2. market_analysis - Analyzing prices, trends, statistics, averages
3. comparison - Comparing two or more properties or areas
4. mortgage - Calculating mortgage, loans, or payments
5. location - Questions about neighborhoods, districts, or areas
6. document_qa - Questions about specific properties mentioned in context
7. general - General real estate questions or out-of-domain queries

Query: "{query}"

Respond with a JSON object containing:
- "intent": one of [property_search, market_analysis, comparison, mortgage, location, document_qa, general]
- "confidence": a float between 0.0 and 1.0 indicating classification confidence
- "complexity": one of [simple, medium, complex]
- "reasoning": a brief explanation of the classification

Example response:
{"intent": "property_search", "confidence": 0.95, "complexity": "simple", "reasoning": "User is asking to show apartments, which is a direct property search request"}

Respond with ONLY the JSON object, no additional text."""


class LLMIntentClassifier:
    """
    Fallback classifier using LLM for ambiguous queries.

    This is used when the rule-based classifier has low confidence
    (below RoutingThresholds.LOW_CONFIDENCE).
    """

    def __init__(self, llm: BaseChatModel):
        """
        Initialize the LLM classifier.

        Args:
            llm: LangChain chat model to use for classification
        """
        self.llm = llm

    async def classify(self, query: str) -> Tuple[QueryIntent, float, Complexity, str]:
        """
        Use LLM to classify query intent.

        Args:
            query: User query string

        Returns:
            Tuple of (intent, confidence, complexity, reasoning)
        """
        prompt = CLASSIFICATION_PROMPT.format(query=query)

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content

            # Parse JSON response
            # Handle potential markdown code blocks
            if "```" in content:
                # Extract JSON from code block
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)

            # Map string to enum
            intent_map = {
                "property_search": QueryIntent.PROPERTY_SEARCH,
                "market_analysis": QueryIntent.MARKET_ANALYSIS,
                "comparison": QueryIntent.COMPARISON,
                "mortgage": QueryIntent.MORTGAGE,
                "location": QueryIntent.LOCATION,
                "document_qa": QueryIntent.DOCUMENT_QA,
                "general": QueryIntent.GENERAL,
            }

            intent = intent_map.get(result["intent"], QueryIntent.GENERAL)
            confidence = float(result.get("confidence", 0.5))
            complexity_str = result.get("complexity", "simple")
            reasoning = result.get("reasoning", "")

            complexity_map = {
                "simple": Complexity.SIMPLE,
                "medium": Complexity.MEDIUM,
                "complex": Complexity.COMPLEX,
            }
            complexity = complexity_map.get(complexity_str, Complexity.SIMPLE)

            return intent, confidence, complexity, reasoning

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback to general with low confidence
            return QueryIntent.GENERAL, 0.3, Complexity.SIMPLE, f"LLM parsing failed: {e}"

    async def classify_with_analysis(
        self,
        query: str,
        rule_based_analysis: QueryAnalysis,
    ) -> QueryAnalysis:
        """
        Enhance rule-based analysis with LLM classification.

        This is called when rule-based confidence is below threshold.
        The LLM result is merged with the existing analysis.

        Args:
            query: User query string
            rule_based_analysis: Analysis from rule-based classifier

        Returns:
            Enhanced QueryAnalysis with LLM classification
        """
        intent, confidence, complexity, reasoning = await self.classify(query)

        # Create new analysis based on LLM result but preserving rule-based data
        return QueryAnalysis(
            query=query,
            intent=rule_based_analysis.intent,  # Keep legacy intent for compatibility
            complexity=complexity,
            requires_computation=rule_based_analysis.requires_computation,
            requires_comparison=intent == QueryIntent.COMPARISON,
            requires_external_data=rule_based_analysis.requires_external_data,
            tools_needed=rule_based_analysis.tools_needed,
            extracted_filters=rule_based_analysis.extracted_filters,
            confidence=confidence,
            reasoning=f"LLM: {reasoning}",
            primary_intent=intent,
            secondary_intents=rule_based_analysis.secondary_intents,
            intent_weights=rule_based_analysis.intent_weights,
            modifiers=rule_based_analysis.modifiers,
            processing_strategy=rule_based_analysis.processing_strategy,
            language_detected=rule_based_analysis.language_detected,
            ambiguity_signals=rule_based_analysis.ambiguity_signals,
        )


def should_use_llm_fallback(analysis: QueryAnalysis) -> bool:
    """
    Determine if LLM fallback should be used.

    Args:
        analysis: QueryAnalysis from rule-based classifier

    Returns:
        True if LLM fallback should be used
    """
    return analysis.confidence < RoutingThresholds.LOW_CONFIDENCE
