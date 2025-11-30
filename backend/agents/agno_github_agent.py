"""
GitHub MCP Agent using Agno Framework
Integrates with GitHub MCP server for repository and file access
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


class AgnoGitHubAgent(AgnoBaseAgent):
    """
    GitHub MCP Agent using Agno framework.
    Specializes in accessing GitHub repositories, files, and content via MCP server.
    """

    def __init__(self, enable_rag: bool = False):
        system_prompt = """You are a GitHub Integration Specialist. Your primary function is to:
1. Access GitHub repositories and files via the GitHub MCP server
2. Retrieve file content from GitHub repositories
3. List repositories and their contents
4. Search for specific files or content in repositories
5. Extract and process documentation from GitHub URLs

When given a GitHub URL, extract the repository name and file path, then use the MCP server to retrieve the content.
Always provide clear, structured responses with source information.
"""
        super().__init__(
            name="GitHub MCP Agent",
            role="github_mcp",
            system_prompt=system_prompt,
            enable_rag=enable_rag,
            rag_table_name="github_knowledge_base",
            model_tier="fast",  # Use fast model for GitHub operations
            capabilities=[
                "github repository access",
                "file content retrieval",
                "repository listing",
                "documentation extraction",
                "code analysis",
                "github url processing"
            ]
        )
        self.mcp_server_url = settings.mcp_github_url

    async def fetch_from_github_url(
        self,
        github_url: str,
        user_id: str,
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch content from a GitHub URL using the MCP server.
        
        Args:
            github_url: GitHub URL (e.g., https://github.com/owner/repo/blob/branch/path/to/file.md)
            user_id: User ID for authentication
            product_id: Optional product ID for context
            
        Returns:
            Dictionary with content and metadata
        """
        self_logger = self.logger.bind(user_id=user_id, github_url=github_url)
        self_logger.info("fetching_github_url")
        
        try:
            # Parse GitHub URL to extract repo and path
            # Format: https://github.com/owner/repo/blob/branch/path/to/file
            parts = github_url.replace("https://github.com/", "").split("/")
            if len(parts) < 3:
                raise ValueError("Invalid GitHub URL format")
            
            owner = parts[0]
            repo = parts[1]
            branch = parts[3] if len(parts) > 3 and parts[2] == "blob" else "main"
            file_path = "/".join(parts[4:]) if len(parts) > 4 else None
            
            repo_name = f"{owner}/{repo}"
            
            # Call MCP server to get file content
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use MCP server's get_file_content tool
                mcp_response = await client.post(
                    f"{self.mcp_server_url}/tools/get_file_content",
                    json={
                        "repo_name": repo_name,
                        "file_path": file_path,
                        "branch": branch
                    },
                    headers={"Authorization": f"Bearer {user_id}"}  # Use user_id as auth for now
                )
                
                if mcp_response.status_code == 200:
                    file_data = mcp_response.json()
                    
                    # Add to knowledge base if RAG is enabled
                    if hasattr(self.agno_agent, 'knowledge') and self.agno_agent.knowledge:
                        content = file_data.get("content", "")
                        metadata = {
                            "source": "github",
                            "url": github_url,
                            "repo": repo_name,
                            "path": file_path,
                            "branch": branch,
                            "product_id": product_id
                        }
                        self.add_to_knowledge_base(content, metadata)
                    
                    return {
                        "success": True,
                        "content": file_data.get("content", ""),
                        "metadata": {
                            "url": github_url,
                            "repo": repo_name,
                            "path": file_path,
                            "branch": branch,
                            "size": file_data.get("size", 0)
                        }
                    }
                else:
                    raise Exception(f"MCP server error: {mcp_response.status_code}")
        
        except Exception as e:
            self_logger.error("github_fetch_error", error=str(e))
            raise

    async def list_repositories(
        self,
        org: Optional[str] = None,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        List repositories using GitHub MCP server.
        
        Args:
            org: Optional organization name
            user_id: User ID for authentication
            
        Returns:
            List of repository dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                mcp_response = await client.post(
                    f"{self.mcp_server_url}/tools/list_repositories",
                    json={"org": org} if org else {},
                    headers={"Authorization": f"Bearer {user_id}"} if user_id else {}
                )
                
                if mcp_response.status_code == 200:
                    data = mcp_response.json()
                    return data.get("repositories", [])
                else:
                    raise Exception(f"MCP server error: {mcp_response.status_code}")
        
        except Exception as e:
            self.logger.error("list_repositories_error", error=str(e))
            return []

    async def process(
        self,
        messages: List[AgentMessage],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Process messages, handling GitHub URL extraction and fetching."""
        # Check if any message contains a GitHub URL
        github_urls = []
        for msg in messages:
            import re
            urls = re.findall(r'https?://github\.com/[^\s]+', msg.content)
            github_urls.extend(urls)
        
        # If GitHub URLs found, fetch them and add to context
        if github_urls and context:
            user_id = context.get("user_id", "")
            product_id = context.get("product_id")
            
            for url in github_urls:
                try:
                    fetched_data = await self.fetch_from_github_url(url, user_id, product_id)
                    if fetched_data.get("success"):
                        # Add fetched content to the message context
                        context[f"github_content_{url}"] = fetched_data
                except Exception as e:
                    self.logger.warning("failed_to_fetch_github_url", url=url, error=str(e))
        
        return await super().process(messages, context)

