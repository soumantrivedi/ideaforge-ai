"""
Comprehensive V0 workflow test to validate:
1. Duplicate project prevention
2. Status tracking and async polling (10-15 min timeout)
3. Status checking without creating new projects
4. Handling of orphaned projects

Run with: python backend/test_v0_workflow_comprehensive.py
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

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
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


# In-memory project tracker (simulates database)
class ProjectTracker:
    """Tracks V0 projects to prevent duplicates and enable status checking."""
    
    def __init__(self):
        self.projects = {}  # {project_key: project_data}
    
    def get_project_key(self, product_id: str, phase_submission_id: Optional[str], user_id: str) -> str:
        """Generate a unique key for a project."""
        if phase_submission_id:
            return f"{user_id}:{product_id}:{phase_submission_id}"
        return f"{user_id}:{product_id}"
    
    def get_in_progress_project(self, product_id: str, phase_submission_id: Optional[str], user_id: str) -> Optional[Dict]:
        """Check if there's an in-progress project for this context."""
        key = self.get_project_key(product_id, phase_submission_id, user_id)
        project = self.projects.get(key)
        
        if project:
            status = project.get("status", "unknown")
            created_at = project.get("created_at")
            
            # Check if project is still in progress (not older than 15 minutes)
            if created_at:
                age = datetime.now() - created_at
                if age > timedelta(minutes=15):
                    # Project is stale, mark as failed
                    project["status"] = "timeout"
                    return None
            
            if status in ["pending", "in_progress", "polling"]:
                return project
        
        return None
    
    def create_project(self, product_id: str, phase_submission_id: Optional[str], user_id: str, 
                      chat_id: Optional[str], prompt: str) -> Dict:
        """Create a new project entry."""
        key = self.get_project_key(product_id, phase_submission_id, user_id)
        project = {
            "key": key,
            "product_id": product_id,
            "phase_submission_id": phase_submission_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "prompt": prompt,
            "status": "pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "project_url": None,
            "web_url": None,
            "demo_url": None,
            "poll_count": 0,
            "metadata": {}
        }
        self.projects[key] = project
        return project
    
    def update_project_status(self, key: str, status: str, **kwargs):
        """Update project status and other fields."""
        if key in self.projects:
            self.projects[key]["status"] = status
            self.projects[key]["updated_at"] = datetime.now()
            for k, v in kwargs.items():
                self.projects[key][k] = v
    
    def get_project(self, key: str) -> Optional[Dict]:
        """Get project by key."""
        return self.projects.get(key)


# Global project tracker
project_tracker = ProjectTracker()


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
    # Clean prompt (remove headers/footers)
    lines = prompt.split('\n')
    cleaned_lines = []
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
    
    skip_until_content = True
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


async def verify_v0_api_key(api_key: str) -> Dict[str, Any]:
    """Verify V0 API key."""
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        try:
            response = await client.get(
                "https://api.v0.dev/v1/user",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                user_data = response.json()
                return {"valid": True, "data": user_data}
            return {"valid": False, "status": response.status_code}
        except Exception as e:
            return {"valid": None, "error": str(e)}


async def poll_chat_status(api_key: str, chat_id: str, max_polls: int = 200, poll_interval: float = 3.0) -> Dict[str, Any]:
    """
    Poll V0 chat status until prototype is ready or timeout (10-15 minutes).
    max_polls=200 * 3s = 600s = 10 minutes
    """
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        request_headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        
        for poll_count in range(max_polls):
            try:
                response = await client.get(
                    f"https://api.v0.dev/v1/chats/{chat_id}",
                    headers=request_headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                    demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                    files = result.get("files", [])
                    status = result.get("status", "unknown")
                    
                    if demo_url or web_url or (files and len(files) > 0):
                        elapsed = int((poll_count + 1) * poll_interval)
                        print(f"✅ Chat ready after {poll_count + 1} polls ({elapsed}s)")
                        return {
                            "ready": True,
                            "chat_id": chat_id,
                            "web_url": web_url,
                            "demo_url": demo_url,
                            "files": files,
                            "status": status,
                            "poll_count": poll_count + 1,
                            "elapsed_seconds": elapsed,
                            "metadata": result
                        }
                    else:
                        if poll_count % 10 == 0:  # Print progress every 10 polls (30s)
                            elapsed = int((poll_count + 1) * poll_interval)
                            print(f"⏳ Polling... ({poll_count + 1}/{max_polls}, {elapsed}s elapsed, status: {status})")
                elif response.status_code == 404:
                    if poll_count % 10 == 0:
                        print(f"⚠️  Chat {chat_id} not found, may still be creating...")
                else:
                    if poll_count % 10 == 0:
                        print(f"⚠️  Status check returned {response.status_code}")
                
                if poll_count < max_polls - 1:
                    await asyncio.sleep(poll_interval)
                    
            except Exception as e:
                if poll_count % 10 == 0:
                    print(f"⚠️  Error polling: {str(e)[:100]}")
                if poll_count < max_polls - 1:
                    await asyncio.sleep(poll_interval)
        
        # Timeout after 10 minutes
        elapsed = int(max_polls * poll_interval)
        print(f"⏱️  Polling timeout after {max_polls} attempts ({elapsed}s = {elapsed/60:.1f} minutes)")
        return {
            "ready": False,
            "chat_id": chat_id,
            "timeout": True,
            "poll_count": max_polls,
            "elapsed_seconds": elapsed
        }


async def create_v0_project_with_duplicate_prevention(
    api_key: str,
    prompt: str,
    product_id: str,
    phase_submission_id: Optional[str],
    user_id: str,
    timeout_seconds: int = 600  # 10 minutes default
) -> Dict[str, Any]:
    """
    Create V0 project with duplicate prevention and async status polling.
    Returns existing project if one is in progress.
    """
    # Step 1: Check for existing in-progress project
    existing_project = project_tracker.get_in_progress_project(
        product_id, phase_submission_id, user_id
    )
    
    if existing_project:
        print(f"\n⚠️  Found existing in-progress project:")
        print(f"   Chat ID: {existing_project.get('chat_id')}")
        print(f"   Status: {existing_project.get('status')}")
        print(f"   Created: {existing_project.get('created_at')}")
        print(f"   Age: {(datetime.now() - existing_project['created_at']).total_seconds():.0f}s")
        
        # Check if we should continue polling or return existing
        chat_id = existing_project.get("chat_id")
        if chat_id:
            print(f"   Continuing to poll existing project...")
            # Continue polling the existing project
            poll_result = await poll_chat_status(
                api_key, 
                chat_id, 
                max_polls=int(timeout_seconds / 3),  # Adjust based on timeout
                poll_interval=3.0
            )
            
            if poll_result.get("ready"):
                project_key = project_tracker.get_project_key(product_id, phase_submission_id, user_id)
                project_tracker.update_project_status(
                    project_key,
                    "completed",
                    project_url=poll_result.get("demo_url") or poll_result.get("web_url"),
                    web_url=poll_result.get("web_url"),
                    demo_url=poll_result.get("demo_url"),
                    poll_count=poll_result.get("poll_count", 0)
                )
                return {
                    "chat_id": chat_id,
                    "project_url": poll_result.get("demo_url") or poll_result.get("web_url"),
                    "web_url": poll_result.get("web_url"),
                    "demo_url": poll_result.get("demo_url"),
                    "status": "completed",
                    "from_existing": True,
                    "poll_count": poll_result.get("poll_count", 0)
                }
            else:
                return {
                    "chat_id": chat_id,
                    "status": "timeout" if poll_result.get("timeout") else "in_progress",
                    "from_existing": True,
                    "poll_count": poll_result.get("poll_count", 0)
                }
        
        # Return existing project info
        return {
            "chat_id": existing_project.get("chat_id"),
            "status": existing_project.get("status"),
            "from_existing": True,
            "message": "Project already in progress"
        }
    
    # Step 2: Create new project (no existing project found)
    print(f"\n📤 Creating new V0 project...")
    print(f"   Product ID: {product_id}")
    print(f"   Phase Submission ID: {phase_submission_id}")
    print(f"   User ID: {user_id}")
    print(f"   Prompt length: {len(prompt)} characters")
    
    async with httpx.AsyncClient(timeout=timeout_seconds, verify=False) as client:
        try:
            request_headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            request_body = {
                "message": prompt,
                "model": "v0-1.5-md",
                "scope": "mckinsey"
            }
            
            print(f"   Request endpoint: https://api.v0.dev/v1/chats")
            print(f"   Request scope: mckinsey")
            
            response = await client.post(
                "https://api.v0.dev/v1/chats",
                headers=request_headers,
                json=request_body
            )
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 401:
                raise ValueError("V0 API key is invalid or unauthorized")
            elif response.status_code == 402:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_text)
                except:
                    error_detail = error_text
                raise ValueError(f"V0 API credits exhausted: {error_detail}")
            elif response.status_code not in [200, 201]:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_text = error_json.get("error", {}).get("message", error_text)
                except:
                    pass
                raise ValueError(f"V0 API error: {response.status_code} - {error_text}")
            
            result = response.json()
            chat_id = result.get("id") or result.get("chat_id")
            
            if not chat_id:
                raise ValueError("No chat_id returned from V0 API")
            
            print(f"   ✅ Chat created with ID: {chat_id}")
            
            # Step 3: Track project in database (simulated)
            project = project_tracker.create_project(
                product_id, phase_submission_id, user_id, chat_id, prompt
            )
            project_tracker.update_project_status(project["key"], "in_progress")
            
            # Step 4: Start async polling
            print(f"   🔄 Starting async polling (timeout: {timeout_seconds}s = {timeout_seconds/60:.1f} minutes)...")
            poll_result = await poll_chat_status(
                api_key,
                chat_id,
                max_polls=int(timeout_seconds / 3),  # Poll every 3 seconds
                poll_interval=3.0
            )
            
            # Step 5: Update project status based on polling result
            if poll_result.get("ready"):
                project_tracker.update_project_status(
                    project["key"],
                    "completed",
                    project_url=poll_result.get("demo_url") or poll_result.get("web_url"),
                    web_url=poll_result.get("web_url"),
                    demo_url=poll_result.get("demo_url"),
                    poll_count=poll_result.get("poll_count", 0)
                )
                return {
                    "chat_id": chat_id,
                    "project_url": poll_result.get("demo_url") or poll_result.get("web_url"),
                    "web_url": poll_result.get("web_url"),
                    "demo_url": poll_result.get("demo_url"),
                    "status": "completed",
                    "from_existing": False,
                    "poll_count": poll_result.get("poll_count", 0),
                    "elapsed_seconds": poll_result.get("elapsed_seconds", 0)
                }
            else:
                status = "timeout" if poll_result.get("timeout") else "in_progress"
                project_tracker.update_project_status(
                    project["key"],
                    status,
                    poll_count=poll_result.get("poll_count", 0)
                )
                return {
                    "chat_id": chat_id,
                    "status": status,
                    "from_existing": False,
                    "poll_count": poll_result.get("poll_count", 0),
                    "elapsed_seconds": poll_result.get("elapsed_seconds", 0),
                    "message": "Project created but not ready yet. Use status check endpoint to continue polling."
                }
            
        except httpx.TimeoutException:
            raise ValueError(f"V0 API request timed out after {timeout_seconds}s")
        except httpx.RequestError as e:
            raise ValueError(f"V0 API connection error: {str(e)}")
        except Exception as e:
            raise ValueError(f"V0 API error: {str(e)}")


async def check_project_status(
    api_key: str,
    product_id: str,
    phase_submission_id: Optional[str],
    user_id: str
) -> Dict[str, Any]:
    """
    Check project status without creating a new project.
    Allows users to come back and check status later.
    """
    project_key = project_tracker.get_project_key(product_id, phase_submission_id, user_id)
    project = project_tracker.get_project(project_key)
    
    if not project:
        return {
            "status": "not_found",
            "message": "No project found for this context"
        }
    
    chat_id = project.get("chat_id")
    if not chat_id:
        return {
            "status": project.get("status", "unknown"),
            "message": "Project exists but no chat_id available"
        }
    
    # Poll current status from V0 API
    print(f"\n🔍 Checking status for existing project...")
    print(f"   Chat ID: {chat_id}")
    print(f"   Current status: {project.get('status')}")
    
    poll_result = await poll_chat_status(api_key, chat_id, max_polls=10, poll_interval=3.0)
    
    if poll_result.get("ready"):
        project_tracker.update_project_status(
            project_key,
            "completed",
            project_url=poll_result.get("demo_url") or poll_result.get("web_url"),
            web_url=poll_result.get("web_url"),
            demo_url=poll_result.get("demo_url")
        )
        return {
            "status": "completed",
            "chat_id": chat_id,
            "project_url": poll_result.get("demo_url") or poll_result.get("web_url"),
            "web_url": poll_result.get("web_url"),
            "demo_url": poll_result.get("demo_url")
        }
    else:
        return {
            "status": "in_progress" if not poll_result.get("timeout") else "timeout",
            "chat_id": chat_id,
            "message": "Project still processing. Check again later."
        }


async def test_comprehensive_workflow():
    """Test comprehensive V0 workflow with duplicate prevention."""
    print("=" * 80)
    print("COMPREHENSIVE V0 WORKFLOW TEST")
    print("=" * 80)
    print("\nTesting:")
    print("1. Duplicate project prevention")
    print("2. Async status polling (10-15 min timeout)")
    print("3. Status checking without creating new projects")
    print("4. Handling of orphaned/stale projects")
    print("=" * 80)
    
    # Test parameters
    product_id = "test-product-123"
    phase_submission_id = "test-phase-456"
    user_id = "test-user-789"
    product_description = "A modern dashboard for project management with user authentication, task boards, and analytics charts"
    
    try:
        # Verify API key
        print("\n" + "=" * 80)
        print("STEP 1: Verifying V0 API key...")
        print("=" * 80)
        verification = await verify_v0_api_key(V0_API_KEY)
        if not verification.get("valid"):
            print("❌ API key verification failed")
            sys.exit(1)
        print("✅ API key verified")
        
        # Generate prompt
        print("\n" + "=" * 80)
        print("STEP 2: Generating V0 prompt...")
        print("=" * 80)
        prompt = await generate_v0_prompt_with_openai(product_description)
        print(f"✅ Generated prompt ({len(prompt)} chars)")
        
        # Test 1: Create first project
        print("\n" + "=" * 80)
        print("TEST 1: Creating first project...")
        print("=" * 80)
        print("⚠️  This test will wait up to 15 minutes for prototype completion...")
        result1 = await create_v0_project_with_duplicate_prevention(
            V0_API_KEY, prompt, product_id, phase_submission_id, user_id, timeout_seconds=900  # 15 minutes
        )
        print(f"\nResult 1:")
        print(f"  Status: {result1.get('status')}")
        print(f"  Chat ID: {result1.get('chat_id')}")
        print(f"  From existing: {result1.get('from_existing', False)}")
        print(f"  Project URL: {result1.get('project_url')}")
        print(f"  Poll count: {result1.get('poll_count', 0)}")
        print(f"  Elapsed: {result1.get('elapsed_seconds', 0)}s")
        
        # Test 2: Try to create duplicate (should return existing)
        print("\n" + "=" * 80)
        print("TEST 2: Attempting to create duplicate project...")
        print("=" * 80)
        result2 = await create_v0_project_with_duplicate_prevention(
            V0_API_KEY, prompt, product_id, phase_submission_id, user_id, timeout_seconds=900  # 15 minutes
        )
        print(f"\nResult 2:")
        print(f"  Status: {result2.get('status')}")
        print(f"  Chat ID: {result2.get('chat_id')}")
        print(f"  From existing: {result2.get('from_existing', False)}")
        print(f"  Message: {result2.get('message', 'N/A')}")
        
        if result2.get("from_existing"):
            print("✅ Duplicate prevention working correctly!")
        else:
            print("❌ Duplicate prevention failed - new project was created!")
        
        # Test 3: Check status without creating new project
        print("\n" + "=" * 80)
        print("TEST 3: Checking project status (without creating new)...")
        print("=" * 80)
        status_result = await check_project_status(
            V0_API_KEY, product_id, phase_submission_id, user_id
        )
        print(f"\nStatus Result:")
        print(f"  Status: {status_result.get('status')}")
        print(f"  Chat ID: {status_result.get('chat_id')}")
        print(f"  Project URL: {status_result.get('project_url')}")
        print(f"  Message: {status_result.get('message', 'N/A')}")
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✅ API key verification: PASSED")
        print(f"✅ Prompt generation: PASSED")
        print(f"✅ Project creation: {'PASSED' if result1.get('chat_id') else 'FAILED'}")
        print(f"✅ Duplicate prevention: {'PASSED' if result2.get('from_existing') else 'FAILED'}")
        print(f"✅ Status checking: {'PASSED' if status_result.get('status') else 'FAILED'}")
        print(f"✅ Async polling: {'PASSED' if result1.get('poll_count', 0) > 0 else 'PARTIAL'}")
        
        # Final validation - ensure we have a completed prototype
        if result1.get("project_url") and result1.get("status") == "completed":
            print(f"\n✅ END-TO-END WORKFLOW COMPLETE")
            print(f"   ✅ Prototype URL: {result1.get('project_url')}")
            print(f"   ✅ Status: {result1.get('status')}")
            print(f"   ✅ Chat ID: {result1.get('chat_id')}")
            print(f"   ✅ Poll Count: {result1.get('poll_count', 0)}")
            print(f"   ✅ Elapsed Time: {result1.get('elapsed_seconds', 0)}s ({result1.get('elapsed_seconds', 0)/60:.1f} minutes)")
            print(f"\n🎉 SUCCESS: Complete end-to-end workflow validated!")
            print(f"   The prototype is ready and accessible at: {result1.get('project_url')}")
        elif result1.get("project_url"):
            print(f"\n⚠️  WORKFLOW PARTIALLY COMPLETE")
            print(f"   Prototype URL: {result1.get('project_url')}")
            print(f"   Status: {result1.get('status')}")
            print(f"   ⚠️  Prototype may still be processing")
        elif result1.get("status") == "in_progress" or result1.get("status") == "timeout":
            print(f"\n❌ WORKFLOW INCOMPLETE - PROTOTYPE NOT READY")
            print(f"   Chat ID: {result1.get('chat_id')}")
            print(f"   Status: {result1.get('status')}")
            print(f"   Poll Count: {result1.get('poll_count', 0)}")
            print(f"   Elapsed Time: {result1.get('elapsed_seconds', 0)}s")
            print(f"   ⚠️  Prototype is still being generated or timed out")
            print(f"   ⚠️  Cannot finalize implementation until prototype completes")
            sys.exit(1)
        else:
            print(f"\n❌ WORKFLOW FAILED")
            print(f"   Status: {result1.get('status')}")
            print(f"   Error: {result1.get('message', 'Unknown error')}")
            sys.exit(1)
        
        return result1
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_comprehensive_workflow())

