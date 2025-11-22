from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import structlog

from backend.config import settings
from backend.models.schemas import (
    AgentRequest,
    AgentResponse,
    HealthCheckResponse,
)
from backend.agents.orchestrator import AgenticOrchestrator

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

orchestrator = AgenticOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version="1.0.0")
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
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
async def root():
    return {
        "name": "Agentic PM Platform API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check():
    services = {
        "api": True,
        "openai": settings.openai_api_key is not None,
        "anthropic": settings.anthropic_api_key is not None,
        "google": settings.google_api_key is not None,
        "supabase": bool(settings.supabase_url and settings.supabase_anon_key),
    }

    return HealthCheckResponse(
        status="healthy" if all(services.values()) else "degraded",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level
    )
