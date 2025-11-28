"""
V0 Project-Based Workflow Test:
1. Create/get a project and get project_id immediately
2. Submit chat/message to that project
3. Check status by querying latest chat of the project_id

This approach avoids waiting 10-15 minutes by:
- Getting project_id immediately
- Submitting chat separately (may return immediately)
- Checking status by querying project's latest chat

Run with: python test-workflow/v0/test_v0_project_based_workflow.py
Requires: OPENAI_API_KEY and V0_API_KEY in environment
"""
import asyncio
import os
import sys
import httpx
from openai import AsyncOpenAI
from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta

# Add project root to path for .env file access
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path)
    print(f"✅ Loaded .env file from: {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
    pass

V0_API_KEY = os.getenv("V0_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY environment variable is required")
    sys.exit(1)
if not V0_API_KEY:
    print("❌ V0_API_KEY environment variable is required")
    sys.exit(1)


async def generate_v0_prompt_with_openai(product_description: str) -> str:
    """Generate a V0-ready prompt using OpenAI."""
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    system_prompt = """You are an expert at creating V0 (Vercel) design prompts. 
V0 generates React/Next.js components with Tailwind CSS and shadcn/ui.

Create a detailed, actionable prompt that:
1. Describes the UI components needed
2. Specifies layout and structure
3. Includes styling preferences (colors, typography, spacing)
4. Mentions responsive design requirements
5. Includes accessibility considerations

Return ONLY the prompt content, no headers, footers, or instructions."""

    user_prompt = f"""Create a V0 design prompt for: {product_description}"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    prompt = response.choices[0].message.content.strip()
    return clean_v0_prompt(prompt)


def clean_v0_prompt(prompt: str) -> str:
    """Clean V0 prompt by removing instructional headers/footers."""
    if not prompt:
        return prompt
    
    lines = prompt.split('\n')
    cleaned_lines = []
    skip_until_content = True
    
    skip_patterns = [
        "below is a v0-ready prompt",
        "below is a v0 prompt",
        "v0-ready prompt",
        "you can paste directly into",
        "v0 api or v0 ui",
        "written for `v0-1.5-md`",
        "assumes react",
        "assumes next.js",
        "tailwind",
        "shadcn/ui",
    ]
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if skip_until_content and not line_lower:
            continue
        
        should_skip = any(pattern in line_lower for pattern in skip_patterns)
        
        if should_skip:
            skip_until_content = True
            continue
        
        if line_lower and not should_skip:
            skip_until_content = False
            cleaned_lines.append(line)
        elif not skip_until_content:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip() or prompt


async def explore_v0_api_endpoints(api_key: str) -> Dict[str, Any]:
    """
    Explore V0 API to find project-related endpoints.
    Tests various endpoints to understand the API structure.
    """
    print(f"\n🔍 Exploring V0 API endpoints...")
    
    endpoints_to_test = [
        ("GET", "https://api.v0.dev/v1/projects", "List projects"),
        ("GET", "https://api.v0.dev/v1/user", "User info"),
        ("GET", "https://api.v0.dev/v1/user/projects", "User projects"),
        ("POST", "https://api.v0.dev/v1/projects", "Create project"),
    ]
    
    results = {}
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        
        for method, url, description in endpoints_to_test:
            try:
                print(f"   Testing {method} {url} ({description})...")
                if method == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    # POST with minimal body
                    response = await client.post(url, headers=headers, json={})
                
                print(f"      Status: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        results[url] = {
                            "status": response.status_code,
                            "method": method,
                            "data": data,
                            "keys": list(data.keys()) if isinstance(data, dict) else "not_dict"
                        }
                        print(f"      ✅ Success - Keys: {results[url]['keys']}")
                    except:
                        results[url] = {
                            "status": response.status_code,
                            "method": method,
                            "text": response.text[:200]
                        }
                        print(f"      ✅ Success - Text response")
                elif response.status_code == 404:
                    print(f"      ⚠️  Not found (404)")
                    results[url] = {"status": 404, "method": method, "exists": False}
                else:
                    print(f"      ⚠️  Status {response.status_code}: {response.text[:100]}")
                    results[url] = {"status": response.status_code, "method": method}
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:100]}")
                results[url] = {"status": "error", "method": method, "error": str(e)}
    
    return results


async def create_or_get_project(api_key: str, project_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Attempt to create or get a project.
    Returns project_id immediately if possible.
    """
    print(f"\n📦 Step 1: Creating/getting project...")
    
    # Try different approaches
    approaches = [
        {
            "name": "POST /v1/projects",
            "method": "POST",
            "url": "https://api.v0.dev/v1/projects",
            "body": {"name": project_name or "Test Project", "scope": "mckinsey"}
        },
        {
            "name": "GET /v1/user/projects",
            "method": "GET",
            "url": "https://api.v0.dev/v1/user/projects"
        },
        {
            "name": "GET /v1/projects",
            "method": "GET",
            "url": "https://api.v0.dev/v1/projects"
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        
        for approach in approaches:
            try:
                print(f"   Trying {approach['name']}...")
                if approach["method"] == "POST":
                    response = await client.post(
                        approach["url"],
                        headers=headers,
                        json=approach.get("body", {})
                    )
                else:
                    response = await client.get(approach["url"], headers=headers)
                
                print(f"      Status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    print(f"      ✅ Success!")
                    print(f"      Response keys: {list(result.keys()) if isinstance(result, dict) else 'not_dict'}")
                    
                    # Try to extract project_id
                    project_id = (
                        result.get("id") or 
                        result.get("project_id") or
                        result.get("projectId") or
                        (result.get("projects", [{}])[0].get("id") if isinstance(result.get("projects"), list) else None)
                    )
                    
                    if project_id:
                        return {
                            "success": True,
                            "project_id": project_id,
                            "project_url": result.get("url") or result.get("project_url"),
                            "method": approach["name"],
                            "data": result
                        }
                    else:
                        print(f"      ⚠️  No project_id found in response")
                        return {
                            "success": True,
                            "project_id": None,
                            "method": approach["name"],
                            "data": result,
                            "note": "No project_id in response, but endpoint exists"
                        }
                elif response.status_code == 404:
                    print(f"      ⚠️  Endpoint not found")
                    continue
                else:
                    print(f"      ⚠️  Status {response.status_code}: {response.text[:100]}")
                    continue
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:100]}")
                continue
    
    # If no project endpoint works, we'll use chat_id as project_id
    print(f"   ⚠️  No project endpoints found, will use chat-based approach")
    return {
        "success": False,
        "project_id": None,
        "note": "No project endpoints available, using chat-based workflow"
    }


async def submit_chat_to_project(api_key: str, prompt: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Submit a chat/message to a project.
    If project_id is provided, try to submit to that project.
    Otherwise, create a new chat (which may create a project).
    """
    print(f"\n💬 Step 2: Submitting chat/message...")
    
    async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        
        # Try to submit to project if project_id exists
        if project_id:
            # Try different endpoints for submitting to a project
            endpoints = [
                f"https://api.v0.dev/v1/projects/{project_id}/chats",
                f"https://api.v0.dev/v1/projects/{project_id}/messages",
                f"https://api.v0.dev/v1/projects/{project_id}/chat",
            ]
            
            for endpoint in endpoints:
                try:
                    print(f"   Trying to submit to project via {endpoint}...")
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        json={
                            "message": prompt,
                            "model": "v0-1.5-md",
                            "scope": "mckinsey"
                        }
                    )
                    
                    if response.status_code in [200, 201]:
                        result = response.json()
                        chat_id = result.get("id") or result.get("chat_id")
                        print(f"      ✅ Success! Chat ID: {chat_id}")
                        return {
                            "success": True,
                            "chat_id": chat_id,
                            "project_id": project_id,
                            "method": endpoint,
                            "data": result
                        }
                    elif response.status_code == 404:
                        continue
                except Exception as e:
                    continue
        
        # Fallback: Create new chat (standard approach)
        # Try to include project_id in the request if available
        print(f"   Using standard /v1/chats endpoint...")
        if project_id:
            print(f"   Attempting to associate chat with project {project_id}...")
        
        chat_payload = {
            "message": prompt,
            "model": "v0-1.5-md",
            "scope": "mckinsey"
        }
        
        # Try to include project_id if available
        if project_id:
            # Try different ways to specify project
            chat_payload["project_id"] = project_id
            # Also try projectId (camelCase)
            # chat_payload["projectId"] = project_id
        
        try:
            response = await client.post(
                "https://api.v0.dev/v1/chats",
                headers=headers,
                json=chat_payload
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                chat_id = result.get("id") or result.get("chat_id")
                
                # Try to extract project_id from response
                extracted_project_id = (
                    result.get("project_id") or
                    result.get("projectId") or
                    result.get("project", {}).get("id") if isinstance(result.get("project"), dict) else None
                )
                
                print(f"      ✅ Chat created! Chat ID: {chat_id}")
                if extracted_project_id:
                    print(f"      ✅ Project ID found: {extracted_project_id}")
                
                return {
                    "success": True,
                    "chat_id": chat_id,
                    "project_id": extracted_project_id or project_id or chat_id,  # Use chat_id as fallback
                    "method": "POST /v1/chats",
                    "data": result,
                    "note": "Used standard chat endpoint"
                }
            else:
                raise ValueError(f"HTTP {response.status_code}: {response.text[:200]}")
        except httpx.TimeoutException:
            # Even on timeout, if we got headers, we might have info
            raise ValueError("Request timed out - V0 API may be generating")
        except Exception as e:
            raise ValueError(f"Error submitting chat: {str(e)}")


async def get_project_latest_chat(api_key: str, project_id: str) -> Dict[str, Any]:
    """
    Get the latest chat of a project.
    This is used for status checking.
    """
    print(f"\n🔍 Getting latest chat for project {project_id}...")
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        
        # Get project info - it should contain chats array
        try:
            print(f"   Getting project info from /v1/projects/{project_id}...")
            response = await client.get(
                f"https://api.v0.dev/v1/projects/{project_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"      ✅ Success!")
                
                # Extract chats from project
                chats = result.get("chats", [])
                if isinstance(chats, list) and len(chats) > 0:
                    # Get the latest chat (first one, or sort by createdAt if available)
                    latest_chat = chats[0]
                    chat_id = latest_chat.get("id") or latest_chat.get("chat_id")
                    
                    # If we have multiple chats, try to find the latest by createdAt
                    if len(chats) > 1:
                        sorted_chats = sorted(
                            chats,
                            key=lambda x: x.get("createdAt", ""),
                            reverse=True
                        )
                        latest_chat = sorted_chats[0]
                        chat_id = latest_chat.get("id") or latest_chat.get("chat_id")
                    
                    print(f"      Found {len(chats)} chat(s), using latest: {chat_id}")
                    return {
                        "success": True,
                        "chat_id": chat_id,
                        "project_id": project_id,
                        "latest_chat": latest_chat,
                        "all_chats": chats,
                        "method": "GET /v1/projects/{project_id}"
                    }
                else:
                    print(f"      ⚠️  No chats found in project")
                    return {
                        "success": False,
                        "project_id": project_id,
                        "note": "Project exists but has no chats yet"
                    }
            elif response.status_code == 404:
                print(f"      ⚠️  Project not found")
                return {
                    "success": False,
                    "project_id": project_id,
                    "error": "Project not found"
                }
            else:
                print(f"      ⚠️  Status {response.status_code}: {response.text[:100]}")
                return {
                    "success": False,
                    "project_id": project_id,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e)
            }


async def check_status_by_project(api_key: str, project_id: str) -> Dict[str, Any]:
    """
    Check project status by getting latest chat and checking its status.
    """
    print(f"\n📊 Checking status for project {project_id}...")
    
    # First, try to get latest chat
    latest_chat_result = await get_project_latest_chat(api_key, project_id)
    
    if not latest_chat_result.get("success"):
        return {
            "success": False,
            "project_id": project_id,
            "error": "Could not get latest chat for project"
        }
    
    chat_id = latest_chat_result.get("chat_id")
    if not chat_id:
        return {
            "success": False,
            "project_id": project_id,
            "error": "No chat_id found in latest chat",
            "latest_chat_result": latest_chat_result
        }
    
    # Now check the chat status using the chat_id
    print(f"   Checking status of chat {chat_id}...")
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.get(
                f"https://api.v0.dev/v1/chats/{chat_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                web_url = result.get("webUrl") or result.get("web_url")
                demo_url = result.get("demo") or result.get("demoUrl")
                files = result.get("files", [])
                status = result.get("status", "unknown")
                
                is_complete = bool(demo_url or web_url or (files and len(files) > 0))
                
                return {
                    "success": True,
                    "project_id": project_id,
                    "chat_id": chat_id,
                    "status": "completed" if is_complete else status,
                    "is_complete": is_complete,
                    "project_url": demo_url or web_url,
                    "web_url": web_url,
                    "demo_url": demo_url,
                    "files": files,
                    "num_files": len(files)
                }
            else:
                return {
                    "success": False,
                    "project_id": project_id,
                    "chat_id": chat_id,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "chat_id": chat_id,
                "error": str(e)
            }


async def test_project_based_workflow():
    """Test the complete project-based workflow."""
    print("=" * 80)
    print("V0 PROJECT-BASED WORKFLOW TEST")
    print("=" * 80)
    print("\nThis test explores:")
    print("1. Creating/getting a project (should return project_id immediately)")
    print("2. Submitting chat to that project")
    print("3. Checking status by querying project's latest chat")
    print("=" * 80)
    
    product_description = "A simple login page with email and password fields"
    
    try:
        # Step 0: Explore API endpoints
        print("\n" + "=" * 80)
        print("STEP 0: Exploring V0 API endpoints...")
        print("=" * 80)
        api_exploration = await explore_v0_api_endpoints(V0_API_KEY)
        
        print("\n📋 API Exploration Results:")
        for endpoint, result in api_exploration.items():
            if result.get("status") == 200:
                print(f"   ✅ {endpoint}: Available")
                if "keys" in result:
                    print(f"      Keys: {result['keys']}")
            elif result.get("status") == 404:
                print(f"   ❌ {endpoint}: Not found")
            else:
                print(f"   ⚠️  {endpoint}: Status {result.get('status')}")
        
        # Step 1: Generate prompt
        print("\n" + "=" * 80)
        print("STEP 1: Generating V0 prompt...")
        print("=" * 80)
        v0_prompt = await generate_v0_prompt_with_openai(product_description)
        print(f"✅ Generated prompt ({len(v0_prompt)} chars)")
        
        # Step 2: Create/get project
        print("\n" + "=" * 80)
        print("STEP 2: Creating/getting project...")
        print("=" * 80)
        project_result = await create_or_get_project(V0_API_KEY, "Test Project")
        
        project_id = project_result.get("project_id")
        if project_id:
            print(f"✅ Got project_id: {project_id}")
        else:
            print(f"⚠️  No project_id from project creation, will use chat-based approach")
        
        # Step 3: Submit chat to project
        print("\n" + "=" * 80)
        print("STEP 3: Submitting chat to project...")
        print("=" * 80)
        print(f"   Project ID: {project_id}")
        print(f"   Attempting to submit chat to project...")
        
        chat_result = await submit_chat_to_project(V0_API_KEY, v0_prompt, project_id)
        
        if not chat_result.get("success"):
            print(f"❌ Failed to submit chat")
            return
        
        final_project_id = chat_result.get("project_id")
        chat_id = chat_result.get("chat_id")
        
        print(f"✅ Chat submitted!")
        print(f"   Project ID: {final_project_id}")
        print(f"   Chat ID: {chat_id}")
        print(f"   Method: {chat_result.get('method', 'unknown')}")
        
        # Check if chat response includes project info
        chat_data = chat_result.get("data", {})
        response_project_id = (
            chat_data.get("project_id") or
            chat_data.get("projectId") or
            (chat_data.get("project", {}).get("id") if isinstance(chat_data.get("project"), dict) else None)
        )
        
        if response_project_id:
            print(f"   ✅ Chat response includes project_id: {response_project_id}")
            if response_project_id != final_project_id:
                print(f"   ⚠️  Project ID mismatch: expected {final_project_id}, got {response_project_id}")
                final_project_id = response_project_id  # Use the one from response
        
        # Wait a moment for chat to be associated with project
        print(f"   ⏳ Waiting 5 seconds for chat to be associated with project...")
        await asyncio.sleep(5)
        
        # Step 4: Check status by project
        print("\n" + "=" * 80)
        print("STEP 4: Checking status by project...")
        print("=" * 80)
        status_result = await check_status_by_project(V0_API_KEY, final_project_id)
        
        if status_result.get("success"):
            print(f"✅ Status check successful!")
            print(f"   Status: {status_result.get('status')}")
            print(f"   Is complete: {status_result.get('is_complete')}")
            if status_result.get("project_url"):
                print(f"   Project URL: {status_result.get('project_url')}")
        else:
            print(f"⚠️  Status check failed: {status_result.get('error')}")
        
        # Summary
        print("\n" + "=" * 80)
        print("WORKFLOW SUMMARY")
        print("=" * 80)
        print(f"✅ Prompt generation: SUCCESS")
        print(f"{'✅' if project_id else '⚠️ '} Project creation: {'SUCCESS' if project_id else 'FALLBACK TO CHAT'}")
        print(f"✅ Chat submission: SUCCESS")
        print(f"{'✅' if status_result.get('success') else '⚠️ '} Status check: {'SUCCESS' if status_result.get('success') else 'PARTIAL'}")
        
        print("\n💡 Key Findings:")
        if project_id:
            print("   ✅ Project-based workflow is POSSIBLE")
            print("   ✅ Can get project_id immediately")
            print("   ✅ Can check status by querying project's latest chat")
        else:
            print("   ⚠️  Project endpoints may not be available")
            print("   ⚠️  Using chat_id as project_id fallback")
            print("   ⚠️  Status checking uses chat_id directly")
        
        return {
            "api_exploration": api_exploration,
            "project_result": project_result,
            "chat_result": chat_result,
            "status_result": status_result
        }
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_project_based_workflow())

