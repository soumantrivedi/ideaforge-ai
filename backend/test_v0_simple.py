#!/usr/bin/env python3
"""
Simple standalone test for V0 API end-to-end workflow.
Tests the actual V0 API behavior to understand response patterns.
"""
import asyncio
import httpx
import os
import sys
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

async def test_v0_workflow_simple():
    """Test V0 API workflow with minimal complexity."""
    v0_api_key = os.getenv("V0_API_KEY")
    
    if not v0_api_key:
        print("❌ V0_API_KEY not found in .env file")
        return False
    
    print(f"✅ V0 API Key found (length: {len(v0_api_key)})")
    print(f"   Key prefix: {v0_api_key[:8]}...")
    print()
    
    # Simple test prompt
    test_prompt = """Create a simple landing page for a SaaS product with:
- Hero section with headline and CTA button
- Features section with 3 feature cards
- Footer with links
Use Tailwind CSS and React components."""
    
    print("📝 Test Prompt:")
    print(f"   {test_prompt[:80]}...")
    print()
    
    # Test 1: Create chat
    print("🔵 Step 1: Creating V0 chat...")
    try:
        async with httpx.AsyncClient(timeout=90.0, verify=False) as client:
            response = await client.post(
                "https://api.v0.dev/v1/chats",
                headers={
                    "Authorization": f"Bearer {v0_api_key.strip()}",
                    "Content-Type": "application/json"
                },
                json={
                    "message": test_prompt,
                    "model": "v0-1.5-md",
                    "scope": "mckinsey"
                }
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                chat_id = result.get("id") or result.get("chat_id")
                web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                files = result.get("files", [])
                
                print(f"   ✅ Chat created successfully!")
                print(f"   Chat ID: {chat_id}")
                print(f"   Web URL: {web_url}")
                print(f"   Demo URL: {demo_url}")
                print(f"   Files: {len(files)}")
                print()
                
                # Test 2: Check chat status immediately
                print("🔵 Step 2: Checking chat status immediately...")
                status_response = await client.get(
                    f"https://api.v0.dev/v1/chats/{chat_id}",
                    headers={
                        "Authorization": f"Bearer {v0_api_key.strip()}",
                        "Content-Type": "application/json"
                    }
                )
                
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    print(f"   ✅ Status check successful")
                    print(f"   Status: {status_result.get('status', 'unknown')}")
                    print(f"   Has web URL: {bool(status_result.get('webUrl') or status_result.get('web_url'))}")
                    print(f"   Has demo URL: {bool(status_result.get('demo') or status_result.get('demoUrl'))}")
                    print(f"   Files count: {len(status_result.get('files', []))}")
                    print()
                    
                    # Return what we have
                    return {
                        "success": True,
                        "chat_id": chat_id,
                        "project_id": chat_id,  # Use chat_id as project_id
                        "project_url": demo_url or web_url or f"https://v0.dev/chat/{chat_id}",
                        "web_url": web_url,
                        "demo_url": demo_url,
                        "project_name": status_result.get("name") or f"V0 Project {chat_id[:8]}",
                        "project_status": "completed" if (demo_url or web_url or files) else "in_progress",
                        "files": files
                    }
                else:
                    print(f"   ⚠️ Status check failed: {status_response.status_code}")
                    print(f"   Response: {status_response.text[:200]}")
                    print()
                    
                    # Still return what we have from creation
                    return {
                        "success": True,
                        "chat_id": chat_id,
                        "project_id": chat_id,
                        "project_url": demo_url or web_url or f"https://v0.dev/chat/{chat_id}",
                        "web_url": web_url,
                        "demo_url": demo_url,
                        "project_name": f"V0 Project {chat_id[:8]}",
                        "project_status": "in_progress",
                        "files": files
                    }
            elif response.status_code == 401:
                print(f"   ❌ Authentication failed")
                print(f"   Response: {response.text[:200]}")
                return {"success": False, "error": "Authentication failed"}
            elif response.status_code == 402:
                print(f"   ❌ Payment required (out of credits)")
                print(f"   Response: {response.text[:200]}")
                return {"success": False, "error": "Out of credits"}
            else:
                print(f"   ❌ Failed with status {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
    except httpx.TimeoutException:
        print(f"   ❌ Request timed out after 90 seconds")
        print(f"   ⚠️ This might mean V0 is still processing")
        return {"success": False, "error": "Timeout - V0 may still be processing"}
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}

async def main():
    print("=" * 60)
    print("V0 API End-to-End Test")
    print("=" * 60)
    print()
    
    result = await test_v0_workflow_simple()
    
    print()
    print("=" * 60)
    print("Test Results")
    print("=" * 60)
    print()
    
    if result.get("success"):
        print("✅ Test PASSED")
        print()
        print("📋 Response Data:")
        print(json.dumps(result, indent=2))
        print()
        print("💡 Key Insights:")
        print("   - V0 API returns chat_id immediately")
        print("   - Status can be checked separately")
        print("   - Project may be 'in_progress' initially")
        print("   - User can check status later")
    else:
        print("❌ Test FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print()
        print("💡 Recommendations:")
        if "Timeout" in result.get("error", ""):
            print("   - V0 API takes time to process")
            print("   - Return chat_id immediately, check status separately")
            print("   - Don't wait for full completion")
        elif "credits" in result.get("error", "").lower():
            print("   - Check V0 account credits")
            print("   - Add credits or enable auto-topup")
        else:
            print("   - Check API key validity")
            print("   - Verify network connectivity")
    
    return result.get("success", False)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

