from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
import structlog

from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai import AuthenticationError as OpenAIAuthenticationError
from openai import APIError as OpenAIAPIError
from openai import APIConnectionError as OpenAIConnectionError
from anthropic import AsyncAnthropic
from anthropic import AuthenticationError as ClaudeAuthenticationError
from anthropic import APIError as ClaudeAPIError
from anthropic import APIConnectionError as ClaudeConnectionError
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError, PermissionDenied, Unauthenticated

from backend.config import settings
from backend.models.schemas import (
    AgentRequest,
    AgentResponse,
    HealthCheckResponse,
    MultiAgentRequest,
    MultiAgentResponse,
    AgentCapability,
)
from backend.agents.orchestrator import AgenticOrchestrator
from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator
from backend.agents import AGNO_AVAILABLE
from backend.database import init_db, check_db_health, get_db
from backend.api.database import router as db_router
from backend.api.design import router as design_router
from backend.api.auth import router as auth_router, get_current_user
from backend.api.users import router as users_router
from backend.api.products import router as products_router
from backend.api.conversations import router as conversations_router
from backend.api.product_scoring import router as product_scoring_router
from backend.api.integrations import router as integrations_router
from backend.api.documents import router as documents_router
from backend.api.export import router as export_router
from backend.services.provider_registry import provider_registry

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Global orchestrator - can be reinitialized dynamically
orchestrator: Optional[AgenticOrchestrator] = None
agno_enabled: bool = False

def _initialize_orchestrator(force_agno: Optional[bool] = None) -> tuple[AgenticOrchestrator, bool]:
    """
    Initialize orchestrator based on provider availability and feature flag.
    Returns (orchestrator, agno_enabled)
    """
    global orchestrator, agno_enabled
    
    # Check if any provider is configured
    has_provider = (
        provider_registry.has_openai_key() or
        provider_registry.has_claude_key() or
        provider_registry.has_gemini_key()
    )
    
    # Determine if Agno should be enabled
    should_enable_agno = False
    if force_agno is not None:
        should_enable_agno = force_agno
    elif has_provider and settings.feature_agno_framework and AGNO_AVAILABLE:
        should_enable_agno = True
    
    if should_enable_agno and AGNO_AVAILABLE:
        try:
            new_orchestrator = AgnoAgenticOrchestrator(enable_rag=True)
            logger.info("agno_orchestrator_initialized", framework="agno", rag_enabled=True, has_provider=has_provider)
            agno_enabled = True
            return new_orchestrator, True
        except Exception as e:
            logger.warning("agno_orchestrator_failed", error=str(e), falling_back="legacy")
            new_orchestrator = AgenticOrchestrator()
            agno_enabled = False
            return new_orchestrator, False
    else:
        new_orchestrator = AgenticOrchestrator()
        agno_enabled = False
        reason = "no_provider" if not has_provider else "agno_unavailable" if not AGNO_AVAILABLE else "feature_disabled"
        logger.info("legacy_orchestrator_initialized", framework="legacy", reason=reason)
        return new_orchestrator, False

# Initialize orchestrator on startup
orchestrator, agno_enabled = _initialize_orchestrator()

def reinitialize_orchestrator():
    """Reinitialize the global orchestrator. Can be called when API keys are updated."""
    global orchestrator, agno_enabled
    orchestrator, agno_enabled = _initialize_orchestrator()
    
    # If using Agno orchestrator, also reinitialize its components
    if agno_enabled and hasattr(orchestrator, 'reinitialize'):
        try:
            orchestrator.reinitialize()
            logger.info("orchestrator_reinitialized", framework="agno")
        except Exception as e:
            logger.warning("orchestrator_reinitialize_failed", error=str(e))


def _map_provider_exception(exc: Exception):
    """Translate upstream LLM provider errors into actionable HTTP responses."""
    if isinstance(exc, OpenAIAuthenticationError):
        raise HTTPException(
            status_code=401,
            detail="OpenAI rejected the API key. Please verify the key in Settings → Providers."
        )
    if isinstance(exc, ClaudeAuthenticationError):
        raise HTTPException(
            status_code=401,
            detail="Anthropic Claude rejected the API key. Please verify the key in Settings → Providers."
        )
    if isinstance(exc, (PermissionDenied, Unauthenticated)):
        raise HTTPException(
            status_code=401,
            detail="Google Gemini rejected the API key. Please verify the key in Settings → Providers."
        )
    if isinstance(exc, (OpenAIConnectionError, ClaudeConnectionError, GoogleAPIError, OpenAIAPIError, ClaudeAPIError)):
        raise HTTPException(
            status_code=502,
            detail="Unable to reach the configured LLM provider. Please retry or update the provider settings."
        )


class APIKeyVerificationRequest(BaseModel):
    provider: Literal["openai", "claude", "gemini", "v0"]
    api_key: str
    verify_ssl: Optional[bool] = None  # Optional: if not provided, uses settings.verify_ssl


class APIKeyVerificationResponse(BaseModel):
    provider: Literal["openai", "claude", "gemini", "v0"]
    valid: bool
    message: str


class ProviderConfigureRequest(BaseModel):
    openaiKey: Optional[str] = None
    claudeKey: Optional[str] = None
    geminiKey: Optional[str] = None
    v0Key: Optional[str] = None
    lovableKey: Optional[str] = None


class ProviderConfigureResponse(BaseModel):
    configured_providers: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("application_startup", version="1.0.0")
    
    # Initialize database connection
    db_connected = await init_db()
    if db_connected:
        logger.info("database_initialized", status="success")
    else:
        logger.warning("database_initialization_failed", status="warning")
    
    # Log provider status at startup (from environment variables/Kubernetes secrets)
    # Provider registry is initialized from .env file via Settings class
    configured_providers = provider_registry.get_configured_providers()
    logger.info(
        "startup_provider_status",
        providers=configured_providers,
        has_openai=provider_registry.has_openai_key(),
        has_claude=provider_registry.has_claude_key(),
        has_gemini=provider_registry.has_gemini_key(),
        source="environment_variables",
        openai_key_present=bool(settings.openai_api_key),
        anthropic_key_present=bool(settings.anthropic_api_key),
        google_key_present=bool(settings.google_api_key)
    )
    
    # Reinitialize orchestrator on startup to ensure Agno is initialized if providers are available
    # This uses API keys from .env file (via provider_registry which reads from Settings)
    global orchestrator, agno_enabled
    orchestrator, agno_enabled = _initialize_orchestrator()
    
    # Log orchestrator initialization status
    logger.info(
        "startup_orchestrator_status",
        orchestrator_type=type(orchestrator).__name__,
        agno_enabled=agno_enabled,
        has_providers=bool(configured_providers),
        feature_agno_framework=settings.feature_agno_framework,
        agno_available=AGNO_AVAILABLE
    )
    
    # Agno agents are automatically initialized when orchestrator is created
    # No additional initialization needed at startup if providers are in .env
    if agno_enabled:
        logger.info(
            "agno_framework_ready_at_startup",
            providers=configured_providers,
            message="Agno framework initialized automatically from .env file API keys"
        )
    elif configured_providers and AGNO_AVAILABLE and settings.feature_agno_framework:
        logger.warning(
            "agno_framework_not_enabled_despite_providers",
            providers=configured_providers,
            message="Providers available but Agno not enabled. Check feature flag and Agno availability."
        )
    elif not configured_providers:
        logger.info(
            "agno_framework_waiting_for_providers",
            message="No AI providers configured in .env. Users can configure API keys in Settings to enable Agno."
        )
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")


app = FastAPI(
    title="IdeaForge AI - Agentic PM Platform API",
    description="Enterprise multi-agent system for Product Management with user authentication, tenant isolation, and product lifecycle management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Build CORS allowed origins list
# Environment-specific defaults:
# - docker-compose: localhost:3001 (frontend on port 3001)
# - kind: localhost:80 (ingress) or ideaforge.local
# - eks: external domain (set via ConfigMap)
cors_origins = [
    settings.frontend_url,
    "http://localhost:3000",  # Vite dev server
    "http://localhost:3001",  # docker-compose frontend
    "http://localhost:5173",  # Vite HMR port
    "http://localhost",  # For ingress access (port 80)
    "http://localhost:80",  # Explicit port 80
    "http://localhost:8080",  # For kind cluster with port 8080
    "http://ideaforge.local",  # For hostname-based access
    "http://api.ideaforge.local",  # For API hostname
]

# Add environment variable origins if set
import os
env_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins.extend([origin.strip() for origin in env_origins if origin.strip()])

# Remove duplicates and empty strings
cors_origins = list(set([origin for origin in cors_origins if origin]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
from backend.api.api_keys import router as api_keys_router
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(products_router)
app.include_router(conversations_router)
app.include_router(db_router)
app.include_router(design_router)
app.include_router(api_keys_router)
app.include_router(product_scoring_router)
app.include_router(integrations_router)
app.include_router(documents_router)
app.include_router(export_router)


@app.get("/", tags=["health"])
async def root():
    """Root endpoint with API information and links to documentation."""
    return {
        "name": "IdeaForge AI - Agentic PM Platform API",
        "version": "1.0.0",
        "status": "operational",
        "docs": {
            "swagger_ui": "/api/docs",
            "redoc": "/api/redoc",
            "openapi_json": "/api/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "authentication": "/api/auth",
            "users": "/api/users",
            "products": "/api/products",
            "conversations": "/api/conversations",
            "agents": "/api/agents",
            "multi_agent": "/api/multi-agent"
        }
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check():
    db_healthy = await check_db_health()
    
    services = {
        "api": True,
        "database": db_healthy,
        "openai": provider_registry.has_openai_key(),
        "anthropic": provider_registry.has_claude_key(),
        "google": provider_registry.has_gemini_key(),
        "redis": True,  # Redis is optional
    }

    return HealthCheckResponse(
        status="healthy" if db_healthy and services["api"] else "degraded",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services=services
    )


@app.get("/api/agents", tags=["agents"])
async def list_agents():
    agents = orchestrator.get_available_agents()
    return {
        "agents": agents,
        "count": len(agents)
    }


@app.get("/api/agents/capabilities", tags=["agents"])
async def get_agent_capabilities():
    """Get capabilities of all agents."""
    capabilities = orchestrator.get_agent_capabilities()
    return {
        "capabilities": capabilities,
        "count": len(capabilities)
    }


@app.get("/api/agents/by-phase", tags=["agents"])
async def get_agents_by_phase(phase_name: Optional[str] = None):
    """
    Get agents relevant to a specific product lifecycle phase.
    
    Maps phases to their relevant agents:
    - Ideation: ideation, research, rag
    - Market Research: research, analysis, rag
    - Requirements: analysis, prd_authoring, rag
    - Design: ideation, v0, lovable, rag
    - Development Planning: prd_authoring, github_mcp, atlassian_mcp, rag
    - Go-to-Market: summary, scoring, export, rag
    """
    # Phase to agent mapping
    PHASE_AGENT_MAP = {
        "Ideation": ["ideation", "research", "rag"],
        "Market Research": ["research", "analysis", "rag"],
        "Requirements": ["analysis", "prd_authoring", "rag"],
        "Design": ["ideation", "v0", "lovable", "rag"],
        "Development Planning": ["prd_authoring", "github_mcp", "atlassian_mcp", "rag"],
        "Go-to-Market": ["summary", "scoring", "export", "rag"],
    }
    
    # Agent metadata with descriptions
    AGENT_METADATA = {
        "ideation": {
            "name": "Ideation Agent",
            "description": "Generates creative product ideas and concepts",
            "icon": "💡",
        },
        "research": {
            "name": "Research Agent",
            "description": "Conducts market and competitive research",
            "icon": "🔬",
        },
        "analysis": {
            "name": "Analysis Agent",
            "description": "Analyzes requirements and provides insights",
            "icon": "📊",
        },
        "prd_authoring": {
            "name": "PRD Authoring Agent",
            "description": "Creates comprehensive product requirements documents",
            "icon": "📝",
        },
        "summary": {
            "name": "Summary Agent",
            "description": "Generates summaries and overviews",
            "icon": "📄",
        },
        "scoring": {
            "name": "Scoring Agent",
            "description": "Evaluates and scores product ideas",
            "icon": "⭐",
        },
        "export": {
            "name": "Export Agent",
            "description": "Exports documents and generates reports",
            "icon": "📤",
        },
        "v0": {
            "name": "V0 Agent",
            "description": "Generates design prompts for V0",
            "icon": "🎨",
        },
        "lovable": {
            "name": "Lovable Agent",
            "description": "Generates design prompts for Lovable",
            "icon": "🎭",
        },
        "github_mcp": {
            "name": "GitHub Agent",
            "description": "Manages GitHub repositories and code",
            "icon": "🐙",
        },
        "atlassian_mcp": {
            "name": "Atlassian Agent",
            "description": "Manages Jira and Confluence integration",
            "icon": "🔷",
        },
        "rag": {
            "name": "RAG Agent",
            "description": "Retrieves context from knowledge base",
            "icon": "📚",
        },
    }
    
    if phase_name:
        # Get agents for specific phase
        agent_roles = PHASE_AGENT_MAP.get(phase_name, [])
    else:
        # Return all agents if no phase specified
        agent_roles = list(AGENT_METADATA.keys())
    
    # Build agent list with metadata
    agents = []
    for role in agent_roles:
        if role in AGENT_METADATA:
            metadata = AGENT_METADATA[role]
            agents.append({
                "role": role,
                "name": metadata["name"],
                "description": metadata["description"],
                "icon": metadata["icon"],
                "isActive": True,  # All agents are available
            })
    
    return {
        "phase": phase_name,
        "agents": agents,
        "count": len(agents)
    }


@app.post("/api/agents/process", response_model=AgentResponse, tags=["agents"])
async def process_agent_request(request: AgentRequest):
    try:
        logger.info(
            "agent_request",
            user_id=str(request.user_id),
            agent_type=request.agent_type,
            message_count=len(request.messages)
        )

        response = await orchestrator.route_request(
            user_id=request.user_id,
            product_id=request.product_id,
            agent_type=request.agent_type,
            messages=request.messages,
            context=request.context
        )

        return response

    except ValueError as e:
        logger.error("invalid_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _map_provider_exception(e)
        logger.error("processing_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/workflows/{workflow_type}", tags=["workflows"])
async def execute_workflow(
    workflow_type: str,
    request: AgentRequest
):
    try:
        if not request.product_id:
            raise ValueError("product_id is required for workflows")

        logger.info(
            "workflow_request",
            workflow_type=workflow_type,
            user_id=str(request.user_id),
            product_id=str(request.product_id)
        )

        initial_input = request.messages[0].content if request.messages else ""

        results = await orchestrator.collaborative_workflow(
            user_id=request.user_id,
            product_id=request.product_id,
            workflow_type=workflow_type,
            initial_input=initial_input,
            context=request.context
        )

        return {
            "workflow_type": workflow_type,
            "results": results,
            "timestamp": datetime.utcnow()
        }

    except ValueError as e:
        logger.error("invalid_workflow", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _map_provider_exception(e)
        logger.error("workflow_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/multi-agent/process", response_model=MultiAgentResponse, tags=["multi-agent"])
async def process_multi_agent_request(
    request: MultiAgentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process a multi-agent coordination request."""
    try:
        # First, check if providers are already configured from environment variables (Kubernetes secrets)
        configured_providers = provider_registry.get_configured_providers()
        logger.info(
            "checking_providers",
            user_id=str(current_user["id"]),
            env_providers=configured_providers,
            has_env_keys=True if configured_providers else False
        )
        
        # Load user-specific API keys from database and update provider registry
        # Only update if user has keys in database (user keys take precedence)
        from backend.services.api_key_loader import load_user_api_keys_from_db
        
        user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        logger.info(
            "loading_user_api_keys",
            user_id=str(current_user["id"]),
            keys_found=list(user_keys.keys()) if user_keys else [],
            key_count=len(user_keys) if user_keys else 0
        )
        
        # Update provider registry with user's keys ONLY if they exist
        # This allows user keys to override environment keys, but preserves env keys if user has none
        if user_keys:
            provider_registry.update_keys(
                openai_key=user_keys.get("openai"),
                claude_key=user_keys.get("claude"),
                gemini_key=user_keys.get("gemini"),
            )
            logger.info(
                "user_api_keys_loaded",
                user_id=str(current_user["id"]),
                providers=list(user_keys.keys()),
                configured_providers=provider_registry.get_configured_providers()
            )
        else:
            logger.info(
                "using_environment_keys",
                user_id=str(current_user["id"]),
                message="No user keys found, using environment-configured keys",
                configured_providers=provider_registry.get_configured_providers()
            )
        
        # Check if any provider is configured (either from env or user keys)
        configured_providers = provider_registry.get_configured_providers()
        if not configured_providers:
            logger.error(
                "no_providers_configured",
                user_id=str(current_user["id"]),
                user_keys_found=list(user_keys.keys()) if user_keys else [],
                registry_state={
                    "has_openai": provider_registry.has_openai_key(),
                    "has_claude": provider_registry.has_claude_key(),
                    "has_gemini": provider_registry.has_gemini_key()
                }
            )
            raise HTTPException(
                status_code=400,
                detail="No AI provider is configured. Please go to Settings and configure at least one AI provider (OpenAI, Anthropic, or Google Gemini) before using this feature."
            )
        
        # Use authenticated user's ID (not the one from request to ensure security)
        authenticated_user_id = UUID(str(current_user["id"]))
        
        logger.info(
            "multi_agent_request",
            user_id=str(authenticated_user_id),
            request_user_id=str(request.user_id),
            coordination_mode=request.coordination_mode,
            primary_agent=request.primary_agent,
            supporting_agents=request.supporting_agents,
            configured_providers=provider_registry.get_configured_providers()
        )

        # Create a new request with authenticated user ID for security
        # Use copy of request but with authenticated user ID
        authenticated_request = request.model_copy(update={"user_id": authenticated_user_id})

        response = await orchestrator.process_multi_agent_request(
            user_id=authenticated_user_id,
            request=authenticated_request
        )

        # Save conversation messages to database for historical access
        try:
            from backend.api.database import router as db_router
            import json
            from sqlalchemy import text
            
            session_id = request.context.get("session_id") if request.context else None
            product_id_str = str(request.product_id) if request.product_id else None
            
            # Save user message
            user_message_query = text("""
                INSERT INTO conversation_history
                (session_id, product_id, message_type, agent_name, agent_role, content, tenant_id)
                VALUES (:session_id, :product_id, :message_type, :agent_name, :agent_role, :content, :tenant_id)
            """)
            await db.execute(user_message_query, {
                "session_id": session_id,
                "product_id": product_id_str,
                "message_type": "user",
                "agent_name": None,
                "agent_role": None,
                "content": request.query,
                "tenant_id": current_user.get("tenant_id")
            })
            
            # Save assistant response with agent interactions metadata
            interaction_metadata = {
                "primary_agent": response.primary_agent,
                "coordination_mode": response.coordination_mode,
                "agent_interactions": [
                    {
                        "from_agent": i.get('from_agent') if isinstance(i, dict) else (i.from_agent if hasattr(i, 'from_agent') else ''),
                        "to_agent": i.get('to_agent') if isinstance(i, dict) else (i.to_agent if hasattr(i, 'to_agent') else ''),
                        "query": i.get('query') if isinstance(i, dict) else (i.query if hasattr(i, 'query') else ''),
                        "response": i.get('response') if isinstance(i, dict) else (i.response if hasattr(i, 'response') else ''),
                        "metadata": i.get('metadata', {}) if isinstance(i, dict) else (i.metadata if hasattr(i, 'metadata') else {})
                    }
                    for i in (response.agent_interactions or [])
                ] if response.agent_interactions else []
            }
            
            assistant_message_query = text("""
                INSERT INTO conversation_history
                (session_id, product_id, message_type, agent_name, agent_role, content, interaction_metadata, tenant_id)
                VALUES (:session_id, :product_id, :message_type, :agent_name, :agent_role, :content, CAST(:interaction_metadata AS jsonb), :tenant_id)
            """)
            await db.execute(assistant_message_query, {
                "session_id": session_id,
                "product_id": product_id_str,
                "message_type": "assistant",
                "agent_name": response.primary_agent,
                "agent_role": response.primary_agent,
                "content": response.response,
                "interaction_metadata": json.dumps(interaction_metadata),
                "tenant_id": current_user.get("tenant_id")
            })
            
            await db.commit()
        except Exception as e:
            logger.warning("failed_to_save_conversation", error=str(e), user_id=str(authenticated_user_id))
            await db.rollback()

        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("invalid_multi_agent_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _map_provider_exception(e)
        logger.error("multi_agent_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/multi-agent/interactions", tags=["multi-agent"])
async def get_agent_interactions():
    """Get recent agent-to-agent interactions."""
    interactions = orchestrator.coordinator.get_interaction_history()
    return {
        "interactions": [interaction.dict() for interaction in interactions[-20:]],  # Last 20
        "count": len(interactions)
    }


@app.post("/api/providers/verify", response_model=APIKeyVerificationResponse, tags=["providers"])
async def verify_provider_key(payload: APIKeyVerificationRequest):
    """Verify that an API key is valid for the selected provider."""
    try:
        if payload.provider == "openai":
            client = AsyncOpenAI(api_key=payload.api_key)
            await client.models.list()
            return APIKeyVerificationResponse(
                provider="openai",
                valid=True,
                message="OpenAI API key is valid."
            )

        if payload.provider == "claude":
            client = AsyncAnthropic(api_key=payload.api_key)
            await client.models.list()
            return APIKeyVerificationResponse(
                provider="claude",
                valid=True,
                message="Anthropic Claude API key is valid."
            )

        if payload.provider == "gemini":
            def verify_gemini_key() -> bool:
                genai.configure(api_key=payload.api_key)
                # Listing models is sufficient to validate the key
                next(genai.list_models())
                return True

            await run_in_threadpool(verify_gemini_key)
            return APIKeyVerificationResponse(
                provider="gemini",
                valid=True,
                message="Google Gemini API key is valid."
            )

        if payload.provider == "v0":
            # V0 API verification - perform complete API verification
            import httpx
            import ssl
            try:
                # Basic format validation first
                if not payload.api_key or len(payload.api_key) < 10:
                    raise HTTPException(
                        status_code=400,
                        detail="V0 API key format appears invalid. Please check your key."
                    )
                
                # Get SSL verification setting from request or fallback to config
                verify_ssl = payload.verify_ssl if payload.verify_ssl is not None else settings.verify_ssl
                
                # Create httpx client with SSL configuration
                # SSL verification can be disabled via VERIFY_SSL=false for development/testing
                async with httpx.AsyncClient(
                    verify=verify_ssl,  # Configurable SSL verification
                    timeout=httpx.Timeout(10.0, connect=5.0),
                    follow_redirects=True
                ) as client:
                    # V0 API uses https://api.v0.dev/v1/chat/completions for verification
                    # We'll test the token by making a minimal chat completion request
                    verification_attempts = [
                        # Primary V0 API endpoint - chat completions
                        {
                            "url": "https://api.v0.dev/v1/chat/completions",
                            "headers": {"Authorization": f"Bearer {payload.api_key}", "Content-Type": "application/json"},
                            "method": "POST",
                            "body": {"model": "v0-1.5-md", "messages": [{"role": "user", "content": "test"}]}
                        },
                        # Alternative: try with different model
                        {
                            "url": "https://api.v0.dev/v1/chat/completions",
                            "headers": {"Authorization": f"Bearer {payload.api_key}", "Content-Type": "application/json"},
                            "method": "POST",
                            "body": {"model": "v0", "messages": [{"role": "user", "content": "test"}]}
                        },
                        # Fallback: try user/profile endpoints (may not exist but worth trying)
                        {
                            "url": "https://api.v0.dev/v1/user",
                            "headers": {"Authorization": f"Bearer {payload.api_key}", "Content-Type": "application/json"},
                            "method": "GET",
                            "body": None
                        },
                        {
                            "url": "https://api.v0.dev/user",
                            "headers": {"Authorization": f"Bearer {payload.api_key}", "Content-Type": "application/json"},
                            "method": "GET",
                            "body": None
                        },
                    ]
                    
                    verification_successful = False
                    last_error = None
                    last_status_code = None
                    last_response_body = None
                    
                    for attempt in verification_attempts:
                        try:
                            if attempt["method"] == "GET":
                                response = await client.get(
                                    attempt["url"],
                                    headers=attempt["headers"],
                                    timeout=10.0
                                )
                            else:
                                # For POST, use the body specified in the attempt, or empty body
                                post_body = attempt.get("body", {})
                                response = await client.post(
                                    attempt["url"],
                                    headers=attempt["headers"],
                                    json=post_body if post_body else None,
                                    timeout=10.0
                                )
                            
                            last_status_code = response.status_code
                            
                            # Try to capture response body for debugging
                            try:
                                last_response_body = response.text[:500]  # First 500 chars
                            except:
                                last_response_body = "Could not read response body"
                            
                            # Success - key is valid
                            if response.status_code == 200:
                                # Try to parse response to ensure it's a valid API response
                                try:
                                    data = response.json()
                                    # If we get user data or any valid JSON, the key is authenticated
                                    verification_successful = True
                                    logger.info("v0_verification_success", endpoint=attempt["url"], method=attempt["method"])
                                    break
                                except:
                                    # Even if JSON parsing fails, 200 status means auth worked
                                    verification_successful = True
                                    logger.info("v0_verification_success_no_json", endpoint=attempt["url"], method=attempt["method"])
                                    break
                            
                            # Unauthorized - key is invalid
                            elif response.status_code == 401:
                                # For V0 API, 401 from chat/completions endpoint means token is invalid
                                # But we've reached the correct endpoint, so provide helpful error
                                error_detail = "V0 API key is invalid or unauthorized."
                                try:
                                    error_body = response.json()
                                    if "error" in error_body:
                                        error_detail += f" API Error: {error_body['error']}"
                                    elif "message" in error_body:
                                        error_detail += f" {error_body['message']}"
                                except:
                                    pass
                                error_detail += " Please verify your token is correct and has not expired."
                                raise HTTPException(
                                    status_code=400,
                                    detail=error_detail
                                )
                            
                            # Forbidden - key might be valid but lacks permissions
                            elif response.status_code == 403:
                                # Key is valid but may not have access to this endpoint
                                # Continue to next endpoint
                                logger.debug("v0_endpoint_forbidden", endpoint=attempt["url"], method=attempt["method"])
                                continue
                            
                            # Not found - endpoint doesn't exist
                            elif response.status_code == 404:
                                logger.debug("v0_endpoint_not_found", endpoint=attempt["url"], method=attempt["method"])
                                continue
                            
                            # Method not allowed - try POST instead
                            elif response.status_code == 405:
                                logger.debug("v0_method_not_allowed", endpoint=attempt["url"], method=attempt["method"])
                                # If we tried GET and got 405, try POST on the same endpoint
                                if attempt["method"] == "GET":
                                    try:
                                        post_response = await client.post(
                                            attempt["url"],
                                            headers=attempt["headers"],
                                            timeout=10.0
                                        )
                                        if post_response.status_code == 200:
                                            verification_successful = True
                                            logger.info("v0_verification_success_post_after_405", endpoint=attempt["url"])
                                            break
                                        elif post_response.status_code == 401:
                                            error_detail = "V0 API key is invalid or unauthorized."
                                            try:
                                                error_body = post_response.json()
                                                if "message" in error_body:
                                                    error_detail += f" {error_body['message']}"
                                            except:
                                                pass
                                            raise HTTPException(
                                                status_code=400,
                                                detail=error_detail
                                            )
                                    except HTTPException:
                                        raise
                                    except Exception as e:
                                        logger.debug("v0_post_after_405_failed", endpoint=attempt["url"], error=str(e))
                                continue
                            
                            # Other 2xx status codes might indicate success
                            elif 200 <= response.status_code < 300:
                                verification_successful = True
                                logger.info("v0_verification_success_2xx", endpoint=attempt["url"], status=response.status_code)
                                break
                            else:
                                # Other status codes - log for debugging
                                logger.debug("v0_unexpected_status", endpoint=attempt["url"], status=response.status_code)
                                last_error = f"Unexpected status code: {response.status_code}"
                                continue
                                
                        except httpx.HTTPStatusError as e:
                            last_status_code = e.response.status_code
                            try:
                                last_response_body = e.response.text[:500]
                            except:
                                last_response_body = "Could not read error response body"
                            
                            if e.response.status_code == 401:
                                # Unauthorized - key is definitely invalid
                                error_detail = f"V0 API key is invalid or unauthorized. Status: {e.response.status_code}"
                                try:
                                    error_body = e.response.json()
                                    if "message" in error_body:
                                        error_detail += f" - {error_body['message']}"
                                except:
                                    pass
                                raise HTTPException(
                                    status_code=400,
                                    detail=error_detail
                                )
                            elif e.response.status_code == 403:
                                # Forbidden - continue to next endpoint
                                logger.debug("v0_endpoint_forbidden_exception", endpoint=attempt["url"], status=e.response.status_code)
                                continue
                            else:
                                last_error = f"HTTP {e.response.status_code}: {str(e)}"
                                logger.warning("v0_http_error", endpoint=attempt["url"], status=e.response.status_code, error=str(e))
                                continue
                        except (httpx.RequestError, httpx.ConnectError, httpx.ConnectTimeout) as e:
                            # Network/connection errors - try next endpoint
                            last_error = f"Connection error: {str(e)}"
                            logger.warning("v0_connection_error", endpoint=attempt["url"], error=str(e))
                            continue
                        except ssl.SSLError as e:
                            # SSL certificate errors - log but try next endpoint
                            # This might indicate a proxy or network configuration issue
                            last_error = f"SSL verification error: {str(e)}"
                            logger.warning("v0_ssl_verification_error", error=str(e), endpoint=attempt["url"])
                            continue
                        except Exception as e:
                            last_error = f"Unexpected error: {str(e)}"
                            logger.error("v0_unexpected_error", endpoint=attempt["url"], error=str(e), error_type=type(e).__name__)
                            continue
                    
                    # If we successfully verified with any endpoint
                    if verification_successful:
                            return APIKeyVerificationResponse(
                                provider="v0",
                                valid=True,
                            message="V0 API key is valid and authenticated successfully."
                        )
                    
                    # If all endpoints failed but we didn't get 401, try a POST request to verify token
                    # Some APIs require POST for token verification
                    if not verification_successful:
                        post_endpoints = [
                            {
                                "url": "https://v0.dev/api/auth/verify",
                                "headers": {
                                    "Authorization": f"Bearer {payload.api_key}",
                                    "Content-Type": "application/json"
                                },
                                "body": {"token": payload.api_key}
                            },
                            {
                                "url": "https://v0.dev/api/v1/auth/verify",
                                "headers": {
                                    "Authorization": f"Bearer {payload.api_key}",
                                    "Content-Type": "application/json"
                                },
                                "body": {"token": payload.api_key}
                            },
                        ]
                        
                        for post_attempt in post_endpoints:
                            try:
                                post_response = await client.post(
                                    post_attempt["url"],
                                    headers=post_attempt["headers"],
                                    json=post_attempt["body"],
                                    timeout=10.0
                                )
                                
                                last_status_code = post_response.status_code
                                try:
                                    last_response_body = post_response.text[:500]
                                except:
                                    pass
                                
                                if post_response.status_code == 200:
                                    verification_successful = True
                                    logger.info("v0_verification_success_post", endpoint=post_attempt["url"])
                                    break
                                elif post_response.status_code == 401:
                                    error_detail = "V0 API key is invalid or unauthorized."
                                    try:
                                        error_body = post_response.json()
                                        if "message" in error_body:
                                            error_detail += f" {error_body['message']}"
                                    except:
                                        pass
                                    raise HTTPException(
                                        status_code=400,
                                        detail=error_detail
                                    )
                            except HTTPException:
                                raise
                            except httpx.HTTPStatusError as e:
                                if e.response.status_code == 401:
                                    raise HTTPException(
                                        status_code=400,
                                        detail="V0 API key is invalid or unauthorized. Please check your key."
                                    )
                                last_error = f"POST HTTP {e.response.status_code}: {str(e)}"
                                continue
                            except Exception as e:
                                last_error = f"POST error: {str(e)}"
                                continue
                    
                    # If we successfully verified with any endpoint
                    if verification_successful:
                        return APIKeyVerificationResponse(
                            provider="v0",
                            valid=True,
                            message="V0 API key is valid and authenticated successfully."
                        )
                    
                    # If we reach here, verification failed
                    # Build detailed error message
                    error_parts = []
                    if last_status_code:
                        error_parts.append(f"Last status code: {last_status_code}")
                    if last_response_body:
                        error_parts.append(f"Response: {last_response_body[:200]}")
                    if last_error:
                        error_parts.append(f"Error: {last_error}")
                    
                    error_detail = "V0 API key verification failed. Could not authenticate with V0 API."
                    if error_parts:
                        error_detail += " " + " | ".join(error_parts)
                    else:
                        error_detail += " All verification attempts failed without returning specific error information."
                    
                    # Check if it's an SSL error specifically
                    if last_error and ("SSL" in last_error or "certificate" in last_error.lower() or "CERTIFICATE_VERIFY_FAILED" in last_error):
                        error_detail = f"V0 API key verification failed due to SSL certificate issue. This may be due to network/proxy configuration. {error_detail}"
                    
                    logger.error("v0_verification_failed", 
                                last_status_code=last_status_code,
                                last_error=last_error,
                                last_response_body=last_response_body[:200] if last_response_body else None)
                    
                    raise HTTPException(
                        status_code=400,
                        detail=error_detail
                    )
                    
            except HTTPException:
                raise
            except ssl.SSLError as e:
                # SSL certificate verification failed
                raise HTTPException(
                    status_code=400,
                    detail=f"V0 API key verification failed due to SSL certificate verification error. This may be due to network/proxy configuration or a self-signed certificate in the chain. Please check your network settings or contact your administrator. Error: {str(e)}"
                )
            except Exception as e:
                # For any other error, provide detailed error message
                error_msg = str(e)
                if "SSL" in error_msg or "certificate" in error_msg.lower() or "CERTIFICATE_VERIFY_FAILED" in error_msg:
                    raise HTTPException(
                        status_code=400,
                        detail=f"V0 API key verification failed due to SSL certificate issue. This may be due to network/proxy configuration. Please check your network settings or contact your administrator. Error: {error_msg}"
                    )
                elif "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
                    raise HTTPException(
                        status_code=400,
                        detail=f"V0 API key is invalid: {error_msg}"
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"V0 API key verification failed: {error_msg}"
                    )

        raise HTTPException(status_code=400, detail="Unsupported provider")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "provider_verification_failed",
            provider=payload.provider,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/providers/configure", response_model=ProviderConfigureResponse, tags=["providers"])
async def configure_provider_keys(
    payload: ProviderConfigureRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Configure provider API keys for backend agents and save to database."""
    try:
        from backend.api.api_keys import _save_api_key_internal
        from backend.services.api_key_loader import load_user_api_keys_from_db
        
        # Load existing keys from database to preserve them if not provided
        existing_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
        
        # Determine which keys to save (only if provided and not empty)
        keys_to_save = {}
        keys_to_update_registry = {}
        
        # OpenAI
        if payload.openaiKey is not None and payload.openaiKey.strip():
            keys_to_save['openai'] = payload.openaiKey.strip()
            keys_to_update_registry['openai_key'] = payload.openaiKey.strip()
        elif 'openai' in existing_keys:
            # Preserve existing key
            keys_to_update_registry['openai_key'] = existing_keys['openai']
        
        # Claude/Anthropic
        if payload.claudeKey is not None and payload.claudeKey.strip():
            keys_to_save['anthropic'] = payload.claudeKey.strip()
            keys_to_update_registry['claude_key'] = payload.claudeKey.strip()
        elif 'claude' in existing_keys:
            # Preserve existing key
            keys_to_update_registry['claude_key'] = existing_keys['claude']
        
        # Gemini/Google
        if payload.geminiKey is not None and payload.geminiKey.strip():
            keys_to_save['google'] = payload.geminiKey.strip()
            keys_to_update_registry['gemini_key'] = payload.geminiKey.strip()
        elif 'gemini' in existing_keys:
            # Preserve existing key
            keys_to_update_registry['gemini_key'] = existing_keys['gemini']
        
        # V0
        if payload.v0Key is not None and payload.v0Key.strip():
            v0_key_trimmed = payload.v0Key.strip()
            keys_to_save['v0'] = v0_key_trimmed
            settings.v0_api_key = v0_key_trimmed
            import os
            os.environ["V0_API_KEY"] = settings.v0_api_key
            logger.info("v0_key_saved",
                       user_id=str(current_user['id']),
                       key_length=len(v0_key_trimmed),
                       key_prefix=v0_key_trimmed[:8] + "..." if len(v0_key_trimmed) > 8 else "N/A")
        elif 'v0' in existing_keys:
            # Preserve existing key
            settings.v0_api_key = existing_keys['v0']
            import os
            if settings.v0_api_key:
                os.environ["V0_API_KEY"] = settings.v0_api_key
                logger.info("v0_key_preserved",
                           user_id=str(current_user['id']),
                           key_length=len(settings.v0_api_key))
        
        # Lovable - No API key needed (uses link generator)
        # Remove any existing Lovable API keys from database
        if 'lovable' in existing_keys:
            # Delete existing Lovable API key (no longer needed)
            delete_query = text("""
                DELETE FROM user_api_keys
                WHERE user_id = :user_id AND provider = 'lovable'
            """)
            await db.execute(delete_query, {"user_id": current_user['id']})
            logger.info("lovable_api_key_removed", user_id=current_user['id'])
        
        # Save only the keys that were provided
        for provider, key_value in keys_to_save.items():
            # Ensure V0 provider name matches database schema
            db_provider = provider
            if provider == 'v0':
                db_provider = 'v0'  # Ensure it's saved as 'v0' in database
            await _save_api_key_internal(db_provider, key_value.strip(), current_user['id'], db)
            logger.info("api_key_saved_to_db",
                       user_id=str(current_user['id']),
                       provider=db_provider,
                       key_length=len(key_value.strip()))
        
        # Update in-memory registry with all keys (new + existing)
        configured = provider_registry.update_keys(**keys_to_update_registry)
        
        logger.info(
            "provider_keys_configured",
            user_id=str(current_user["id"]),
            keys_saved=list(keys_to_save.keys()),
            keys_preserved=[k for k in existing_keys.keys() if k not in keys_to_save],
            configured_providers=configured
        )
        
        # Automatically enable/disable Agno based on provider availability
        global orchestrator, agno_enabled
        orchestrator, agno_enabled = _initialize_orchestrator()
        
        # If Agno is enabled, reinitialize agents to use the new API keys
        if agno_enabled and hasattr(orchestrator, 'reinitialize'):
            try:
                orchestrator.reinitialize()
                logger.info("agno_agents_reinitialized_after_api_key_update", providers=configured)
            except Exception as e:
                logger.warning("agno_agents_reinitialization_failed", error=str(e))
        
        return ProviderConfigureResponse(configured_providers=configured)
    except Exception as e:
        logger.error("provider_configuration_failed", error=str(e), user_id=str(current_user["id"]))
        raise HTTPException(status_code=400, detail=str(e))


class AgnoStatusResponse(BaseModel):
    agno_available: bool
    agno_enabled: bool
    providers_configured: bool
    configured_providers: list[str]
    can_initialize: bool
    message: str


@app.get("/api/agno/status", response_model=AgnoStatusResponse, tags=["agno"])
async def get_agno_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get Agno framework status and initialization capability."""
    from backend.services.api_key_loader import load_user_api_keys_from_db
    
    # Load user's API keys
    user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
    
    # Check if any provider is configured
    has_openai = bool(user_keys.get("openai"))
    has_claude = bool(user_keys.get("claude"))
    has_gemini = bool(user_keys.get("gemini"))
    providers_configured = has_openai or has_claude or has_gemini
    
    configured_providers = []
    if has_openai:
        configured_providers.append("openai")
    if has_claude:
        configured_providers.append("claude")
    if has_gemini:
        configured_providers.append("gemini")
    
    can_initialize = AGNO_AVAILABLE and providers_configured
    
    message = ""
    if not AGNO_AVAILABLE:
        message = "Agno framework is not available. Please ensure agno package is installed."
    elif not providers_configured:
        message = "No AI provider configured. Please configure at least one provider (OpenAI, Claude, or Gemini) to enable Agno framework."
    elif not agno_enabled:
        message = "Agno framework is available and providers are configured. Click 'Initialize Agents' to enable."
    else:
        message = "Agno framework is enabled and ready to use."
    
    return AgnoStatusResponse(
        agno_available=AGNO_AVAILABLE,
        agno_enabled=agno_enabled,
        providers_configured=providers_configured,
        configured_providers=configured_providers,
        can_initialize=can_initialize,
        message=message
    )


class InitializeAgentsResponse(BaseModel):
    success: bool
    agno_enabled: bool
    message: str


@app.post("/api/agno/initialize", response_model=InitializeAgentsResponse, tags=["agno"])
async def initialize_agno_agents(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize Agno agents on demand.
    Uses user's API keys from database if available, otherwise falls back to .env keys.
    """
    from backend.services.api_key_loader import load_user_api_keys_from_db
    
    if not AGNO_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Agno framework is not available. Please ensure agno package is installed."
        )
    
    # Load user's API keys from database (if any)
    user_keys = await load_user_api_keys_from_db(db, str(current_user["id"]))
    
    # Update provider registry with user's keys (user keys override .env keys)
    # If user hasn't set keys, provider_registry still has .env keys from initialization
    provider_registry.update_keys(
        openai_key=user_keys.get("openai"),
        claude_key=user_keys.get("claude"),
        gemini_key=user_keys.get("gemini"),
    )
    
    # Check if any provider is configured (either from user keys or .env)
    has_provider = (
        provider_registry.has_openai_key() or
        provider_registry.has_claude_key() or
        provider_registry.has_gemini_key()
    )
    
    if not has_provider:
        raise HTTPException(
            status_code=400,
            detail="No AI provider configured. Please configure at least one provider (OpenAI, Claude, or Gemini) in Settings or ensure .env file has API keys."
        )
    
    # Get configured providers list
    configured_providers_list = []
    if provider_registry.has_openai_key():
        configured_providers_list.append("openai")
    if provider_registry.has_claude_key():
        configured_providers_list.append("claude")
    if provider_registry.has_gemini_key():
        configured_providers_list.append("gemini")
    
    # Initialize orchestrator with Agno
    global orchestrator, agno_enabled
    try:
        orchestrator, agno_enabled = _initialize_orchestrator(force_agno=True)
        
        # Reinitialize agents to use the updated API keys
        if agno_enabled and hasattr(orchestrator, 'reinitialize'):
            orchestrator.reinitialize()
            logger.info("agno_agents_reinitialized", providers=configured_providers_list)
        
        if agno_enabled:
            logger.info(
                "agno_agents_initialized_on_demand",
                user_id=str(current_user["id"]),
                providers=configured_providers_list
            )
            return InitializeAgentsResponse(
                success=True,
                agno_enabled=True,
                message="Agno agents initialized successfully!"
            )
        else:
            return InitializeAgentsResponse(
                success=False,
                agno_enabled=False,
                message="Failed to initialize Agno agents. Falling back to legacy orchestrator."
            )
    except Exception as e:
        logger.error("agno_initialization_failed", error=str(e), user_id=str(current_user["id"]))
        orchestrator, agno_enabled = _initialize_orchestrator(force_agno=False)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Agno agents: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level
    )
