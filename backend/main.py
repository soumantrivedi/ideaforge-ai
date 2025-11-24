from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal, Optional
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
from backend.services.provider_registry import provider_registry

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize orchestrator based on feature flag
if settings.feature_agno_framework and AGNO_AVAILABLE:
    try:
        orchestrator = AgnoAgenticOrchestrator(enable_rag=True)
        logger.info("agno_orchestrator_initialized", framework="agno", rag_enabled=True)
    except Exception as e:
        logger.warning("agno_orchestrator_failed", error=str(e), falling_back="legacy")
        orchestrator = AgenticOrchestrator()
else:
    orchestrator = AgenticOrchestrator()
    logger.info("legacy_orchestrator_initialized", framework="legacy")


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
    title="IdeaForge AI - Agentic PM Platform API",
    description="Enterprise multi-agent system for Product Management with user authentication, tenant isolation, and product lifecycle management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
                    # Try multiple V0 API endpoints for complete verification
                    # V0 typically uses these endpoints for authentication verification
                    verification_endpoints = [
                        "https://v0.dev/api/user",
                        "https://v0.dev/api/v1/user",
                        "https://api.v0.dev/user",
                        "https://v0.dev/api/auth/verify",
                    ]
                    
                    verification_successful = False
                    last_error = None
                    
                    for endpoint in verification_endpoints:
                        try:
                            response = await client.get(
                                endpoint,
                                headers={"Authorization": f"Bearer {payload.api_key}"},
                                timeout=10.0
                            )
                            
                            # Success - key is valid
                            if response.status_code == 200:
                                # Try to parse response to ensure it's a valid API response
                                try:
                                    data = response.json()
                                    # If we get user data or any valid JSON, the key is authenticated
                                    verification_successful = True
                                    break
                                except:
                                    # Even if JSON parsing fails, 200 status means auth worked
                                    verification_successful = True
                                    break
                            
                            # Unauthorized - key is invalid
                            elif response.status_code == 401:
                                raise HTTPException(
                                    status_code=400,
                                    detail="V0 API key is invalid or unauthorized. Please check your key."
                                )
                            
                            # Forbidden - key might be valid but lacks permissions
                            elif response.status_code == 403:
                                # Key is valid but may not have access to this endpoint
                                # Continue to next endpoint
                                continue
                            
                            # Other 2xx status codes might indicate success
                            elif 200 <= response.status_code < 300:
                                verification_successful = True
                                break
                                
                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 401:
                                # Unauthorized - key is definitely invalid
                                raise HTTPException(
                                    status_code=400,
                                    detail="V0 API key is invalid or unauthorized. Please check your key."
                                )
                            elif e.response.status_code == 403:
                                # Forbidden - continue to next endpoint
                                continue
                            else:
                                last_error = str(e)
                                continue
                        except (httpx.RequestError, httpx.ConnectError, httpx.ConnectTimeout) as e:
                            # Network/connection errors - try next endpoint
                            last_error = str(e)
                            continue
                        except ssl.SSLError as e:
                            # SSL certificate errors - log but try next endpoint
                            # This might indicate a proxy or network configuration issue
                            last_error = f"SSL verification error: {str(e)}"
                            logger.warning("v0_ssl_verification_error", error=str(e), endpoint=endpoint)
                            continue
                        except Exception as e:
                            last_error = str(e)
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
                    try:
                        post_response = await client.post(
                            "https://v0.dev/api/auth/verify",
                            headers={
                                "Authorization": f"Bearer {payload.api_key}",
                                "Content-Type": "application/json"
                            },
                            json={"token": payload.api_key},
                            timeout=10.0
                        )
                        
                        if post_response.status_code == 200:
                            return APIKeyVerificationResponse(
                                provider="v0",
                                valid=True,
                                message="V0 API key is valid and authenticated successfully."
                            )
                        elif post_response.status_code == 401:
                            raise HTTPException(
                                status_code=400,
                                detail="V0 API key is invalid or unauthorized. Please check your key."
                            )
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 401:
                            raise HTTPException(
                                status_code=400,
                                detail="V0 API key is invalid or unauthorized. Please check your key."
                            )
                    
                    # If we reach here, verification failed
                    # Check if it's an SSL error specifically
                    if last_error and ("SSL" in last_error or "certificate" in last_error.lower() or "CERTIFICATE_VERIFY_FAILED" in last_error):
                        raise HTTPException(
                            status_code=400,
                            detail=f"V0 API key verification failed due to SSL certificate issue. This may be due to network/proxy configuration. Please check your network settings or contact your administrator. Error: {last_error}"
                        )
                    
                    # Otherwise, general verification failure
                    raise HTTPException(
                        status_code=400,
                        detail=f"V0 API key verification failed. Could not authenticate with V0 API. Please verify your key is correct and has proper permissions. Error: {last_error or 'Unknown error'}"
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
        
        # Save API keys to database
        if payload.openaiKey is not None and payload.openaiKey.strip():
            await _save_api_key_internal('openai', payload.openaiKey, current_user['id'], db)
        
        if payload.claudeKey is not None and payload.claudeKey.strip():
            await _save_api_key_internal('anthropic', payload.claudeKey, current_user['id'], db)
        
        if payload.geminiKey is not None and payload.geminiKey.strip():
            await _save_api_key_internal('google', payload.geminiKey, current_user['id'], db)
        
        if payload.v0Key is not None and payload.v0Key.strip():
            await _save_api_key_internal('v0', payload.v0Key, current_user['id'], db)
        
        if payload.lovableKey is not None and payload.lovableKey.strip():
            await _save_api_key_internal('lovable', payload.lovableKey, current_user['id'], db)
        
        # Update in-memory registry for immediate use
        configured = provider_registry.update_keys(
            openai_key=payload.openaiKey,
            claude_key=payload.claudeKey,
            gemini_key=payload.geminiKey,
        )
        
        # Handle V0 and Lovable keys in settings
        if payload.v0Key is not None:
            settings.v0_api_key = payload.v0Key or None
            import os
            if settings.v0_api_key:
                os.environ["V0_API_KEY"] = settings.v0_api_key
            else:
                os.environ.pop("V0_API_KEY", None)
        
        if payload.lovableKey is not None:
            settings.lovable_api_key = payload.lovableKey or None
            import os
            if settings.lovable_api_key:
                os.environ["LOVABLE_API_KEY"] = settings.lovable_api_key
            else:
                os.environ.pop("LOVABLE_API_KEY", None)
        
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
