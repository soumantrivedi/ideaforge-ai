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
            model_tier="fast",  # Use fast model for Atlassian operations
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
        product_id: Optional[str] = None,
        confluence_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetch a Confluence page using the Atlassian MCP server.
        
        Args:
            page_id: Confluence page ID
            user_id: User ID for authentication
            product_id: Optional product ID for context
            confluence_url: Optional Confluence URL (used to extract cloud ID)
            context: Optional context dict with credentials (preferred - avoids DB call)
            
        Returns:
            Dictionary with page content and metadata
        """
        self_logger = self.logger.bind(user_id=user_id, page_id=page_id)
        self_logger.info("fetching_confluence_page")
        
        try:
            # Extract Atlassian credentials from context (passed from API endpoint) or load from database
            atlassian_email = None
            atlassian_token = None
            cloud_id = None
            
            if context:
                # Use credentials from context (preferred - avoids DB call)
                atlassian_email = context.get("atlassian_email")
                atlassian_token = context.get("atlassian_token")
                user_keys = context.get("user_keys", {})
                cloud_id = user_keys.get("atlassian_cloud_id")
            
            # If not in context, load from database using AsyncSessionLocal
            if not atlassian_email or not atlassian_token:
                from backend.services.api_key_loader import load_user_api_keys_from_db
                from backend.database import AsyncSessionLocal
                
                async with AsyncSessionLocal() as db:
                    user_keys = await load_user_api_keys_from_db(db, user_id)
                
                atlassian_email = user_keys.get("atlassian_email") or user_keys.get("ATLASSIAN_EMAIL")
                atlassian_token = user_keys.get("atlassian_api_token") or user_keys.get("ATLASSIAN_API_TOKEN")
                if not cloud_id:
                    cloud_id = user_keys.get("atlassian_cloud_id")
            
            # Fallback to environment variables
            if not atlassian_email or not atlassian_token:
                from backend.config import settings
                atlassian_email = settings.jira_email or settings.confluence_email
                atlassian_token = settings.jira_api_token or settings.confluence_api_token
            
            if not atlassian_email or not atlassian_token:
                raise ValueError("Atlassian credentials not configured. Please configure Atlassian email and API token in Settings → Integrations.")
            
            # Extract cloud ID from URL if not already set
            if not cloud_id:
                # Try to extract from confluence_url parameter
                if confluence_url:
                    import re
                    url_match = re.search(r'https?://([^.]+)\.atlassian\.net', confluence_url)
                    if url_match:
                        cloud_id = url_match.group(1)
                
                # If still not found, try settings
                if not cloud_id:
                    from backend.config import settings
                    if settings.jira_url:
                        import re
                        url_match = re.search(r'https?://([^.]+)\.atlassian\.net', settings.jira_url)
                        if url_match:
                            cloud_id = url_match.group(1)
                    elif settings.confluence_url:
                        import re
                        url_match = re.search(r'https?://([^.]+)\.atlassian\.net', settings.confluence_url)
                        if url_match:
                            cloud_id = url_match.group(1)
                
                if not cloud_id:
                    raise ValueError("Atlassian Cloud ID not found. Please provide a full Confluence URL (e.g., https://your-domain.atlassian.net/wiki/...) or configure it in Settings → Integrations.")
            
            # Use Atlassian MCP server tools to fetch the page
            # The MCP server should be configured and accessible
            # For now, we'll use direct API call as fallback until MCP client is properly integrated
            import base64
            import httpx
            
            # Construct Confluence API URL
            # For Confluence Cloud, use: https://{site}.atlassian.net/wiki/api/v2/pages/{id}
            # The cloud_id extracted from URL is the site name (e.g., "mckinsey" from "mckinsey.atlassian.net")
            confluence_base_url = f"https://{cloud_id}.atlassian.net/wiki/api/v2"
            
            # Use Basic auth with email:API token for Confluence Cloud
            auth_header = base64.b64encode(f"{atlassian_email}:{atlassian_token}".encode()).decode()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch page using Confluence API v2
                # First, try to get page with expand parameter to get body content
                response = await client.get(
                    f"{confluence_base_url}/pages/{page_id}",
                    headers={
                        "Authorization": f"Basic {auth_header}",
                        "Accept": "application/json"
                    },
                    params={
                        "body-format": "atlas_doc_format,storage,view"
                    }
                )
                
                if response.status_code == 200:
                    page_data = response.json()
                    
                    # Extract content from response
                    content = ""
                    if "body" in page_data:
                        body_obj = page_data["body"]
                        # Try different body formats in order of preference
                        if "atlas_doc_format" in body_obj:
                            # Convert atlas_doc_format to markdown (simplified - just extract text)
                            atlas_doc = body_obj["atlas_doc_format"]
                            if isinstance(atlas_doc, dict):
                                # Try to extract text from atlas_doc_format structure
                                content = str(atlas_doc)
                            else:
                                content = str(atlas_doc)
                        elif "storage" in body_obj:
                            # Storage format (HTML-like)
                            storage_obj = body_obj["storage"]
                            if isinstance(storage_obj, dict) and "value" in storage_obj:
                                content = storage_obj["value"]
                            else:
                                content = str(storage_obj)
                        elif "view" in body_obj:
                            # View format (rendered HTML)
                            view_obj = body_obj["view"]
                            if isinstance(view_obj, dict) and "value" in view_obj:
                                content = view_obj["value"]
                            else:
                                content = str(view_obj)
                        else:
                            # Fallback: use entire body object as string
                            content = str(body_obj)
                    
                    # If still no content, try fetching with different format
                    if not content or len(content.strip()) < 10:
                        # Try fetching with storage format explicitly
                        storage_response = await client.get(
                            f"{confluence_base_url}/pages/{page_id}",
                            headers={
                                "Authorization": f"Basic {auth_header}",
                                "Accept": "application/json"
                            },
                            params={
                                "body-format": "storage"
                            }
                        )
                        if storage_response.status_code == 200:
                            storage_data = storage_response.json()
                            if "body" in storage_data and "storage" in storage_data["body"]:
                                storage_value = storage_data["body"]["storage"]
                                if isinstance(storage_value, dict) and "value" in storage_value:
                                    content = storage_value["value"]
                    
                    # If no content extracted, use title as fallback
                    if not content or len(content.strip()) < 10:
                        content = page_data.get("title", "No content available")
                    
                    page_title = page_data.get("title", "Confluence Page")
                    page_url = page_data.get("_links", {}).get("webui", "")
                    
                    # Add to knowledge base if RAG is enabled
                    if hasattr(self, 'agno_agent') and self.agno_agent and hasattr(self.agno_agent, 'knowledge') and self.agno_agent.knowledge:
                        metadata = {
                            "source": "confluence",
                            "page_id": page_id,
                            "product_id": product_id
                        }
                        self.add_to_knowledge_base(content, metadata)
                    
                    return {
                        "success": True,
                        "content": content,
                        "metadata": {
                            "page_id": page_id,
                            "title": page_title,
                            "url": page_url,
                            "space_id": page_data.get("spaceId"),
                            "version": page_data.get("version", {}).get("number", 1)
                        }
                    }
                elif response.status_code == 401:
                    error_detail = response.text
                    self_logger.error("confluence_auth_failed", status_code=401, error=error_detail, cloud_id=cloud_id, page_id=page_id)
                    raise ValueError("Atlassian authentication failed. Please verify your API token in Settings → Integrations.")
                elif response.status_code == 403:
                    error_detail = response.text
                    self_logger.error("confluence_forbidden", status_code=403, error=error_detail, cloud_id=cloud_id, page_id=page_id)
                    raise ValueError("Access forbidden. Please verify your API token has permission to access this Confluence page.")
                elif response.status_code == 404:
                    error_detail = response.text
                    self_logger.error("confluence_page_not_found", status_code=404, error=error_detail, cloud_id=cloud_id, page_id=page_id, url=confluence_url)
                    raise ValueError(f"Confluence page {page_id} not found. Please verify the page ID or URL. URL used: {confluence_url or 'N/A'}, Cloud ID: {cloud_id}")
                else:
                    error_text = response.text
                    self_logger.error("confluence_api_error", status_code=response.status_code, error=error_text, cloud_id=cloud_id, page_id=page_id)
                    raise Exception(f"Failed to fetch Confluence page: HTTP {response.status_code} - {error_text[:200]}")
        
        except ValueError as e:
            self_logger.error("confluence_fetch_validation_error", error=str(e))
            raise
        except Exception as e:
            self_logger.error("confluence_fetch_error", error=str(e), error_type=type(e).__name__)
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

