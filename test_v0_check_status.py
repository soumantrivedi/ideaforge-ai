"""
Test script to check V0 project status directly using V0 API.
Tests the check-status functionality with projectId (camelCase).

Run with: python test_v0_check_status.py
Requires: V0_API_KEY in environment or .env file
"""
import asyncio
import os
import sys
import httpx
import json
from typing import Dict, Any, Optional

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded .env file from: {env_path}")
    else:
        print(f"⚠️  .env file not found at: {env_path}")
        print("   Using system environment variables")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")
    pass

V0_API_KEY = os.getenv("V0_API_KEY", "").strip()

if not V0_API_KEY:
    print("❌ V0_API_KEY environment variable is required")
    print("   Set it in .env file or export V0_API_KEY=your-key")
    sys.exit(1)

# Test payload data
TEST_PAYLOAD = {
    "product_id": "a7b8c9d0-e1f2-4345-a678-901234567890",
    "projectId": "J8hZlPsWQdX",  # Using camelCase as per V0 API format
    "provider": "v0",
    "prompt": "You are V0 (model: v0-1.5-md). The product mus"
}


async def check_v0_project_status_direct(
    project_id: str,
    v0_api_key: str
) -> Dict[str, Any]:
    """
    Check status of V0 project by getting latest chat and checking its status.
    This mimics the backend check_v0_project_status method.
    """
    print(f"\n🔍 Checking V0 project status...")
    print(f"   Project ID: {project_id}")
    print(f"   API Key: {v0_api_key[:15]}...")
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        headers = {
            "Authorization": f"Bearer {v0_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Step 1: Get project to find latest chat
            print(f"\n📡 Step 1: Fetching project details...")
            project_resp = await client.get(
                f"https://api.v0.dev/v1/projects/{project_id}",
                headers=headers
            )
            
            print(f"   Status Code: {project_resp.status_code}")
            
            if project_resp.status_code == 404:
                return {
                    "projectId": project_id,
                    "project_id": project_id,
                    "chat_id": None,
                    "project_status": "unknown",
                    "project_url": None,
                    "web_url": None,
                    "demo_url": None,
                    "is_complete": False,
                    "error": "Project not found"
                }
            
            if project_resp.status_code != 200:
                error_text = project_resp.text
                print(f"   ❌ Error: {error_text}")
                raise ValueError(f"Failed to get project: {project_resp.status_code} - {error_text}")
            
            project_data = project_resp.json()
            print(f"   ✅ Project found")
            print(f"   Project data keys: {list(project_data.keys())}")
            
            chats = project_data.get("chats", [])
            print(f"   Chats found: {len(chats)}")
            
            if not chats or len(chats) == 0:
                return {
                    "projectId": project_id,
                    "project_id": project_id,
                    "chat_id": None,
                    "project_status": "pending",
                    "project_url": None,
                    "web_url": None,
                    "demo_url": None,
                    "is_complete": False,
                    "note": "No chats found in project"
                }
            
            # Get latest chat (first in list, usually sorted by date)
            latest_chat = chats[0]
            chat_id = latest_chat.get("id")
            
            print(f"\n📡 Step 2: Fetching latest chat details...")
            print(f"   Chat ID: {chat_id}")
            
            if not chat_id:
                return {
                    "projectId": project_id,
                    "project_id": project_id,
                    "chat_id": None,
                    "project_status": "unknown",
                    "project_url": None,
                    "web_url": None,
                    "demo_url": None,
                    "is_complete": False,
                    "error": "No chat ID found"
                }
            
            # Step 2: Check chat status
            chat_resp = await client.get(
                f"https://api.v0.dev/v1/chats/{chat_id}",
                headers=headers
            )
            
            print(f"   Status Code: {chat_resp.status_code}")
            
            if chat_resp.status_code != 200:
                error_text = chat_resp.text
                print(f"   ❌ Error: {error_text}")
                return {
                    "projectId": project_id,
                    "project_id": project_id,
                    "chat_id": chat_id,
                    "project_status": "unknown",
                    "project_url": None,
                    "web_url": None,
                    "demo_url": None,
                    "is_complete": False,
                    "error": f"Failed to get chat: {chat_resp.status_code} - {error_text}"
                }
            
            chat_data = chat_resp.json()
            print(f"   ✅ Chat found")
            print(f"   Chat data keys: {list(chat_data.keys())}")
            
            # Extract URLs (V0 API uses camelCase)
            web_url = chat_data.get("webUrl") or chat_data.get("web_url")
            demo_url = chat_data.get("demo") or chat_data.get("demoUrl") or chat_data.get("demo_url")
            files = chat_data.get("files", [])
            
            print(f"\n📊 Status Summary:")
            print(f"   Web URL: {web_url}")
            print(f"   Demo URL: {demo_url}")
            print(f"   Files: {len(files)}")
            
            # Determine status
            is_complete = bool(demo_url or web_url or (files and len(files) > 0))
            project_status = "completed" if is_complete else "in_progress"
            project_url = demo_url or web_url or (f"https://v0.dev/chat/{chat_id}" if chat_id else None)
            
            result = {
                "projectId": project_id,  # camelCase to match V0 API format
                "project_id": project_id,  # snake_case for backward compatibility
                "chat_id": chat_id,
                "project_status": project_status,
                "project_url": project_url,
                "web_url": web_url,
                "demo_url": demo_url,
                "is_complete": is_complete,
                "num_files": len(files),
                "files": files
            }
            
            print(f"   Status: {project_status}")
            print(f"   Is Complete: {is_complete}")
            print(f"   Project URL: {project_url}")
            
            return result
            
        except httpx.RequestError as e:
            print(f"   ❌ Connection error: {str(e)}")
            raise ValueError(f"V0 API connection error: {str(e)}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            raise


async def test_check_status_with_payload():
    """Test check-status with the provided payload."""
    print("=" * 60)
    print("V0 Check Status Test")
    print("=" * 60)
    print(f"\n📋 Test Payload:")
    print(json.dumps(TEST_PAYLOAD, indent=2))
    
    project_id = TEST_PAYLOAD["projectId"]  # Using camelCase from payload
    
    try:
        result = await check_v0_project_status_direct(
            project_id=project_id,
            v0_api_key=V0_API_KEY
        )
        
        print("\n" + "=" * 60)
        print("✅ Test Results")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        
        # Validate response format
        print("\n🔍 Response Validation:")
        required_fields = ["projectId", "project_id", "project_status", "is_complete"]
        for field in required_fields:
            if field in result:
                print(f"   ✅ {field}: {result[field]}")
            else:
                print(f"   ❌ Missing field: {field}")
        
        # Check if using camelCase
        if "projectId" in result:
            print(f"\n✅ Response includes 'projectId' (camelCase): {result['projectId']}")
        if "project_id" in result:
            print(f"✅ Response includes 'project_id' (snake_case): {result['project_id']}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("🚀 Starting V0 Check Status Test...")
    result = asyncio.run(test_check_status_with_payload())
    
    if result:
        print("\n✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test failed!")
        sys.exit(1)

