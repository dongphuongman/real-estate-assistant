from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from agents.hybrid_agent import HybridPropertyAgent, SimpleRAGAgent
from agents.query_analyzer import Complexity, QueryAnalysis, QueryIntent


def test_hybrid_property_agent_get_sources_for_query_uses_retrieve_documents():
    llm = MagicMock()
    retriever = MagicMock()

    with (
        patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=MagicMock()),
        patch("agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=MagicMock()),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.FILTERED_SEARCH,
        complexity=Complexity.SIMPLE,
        extracted_filters={"city": "Krakow"},
    )
    agent.analyzer.analyze = MagicMock(return_value=analysis)
    expected = [Document(page_content="Doc", metadata={"id": "x"})]

    with patch.object(agent, "_retrieve_documents", return_value=expected) as mock_retrieve:
        docs = agent.get_sources_for_query("q", k=3)
        assert docs == expected
        mock_retrieve.assert_called_once_with("q", analysis, k=3)


def test_hybrid_property_agent_get_sources_for_query_skips_calculation_intent():
    llm = MagicMock()
    retriever = MagicMock()

    with (
        patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain", return_value=MagicMock()),
        patch("agents.hybrid_agent.HybridPropertyAgent._create_tool_agent", return_value=MagicMock()),
        patch("agents.hybrid_agent.create_property_tools", return_value=[]),
    ):
        agent = HybridPropertyAgent(llm=llm, retriever=retriever)

    analysis = QueryAnalysis(
        query="q",
        intent=QueryIntent.CALCULATION,
        complexity=Complexity.SIMPLE,
        extracted_filters={},
    )
    agent.analyzer.analyze = MagicMock(return_value=analysis)
    assert agent.get_sources_for_query("q") == []


def test_simple_rag_agent_get_sources_for_query_returns_empty_on_error():
    retriever = MagicMock()
    retriever.get_relevant_documents.side_effect = RuntimeError("fail")
    with patch("agents.hybrid_agent.ConversationalRetrievalChain.from_llm", return_value=MagicMock()):
        agent = SimpleRAGAgent(llm=MagicMock(), retriever=retriever)
    assert agent.get_sources_for_query("q") == []
