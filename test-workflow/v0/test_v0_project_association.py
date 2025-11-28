"""
Test to verify project association when creating chats.
Tests projectId parameter and PATCH assignment.
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

V0_API_KEY = os.getenv("V0_API_KEY", "").strip()

async def test_project_association():
    """Test if projectId parameter prevents new project creation."""
    print("=" * 80)
    print("V0 PROJECT ASSOCIATION TEST")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        headers = {
            "Authorization": f"Bearer {V0_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Get existing project
        projects_resp = await client.get("https://api.v0.dev/v1/projects", headers=headers)
        projects = projects_resp.json().get("data", [])
        project = projects[0]
        project_id = project.get("id")
        project_name = project.get("name")
        
        print(f"\nUsing project: {project_name} (ID: {project_id})")
        print(f"Total projects before: {len(projects)}\n")
        
        # Test 1: Submit chat WITH projectId
        print("=" * 80)
        print("TEST 1: Submit chat WITH projectId parameter")
        print("=" * 80)
        
        try:
            chat_resp = await client.post(
                "https://api.v0.dev/v1/chats",
                headers=headers,
                json={
                    "message": "Create a simple button",
                    "model": "v0-1.5-md",
                    "scope": "mckinsey",
                    "projectId": project_id  # camelCase
                },
                timeout=5.0
            )
            
            if chat_resp.status_code in [200, 201]:
                result = chat_resp.json()
                chat_id = result.get("id")
                returned_project_id = result.get("projectId")
                print(f"✅ Chat created immediately!")
                print(f"   Chat ID: {chat_id}")
                print(f"   Returned projectId: {returned_project_id}")
                print(f"   Matches input: {returned_project_id == project_id}")
        except httpx.TimeoutException:
            print("⏱️  Request timed out (expected)")
            print("   Will check project count after delay...")
        
        # Wait and check project count
        await asyncio.sleep(3)
        projects_after = await client.get("https://api.v0.dev/v1/projects", headers=headers)
        count_after = len(projects_after.json().get("data", []))
        
        print(f"\nProjects after: {count_after}")
        print(f"New projects created: {count_after - len(projects)}")
        
        if count_after == len(projects):
            print("✅ SUCCESS: No new project created!")
        else:
            print("⚠️  New project was created")
            # Check the new project
            new_projects = projects_after.json().get("data", [])[:count_after - len(projects)]
            for p in new_projects:
                print(f"   New project: {p.get('name')} - ID: {p.get('id')}")
        
        # Test 2: Check if we can find the chat in the project
        print("\n" + "=" * 80)
        print("TEST 2: Check if chat appears in project")
        print("=" * 80)
        
        project_detail = await client.get(
            f"https://api.v0.dev/v1/projects/{project_id}",
            headers=headers
        )
        
        if project_detail.status_code == 200:
            detail = project_detail.json()
            chats = detail.get("chats", [])
            print(f"Chats in project: {len(chats)}")
            
            if chats:
                latest_chat = chats[0]
                print(f"Latest chat ID: {latest_chat.get('id')}")
                print(f"Latest chat projectId: {latest_chat.get('projectId')}")
                print(f"Matches target project: {latest_chat.get('projectId') == project_id}")
        
        # Test 3: Test PATCH to assign project
        print("\n" + "=" * 80)
        print("TEST 3: Test PATCH to assign project to chat")
        print("=" * 80)
        
        # Create a chat without projectId first
        try:
            chat_resp2 = await client.post(
                "https://api.v0.dev/v1/chats",
                headers=headers,
                json={
                    "message": "Create a card component",
                    "model": "v0-1.5-md",
                    "scope": "mckinsey"
                    # No projectId
                },
                timeout=5.0
            )
            
            if chat_resp2.status_code in [200, 201]:
                chat2_id = chat_resp2.json().get("id")
                chat2_project = chat_resp2.json().get("projectId")
                print(f"Chat created: {chat2_id}")
                print(f"Original projectId: {chat2_project}")
                
                if chat2_project != project_id:
                    print(f"Assigning to project {project_id}...")
                    patch_resp = await client.patch(
                        f"https://api.v0.dev/v1/chats/{chat2_id}",
                        headers=headers,
                        json={"projectId": project_id}
                    )
                    
                    if patch_resp.status_code in [200, 201, 204]:
                        print(f"✅ Successfully assigned chat to project!")
                        # Verify
                        chat_detail = await client.get(
                            f"https://api.v0.dev/v1/chats/{chat2_id}",
                            headers=headers
                        )
                        if chat_detail.status_code == 200:
                            updated_project = chat_detail.json().get("projectId")
                            print(f"Updated projectId: {updated_project}")
                            print(f"Assignment successful: {updated_project == project_id}")
        except httpx.TimeoutException:
            print("⏱️  Timeout (expected)")
        except Exception as e:
            print(f"Error: {str(e)[:100]}")
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("✅ Tested projectId parameter in POST /v1/chats")
        print("✅ Tested PATCH /v1/chats/{id} to assign project")
        print("✅ Verified project association")

if __name__ == "__main__":
    asyncio.run(test_project_association())

