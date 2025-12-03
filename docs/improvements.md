If your Agno multi-agent setup is taking ~2 minutes, something is way off compared to what the framework can do. Let’s turn this into a performance-tuning checklist you can apply right now.

I’ll break it into:

Figure out where the 2 mins are spent

Make each LLM call cheaper & faster

Cut down the number of LLM calls / agent hops

Use parallelism & async properly

Tune tools, RAG, and history

Runtime & infra tips

1. First: profile your runs (don’t guess)

Turn on Agno’s debug & metrics so you can see exactly where time is going. Agno’s debug mode + metrics show token usage, tool calls, and execution time per run. 
docs.agno.com
+1

from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    markdown=True,
    debug_mode=True,   # enable detailed logs
    # debug_level=2,   # uncomment for even more detail
)

response = agent.run("Some query")
print(response.metrics)  # includes duration, token stats etc.


For Teams, also enable debug on the team so you can see delegation & member runs: 
docs.agno.com
+1

Key things to look for:

Is most time in:

Model calls (LLM latency, many steps, many agents)?

Tool calls (slow HTTP / DB / web search)?

Workflow orchestration (loops, long workflows)?

Once you know “where the time goes”, you can target the right knobs below.

2. Make each LLM call faster & cheaper
2.1 Use the right model(s)

Prefer “mini” / “fast” variants for most agents and keep the heavy models only where absolutely required.

Agno lets you even split models: one for internal reasoning, one for final answer (via output_model). 
docs.agno.com

Example: heavy model to do tool+reasoning, fast model to draft the final answer:

from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4.1"),        # reasoning + tools
    output_model=OpenAIChat(id="gpt-5-mini"),  # fast final answer
)

2.2 Trim prompt & context

Every extra token slows the call and increases cost:

Keep system instructions tight – move long docs into knowledge / tools instead of bloating the prompt.

Avoid dumping huge chat history on each call. Instead:

Use add_history_to_context=False unless really needed, or

Limit it: num_history_runs & (from recent changelog) max_tool_calls_from_history to keep only the last few tool calls in context. 
docs.agno.com
+1

Enable compress_tool_results=True if your tools return large payloads; this shrinks what gets sent back to the model. 
docs.agno.com

Example:

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    add_history_to_context=True,
    num_history_runs=3,
    max_tool_calls_from_history=3,  # keep history lean
    compress_tool_results=True,
)

2.3 Set sensible generation limits

On the model:

max_tokens: cap this so the model doesn’t ramble.

temperature / top_p: more about style, but very high values can make outputs longer or more verbose.

Use prompt caching at provider level for large static prompts where available. 
docs.agno.com
+1

On Agno model config: 
docs.agno.com

from agno.models.openai import OpenAIChat

fast_model = OpenAIChat(
    id="gpt-4o-mini",
    max_tokens=256,
    temperature=0.4,
)

3. Reduce the number of LLM calls / reasoning steps
3.1 Turn down team-level reasoning

Teams can have a reasoning agent with multiple reasoning steps; great for quality, bad for latency if cranked up. Team reference: reasoning_agent, reasoning_min_steps, reasoning_max_steps. 
docs.agno.com

If you don’t really need deep multi-step chain-of-thought at the team level:

from agno.team import Team
from agno.models.openai import OpenAIChat

team = Team(
    name="My Team",
    members=[...],
    model=OpenAIChat(id="gpt-4o-mini"),
    reasoning_agent=None,       # disable team-level reasoning
    reasoning_min_steps=1,
    reasoning_max_steps=3,      # or keep this low if used
)

3.2 Keep agents narrow and tool-light

Agno recommends: agents do best when they have narrow scope and few tools. If you give one agent everything, the model spends time just deciding what to do. For complex tasks, split into specialized agents / workflows instead. 
docs-v1.agno.com
+1

If your current design:

1 user query → “coordinator” agent → 5–6 specialized agents in multiple rounds

Try:

A Workflow that:

Calls the few necessary agents once (maybe in parallel),

Then a single “synthesizer” step.

That cuts multiple agent hand-offs.

3.3 Avoid unbounded loops & iterative workflows

Workflows 2.0 supports loops and iterative research flows that run until a condition is met. Great for quality, but can easily blow up into 10+ model calls. 
docs.agno.com
+1

If you’re using loops:

Cap them: max_iterations=1 or 2 rather than 3–5.

Make the end condition easier to satisfy so you don’t keep iterating.

4. Use parallelism & async so work happens concurrently

Agno has built-in patterns for Parallel steps in Workflows and Teams. This is often the largest win for multi-agent latency. 
docs.agno.com
+3
docs.agno.com
+3
docs.agno.com
+3

4.1 Parallel workflow pattern

If you’re currently doing:

Step 1: Web research agent
Step 2: HN research agent
Step 3: Academic research agent
Step 4: Synthesis agent


Switch to:

from agno.workflow import Workflow, Step
from agno.workflow.parallel import Parallel

workflow = Workflow(
    name="Parallel Research Pipeline",
    steps=[
        Parallel(
            Step(name="Web Research",      agent=web_researcher),
            Step(name="HN Research",       agent=hn_researcher),
            Step(name="Academic Research", agent=academic_researcher),
            name="Research Phase",
        ),
        Step(name="Synthesis", agent=synthesizer),
    ],
)

workflow.print_response("Write about the latest AI developments", markdown=True)


All three research agents run at the same time, so latency ≈ max(single step time) instead of sum of all three. 
docs.agno.com
+1

4.2 Async (arun, async DBs, etc.)

Use async variants (Agent.arun, Team.arun) where you’re handling multiple user requests concurrently. 
docs.agno.com
+1

If you’re using a DB for sessions/memory, consider AsyncSqliteDb / AsyncMongoDb to avoid blocking. 
Agno

Example:

from agno.agent import Agent
from agno.db.sqlite import AsyncSqliteDb
from agno.models.openai import OpenAIChat

agent = Agent(
    db=AsyncSqliteDb(db_file="sessions.db"),
    model=OpenAIChat(id="gpt-4o-mini"),
)

async def handle(query: str):
    return await agent.arun(query)

5. Tools, RAG & history: avoid external bottlenecks
5.1 Optimize your tools

Tools are just Python functions / HTTP calls; if they’re slow, your agent is slow. 
docs.agno.com
+1

Make sure any HTTP clients use keep-alive and short timeouts.

Avoid multi-hop internal microservice calls inside tools.

When possible, batch operations in one tool call instead of making 5 separate calls.

Also, for development & repeated queries:

Enable tool result caching (cache_results=True on Toolkits or @tool) to avoid re-doing the same work repeatedly. 
docs.agno.com

from agno.tools.duckduckgo import DuckDuckGoTools
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[DuckDuckGoTools(cache_results=True)],
)

5.2 RAG / knowledge: tune retrieval

If you use Agno’s knowledge / vector DB:

Keep top_k modest (e.g. 3–5).

Pre-chunk and summarize documents so retrieval is fast and the context is small.

Don’t run multiple redundant knowledge searches in different agents if one shared “research agent” can handle it.

5.3 History + memory

Memory & session summaries are powerful but can add overhead: 
docs.agno.com
+1

Only enable enable_agentic_memory, enable_session_summaries, etc. where needed.

For short, stateless requests, turn them off so the framework doesn’t hit DB / memory systems unnecessarily.

6. Runtime / deployment tweaks

A few “plumbing” optimizations can easily shave seconds off:

Run AgentOS or FastAPI app in production mode

Use gunicorn/uvicorn with multiple workers, not reload=True dev mode. 
docs.agno.com
+1

Place services in the same region

AgentOS, DB, vector DB, and external tools (if internal microservices) should be close to each other and to the LLM endpoint where possible to minimize network RTT.

Connection pooling

For DBs and external HTTP, reuse clients instead of instantiating a new client in every tool call.

Retries & backoff

Teams & Agents both support retries, delay_between_retries, exponential_backoff. For a stable production system, keep retries low (or 0) to avoid invisible extra minutes if a provider is flaky. 
docs.agno.com
+1

7. Caching for repeated / similar queries

For development, demos, or workloads where the same query appears often:

Enable LLM response caching (cache_response=True and optional cache_ttl) on the model. Later identical queries will be almost instant. 
docs.agno.com
+2
docs.agno.com
+2

from agno.models.openai import OpenAIChat
from agno.agent import Agent

agent = Agent(
    model=OpenAIChat(
        id="gpt-4o",
        cache_response=True,
        cache_ttl=3600,  # 1 hour
    )
)


⚠️ Use this mainly for dev / testing / repeated scripted queries, not for truly dynamic user-facing queries that must always be fresh. 
docs.agno.com
+1