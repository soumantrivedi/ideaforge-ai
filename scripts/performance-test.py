#!/usr/bin/env python3
"""
Performance Testing Script for IdeaForge AI
Tests 100 concurrent users making multi-agent queries
Measures: Response time, throughput, error rate, quality metrics
"""
import asyncio
import aiohttp
import json
import time
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import argparse
import sys

@dataclass
class TestResult:
    """Individual test result"""
    user_id: int
    query: str
    start_time: float
    end_time: Optional[float] = None
    response_time: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_length: int = 0
    agent_count: int = 0
    events_received: int = 0
    first_chunk_time: Optional[float] = None
    quality_score: Optional[float] = None

@dataclass
class TestMetrics:
    """Aggregated test metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    first_chunk_times: List[float] = field(default_factory=list)
    error_rate: float = 0.0
    throughput: float = 0.0
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    avg_first_chunk_time: float = 0.0
    avg_response_length: float = 0.0
    avg_agent_count: float = 0.0
    quality_scores: List[float] = field(default_factory=list)
    avg_quality_score: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

class PerformanceTester:
    """Performance testing orchestrator"""
    
    def __init__(self, base_url: str, auth_token: str = None, num_users: int = 100, 
                 user_accounts: List[Dict[str, Any]] = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.num_users = num_users
        self.user_accounts = user_accounts or []  # List of {email, password, user_id}
        self.user_tokens: Dict[str, str] = {}  # Cache tokens per user
        self.user_ids: Dict[str, str] = {}  # Cache user_ids per user (from login response)
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Test queries that simulate real user journeys: Ideation, Review, and Chatbot
        # These queries will trigger actual agent calls (RAG, Research, Analysis, Ideation, etc.)
        self.test_queries = [
            # Ideation Journey Queries
            "I want to build a product that helps teams collaborate better. What are some innovative features I should consider?",
            "Generate ideas for a mobile app that solves the problem of remote team communication",
            "What are the key features for a SaaS product that helps product managers track user feedback?",
            "Help me brainstorm features for an AI-powered project management tool",
            "What innovative ideas can I explore for a B2B analytics platform?",
            
            # Review Journey Queries
            "Review my product idea for a customer feedback platform and provide feedback on market viability",
            "Analyze the strengths and weaknesses of my product concept for a task management app",
            "Evaluate my product requirements document and suggest improvements",
            "Review my product strategy and identify potential risks and opportunities",
            "Critically assess my product roadmap and provide recommendations",
            
            # Chatbot Journey Queries (General Product Management)
            "What are the best practices for conducting user interviews?",
            "How should I prioritize features for my MVP?",
            "What metrics should I track to measure product success?",
            "Explain the difference between product-market fit and product-channel fit",
            "What are common pitfalls in product development and how can I avoid them?",
            "How do I create an effective go-to-market strategy?",
            "What are the key components of a successful product launch?",
            "How can I validate my product idea before building it?",
            "What are the stages of product development lifecycle?",
            "How do I gather and analyze user feedback effectively?",
        ]
    
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=300, connect=30)  # 5 min total, 30s connect
        # Create base session without auth (will add per-request)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        # Login for all user accounts to get tokens and user_ids
        if self.user_accounts:
            print(f"🔐 Logging in {len(self.user_accounts)} demo accounts...")
            login_tasks = [self._login_user(account) for account in self.user_accounts]
            await asyncio.gather(*login_tasks, return_exceptions=True)
            print(f"✅ Obtained {len(self.user_tokens)} authentication tokens")
            print(f"✅ Obtained {len(self.user_ids)} user IDs")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _login_user(self, account: Dict[str, Any]) -> None:
        """Login a user and cache the token and user_id with retry logic"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                login_url = f"{self.base_url}/api/auth/login"
                # Create a temporary session for login (without auth header)
                timeout = aiohttp.ClientTimeout(total=10, connect=5)
                async with aiohttp.ClientSession(timeout=timeout) as login_session:
                    async with login_session.post(login_url, json={
                        "email": account["email"],
                        "password": account["password"]
                    }) as response:
                        if response.status == 200:
                            data = await response.json()
                            token = data.get("token")
                            user_id = data.get("user_id")
                            if token:
                                self.user_tokens[account["email"]] = token
                                # Store user_id from login response
                                self.user_ids[account["email"]] = user_id
                                print(f"✅ Logged in {account['email']} (user_id: {user_id})")
                                return
                        else:
                            error_text = await response.text()
                            if attempt < max_retries - 1:
                                # Retry with exponential backoff
                                await asyncio.sleep(0.5 * (2 ** attempt))
                                continue
                            else:
                                print(f"❌ Login failed for {account['email']} after {max_retries} attempts: HTTP {response.status}")
                                # Don't add to tokens - this account will be skipped
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                else:
                    print(f"❌ Failed to login {account['email']} after {max_retries} attempts: {e}")
                    # Don't add to tokens - this account will be skipped
    
    async def make_query(self, user_id: int, query: str, product_id: str, 
                        account_email: str = None) -> TestResult:
        """Make a single multi-agent query"""
        result = TestResult(
            user_id=user_id,
            query=query,
            start_time=time.time()
        )
        
        try:
            # Get token and user_id for this user
            token = self.auth_token
            user_id = None
            
            if account_email and account_email in self.user_tokens:
                token = self.user_tokens[account_email]
                # Get user_id from login response
                if account_email in self.user_ids:
                    user_id = self.user_ids[account_email]
            elif not token:
                result.error = "No authentication token available"
                result.end_time = time.time()
                result.response_time = 0
                return result
            
            # Use actual user_id from login, or fallback to dummy UUID if not available
            if not user_id:
                user_id = "00000000-0000-0000-0000-000000000000"
            
            # Prepare request payload
            # user_id is required by API schema for validation, backend will use token user_id for actual processing
            payload = {
                "user_id": user_id,  # Required by schema - use actual user_id from login
                "product_id": product_id,
                "query": query,
                "coordination_mode": "enhanced_collaborative",
                "supporting_agents": ["rag", "research", "analysis", "ideation"],
                "context": {
                    "product_id": product_id,
                    "always_use_rag": True
                }
            }
            
            # Make streaming request with user-specific token
            url = f"{self.base_url}/api/streaming/multi-agent/stream"
            headers = {"Authorization": f"Bearer {token}"}
            async with self.session.post(url, json=payload, headers=headers) as response:
                result.status_code = response.status
                
                if response.status != 200:
                    error_text = await response.text()
                    result.error = f"HTTP {response.status}: {error_text[:200]}"
                    result.end_time = time.time()
                    result.response_time = result.end_time - result.start_time
                    return result
                
                # Read SSE stream
                # SSE format: event: <type>\ndata: <json>\n\n
                accumulated_response = ""
                events_count = 0
                first_chunk_received = False
                agents_seen = set()
                current_event_type = None
                buffer = ""
                
                async for chunk in response.content.iter_any():
                    buffer += chunk.decode('utf-8', errors='ignore')
                    lines = buffer.split('\n')
                    buffer = lines.pop() if lines else ""  # Keep incomplete line in buffer
                    
                    for line in lines:
                        line_str = line.strip()
                        
                        # Track event type from 'event:' line
                        if line_str.startswith('event: '):
                            current_event_type = line_str[7:].strip()
                            continue
                        
                        # Parse data from 'data:' line
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                events_count += 1
                                
                                # Use event type from SSE format (not from data JSON)
                                event_type = current_event_type or data.get('type')
                                
                                # Track first chunk from agent_start or agent_complete
                                if not first_chunk_received and event_type in ['agent_start', 'agent_complete', 'agent_chunk']:
                                    result.first_chunk_time = time.time() - result.start_time
                                    first_chunk_received = True
                                
                                # Track agents
                                if 'agent' in data:
                                    agents_seen.add(data['agent'])
                                
                                # Accumulate response from different event types
                                if event_type == 'agent_chunk' and 'chunk' in data:
                                    accumulated_response += data['chunk']
                                elif event_type == 'agent_complete' and 'response' in data:
                                    # Agent completed - add full response
                                    accumulated_response += data['response']
                                elif event_type == 'complete' and 'response' in data:
                                    # Final completion event - this is the synthesized response
                                    accumulated_response += data['response']
                                
                                # Reset event type after processing
                                current_event_type = None
                            
                            except json.JSONDecodeError as e:
                                # Log but continue - might be a comment or malformed line
                                continue
                
                # Process any remaining buffer
                if buffer.strip():
                    for line in buffer.split('\n'):
                        line_str = line.strip()
                        if line_str.startswith('event: '):
                            current_event_type = line_str[7:].strip()
                        elif line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                events_count += 1
                                event_type = current_event_type or data.get('type')
                                if 'agent' in data:
                                    agents_seen.add(data['agent'])
                                if event_type == 'agent_complete' and 'response' in data:
                                    accumulated_response += data['response']
                                elif event_type == 'complete' and 'response' in data:
                                    accumulated_response += data['response']
                            except:
                                pass
                
                result.end_time = time.time()
                result.response_time = result.end_time - result.start_time
                result.response_length = len(accumulated_response)
                result.agent_count = len(agents_seen)
                result.events_received = events_count
                
                # Calculate quality score (simple heuristic)
                if accumulated_response:
                    # Quality factors: length, agent diversity, response completeness
                    length_score = min(len(accumulated_response) / 500, 1.0)  # Normalize to 500 chars
                    agent_score = min(result.agent_count / 4, 1.0)  # Normalize to 4 agents
                    completeness_score = 1.0 if result.events_received > 5 else result.events_received / 5
                    result.quality_score = (length_score * 0.4 + agent_score * 0.3 + completeness_score * 0.3) * 100
        
        except asyncio.TimeoutError:
            result.error = "Timeout"
            result.end_time = time.time()
            result.response_time = result.end_time - result.start_time
        except Exception as e:
            result.error = str(e)[:200]
            result.end_time = time.time()
            if result.start_time:
                result.response_time = result.end_time - result.start_time
        
        return result
    
    async def run_user_simulation(self, user_id: int, product_id: str, 
                                 account_email: str = None) -> List[TestResult]:
        """Simulate a single user making queries across different journeys"""
        user_results = []
        
        # Simulate realistic user journey: 1 ideation query, 1 review query, 1 chatbot query
        # This ensures we test all agent types and get real results
        journey_queries = [
            self.test_queries[user_id % len(self.test_queries)],  # Ideation journey
            self.test_queries[(user_id + 5) % len(self.test_queries)],  # Review journey
            self.test_queries[(user_id + 10) % len(self.test_queries)],  # Chatbot journey
        ]
        
        for query in journey_queries:
            result = await self.make_query(user_id, query, product_id, account_email)
            user_results.append(result)
            # Small delay between queries to simulate realistic user behavior
            await asyncio.sleep(1.0)  # Increased from 0.5s to 1.0s for more realistic pacing
        
        return user_results
    
    async def run_test(self, product_id: str, ramp_up_seconds: int = 30, 
                      sessions_per_account: int = 10) -> TestMetrics:
        """Run performance test with concurrent users
        
        Args:
            product_id: Product ID for testing
            ramp_up_seconds: Time to ramp up all users
            sessions_per_account: Number of concurrent sessions per demo account
        """
        if self.user_accounts:
            total_sessions = len(self.user_accounts) * sessions_per_account
            print(f"🚀 Starting performance test with {len(self.user_accounts)} demo accounts")
            print(f"   {sessions_per_account} sessions per account = {total_sessions} total concurrent sessions")
        else:
            total_sessions = self.num_users
            print(f"🚀 Starting performance test with {self.num_users} concurrent users")
        
        print(f"   Base URL: {self.base_url}")
        print(f"   Product ID: {product_id}")
        print(f"   Ramp-up time: {ramp_up_seconds}s")
        print()
        
        start_time = time.time()
        
        # Create tasks for all users with ramp-up
        tasks = []
        session_id = 0
        
        if self.user_accounts:
            # Distribute sessions across accounts
            for account_idx, account in enumerate(self.user_accounts):
                account_email = account["email"]
                for session_num in range(sessions_per_account):
                    # Stagger user starts for ramp-up
                    delay = (session_id / total_sessions) * ramp_up_seconds
                    task = asyncio.create_task(
                        self._delayed_user_simulation(session_id, product_id, delay, account_email)
                    )
                    tasks.append(task)
                    session_id += 1
        else:
            # Original behavior: single token for all users
            for user_id in range(self.num_users):
                delay = (user_id / self.num_users) * ramp_up_seconds
                task = asyncio.create_task(
                    self._delayed_user_simulation(user_id, product_id, delay)
                )
                tasks.append(task)
        
        # Wait for all users to complete
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        for result in all_results:
            if isinstance(result, Exception):
                print(f"❌ Task error: {result}")
                continue
            if isinstance(result, list):
                self.results.extend(result)
            else:
                self.results.append(result)
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        metrics = self.calculate_metrics(total_time)
        return metrics
    
    async def _delayed_user_simulation(self, user_id: int, product_id: str, delay: float,
                                       account_email: str = None):
        """Run user simulation with delay"""
        if delay > 0:
            await asyncio.sleep(delay)
        return await self.run_user_simulation(user_id, product_id, account_email)
    
    def calculate_metrics(self, total_time: float) -> TestMetrics:
        """Calculate aggregated metrics"""
        metrics = TestMetrics()
        metrics.total_requests = len(self.results)
        
        successful = [r for r in self.results if r.status_code == 200 and not r.error]
        failed = [r for r in self.results if r.status_code != 200 or r.error]
        
        metrics.successful_requests = len(successful)
        metrics.failed_requests = len(failed)
        metrics.error_rate = (len(failed) / metrics.total_requests * 100) if metrics.total_requests > 0 else 0
        
        # Response times
        response_times = [r.response_time for r in successful if r.response_time]
        if response_times:
            metrics.response_times = response_times
            metrics.avg_response_time = statistics.mean(response_times)
            metrics.p50_response_time = statistics.median(response_times)
            if len(response_times) >= 20:
                metrics.p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
                metrics.p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]
        
        # First chunk times
        first_chunk_times = [r.first_chunk_time for r in successful if r.first_chunk_time]
        if first_chunk_times:
            metrics.first_chunk_times = first_chunk_times
            metrics.avg_first_chunk_time = statistics.mean(first_chunk_times)
        
        # Throughput
        metrics.throughput = metrics.successful_requests / total_time if total_time > 0 else 0
        
        # Response characteristics
        if successful:
            metrics.avg_response_length = statistics.mean([r.response_length for r in successful])
            metrics.avg_agent_count = statistics.mean([r.agent_count for r in successful])
            quality_scores = [r.quality_score for r in successful if r.quality_score]
            if quality_scores:
                metrics.quality_scores = quality_scores
                metrics.avg_quality_score = statistics.mean(quality_scores)
        
        # Error categorization
        for result in failed:
            if result.error:
                error_type = result.error.split(':')[0] if ':' in result.error else result.error
                metrics.errors_by_type[error_type] += 1
        
        return metrics
    
    def print_report(self, metrics: TestMetrics):
        """Print performance test report"""
        print("\n" + "="*80)
        print("📊 PERFORMANCE TEST REPORT")
        print("="*80)
        print(f"\n⏱️  Test Duration: {sum(metrics.response_times):.2f}s (total)")
        print(f"👥 Concurrent Users: {self.num_users}")
        print(f"📈 Total Requests: {metrics.total_requests}")
        print(f"✅ Successful: {metrics.successful_requests} ({100 - metrics.error_rate:.1f}%)")
        print(f"❌ Failed: {metrics.failed_requests} ({metrics.error_rate:.1f}%)")
        print(f"🚀 Throughput: {metrics.throughput:.2f} requests/second")
        
        print("\n📊 RESPONSE TIME METRICS:")
        print(f"   Average: {metrics.avg_response_time:.2f}s")
        print(f"   Median (P50): {metrics.p50_response_time:.2f}s")
        if metrics.p95_response_time:
            print(f"   P95: {metrics.p95_response_time:.2f}s")
        if metrics.p99_response_time:
            print(f"   P99: {metrics.p99_response_time:.2f}s")
        
        print("\n⚡ FIRST CHUNK TIME (Time to First Byte):")
        print(f"   Average: {metrics.avg_first_chunk_time:.2f}s")
        
        print("\n📝 RESPONSE QUALITY:")
        print(f"   Average Response Length: {metrics.avg_response_length:.0f} characters")
        print(f"   Average Agents Used: {metrics.avg_agent_count:.1f}")
        print(f"   Average Quality Score: {metrics.avg_quality_score:.1f}/100")
        
        if metrics.errors_by_type:
            print("\n❌ ERRORS BY TYPE:")
            for error_type, count in sorted(metrics.errors_by_type.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error_type}: {count}")
        
        print("\n" + "="*80)
        print("✅ NFR ASSESSMENT:")
        print("="*80)
        
        # NFR Checks
        nfr_passed = True
        
        # Response Time NFR: P95 < 30s
        if metrics.p95_response_time and metrics.p95_response_time > 30:
            print(f"❌ P95 Response Time: {metrics.p95_response_time:.2f}s (Target: <30s)")
            nfr_passed = False
        else:
            print(f"✅ P95 Response Time: {metrics.p95_response_time:.2f}s (Target: <30s)")
        
        # Error Rate NFR: < 5%
        if metrics.error_rate > 5:
            print(f"❌ Error Rate: {metrics.error_rate:.1f}% (Target: <5%)")
            nfr_passed = False
        else:
            print(f"✅ Error Rate: {metrics.error_rate:.1f}% (Target: <5%)")
        
        # Throughput NFR: > 2 req/s
        if metrics.throughput < 2:
            print(f"❌ Throughput: {metrics.throughput:.2f} req/s (Target: >2 req/s)")
            nfr_passed = False
        else:
            print(f"✅ Throughput: {metrics.throughput:.2f} req/s (Target: >2 req/s)")
        
        # Quality NFR: Average quality score > 60
        if metrics.avg_quality_score < 60:
            print(f"❌ Quality Score: {metrics.avg_quality_score:.1f}/100 (Target: >60)")
            nfr_passed = False
        else:
            print(f"✅ Quality Score: {metrics.avg_quality_score:.1f}/100 (Target: >60)")
        
        # First Chunk Time NFR: < 5s
        if metrics.avg_first_chunk_time > 5:
            print(f"❌ First Chunk Time: {metrics.avg_first_chunk_time:.2f}s (Target: <5s)")
            nfr_passed = False
        else:
            print(f"✅ First Chunk Time: {metrics.avg_first_chunk_time:.2f}s (Target: <5s)")
        
        print("\n" + "="*80)
        if nfr_passed:
            print("🎉 ALL NFR REQUIREMENTS MET!")
        else:
            print("⚠️  SOME NFR REQUIREMENTS NOT MET - REVIEW CONFIGURATION")
        print("="*80 + "\n")
        
        return nfr_passed

async def main():
    parser = argparse.ArgumentParser(description='Performance test for IdeaForge AI')
    parser.add_argument('--url', required=True, help='Base URL (e.g., https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud)')
    parser.add_argument('--token', help='Authentication token (optional if using --accounts-file)')
    parser.add_argument('--product-id', required=True, help='Product ID for testing')
    parser.add_argument('--users', type=int, default=100, help='Number of concurrent users (default: 100, ignored if using --accounts-file)')
    parser.add_argument('--ramp-up', type=int, default=30, help='Ramp-up time in seconds (default: 30)')
    parser.add_argument('--sessions-per-account', type=int, default=10, help='Number of concurrent sessions per demo account (default: 10)')
    parser.add_argument('--accounts-file', help='JSON file with user accounts: [{"email": "...", "password": "...", "user_id": "..."}]')
    parser.add_argument('--output', help='Output JSON file for metrics')
    
    args = parser.parse_args()
    
    # Load user accounts if provided
    user_accounts = None
    if args.accounts_file:
        with open(args.accounts_file, 'r') as f:
            user_accounts = json.load(f)
        print(f"📋 Loaded {len(user_accounts)} user accounts from {args.accounts_file}")
    
    async with PerformanceTester(args.url, args.token, args.users, user_accounts) as tester:
        metrics = await tester.run_test(args.product_id, args.ramp_up, args.sessions_per_account)
        nfr_passed = tester.print_report(metrics)
        
        # Save metrics to JSON if requested
        if args.output:
            metrics_dict = {
                "timestamp": datetime.utcnow().isoformat(),
                "base_url": args.url,
                "num_users": args.users,
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "error_rate": metrics.error_rate,
                "throughput": metrics.throughput,
                "avg_response_time": metrics.avg_response_time,
                "p50_response_time": metrics.p50_response_time,
                "p95_response_time": metrics.p95_response_time,
                "p99_response_time": metrics.p99_response_time,
                "avg_first_chunk_time": metrics.avg_first_chunk_time,
                "avg_response_length": metrics.avg_response_length,
                "avg_agent_count": metrics.avg_agent_count,
                "avg_quality_score": metrics.avg_quality_score,
                "errors_by_type": dict(metrics.errors_by_type),
                "nfr_passed": nfr_passed
            }
            with open(args.output, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
            print(f"📄 Metrics saved to {args.output}")
        
        sys.exit(0 if nfr_passed else 1)

if __name__ == "__main__":
    asyncio.run(main())

