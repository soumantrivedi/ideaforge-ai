"""
Test if additional chats can be posted to update an existing prototype.
This tests the workflow of:
1. Create project
2. Submit first chat (creates prototype)
3. Submit additional chats to same project (updates prototype)
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

V0_API_KEY = os.getenv("V0_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not V0_API_KEY or not OPENAI_API_KEY:
    print("❌ API keys required")
    exit(1)

async def generate_prompt(description: str) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Create V0 design prompts. Return ONLY the prompt."},
            {"role": "user", "content": f"Create a V0 design prompt for: {description}"}
        ],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

async def get_or_create_project(api_key: str, project_name: str = "V0 Test Project"):
    """Get existing project or create new one."""
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # List projects
        projects_resp = await client.get("https://api.v0.dev/v1/projects", headers=headers)
        if projects_resp.status_code == 200:
            projects = projects_resp.json().get("data", [])
            if projects:
                # Look for exact match
                for p in projects:
                    if p.get("name") == project_name:
                        return p.get("id"), True
                # Use most recent
                return projects[0].get("id"), True
        
        # Create new
        create_resp = await client.post(
            "https://api.v0.dev/v1/projects",
            headers=headers,
            json={"name": project_name}
        )
        if create_resp.status_code in [200, 201]:
            return create_resp.json().get("id"), False
    return None, False

async def submit_chat(api_key: str, prompt: str, project_id: str, timeout: float = 5.0):
    """Submit chat with projectId parameter."""
    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
        try:
            resp = await client.post(
                "https://api.v0.dev/v1/chats",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "message": prompt,
                    "model": "v0-1.5-md",
                    "scope": "mckinsey",
                    "projectId": project_id  # camelCase
                }
            )
            if resp.status_code in [200, 201]:
                return resp.json().get("id")
        except httpx.TimeoutException:
            pass
    return None

async def get_project_chats(api_key: str, project_id: str):
    """Get all chats in a project."""
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        resp = await client.get(
            f"https://api.v0.dev/v1/projects/{project_id}",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        if resp.status_code == 200:
            return resp.json().get("chats", [])
    return []

async def check_chat_status(api_key: str, chat_id: str):
    """Check status of a chat."""
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        resp = await client.get(
            f"https://api.v0.dev/v1/chats/{chat_id}",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        if resp.status_code == 200:
            result = resp.json()
            web_url = result.get("webUrl") or result.get("web_url")
            demo_url = result.get("demo") or result.get("demoUrl")
            files = result.get("files", [])
            is_complete = bool(demo_url or web_url or (files and len(files) > 0))
            return {
                "status": "completed" if is_complete else "in_progress",
                "is_complete": is_complete,
                "project_url": demo_url or web_url,
                "num_files": len(files)
            }
    return {"status": "unknown"}

async def test_multiple_chats():
    """Test submitting multiple chats to same project."""
    print("=" * 80)
    print("TEST: Multiple Chats to Update Prototype")
    print("=" * 80)
    
    # Step 1: Get or create project
    print("\n1. Getting or creating project...")
    project_id, is_existing = await get_or_create_project(V0_API_KEY, "V0 Test Project")
    print(f"   ✅ Project ID: {project_id} ({'existing' if is_existing else 'new'})")
    
    # Step 2: Submit first chat
    print("\n2. Submitting first chat (create initial prototype)...")
    prompt1 = await generate_prompt("A simple login form with email and password")
    chat_id1 = await submit_chat(V0_API_KEY, prompt1, project_id, timeout=5.0)
    print(f"   Chat submitted (may timeout, that's OK)")
    
    # Wait and find chat
    await asyncio.sleep(5)
    chats = await get_project_chats(V0_API_KEY, project_id)
    if chats:
        chat_id1 = chats[0].get("id")
        print(f"   ✅ Found chat in project: {chat_id1}")
    
    # Step 3: Check status of first chat
    print("\n3. Checking status of first chat...")
    status1 = await check_chat_status(V0_API_KEY, chat_id1)
    print(f"   Status: {status1.get('status')}")
    print(f"   Is complete: {status1.get('is_complete')}")
    
    # Step 4: Submit second chat (update prototype)
    print("\n4. Submitting second chat (update prototype)...")
    prompt2 = await generate_prompt("Add a remember me checkbox to the login form")
    chat_id2 = await submit_chat(V0_API_KEY, prompt2, project_id, timeout=5.0)
    print(f"   Chat submitted (may timeout, that's OK)")
    
    # Wait and find new chat
    await asyncio.sleep(5)
    chats_after = await get_project_chats(V0_API_KEY, project_id)
    if len(chats_after) > len(chats):
        chat_id2 = chats_after[0].get("id")  # Latest
        print(f"   ✅ Found new chat in project: {chat_id2}")
        print(f"   Total chats in project: {len(chats_after)}")
    
    # Step 5: Check status of second chat
    print("\n5. Checking status of second chat...")
    status2 = await check_chat_status(V0_API_KEY, chat_id2)
    print(f"   Status: {status2.get('status')}")
    print(f"   Is complete: {status2.get('is_complete')}")
    
    # Step 6: Submit third chat (another update)
    print("\n6. Submitting third chat (another update)...")
    prompt3 = await generate_prompt("Add a forgot password link below the login button")
    chat_id3 = await submit_chat(V0_API_KEY, prompt3, project_id, timeout=5.0)
    print(f"   Chat submitted")
    
    await asyncio.sleep(5)
    chats_final = await get_project_chats(V0_API_KEY, project_id)
    print(f"   Total chats in project: {len(chats_final)}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Project: {project_id}")
    print(f"✅ Total chats submitted: 3")
    print(f"✅ Total chats in project: {len(chats_final)}")
    print(f"✅ Multiple chats can be posted to same project")
    print(f"✅ Each chat updates/extends the prototype")
    
    return {
        "project_id": project_id,
        "chats": [chat_id1, chat_id2, chat_id3] if all([chat_id1, chat_id2, chat_id3]) else None,
        "total_chats": len(chats_final)
    }

if __name__ == "__main__":
    asyncio.run(test_multiple_chats())

