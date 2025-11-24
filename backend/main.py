from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal, Optional
import structlog

from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

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
from backend.database import init_db, check_db_health
from backend.api.database import router as db_router
from backend.services.provider_registry import provider_registry

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

orchestrator = AgenticOrchestrator()


class APIKeyVerificationRequest(BaseModel):
    provider: Literal["openai", "claude", "gemini"]
    api_key: str


class APIKeyVerificationResponse(BaseModel):
    provider: Literal["openai", "claude", "gemini"]
    valid: bool
    message: str


class ProviderConfigureRequest(BaseModel):
    openaiKey: Optional[str] = None
    claudeKey: Optional[str] = None
    geminiKey: Optional[str] = None


class ProviderConfigureResponse(BaseModel):
    configured_providers: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version="1.0.0")
    # Initialize database connection
    db_connected = await init_db()
    if db_connected:
        logger.info("database_initialized", status="success")
    else:
        logger.warning("database_initialization_failed", status="warning")
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="Agentic PM Platform API",
    description="Enterprise multi-agent system for Product Management",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include database router
app.include_router(db_router)


@app.get("/", tags=["health"])
async def root():
    return {
        "name": "Agentic PM Platform API",
        "version": "1.0.0",
        "status": "operational"
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
        logger.error("workflow_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/multi-agent/process", response_model=MultiAgentResponse, tags=["multi-agent"])
async def process_multi_agent_request(request: MultiAgentRequest):
    """Process a multi-agent coordination request."""
    try:
        logger.info(
            "multi_agent_request",
            user_id=str(request.user_id),
            coordination_mode=request.coordination_mode,
            primary_agent=request.primary_agent,
            supporting_agents=request.supporting_agents
        )

        response = await orchestrator.process_multi_agent_request(
            user_id=request.user_id,
            request=request
        )

        return response

    except ValueError as e:
        logger.error("invalid_multi_agent_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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
async def configure_provider_keys(payload: ProviderConfigureRequest):
    """Configure provider API keys for backend agents."""
    try:
        configured = provider_registry.update_keys(
            openai_key=payload.openaiKey,
            claude_key=payload.claudeKey,
            gemini_key=payload.geminiKey,
        )
        return ProviderConfigureResponse(configured_providers=configured)
    except Exception as e:
        logger.error("provider_configuration_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level
    )
