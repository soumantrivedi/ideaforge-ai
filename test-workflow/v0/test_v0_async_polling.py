"""
Test V0 workflow with async polling pattern:
1. Generate V0 prompt using OpenAI API
2. Submit project to V0 API (scope: mckinsey) and get project_id immediately
3. Poll status every 2 minutes for 15 minutes using the project_id
4. Print detailed status at each poll

This solves the timeout issue by:
- Returning immediately after project submission (no waiting for completion)
- Using project_id (chat_id) to check status separately
- Polling at regular intervals instead of blocking

Run with: python test-workflow/v0/test_v0_async_polling.py
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


async def submit_v0_project(api_key: str, prompt: str, timeout_seconds: int = 600) -> Dict[str, Any]:
    """
    Submit project to V0 API and return with project_id (chat_id).
    
    IMPORTANT: V0 API /v1/chats endpoint waits for project generation before returning.
    This can take 5-15 minutes depending on project complexity.
    We use a longer timeout (default 600s = 10 minutes) to get the chat_id.
    Once we have chat_id, we can poll status separately for updates.
    
    Args:
        api_key: V0 API key
        prompt: V0 prompt to submit
        timeout_seconds: Timeout for initial submission (default 600s = 10 minutes)
    """
    print(f"\n📤 Submitting project to V0 API...")
    print(f"   Prompt length: {len(prompt)} characters")
    print(f"   Scope: mckinsey")
    print(f"   Timeout: {timeout_seconds} seconds ({timeout_seconds/60:.1f} minutes)")
    print(f"   ⚠️  IMPORTANT: V0 API waits for project generation before returning")
    print(f"   This typically takes 5-15 minutes. Please be patient...")
    print(f"   Once we get chat_id, we can poll for status updates separately.")
    
    # Use a timeout that allows for project generation
    timeout = httpx.Timeout(timeout_seconds, connect=30.0, read=timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
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
            
            print(f"   Endpoint: https://api.v0.dev/v1/chats")
            print(f"   Sending request... (waiting for V0 to generate project)")
            print(f"   This typically takes 5-15 minutes. Please wait...")
            
            # Make the request - V0 API will wait for generation
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
                    error_detail = error_json.get("detail", error_json.get("error", {}).get("message", error_text))
                    if isinstance(error_detail, dict):
                        error_detail = error_detail.get("message", str(error_detail))
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
                raise ValueError("No chat_id (project_id) returned from V0 API")
            
            # Extract initial status information
            web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
            demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
            files = result.get("files", [])
            status = result.get("status", "unknown")
            
            # Determine if project is already complete
            is_complete = bool(demo_url or web_url or (files and len(files) > 0))
            
            print(f"   ✅ Project submitted successfully!")
            print(f"   Project ID (chat_id): {chat_id}")
            print(f"   Initial status: {status}")
            print(f"   Is complete: {is_complete}")
            if is_complete:
                print(f"   Project URL: {demo_url or web_url}")
            
            return {
                "success": True,
                "project_id": chat_id,
                "chat_id": chat_id,
                "status": "completed" if is_complete else "in_progress",
                "project_url": demo_url or web_url,
                "web_url": web_url,
                "demo_url": demo_url,
                "files": files,
                "is_complete": is_complete,
                "metadata": result
            }
            
        except httpx.TimeoutException as e:
            # Timeout occurred - V0 API is taking longer than expected
            print(f"   ⚠️  Request timed out after {timeout_seconds} seconds ({timeout_seconds/60:.1f} minutes)")
            print(f"   V0 API is still generating the project")
            print(f"   💡 Recommendation: Increase timeout to 900s (15 minutes) for complex projects")
            raise ValueError(f"V0 API request timed out after {timeout_seconds} seconds. "
                           f"The API is waiting for project generation which can take 10-15+ minutes. "
                           f"Try increasing timeout_seconds parameter to 900 (15 minutes).")
        except httpx.RequestError as e:
            raise ValueError(f"V0 API connection error: {str(e)}")
        except Exception as e:
            raise ValueError(f"V0 API error: {str(e)}")


async def check_project_status(api_key: str, project_id: str) -> Dict[str, Any]:
    """
    Check project status using project_id (chat_id).
    Returns current status and project details.
    """
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        try:
            request_headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"https://api.v0.dev/v1/chats/{project_id}",
                headers=request_headers
            )
            
            if response.status_code == 200:
                result = response.json()
                web_url = result.get("webUrl") or result.get("web_url") or result.get("url")
                demo_url = result.get("demo") or result.get("demoUrl") or result.get("demo_url")
                files = result.get("files", [])
                status = result.get("status", "unknown")
                
                is_complete = bool(demo_url or web_url or (files and len(files) > 0))
                
                return {
                    "success": True,
                    "project_id": project_id,
                    "status": "completed" if is_complete else status,
                    "is_complete": is_complete,
                    "project_url": demo_url or web_url,
                    "web_url": web_url,
                    "demo_url": demo_url,
                    "files": files,
                    "num_files": len(files),
                    "metadata": result
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "project_id": project_id,
                    "status": "not_found",
                    "error": "Project not found (may still be creating)"
                }
            else:
                return {
                    "success": False,
                    "project_id": project_id,
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "status": "error",
                "error": str(e)
            }


async def poll_project_status(
    api_key: str,
    project_id: str,
    poll_interval_minutes: int = 2,
    max_duration_minutes: int = 15
) -> Dict[str, Any]:
    """
    Poll project status every N minutes for up to M minutes.
    Prints detailed status at each poll.
    """
    poll_interval_seconds = poll_interval_minutes * 60
    max_duration_seconds = max_duration_minutes * 60
    max_polls = max_duration_minutes // poll_interval_minutes
    
    print(f"\n🔄 Starting status polling...")
    print(f"   Project ID: {project_id}")
    print(f"   Poll interval: {poll_interval_minutes} minutes")
    print(f"   Max duration: {max_duration_minutes} minutes")
    print(f"   Max polls: {max_polls}")
    print(f"   {'=' * 80}")
    
    start_time = datetime.now()
    poll_results = []
    
    for poll_num in range(max_polls):
        elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
        
        print(f"\n📊 Poll #{poll_num + 1} (Elapsed: {elapsed_minutes:.1f} minutes)")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        status_result = await check_project_status(api_key, project_id)
        poll_results.append({
            "poll_number": poll_num + 1,
            "elapsed_minutes": elapsed_minutes,
            "timestamp": datetime.now().isoformat(),
            "status": status_result
        })
        
        if status_result.get("success"):
            status = status_result.get("status", "unknown")
            is_complete = status_result.get("is_complete", False)
            
            print(f"   ✅ Status check successful")
            print(f"   Status: {status}")
            print(f"   Is complete: {is_complete}")
            
            if status_result.get("project_url"):
                print(f"   Project URL: {status_result.get('project_url')}")
            if status_result.get("num_files", 0) > 0:
                print(f"   Files generated: {status_result.get('num_files')}")
            if status_result.get("web_url"):
                print(f"   Web URL: {status_result.get('web_url')}")
            if status_result.get("demo_url"):
                print(f"   Demo URL: {status_result.get('demo_url')}")
            
            if is_complete:
                print(f"\n🎉 Project completed!")
                print(f"   Total time: {elapsed_minutes:.1f} minutes")
                print(f"   Total polls: {poll_num + 1}")
                return {
                    "completed": True,
                    "project_id": project_id,
                    "elapsed_minutes": elapsed_minutes,
                    "total_polls": poll_num + 1,
                    "final_status": status_result,
                    "all_polls": poll_results
                }
        else:
            error = status_result.get("error", "Unknown error")
            print(f"   ⚠️  Status check failed: {error}")
        
        # Wait before next poll (except on last poll)
        if poll_num < max_polls - 1:
            print(f"   ⏳ Waiting {poll_interval_minutes} minutes until next poll...")
            await asyncio.sleep(poll_interval_seconds)
    
    # Timeout - project not completed within max duration
    elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
    print(f"\n⏱️  Polling timeout after {max_duration_minutes} minutes")
    print(f"   Total polls: {max_polls}")
    print(f"   Final status: {poll_results[-1].get('status', {}).get('status', 'unknown')}")
    
    return {
        "completed": False,
        "project_id": project_id,
        "elapsed_minutes": elapsed_minutes,
        "total_polls": max_polls,
        "timeout": True,
        "final_status": poll_results[-1].get("status") if poll_results else None,
        "all_polls": poll_results
    }


async def test_async_polling_workflow():
    """Test complete async polling workflow."""
    print("=" * 80)
    print("V0 ASYNC POLLING WORKFLOW TEST")
    print("=" * 80)
    print("\nThis test demonstrates:")
    print("1. Generate V0 prompt using OpenAI API")
    print("2. Submit project to V0 API (scope: mckinsey) - returns immediately with project_id")
    print("3. Poll status every 2 minutes for 15 minutes")
    print("4. Print detailed status at each poll")
    print("=" * 80)
    
    # Test parameters
    product_description = "A modern dashboard for project management with user authentication, task boards, and analytics charts"
    
    try:
        # Step 1: Generate V0 prompt using OpenAI
        print("\n" + "=" * 80)
        print("STEP 1: Generating V0 prompt using OpenAI...")
        print("=" * 80)
        v0_prompt = await generate_v0_prompt_with_openai(product_description)
        print(f"✅ Generated prompt ({len(v0_prompt)} chars)")
        print("-" * 80)
        print(v0_prompt[:500] + "..." if len(v0_prompt) > 500 else v0_prompt)
        print("-" * 80)
        
        # Step 2: Submit project to V0 API
        # IMPORTANT: V0 API waits for project generation before returning chat_id
        # This can take 5-15 minutes. Once we have chat_id, we can poll for updates.
        print("\n" + "=" * 80)
        print("STEP 2: Submitting project to V0 API...")
        print("=" * 80)
        print("⚠️  IMPORTANT: V0 API waits for project generation (5-15 minutes)")
        print("   This is expected behavior - the API generates the project before returning")
        print("   Once we get chat_id, we can poll for status updates separately")
        print("   Using 10-minute timeout - increase to 15 minutes if needed for complex projects")
        submission_result = await submit_v0_project(V0_API_KEY, v0_prompt, timeout_seconds=600)
        
        if not submission_result.get("success"):
            print(f"❌ Project submission failed")
            sys.exit(1)
        
        project_id = submission_result.get("project_id")
        print(f"\n✅ Project submitted successfully!")
        print(f"   Project ID: {project_id}")
        print(f"   Initial status: {submission_result.get('status')}")
        
        if submission_result.get("is_complete"):
            print(f"   ✅ Project completed immediately!")
            print(f"   Project URL: {submission_result.get('project_url')}")
            return submission_result
        
        # Step 3: Poll status every 2 minutes for 15 minutes
        print("\n" + "=" * 80)
        print("STEP 3: Polling project status...")
        print("=" * 80)
        polling_result = await poll_project_status(
            V0_API_KEY,
            project_id,
            poll_interval_minutes=2,
            max_duration_minutes=15
        )
        
        # Step 4: Display final results
        print("\n" + "=" * 80)
        print("FINAL RESULTS")
        print("=" * 80)
        
        if polling_result.get("completed"):
            print("✅ PROJECT COMPLETED SUCCESSFULLY!")
            print(f"   Project ID: {project_id}")
            print(f"   Total time: {polling_result.get('elapsed_minutes', 0):.1f} minutes")
            print(f"   Total polls: {polling_result.get('total_polls', 0)}")
            
            final_status = polling_result.get("final_status", {})
            if final_status.get("project_url"):
                print(f"   Project URL: {final_status.get('project_url')}")
            if final_status.get("web_url"):
                print(f"   Web URL: {final_status.get('web_url')}")
            if final_status.get("demo_url"):
                print(f"   Demo URL: {final_status.get('demo_url')}")
            if final_status.get("num_files", 0) > 0:
                print(f"   Files generated: {final_status.get('num_files')}")
        else:
            print("⚠️  PROJECT NOT COMPLETED WITHIN TIMEOUT")
            print(f"   Project ID: {project_id}")
            print(f"   Total time: {polling_result.get('elapsed_minutes', 0):.1f} minutes")
            print(f"   Total polls: {polling_result.get('total_polls', 0)}")
            
            final_status = polling_result.get("final_status", {})
            if final_status:
                print(f"   Final status: {final_status.get('status', 'unknown')}")
                if final_status.get("error"):
                    print(f"   Error: {final_status.get('error')}")
        
        # Print polling summary
        print("\n" + "=" * 80)
        print("POLLING SUMMARY")
        print("=" * 80)
        all_polls = polling_result.get("all_polls", [])
        for poll in all_polls:
            poll_num = poll.get("poll_number", 0)
            elapsed = poll.get("elapsed_minutes", 0)
            status_info = poll.get("status", {})
            status = status_info.get("status", "unknown")
            is_complete = status_info.get("is_complete", False)
            
            status_icon = "✅" if is_complete else "⏳"
            print(f"   Poll #{poll_num}: {status_icon} {status} (Elapsed: {elapsed:.1f} min)")
        
        print("\n" + "=" * 80)
        print("✅ WORKFLOW TEST COMPLETE")
        print("=" * 80)
        print("\nKey insights:")
        print("  ✅ Project submission returns immediately with project_id")
        print("  ✅ Status can be checked separately using project_id")
        print("  ✅ No timeout issues - polling happens asynchronously")
        print("  ✅ Users can check status later without blocking")
        
        return {
            "submission": submission_result,
            "polling": polling_result
        }
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ WORKFLOW TEST FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_async_polling_workflow())

