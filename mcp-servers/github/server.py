#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from github import Github
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

mcp = FastMCP("GitHub MCP Server")

github_token = os.getenv("GITHUB_TOKEN", "")
github_org = os.getenv("GITHUB_ORG", "")

if github_token:
    github_client = Github(github_token)
else:
    github_client = None
    logger.warning("GitHub token not configured")


@mcp.tool()
async def list_repositories(org: str = None) -> Dict[str, Any]:
    if not github_client:
        return {"error": "GitHub client not configured"}

    try:
        target_org = org or github_org
        if target_org:
            organization = github_client.get_organization(target_org)
            repos = organization.get_repos()
        else:
            repos = github_client.get_user().get_repos()

        repo_list = []
        for repo in repos[:50]:
            repo_list.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "url": repo.html_url,
                "stars": repo.stargazers_count,
                "language": repo.language,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat()
            })

        return {
            "repositories": repo_list,
            "count": len(repo_list)
        }
    except Exception as e:
        logger.error("list_repositories_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def get_repository(repo_name: str) -> Dict[str, Any]:
    if not github_client:
        return {"error": "GitHub client not configured"}

    try:
        repo = github_client.get_repo(repo_name)
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "url": repo.html_url,
            "default_branch": repo.default_branch,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "open_issues": repo.open_issues_count,
            "language": repo.language,
            "topics": repo.get_topics(),
            "created_at": repo.created_at.isoformat(),
            "updated_at": repo.updated_at.isoformat(),
            "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None
        }
    except Exception as e:
        logger.error("get_repository_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def create_issue(
    repo_name: str,
    title: str,
    body: str,
    labels: List[str] = None,
    assignees: List[str] = None
) -> Dict[str, Any]:
    if not github_client:
        return {"error": "GitHub client not configured"}

    try:
        repo = github_client.get_repo(repo_name)
        issue = repo.create_issue(
            title=title,
            body=body,
            labels=labels or [],
            assignees=assignees or []
        )

        return {
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "state": issue.state,
            "created_at": issue.created_at.isoformat()
        }
    except Exception as e:
        logger.error("create_issue_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def list_pull_requests(repo_name: str, state: str = "open") -> Dict[str, Any]:
    if not github_client:
        return {"error": "GitHub client not configured"}

    try:
        repo = github_client.get_repo(repo_name)
        pulls = repo.get_pulls(state=state)

        pr_list = []
        for pr in pulls[:50]:
            pr_list.append({
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "url": pr.html_url,
                "author": pr.user.login,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat()
            })

        return {
            "pull_requests": pr_list,
            "count": len(pr_list)
        }
    except Exception as e:
        logger.error("list_pull_requests_error", error=str(e))
        return {"error": str(e)}


@mcp.tool()
async def get_file_content(repo_name: str, file_path: str, branch: str = None) -> Dict[str, Any]:
    if not github_client:
        return {"error": "GitHub client not configured"}

    try:
        repo = github_client.get_repo(repo_name)
        content = repo.get_contents(file_path, ref=branch or repo.default_branch)

        return {
            "path": content.path,
            "name": content.name,
            "content": content.decoded_content.decode('utf-8'),
            "size": content.size,
            "sha": content.sha,
            "url": content.html_url
        }
    except Exception as e:
        logger.error("get_file_content_error", error=str(e))
        return {"error": str(e)}


@mcp.resource("github://repositories")
async def repositories_resource() -> str:
    result = await list_repositories()
    if "error" in result:
        return f"Error: {result['error']}"
    return f"Found {result['count']} repositories"


if __name__ == "__main__":
    mcp.run(transport="stdio")
