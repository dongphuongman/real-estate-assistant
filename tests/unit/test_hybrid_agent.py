
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from agents.hybrid_agent import HybridPropertyAgent
from agents.query_analyzer import Complexity, QueryAnalysis, QueryIntent


class TestHybridPropertyAgent:
    
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content="Mocked answer")
        return llm
    
    @pytest.fixture
    def mock_retriever(self):
        retriever = MagicMock()
        retriever.get_relevant_documents.return_value = [
            Document(page_content="Doc 1", metadata={"id": "1"}),
            Document(page_content="Doc 2", metadata={"id": "2"})
        ]
        # Add search_with_filters method
        retriever.search_with_filters = MagicMock(return_value=[
            Document(page_content="Filtered Doc 1", metadata={"id": "f1"})
        ])
        return retriever
        
    @pytest.fixture
    def agent(self, mock_llm, mock_retriever):
        # Patch creation methods to avoid instantiation validation
        with patch("agents.hybrid_agent.HybridPropertyAgent._create_rag_chain") as mock_rag_create, \
             patch("agents.hybrid_agent.HybridPropertyAgent._create_tool_agent") as mock_tool_create, \
             patch("agents.hybrid_agent.create_property_tools", return_value=[]):
            
            # Setup mock returns
            mock_rag_create.return_value = MagicMock()
            mock_rag_create.return_value.invoke.return_value = {"answer": "RAG Answer", "source_documents": []}
            # When chain is called directly: chain(inputs) -> returns dict
            mock_rag_create.return_value.return_value = {"answer": "RAG Answer", "source_documents": []}
            
            mock_tool_create.return_value = MagicMock()
            mock_tool_create.return_value.invoke.return_value = {"output": "Agent Answer"}
            
            agent = HybridPropertyAgent(llm=mock_llm, retriever=mock_retriever)
            
            # Ensure attributes are set (mocks return new mocks)
            agent.rag_chain = mock_rag_create.return_value
            agent.tool_agent = mock_tool_create.return_value
            
            return agent

    def test_retrieve_documents_with_filters(self, agent, mock_retriever):
        """Test retrieval uses search_with_filters when filters are present."""
        query = "apartment in Krakow under 500k"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.MEDIUM,
            extracted_filters={"city": "Krakow", "max_price": 500000}
        )
        
        docs = agent._retrieve_documents(query, analysis)
        
        mock_retriever.search_with_filters.assert_called_once()
        args, kwargs = mock_retriever.search_with_filters.call_args
        assert args[0] == query
        assert args[1] == {"city": "Krakow", "max_price": 500000}
        assert docs[0].metadata["id"] == "f1"

    def test_retrieve_documents_without_filters(self, agent, mock_retriever):
        """Test retrieval falls back to get_relevant_documents when no filters."""
        query = "nice apartment"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.SIMPLE_RETRIEVAL,
            complexity=Complexity.SIMPLE,
            extracted_filters={}
        )
        
        docs = agent._retrieve_documents(query, analysis)
        
        mock_retriever.search_with_filters.assert_not_called()
        mock_retriever.get_relevant_documents.assert_called_once_with(query)
        assert docs[0].metadata["id"] == "1"

    def test_process_with_agent_uses_filtered_retrieval(self, agent, mock_retriever):
        """Test _process_with_agent calls _retrieve_documents."""
        query = "complex query with filters"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.ANALYSIS,
            complexity=Complexity.COMPLEX,
            extracted_filters={"city": "Warsaw"}
        )
        
        # Spy on _retrieve_documents
        with patch.object(agent, '_retrieve_documents', return_value=[
            Document(page_content="Filtered Context", metadata={})
        ]) as mock_retrieve:
            
            agent._process_with_agent(query, analysis)
            
            mock_retrieve.assert_called_once_with(query, analysis, k=3)
            
            # Check if agent was invoked with context
            args, _ = agent.tool_agent.invoke.call_args
            input_text = args[0]["input"]
            assert "Filtered Context" in input_text

    def test_process_with_rag_uses_filtered_retrieval(self, agent, mock_llm):
        """Test _process_with_rag uses manual retrieval + LLM when filters exist."""
        query = "simple filtered query"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.FILTERED_SEARCH,
            complexity=Complexity.SIMPLE,
            extracted_filters={"rooms": 2}
        )
        
        with patch.object(agent, '_retrieve_documents', return_value=[
            Document(page_content="Filtered RAG Doc", metadata={})
        ]) as mock_retrieve:
            
            result = agent._process_with_rag(query, analysis)
            
            mock_retrieve.assert_called_once()
            
            # Should invoke LLM directly, not rag_chain
            agent.rag_chain.assert_not_called() # Should be .invoke, but we mocked the object
            # Wait, rag_chain is a Mock, so we can check it wasn't called.
            # However, I mocked rag_chain.invoke in fixture?
            # The code calls self.rag_chain({"question": query}) which is __call__
            agent.rag_chain.assert_not_called()
            
            mock_llm.invoke.assert_called_once()
            assert result["method"] == "rag_filtered"
            assert result["answer"] == "Mocked answer"

    def test_process_hybrid_uses_rag_filtered(self, agent):
        """Test _process_hybrid delegates to _process_with_rag."""
        query = "hybrid query"
        analysis = QueryAnalysis(
            query=query,
            intent=QueryIntent.RECOMMENDATION,
            complexity=Complexity.COMPLEX,
            extracted_filters={"has_pool": True}
        )
        
        with patch.object(agent, '_process_with_rag', return_value={
            "answer": "RAG Base Answer",
            "source_documents": [],
            "method": "rag_filtered"
        }) as mock_rag:
            
            agent._process_hybrid(query, analysis)
            
            mock_rag.assert_called_once_with(query, analysis)
