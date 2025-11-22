#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from atlassian import Confluence
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

mcp = FastMCP("Confluence MCP Server")

confluence_url = os.getenv("CONFLUENCE_URL", "")
confluence_email = os.getenv("CONFLUENCE_EMAIL", "")
confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN", "")

if confluence_url and confluence_email and confluence_api_token:
    confluence_client = Confluence(
        url=confluence_url,
        username=confluence_email,
        password=confluence_api_token,
        cloud=True
    )
else:
    confluence_client = None
    logger.warning("Confluence credentials not configured")


@mcp.tool()
async def list_spaces() -> Dict[str, Any]:
    if not confluence_client:
        return {"error": "Confluence client not configured"}

    try:
        spaces = confluence_client.get_all_spaces(limit=100)
        space_list = []

        for space in spaces.get('results', []):
            space_list.append({
                "key": space.get('key'),
                "name": space.get('name'),
                "id": space.get('id'),
                "type": space.get('type'),
                "url": f"{confluence_url}/wiki/spaces/{space.get('key')}"
            })

        return {
            "spaces": space_list,
            "count": len(space_list)
        }
    except Exception as e:
        logger.error("list_spaces_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def get_space(space_key: str) -> Dict[str, Any]:
    if not confluence_client:
        return {"error": "Confluence client not configured"}

    try:
        space = confluence_client.get_space(space_key)
        return {
            "key": space.get('key'),
            "name": space.get('name'),
            "id": space.get('id'),
            "type": space.get('type'),
            "description": space.get('description', {}).get('plain', {}).get('value', ''),
            "url": f"{confluence_url}/wiki/spaces/{space.get('key')}"
        }
    except Exception as e:
        logger.error("get_space_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def create_page(
    space_key: str,
    title: str,
    content: str,
    parent_id: str = None
) -> Dict[str, Any]:
    if not confluence_client:
        return {"error": "Confluence client not configured"}

    try:
        page = confluence_client.create_page(
            space=space_key,
            title=title,
            body=content,
            parent_id=parent_id
        )

        return {
            "id": page.get('id'),
            "title": page.get('title'),
            "space": space_key,
            "version": page.get('version', {}).get('number', 1),
            "url": f"{confluence_url}/wiki{page.get('_links', {}).get('webui', '')}"
        }
    except Exception as e:
        logger.error("create_page_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def get_page(page_id: str) -> Dict[str, Any]:
    if not confluence_client:
        return {"error": "Confluence client not configured"}

    try:
        page = confluence_client.get_page_by_id(
            page_id,
            expand='body.storage,version,space'
        )

        return {
            "id": page.get('id'),
            "title": page.get('title'),
            "space": page.get('space', {}).get('key'),
            "content": page.get('body', {}).get('storage', {}).get('value', ''),
            "version": page.get('version', {}).get('number'),
            "created": page.get('version', {}).get('when'),
            "url": f"{confluence_url}/wiki{page.get('_links', {}).get('webui', '')}"
        }
    except Exception as e:
        logger.error("get_page_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def update_page(
    page_id: str,
    title: str,
    content: str
) -> Dict[str, Any]:
    if not confluence_client:
        return {"error": "Confluence client not configured"}

    try:
        page = confluence_client.get_page_by_id(page_id, expand='version')
        current_version = page.get('version', {}).get('number', 1)

        updated_page = confluence_client.update_page(
            page_id=page_id,
            title=title,
            body=content,
            version_number=current_version + 1
        )

        return {
            "id": updated_page.get('id'),
            "title": updated_page.get('title'),
            "version": updated_page.get('version', {}).get('number'),
            "url": f"{confluence_url}/wiki{updated_page.get('_links', {}).get('webui', '')}"
        }
    except Exception as e:
        logger.error("update_page_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def search_content(query: str, limit: int = 20) -> Dict[str, Any]:
    if not confluence_client:
        return {"error": "Confluence client not configured"}

    try:
        results = confluence_client.cql(
            f'text ~ "{query}"',
            limit=limit
        )

        content_list = []
        for result in results.get('results', []):
            content_list.append({
                "id": result.get('content', {}).get('id'),
                "title": result.get('content', {}).get('title'),
                "type": result.get('content', {}).get('type'),
                "space": result.get('content', {}).get('space', {}).get('key'),
                "url": f"{confluence_url}/wiki{result.get('content', {}).get('_links', {}).get('webui', '')}"
            })

        return {
            "results": content_list,
            "count": len(content_list),
            "query": query
        }
    except Exception as e:
        logger.error("search_content_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def get_page_children(page_id: str) -> Dict[str, Any]:
    if not confluence_client:
        return {"error": "Confluence client not configured"}

    try:
        children = confluence_client.get_page_child_by_type(
            page_id,
            type='page',
            limit=100
        )

        child_list = []
        for child in children:
            child_list.append({
                "id": child.get('id'),
                "title": child.get('title'),
                "url": f"{confluence_url}/wiki{child.get('_links', {}).get('webui', '')}"
            })

        return {
            "children": child_list,
            "count": len(child_list),
            "parent_id": page_id
        }
    except Exception as e:
        logger.error("get_page_children_error", error=str(e))
        return {"error": str(e)}


@mcp.resource("confluence://spaces")
async def spaces_resource() -> str:
    result = await list_spaces()
    if "error" in result:
        return f"Error: {result['error']}"
    return f"Found {result['count']} Confluence spaces"


if __name__ == "__main__":
    mcp.run(transport="stdio")
