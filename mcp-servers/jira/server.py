#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from jira import JIRA
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

mcp = FastMCP("Jira MCP Server")

jira_url = os.getenv("JIRA_URL", "")
jira_email = os.getenv("JIRA_EMAIL", "")
jira_api_token = os.getenv("JIRA_API_TOKEN", "")

if jira_url and jira_email and jira_api_token:
    jira_client = JIRA(
        server=jira_url,
        basic_auth=(jira_email, jira_api_token)
    )
else:
    jira_client = None
    logger.warning("Jira credentials not configured")


@mcp.tool()
async def list_projects() -> Dict[str, Any]:
    if not jira_client:
        return {"error": "Jira client not configured"}

    try:
        projects = jira_client.projects()
        project_list = []

        for project in projects:
            project_list.append({
                "key": project.key,
                "name": project.name,
                "id": project.id,
                "lead": project.lead.displayName if hasattr(project, 'lead') else None
            })

        return {
            "projects": project_list,
            "count": len(project_list)
        }
    except Exception as e:
        logger.error("list_projects_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def get_project(project_key: str) -> Dict[str, Any]:
    if not jira_client:
        return {"error": "Jira client not configured"}

    try:
        project = jira_client.project(project_key)
        return {
            "key": project.key,
            "name": project.name,
            "id": project.id,
            "description": getattr(project, 'description', None),
            "lead": project.lead.displayName if hasattr(project, 'lead') else None,
            "url": f"{jira_url}/browse/{project.key}"
        }
    except Exception as e:
        logger.error("get_project_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def create_epic(
    project_key: str,
    epic_name: str,
    summary: str,
    description: str = ""
) -> Dict[str, Any]:
    if not jira_client:
        return {"error": "Jira client not configured"}

    try:
        epic_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Epic'},
            'customfield_10011': epic_name
        }

        epic = jira_client.create_issue(fields=epic_dict)

        return {
            "key": epic.key,
            "id": epic.id,
            "name": epic_name,
            "summary": summary,
            "url": f"{jira_url}/browse/{epic.key}",
            "status": epic.fields.status.name
        }
    except Exception as e:
        logger.error("create_epic_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def create_story(
    project_key: str,
    summary: str,
    description: str,
    epic_key: str = None,
    priority: str = "Medium",
    labels: List[str] = None
) -> Dict[str, Any]:
    if not jira_client:
        return {"error": "Jira client not configured"}

    try:
        story_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Story'},
            'priority': {'name': priority},
        }

        if epic_key:
            story_dict['customfield_10014'] = epic_key

        if labels:
            story_dict['labels'] = labels

        story = jira_client.create_issue(fields=story_dict)

        return {
            "key": story.key,
            "id": story.id,
            "summary": summary,
            "url": f"{jira_url}/browse/{story.key}",
            "status": story.fields.status.name,
            "epic": epic_key
        }
    except Exception as e:
        logger.error("create_story_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def get_issue(issue_key: str) -> Dict[str, Any]:
    if not jira_client:
        return {"error": "Jira client not configured"}

    try:
        issue = jira_client.issue(issue_key)
        return {
            "key": issue.key,
            "id": issue.id,
            "summary": issue.fields.summary,
            "description": issue.fields.description,
            "type": issue.fields.issuetype.name,
            "status": issue.fields.status.name,
            "priority": issue.fields.priority.name if issue.fields.priority else None,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
            "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
            "created": issue.fields.created,
            "updated": issue.fields.updated,
            "url": f"{jira_url}/browse/{issue.key}"
        }
    except Exception as e:
        logger.error("get_issue_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def search_issues(jql: str, max_results: int = 50) -> Dict[str, Any]:
    if not jira_client:
        return {"error": "Jira client not configured"}

    try:
        issues = jira_client.search_issues(jql, maxResults=max_results)

        issue_list = []
        for issue in issues:
            issue_list.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "type": issue.fields.issuetype.name,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "url": f"{jira_url}/browse/{issue.key}"
            })

        return {
            "issues": issue_list,
            "count": len(issue_list),
            "jql": jql
        }
    except Exception as e:
        logger.error("search_issues_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def add_comment(issue_key: str, comment: str) -> Dict[str, Any]:
    if not jira_client:
        return {"error": "Jira client not configured"}

    try:
        comment_obj = jira_client.add_comment(issue_key, comment)
        return {
            "id": comment_obj.id,
            "issue_key": issue_key,
            "body": comment_obj.body,
            "created": comment_obj.created,
            "author": comment_obj.author.displayName
        }
    except Exception as e:
        logger.error("add_comment_error", error=str(e))
        return {"error": str(e)}


@mcp.resource("jira://projects")
async def projects_resource() -> str:
    result = await list_projects()
    if "error" in result:
        return f"Error: {result['error']}"
    return f"Found {result['count']} Jira projects"


if __name__ == "__main__":
    mcp.run(transport="stdio")
