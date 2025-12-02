"""
RAG (Retrieval-Augmented Generation) Agent with Vector Database Support
Uses pgvector for semantic search and knowledge retrieval
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse

logger = structlog.get_logger()


class RAGAgent(AgnoBaseAgent):
    """
    Specialized RAG agent for knowledge retrieval and synthesis.
    Uses vector database (pgvector) for semantic search.
    """
    
    def __init__(self):
        system_prompt = """You are a Knowledge Retrieval and Synthesis Specialist with access to a comprehensive knowledge base.

Your responsibilities:
1. Retrieve relevant information from the knowledge base using semantic search
2. Synthesize information from multiple sources
3. Provide accurate, well-sourced answers
4. Identify knowledge gaps and suggest areas for improvement
5. Cross-reference information for accuracy

When answering questions:
- Always cite sources from the knowledge base
- Synthesize information from multiple relevant documents
- If information is not in the knowledge base, clearly state this
- Provide context and background when relevant
- Use the retrieved knowledge to enhance your responses

Your responses should be:
- Accurate and well-sourced
- Comprehensive yet concise
- Contextually relevant
- Clear and easy to understand"""

        super().__init__(
            name="RAG Knowledge Agent",
            role="rag",
            system_prompt=system_prompt,
            enable_rag=True,  # Enable RAG with vector database
            rag_table_name="rag_knowledge_base",  # Custom table for RAG
            capabilities=[
                "knowledge retrieval",
                "semantic search",
                "information synthesis",
                "document search",
                "knowledge base",
                "vector search",
                "rag",
                "retrieval"
            ]
        )
        
        self.logger.info("rag_agent_initialized", rag_enabled=True)
    
    async def search_knowledge(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for relevant information.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            if not hasattr(self.agno_agent, 'knowledge') or not self.agno_agent.knowledge:
                self.logger.warning("knowledge_base_not_available")
                return []
            
            # Use Agno's knowledge base search
            results = self.agno_agent.knowledge.search(
                query=query,
                num_documents=top_k,
                filters=filters
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.content if hasattr(result, 'content') else str(result),
                    "metadata": result.metadata if hasattr(result, 'metadata') else {},
                    "score": result.score if hasattr(result, 'score') else None
                })
            
            self.logger.info("knowledge_search_completed", query=query, results_count=len(formatted_results))
            return formatted_results
            
        except Exception as e:
            self.logger.error("knowledge_search_error", error=str(e))
            return []
    
    async def add_knowledge(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add content to the knowledge base.
        
        Args:
            content: Content to add
            metadata: Optional metadata (e.g., product_id, source, title)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.add_to_knowledge_base(content, metadata)
            self.logger.info("knowledge_added", content_length=len(content))
            return True
        except Exception as e:
            self.logger.error("failed_to_add_knowledge", error=str(e))
            return False
    
    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Process messages with RAG-enhanced responses.
        Returns empty response if no knowledge base content is available.
        """
        # Extract the query from messages
        query = messages[-1].content if messages else ""
        
        # CRITICAL: Filter by product_id if available in context
        # This ensures only documents for the specific product are retrieved
        filters = {}
        if context and context.get("product_id"):
            filters["product_id"] = str(context.get("product_id"))
            self.logger.info("rag_filtering_by_product_id", product_id=context.get("product_id"))
        
        # Search knowledge base first with product_id filter
        knowledge_results = await self.search_knowledge(query, top_k=5, filters=filters if filters else None)
        
        # If no knowledge results, return empty response immediately (don't process)
        if not knowledge_results:
            self.logger.info("rag_skipped_no_knowledge", query=query[:100])
            from backend.models.schemas import AgentResponse
            return AgentResponse(
                agent_type="rag",
                response="No knowledge base content available.",
                metadata={"skipped": True, "reason": "no_knowledge_base_content", "knowledge_count": 0},
                timestamp=datetime.utcnow()
            )
        
        # Enhance context with knowledge results
        enhanced_context = context or {}
        enhanced_context["knowledge_results"] = knowledge_results
        enhanced_context["knowledge_count"] = len(knowledge_results)
        
        # Call parent process method only if we have knowledge results
        return await super().process(messages, enhanced_context)

