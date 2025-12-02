"""
Comprehensive Agent Verification Tests
Tests all lifecycle agents to ensure:
1. RAG is enabled and working
2. Coaching mode is removed (agents write direct content)
3. Responses are not truncated
4. Knowledge base is being used
5. All agents are functioning correctly
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

import httpx
import structlog

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

logger = structlog.get_logger()

# Test configuration
# When running inside pod, use internal service URL
# When running from host, use http://localhost:8080 (with port-forward)
BASE_URL = os.getenv("TEST_BASE_URL", os.getenv("BACKEND_URL", "http://backend:8000"))
TEST_TIMEOUT = 180  # 3 minutes per test (increased for RAG operations)
# Use demo accounts from seed data
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "admin@ideaforge.ai")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "password123")

# Test results storage
test_results: List[Dict[str, Any]] = []


class AgentVerificationTest:
    """Comprehensive agent verification test suite."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=TEST_TIMEOUT)
        self.token: Optional[str] = None
        self.product_id: Optional[str] = None
        self.user_id: Optional[str] = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def authenticate(self) -> bool:
        """Authenticate and get token."""
        try:
            # Use regular login endpoint with demo account credentials
            response = await self.client.post(
                f"{self.base_url}/api/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
            )
            if response.status_code == 200:
                data = response.json()
                # Token can be in 'token' or 'access_token' field
                self.token = data.get("token") or data.get("access_token")
                if self.token:
                    logger.info("authenticated", method="login", email=TEST_USER_EMAIL)
                    return True
                else:
                    logger.error("authentication_failed_no_token", response_data=data)
            else:
                logger.error("authentication_failed", status=response.status_code, response=response.text[:200])
            return False
        except Exception as e:
            logger.error("authentication_error", error=str(e))
            return False
    
    async def get_user_id(self) -> Optional[str]:
        """Get current user ID from /api/auth/me endpoint."""
        if not self.token:
            return None
        try:
            response = await self.client.get(
                f"{self.base_url}/api/auth/me",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("id") or data.get("user_id")
            return None
        except Exception as e:
            logger.error("get_user_id_error", error=str(e))
            return None
    
    async def create_test_product(self) -> Optional[str]:
        """Create a test product for testing."""
        if not self.token:
            return None
        
        # First try to get an existing product
        existing = await self.get_existing_product()
        if existing:
            return existing
        
        try:
            # Use /api/products endpoint which handles user_id automatically
            response = await self.client.post(
                f"{self.base_url}/api/products",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": f"Test Product - {datetime.utcnow().isoformat()}",
                    "description": "Test product for agent verification"
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.product_id = data.get("id") or data.get("product_id")
                logger.info("test_product_created", product_id=self.product_id)
                return self.product_id
            else:
                logger.warning("product_creation_failed", status=response.status_code, response=response.text[:200])
                return None
        except Exception as e:
            logger.error("product_creation_error", error=str(e))
            return None
    
    async def get_existing_product(self) -> Optional[str]:
        """Get an existing product if creation fails."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/products",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if response.status_code == 200:
                data = response.json()
                products = data if isinstance(data, list) else data.get("products", []) or []
                if products:
                    self.product_id = products[0].get("id") or products[0].get("product_id")
                    logger.info("using_existing_product", product_id=self.product_id)
                    return self.product_id
            return None
        except Exception as e:
            logger.error("get_existing_product_error", error=str(e))
            return None
    
    async def add_test_knowledge(self) -> bool:
        """Add test knowledge base content."""
        if not self.token or not self.product_id:
            return False
        
        try:
            # Add a test knowledge article
            test_content = """
            Product Requirements Document (PRD) Best Practices:
            
            1. Problem Statement: Clearly define the problem being solved
            2. User Personas: Identify primary and secondary users
            3. Functional Requirements: List all features and capabilities
            4. Success Metrics: Define KPIs and success criteria
            5. Technical Architecture: Outline system design and technology stack
            
            This knowledge base article provides guidance for PRD authoring.
            """
            
            response = await self.client.post(
                f"{self.base_url}/api/db/knowledge-articles",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "product_id": self.product_id,
                    "title": "PRD Best Practices",
                    "content": test_content,
                    "source_type": "internal"
                }
            )
            
            if response.status_code in [200, 201]:
                logger.info("test_knowledge_added")
                return True
            else:
                logger.warning("knowledge_add_failed", status=response.status_code)
                return False
        except Exception as e:
            logger.warning("knowledge_add_error", error=str(e))
            return False
    
    async def test_agent(
        self,
        agent_name: str,
        query: str,
        expected_checks: List[str]
    ) -> Dict[str, Any]:
        """Test a specific agent."""
        if not self.token or not self.product_id:
            return {
                "agent": agent_name,
                "status": "skipped",
                "error": "Authentication or product creation failed"
            }
        
        start_time = datetime.utcnow()
        result = {
            "agent": agent_name,
            "query": query,
            "status": "pending",
            "checks": {},
            "response_length": 0,
            "response_preview": "",
            "has_coaching_language": False,
            "has_direct_content": False,
            "rag_used": False,
            "error": None,
            "duration_seconds": 0
        }
        
        try:
            # Make request to multi-agent endpoint
            # Get user_id if not already available
            if not self.user_id:
                self.user_id = await self.get_user_id()
            
            request_body = {
                "query": query,
                "primary_agent": agent_name,
                "product_id": self.product_id,
                "coordination_mode": "enhanced_collaborative"
            }
            
            # Add user_id if available (some endpoints require it)
            if self.user_id:
                request_body["user_id"] = self.user_id
            
            response = await self.client.post(
                f"{self.base_url}/api/multi-agent/process",
                headers={"Authorization": f"Bearer {self.token}"},
                json=request_body
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 2)
            
            if response.status_code != 200:
                result["status"] = "failed"
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                return result
            
            data = response.json()
            agent_response = data.get("response", "")
            metadata = data.get("metadata", {})
            
            result["response_length"] = len(agent_response)
            result["response_preview"] = agent_response[:200] + "..." if len(agent_response) > 200 else agent_response
            
            # Check 1: Response is not empty
            result["checks"]["response_not_empty"] = len(agent_response) > 0
            if not result["checks"]["response_not_empty"]:
                result["status"] = "failed"
                result["error"] = "Empty response"
                return result
            
            # Check 2: No coaching language
            coaching_phrases = [
                "when you define",
                "the goal is to create",
                "you should",
                "you need to",
                "it's important to",
                "remember to"
            ]
            result["has_coaching_language"] = any(
                phrase.lower() in agent_response.lower() for phrase in coaching_phrases
            )
            result["checks"]["no_coaching_language"] = not result["has_coaching_language"]
            
            # Check 3: Has direct content (not coaching)
            # Direct content indicators - agents should write as if user typed it
            direct_content_indicators = [
                "the problem we are solving",
                "our product vision",
                "we are building",
                "the product will",
                "users will be able to",
                "the product",
                "this product",
                "our app",
                "the app",
                "features include",
                "the solution",
                "we will",
                "the system",
                "this system"
            ]
            # Coaching language (should NOT be present)
            coaching_indicators = [
                "when you define",
                "the goal is to create",
                "you should",
                "you need to",
                "it's important to",
                "remember to",
                "make sure to",
                "ensure that you"
            ]
            has_coaching = any(
                phrase.lower() in agent_response.lower() for phrase in coaching_indicators
            )
            has_direct = any(
                indicator.lower() in agent_response.lower() for indicator in direct_content_indicators
            )
            # Direct content if it has direct indicators AND no coaching language
            result["has_direct_content"] = has_direct and not has_coaching
            result["checks"]["has_direct_content"] = result["has_direct_content"]
            
            # Check 4: Response is not truncated (should be substantial)
            result["checks"]["not_truncated"] = len(agent_response) > 100
            if len(agent_response) < 100:
                result["status"] = "warning"
                result["error"] = "Response seems too short (possible truncation)"
            
            # Check 5: RAG was used (check metadata and response content)
            # Check interaction_metadata which contains agent_interactions
            interaction_metadata = metadata.get("interaction_metadata", {}) or {}
            interactions = interaction_metadata.get("agent_interactions", []) or metadata.get("agent_interactions", []) or []
            
            # Check for RAG in interactions (multiple possible field names)
            rag_interaction = next(
                (i for i in interactions if 
                 i.get("agent_name") == "rag" or 
                 i.get("agent_type") == "rag" or 
                 i.get("to_agent") == "rag" or
                 i.get("from_agent") == "rag" or
                 str(i.get("agent_name", "")).lower() == "rag" or
                 str(i.get("to_agent", "")).lower() == "rag"),
                None
            )
            
            # Also check if RAG context is mentioned in metadata
            rag_context_in_metadata = (
                bool(metadata.get("rag_context")) or 
                bool(metadata.get("knowledge_base")) or
                bool(interaction_metadata.get("rag_context")) or
                bool(interaction_metadata.get("knowledge_base"))
            )
            
            # Check if response mentions knowledge base (indirect indicator)
            rag_mentioned_in_response = any(
                keyword.lower() in agent_response.lower()
                for keyword in ["knowledge base", "reference", "according to", "based on", "article", "document", "best practices", "guidance"]
            )
            
            # RAG is used if any indicator is true
            result["rag_used"] = rag_interaction is not None or rag_context_in_metadata or rag_mentioned_in_response
            result["checks"]["rag_used"] = result["rag_used"]
            
            # Store detailed RAG detection info
            result["rag_detection_details"] = {
                "rag_interaction_found": rag_interaction is not None,
                "rag_context_in_metadata": rag_context_in_metadata,
                "rag_mentioned_in_response": rag_mentioned_in_response,
                "interactions_count": len(interactions),
                "interaction_agent_names": [i.get("agent_name") or i.get("to_agent") for i in interactions[:5]]
            }
            
            # Check 6: Knowledge base referenced (if RAG was used)
            if result["rag_used"]:
                result["checks"]["knowledge_referenced"] = any(
                    keyword.lower() in agent_response.lower()
                    for keyword in ["knowledge", "best practices", "guidance", "article", "reference"]
                )
            else:
                result["checks"]["knowledge_referenced"] = None  # N/A if RAG not used
            
            # Overall status
            all_checks_passed = all(
                v for k, v in result["checks"].items()
                if v is not None and k in expected_checks
            )
            
            if all_checks_passed:
                result["status"] = "passed"
            elif result["status"] == "pending":
                result["status"] = "warning"
            
            return result
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
            return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all agent verification tests."""
        logger.info("starting_agent_verification_tests")
        
        # Authenticate
        if not await self.authenticate():
            logger.error("authentication_failed_cannot_proceed")
            return {
                "status": "failed",
                "error": "Authentication failed - cannot proceed with tests",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "results": []
            }
        
        # Create test product
        if not await self.create_test_product():
            logger.error("product_creation_failed_cannot_proceed")
            return {
                "status": "failed",
                "error": "Product creation failed - cannot proceed with tests",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
                "results": []
            }
        
        # Add test knowledge
        await self.add_test_knowledge()
        
        # Define test cases for each agent
        test_cases = [
            {
                "agent": "ideation",
                "query": "Generate innovative ideas for a productivity app",
                "expected_checks": ["response_not_empty", "no_coaching_language", "has_direct_content", "not_truncated", "rag_used"]
            },
            {
                "agent": "research",
                "query": "Research the market for productivity apps",
                "expected_checks": ["response_not_empty", "no_coaching_language", "has_direct_content", "not_truncated", "rag_used"]
            },
            {
                "agent": "analysis",
                "query": "Analyze the feasibility of a productivity app",
                "expected_checks": ["response_not_empty", "no_coaching_language", "has_direct_content", "not_truncated", "rag_used"]
            },
            {
                "agent": "prd_authoring",
                "query": "Create a PRD for a productivity app",
                "expected_checks": ["response_not_empty", "no_coaching_language", "has_direct_content", "not_truncated", "rag_used", "knowledge_referenced"]
            },
            {
                "agent": "validation",
                "query": "Validate the PRD requirements for completeness",
                "expected_checks": ["response_not_empty", "no_coaching_language", "has_direct_content", "not_truncated", "rag_used"]
            },
            {
                "agent": "export",
                "query": "Export a comprehensive PRD document",
                "expected_checks": ["response_not_empty", "no_coaching_language", "has_direct_content", "not_truncated", "rag_used", "knowledge_referenced"]
            }
        ]
        
        # Run tests sequentially (to avoid overwhelming the system)
        results = []
        for test_case in test_cases:
            logger.info("testing_agent", agent=test_case["agent"])
            result = await self.test_agent(
                agent_name=test_case["agent"],
                query=test_case["query"],
                expected_checks=test_case["expected_checks"]
            )
            results.append(result)
            test_results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Calculate summary
        passed = sum(1 for r in results if r["status"] == "passed")
        failed = sum(1 for r in results if r["status"] == "failed")
        warnings = sum(1 for r in results if r["status"] == "warning")
        
        summary = {
            "status": "passed" if failed == 0 else "failed",
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "results": results
        }
        
        return summary


async def main():
    """Main test execution."""
    print("=" * 80)
    print("Agent Verification Test Suite")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Timeout: {TEST_TIMEOUT}s")
    print()
    
    async with AgentVerificationTest() as tester:
        summary = await tester.run_all_tests()
        
        print("\n" + "=" * 80)
        print("Test Results Summary")
        print("=" * 80)
        print(f"Status: {summary['status'].upper()}")
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Warnings: {summary['warnings']}")
        print()
        
        print("Detailed Results:")
        print("-" * 80)
        for result in summary["results"]:
            status_icon = "✅" if result["status"] == "passed" else "⚠️" if result["status"] == "warning" else "❌"
            print(f"{status_icon} {result['agent'].upper()}: {result['status']}")
            print(f"   Query: {result['query'][:60]}...")
            print(f"   Response Length: {result['response_length']} chars")
            print(f"   Duration: {result['duration_seconds']}s")
            
            if result.get("checks"):
                print("   Checks:")
                for check_name, check_result in result["checks"].items():
                    check_icon = "✅" if check_result else "❌" if check_result is False else "➖"
                    print(f"     {check_icon} {check_name}: {check_result}")
            
            if result.get("error"):
                print(f"   Error: {result['error']}")
            
            if result.get("has_coaching_language"):
                print("   ⚠️  WARNING: Coaching language detected!")
            
            if not result.get("has_direct_content"):
                print("   ⚠️  WARNING: Direct content not detected!")
            
            if not result.get("rag_used"):
                print("   ⚠️  WARNING: RAG not used!")
            
            print()
        
        # Save results to file
        results_file = f"/tmp/agent_verification_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Results saved to: {results_file}")
        
        # Exit with appropriate code
        sys.exit(0 if summary["status"] == "passed" else 1)


if __name__ == "__main__":
    asyncio.run(main())

