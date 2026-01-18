"""
Hybrid agent system combining RAG and tool-based agents.

This module provides intelligent orchestration between:
- Simple RAG for straightforward queries
- Tool-based agent for complex tasks
- Hybrid approach combining both
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, cast

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever

from agents.query_analyzer import Complexity, QueryAnalysis, QueryAnalyzer, QueryIntent
from tools.property_tools import create_property_tools

logger = logging.getLogger(__name__)


class HybridPropertyAgent:
    """
    Hybrid agent that intelligently routes queries to RAG or tool-based processing.

    This agent:
    1. Analyzes incoming queries
    2. Routes simple queries to RAG
    3. Routes complex queries to tool-based agent
    4. Combines both approaches when needed
    """

    def __init__(
        self,
        llm: BaseChatModel,
        retriever: BaseRetriever,
        memory: Optional[ConversationBufferMemory] = None,
        tools: Optional[List[BaseTool]] = None,
        verbose: bool = False
    ):
        """
        Initialize hybrid agent.

        Args:
            llm: Language model
            retriever: Vector store retriever
            memory: Conversation memory
            tools: List of tools (defaults to property tools)
            verbose: Enable verbose output
        """
        self.llm = llm
        self.retriever = retriever
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # Try to extract vector_store from retriever to enable tool actions
        vector_store = getattr(retriever, "vector_store", None)
        self.tools = tools or create_property_tools(vector_store=vector_store)
        
        self.verbose = verbose

        # Initialize query analyzer
        self.analyzer = QueryAnalyzer()

        # Initialize RAG chain
        self.rag_chain = self._create_rag_chain()

        # Initialize tool agent
        self.tool_agent = self._create_tool_agent()

    def _create_rag_chain(self) -> ConversationalRetrievalChain:
        """Create RAG chain for simple queries."""
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            verbose=self.verbose
        )

    def _create_tool_agent(self) -> AgentExecutor:
        """Create tool-based agent for complex queries."""

        # Create prompt template for tool agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent real estate assistant with access to specialized tools.

Your capabilities:
- Search property database for listings
- Calculate mortgage payments and costs
- Compare properties side-by-side
- Analyze prices and market trends
- Evaluate locations and neighborhoods

When answering:
1. Use tools when needed for calculations or analysis
2. Provide specific numbers and facts
3. Explain your reasoning
4. Be concise but thorough
5. Always cite sources when using property data

Context from property database will be provided when relevant."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # Create executor
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=self.verbose,
            return_intermediate_steps=True
        )

    def process_query(
        self,
        query: str,
        return_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        Process a query using the hybrid approach.

        Args:
            query: User query
            return_analysis: Whether to include query analysis in response

        Returns:
            Dictionary with answer, sources, and optional analysis
        """
        # Analyze query
        analysis = self.analyzer.analyze(query)

        if self.verbose:
            logger.info("Query Analysis: %s", analysis.reasoning)
            logger.info("Should use agent: %s", analysis.should_use_agent())

        # Route to appropriate processor
        if analysis.should_use_rag_only():
            result = self._process_with_rag(query, analysis)
        elif analysis.should_use_agent():
            result = self._process_with_agent(query, analysis)
        else:
            # Medium complexity - try RAG first, agent if needed
            result = self._process_hybrid(query, analysis)

        # Add analysis to result if requested
        if return_analysis:
            result["analysis"] = analysis.dict()

        return result

    def _retrieve_documents(
        self,
        query: str,
        analysis: QueryAnalysis,
        k: int = 5
    ) -> List[Document]:
        """
        Retrieve documents using hybrid search with explicit filters if available.
        
        Args:
            query: User query
            analysis: Query analysis result
            k: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        # Check if we have extracted filters
        filters = analysis.extracted_filters
        
        # Check if retriever supports explicit filtering (HybridPropertyRetriever)
        if filters and hasattr(self.retriever, "search_with_filters"):
            if self.verbose:
                logger.info(f"Using hybrid search with filters: {filters}")
            return cast(List[Document], self.retriever.search_with_filters(query, filters, k=k))
            
        # Fallback to standard retrieval
        if self.verbose:
            logger.info("Using standard retrieval")
        return self.retriever.get_relevant_documents(query)

    def _process_with_rag(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> Dict[str, Any]:
        """Process simple query with RAG only."""
        if self.verbose:
            logger.info("Processing with RAG only")

        try:
            # If we have filters, we should use them for better retrieval
            if analysis.extracted_filters:
                docs = self._retrieve_documents(query, analysis)
                
                # Construct context from docs
                context_text = "\n\n".join([doc.page_content for doc in docs])
                
                # Simple generation without history rephrasing for now
                # (Or we could implement rephrasing if needed)
                prompt = (
                    f"Answer the question based only on the following context:\n\n"
                    f"{context_text}\n\n"
                    f"Question: {query}"
                )
                
                response_msg = self.llm.invoke(prompt)
                answer = response_msg.content if hasattr(response_msg, "content") else str(response_msg)
                
                return {
                    "answer": answer,
                    "source_documents": docs,
                    "method": "rag_filtered",
                    "intent": analysis.intent.value
                }

            # Standard RAG chain
            response = self.rag_chain({"question": query})

            return {
                "answer": response["answer"],
                "source_documents": response.get("source_documents", []),
                "method": "rag",
                "intent": analysis.intent.value
            }

        except Exception as e:
            return {
                "answer": f"Error processing query with RAG: {str(e)}",
                "source_documents": [],
                "method": "rag",
                "error": str(e)
            }

    def _process_with_agent(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> Dict[str, Any]:
        """Process complex query with tool agent."""
        if self.verbose:
            logger.info("Processing with tool agent")

        try:
            # First, get relevant context from RAG if needed
            context_docs = []
            if analysis.intent not in [QueryIntent.CALCULATION, QueryIntent.GENERAL_QUESTION]:
                # Use hybrid retrieval with filters
                context_docs = self._retrieve_documents(query, analysis, k=3)

            # Add context to query if available
            enhanced_query = query
            if context_docs:
                context_text = "\n\n".join([
                    f"Property {i+1}: {doc.page_content[:200]}..."
                    for i, doc in enumerate(context_docs)
                ])
                enhanced_query = f"{query}\n\nRelevant properties:\n{context_text}"

            # Run agent
            response = self.tool_agent.invoke({
                "input": enhanced_query
            })

            return {
                "answer": response["output"],
                "source_documents": context_docs,
                "method": "agent",
                "intent": analysis.intent.value,
                "intermediate_steps": response.get("intermediate_steps", [])
            }

        except Exception as e:
            return {
                "answer": f"Error processing query with agent: {str(e)}",
                "source_documents": [],
                "method": "agent",
                "error": str(e)
            }

    def _process_hybrid(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> Dict[str, Any]:
        """Process with hybrid approach - RAG + agent capabilities."""
        if self.verbose:
            logger.info("Processing with hybrid approach")

        try:
            # Start with RAG for property retrieval (using filtered search if applicable)
            rag_response = self._process_with_rag(query, analysis)

            # Check if RAG answer is sufficient
            answer = rag_response["answer"]
            source_docs = rag_response.get("source_documents", [])

            # If query needs computation or deeper analysis, enhance with agent
            if analysis.requires_computation or analysis.complexity == Complexity.COMPLEX:
                # Use agent to enhance the answer
                enhanced_query = (
                    f"Based on this information about properties:\n\n"
                    f"{answer}\n\n"
                    f"Now answer this: {query}"
                )

                agent_response = self.tool_agent.invoke({
                    "input": enhanced_query
                })

                answer = agent_response["output"]

            return {
                "answer": answer,
                "source_documents": source_docs,
                "method": "hybrid",
                "intent": analysis.intent.value
            }

        except Exception:
            # Fallback to RAG-only
            return self._process_with_rag(query, analysis)

    async def astream_query(
        self,
        query: str
    ) -> AsyncIterator[str]:
        """
        Process a query using the hybrid approach and stream the response.
        
        Yields:
            JSON string chunks containing 'content' or 'error'.
        """
        try:
            # Analyze query
            analysis = self.analyzer.analyze(query)
            
            # Route to appropriate processor
            if analysis.should_use_rag_only():
                async for chunk in self._astream_with_rag(query, analysis):
                    yield chunk
            elif analysis.should_use_agent():
                async for chunk in self._astream_with_agent(query, analysis):
                    yield chunk
            else:
                # Hybrid
                async for chunk in self._astream_hybrid(query, analysis):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield json.dumps({"error": str(e)})

    async def _astream_with_rag(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> AsyncIterator[str]:
        """Stream RAG response."""
        try:
            async for event in self.rag_chain.astream_events(
                {"question": query},
                version="v1"
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield json.dumps({"content": content})
        except Exception as e:
             yield json.dumps({"error": str(e)})

    async def _astream_with_agent(
        self,
        query: str,
        analysis: QueryAnalysis,
        rag_context: str = ""
    ) -> AsyncIterator[str]:
        """Stream Agent response."""
        
        # Prepare input
        input_text = query
        if rag_context:
            input_text = f"Based on this information about properties:\n\n{rag_context}\n\nNow answer this: {query}"
        elif analysis.intent not in [QueryIntent.CALCULATION, QueryIntent.GENERAL_QUESTION]:
             # Async fetch docs
             try:
                 # We use sync retrieval here for now to support filters
                 context_docs = self._retrieve_documents(query, analysis, k=3)
                 if context_docs:
                    context_text = "\n\n".join([
                        f"Property {i+1}: {doc.page_content[:200]}..."
                        for i, doc in enumerate(context_docs)
                    ])
                    input_text = f"{query}\n\nRelevant properties:\n{context_text}"
             except Exception as e:
                 logger.warning(f"Retrieval failed in stream: {e}")
                 # If retrieval fails, fallback to no context
                 pass

        async for event in self.tool_agent.astream_events(
            {"input": input_text},
            version="v1"
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield json.dumps({"content": content})

    async def _astream_hybrid(
        self,
        query: str,
        analysis: QueryAnalysis
    ) -> AsyncIterator[str]:
        """Stream Hybrid response."""
        try:
            # 1. Run RAG silently
            rag_response = await self.rag_chain.ainvoke({"question": query})
            answer = rag_response["answer"]
            
            if analysis.requires_computation or analysis.complexity == Complexity.COMPLEX:
                # We need agent. Stream agent.
                async for chunk in self._astream_with_agent(query, analysis, rag_context=answer):
                    yield chunk
            else:
                # RAG is enough. Yield as single chunk (simulating stream end)
                yield json.dumps({"content": answer})
        except Exception:
            # Fallback to streaming RAG
            async for chunk in self._astream_with_rag(query, analysis):
                yield chunk

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self.memory.clear()

    def get_memory_summary(self) -> str:
        """Get summary of conversation memory."""
        return str(self.memory.load_memory_variables({}))


class SimpleRAGAgent:
    """
    Simple RAG-only agent for when tools aren't needed.

    This is a lightweight alternative to the full hybrid agent.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        retriever: BaseRetriever,
        memory: Optional[ConversationBufferMemory] = None,
        verbose: bool = False
    ) -> None:
        """Initialize simple RAG agent."""
        self.llm = llm
        self.retriever = retriever
        self.memory = memory or ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        self.verbose = verbose

        self.chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=self.memory,
            return_source_documents=True,
            verbose=verbose
        )

    def process_query(self, query: str) -> Dict[str, Any]:
        """Process query with RAG."""
        try:
            response = self.chain({"question": query})

            return {
                "answer": response["answer"],
                "source_documents": response.get("source_documents", []),
                "method": "rag_only"
            }

        except Exception as e:
            return {
                "answer": f"Error: {str(e)}",
                "source_documents": [],
                "method": "rag_only",
                "error": str(e)
            }

    def clear_memory(self) -> None:
        """Clear conversation memory."""
        self.memory.clear()


def create_hybrid_agent(
    llm: BaseChatModel,
    retriever: BaseRetriever,
    memory: Optional[ConversationBufferMemory] = None,
    use_tools: bool = True,
    verbose: bool = False
) -> Any:
    """
    Factory function to create an agent.

    Args:
        llm: Language model
        retriever: Vector store retriever
        memory: Optional memory instance
        use_tools: Whether to use tool-based agent (default: True)
        verbose: Enable verbose output

    Returns:
        HybridPropertyAgent or SimpleRAGAgent
    """
    if use_tools:
        return HybridPropertyAgent(
            llm=llm,
            retriever=retriever,
            memory=memory,
            verbose=verbose
        )
    else:
        return SimpleRAGAgent(
            llm=llm,
            retriever=retriever,
            memory=memory,
            verbose=verbose
        )
