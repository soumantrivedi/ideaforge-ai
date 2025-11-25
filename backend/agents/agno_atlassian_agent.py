"""
Atlassian MCP Agent using Agno Framework
Integrates with Atlassian MCP server for Confluence document access
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
import httpx

from backend.agents.agno_base_agent import AgnoBaseAgent
from backend.models.schemas import AgentMessage, AgentResponse
from backend.config import settings
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = structlog.get_logger()


class AgnoAtlassianAgent(AgnoBaseAgent):
    """
    Atlassian MCP Agent using Agno framework.
    Specializes in accessing Confluence documents via Atlassian MCP server.
    """

    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are an Atlassian Confluence Integration Specialist. Your primary function is to:
1. Access Confluence spaces and pages via the Atlassian MCP server
2. Retrieve page content from Confluence
3. Search for content in Confluence
4. Extract and process documentation from Confluence URLs
5. Navigate Confluence page hierarchies

When given a Confluence URL or page ID, use the MCP server to retrieve the content.
Always provide clear, structured responses with source information.
"""
        super().__init__(
            name="Atlassian MCP Agent",
            role="atlassian_mcp",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="confluence_knowledge_base",
            capabilities=[
                "confluence page access",
                "confluence space navigation",
                "page content retrieval",
                "confluence search",
                "documentation extraction",
                "confluence url processing"
            ]
        )
        # Use Atlassian MCP server from mcp.json configuration
        # The MCP server URL is configured via SSE at https://mcp.atlassian.com/v1/sse
        # We'll use the MCP tools directly via the configured server

    async def fetch_confluence_page(
        self,
        page_id: str,
        user_id: str,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch a Confluence page using the Atlassian MCP server.
        
        Args:
            page_id: Confluence page ID
            user_id: User ID for authentication
            product_id: Optional product ID for context
            
        Returns:
            Dictionary with page content and metadata
        """
        self_logger = self.logger.bind(user_id=user_id, page_id=page_id)
        self_logger.info("fetching_confluence_page")
        
        try:
            # Use MCP server tools via the configured Atlassian MCP server
            # The MCP server is configured in mcp.json and accessible via MCP protocol
            # For now, we'll use a direct HTTP call pattern (MCP servers typically use stdio/SSE)
            
            # Note: Actual MCP integration would use the MCP client library
            # For now, we'll create a placeholder that can be extended
            
            # This would typically use the MCP client to call:
            # mcp_client.call_tool("get_page", {"page_id": page_id})
            
            # Placeholder implementation - in production, use proper MCP client
            page_data = {
                "id": page_id,
                "content": "",  # Would be fetched via MCP
                "title": "",
                "url": ""
            }
            
            # Add to knowledge base if RAG is enabled
            if hasattr(self.agno_agent, 'knowledge') and self.agno_agent.knowledge:
                content = page_data.get("content", "")
                metadata = {
                    "source": "confluence",
                    "page_id": page_id,
                    "product_id": product_id
                }
                self.add_to_knowledge_base(content, metadata)
            
            return {
                "success": True,
                "content": page_data.get("content", ""),
                "metadata": {
                    "page_id": page_id,
                    "title": page_data.get("title", ""),
                    "url": page_data.get("url", "")
                }
            }
        
        except Exception as e:
            self_logger.error("confluence_fetch_error", error=str(e))
            raise

    async def search_confluence(
        self,
        query: str,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search Confluence content using the Atlassian MCP server.
        
        Args:
            query: Search query
            user_id: User ID for authentication
            limit: Maximum number of results
            
        Returns:
            List of matching pages
        """
        try:
            # Use MCP server's search_content tool
            # This would typically use: mcp_client.call_tool("search_content", {"query": query, "limit": limit})
            
            # Placeholder implementation
            return []
        
        except Exception as e:
            self.logger.error("confluence_search_error", error=str(e))
            return []

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Process messages, handling Confluence URL/page ID extraction and fetching."""
        # Check if any message contains a Confluence URL or page ID
        confluence_refs = []
        for msg in messages:
            import re
            # Match Confluence URLs or page IDs
            urls = re.findall(r'https?://[^/]+/wiki/spaces/[^/]+/pages/(\d+)/', msg.content)
            page_ids = re.findall(r'confluence[:\s]+(\d+)', msg.content, re.IGNORECASE)
            confluence_refs.extend(urls + page_ids)
        
        # If Confluence references found, fetch them and add to context
        if confluence_refs and context:
            user_id = context.get("user_id", "")
            product_id = context.get("product_id")
            
            for page_id in confluence_refs:
                try:
                    fetched_data = await self.fetch_confluence_page(page_id, user_id, product_id)
                    if fetched_data.get("success"):
                        context[f"confluence_content_{page_id}"] = fetched_data
                except Exception as e:
                    self.logger.warning("failed_to_fetch_confluence_page", page_id=page_id, error=str(e))
        
        return await super().process(messages, context)

