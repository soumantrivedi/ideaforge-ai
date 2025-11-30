"""
Streaming API endpoints for real-time multi-agent responses.
Supports Server-Sent Events (SSE) and WebSocket streaming.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Dict, Any, Optional, TYPE_CHECKING
from uuid import UUID
import json
import asyncio
import structlog
from datetime import datetime

from backend.database import get_db
from backend.api.auth import get_current_user
from backend.models.schemas import MultiAgentRequest, AgentInteraction
from backend.services.provider_registry import provider_registry

logger = structlog.get_logger()
router = APIRouter(prefix="/api/streaming", tags=["streaming"])

# Import orchestrator from main app context
# This will be set during app initialization
_orchestrator = None

def set_orchestrator(orch):
    """Set the orchestrator instance (called from main.py)."""
    global _orchestrator
    _orchestrator = orch

def get_orchestrator():
    """Get the orchestrator instance."""
    if _orchestrator is None:
        from backend.agents.agno_orchestrator import AgnoAgenticOrchestrator
        return AgnoAgenticOrchestrator(enable_rag=True)
    return _orchestrator


class StreamingEvent:
    """Helper class for creating SSE events."""
    
    @staticmethod
    def format_event(event_type: str, data: Dict[str, Any]) -> str:
        """Format data as SSE event."""
        json_data = json.dumps(data, default=str)
        return f"event: {event_type}\ndata: {json_data}\n\n"
    
    @staticmethod
    def agent_start(agent_name: str, query: str) -> str:
        """Agent started processing."""
        return StreamingEvent.format_event("agent_start", {
            "agent": agent_name,
            "query": query,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    def agent_chunk(agent_name: str, chunk: str) -> str:
        """Agent response chunk."""
        return StreamingEvent.format_event("agent_chunk", {
            "agent": agent_name,
            "chunk": chunk,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    def agent_complete(agent_name: str, response: str, metadata: Optional[Dict] = None) -> str:
        """Agent completed processing."""
        event_data = {
            "agent": agent_name,
            "response": response,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        # Include full metadata for transparency
        if metadata:
            event_data.update({
                "system_context": metadata.get("system_context"),
                "system_prompt": metadata.get("system_prompt"),
                "user_prompt": metadata.get("user_prompt"),
                "rag_context": metadata.get("rag_context"),
            })
        return StreamingEvent.format_event("agent_complete", event_data)
    
    @staticmethod
    def interaction(from_agent: str, to_agent: str, query: str, response: str, metadata: Optional[Dict] = None) -> str:
        """Agent-to-agent interaction."""
        event_data = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "query": query,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        # Include metadata if provided
        if metadata:
            event_data["metadata"] = metadata
        return StreamingEvent.format_event("interaction", event_data)
    
    @staticmethod
    def error(error: str, agent: Optional[str] = None) -> str:
        """Error event."""
        return StreamingEvent.format_event("error", {
            "error": error,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    def progress(progress: float, message: str) -> str:
        """Progress update."""
        return StreamingEvent.format_event("progress", {
            "progress": progress,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    def complete(response: str, interactions: list, metadata: Dict) -> str:
        """Final completion event."""
        return StreamingEvent.format_event("complete", {
            "response": response,
            "interactions": interactions,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat()
        })


async def stream_multi_agent_response(
    request: MultiAgentRequest,
    user_id: UUID,
    db: AsyncSession
) -> AsyncGenerator[str, None]:
    """
    Stream multi-agent response using SSE.
    Yields formatted SSE events as agent processing occurs.
    """
    try:
        # Load user API keys
        from backend.services.api_key_loader import load_user_api_keys_from_db
        user_keys = await load_user_api_keys_from_db(db, str(user_id))
        
        if user_keys:
            provider_registry.update_keys(
                openai_key=user_keys.get("openai"),
                claude_key=user_keys.get("claude"),
                gemini_key=user_keys.get("gemini"),
            )
        
        # Check providers
        if not provider_registry.get_configured_providers():
            yield StreamingEvent.error("No AI provider configured")
            return
        
        # Send initial progress
        yield StreamingEvent.progress(0.1, "Initializing agents...")
        
        # Create authenticated request
        authenticated_request = request.model_copy(update={"user_id": user_id})
        
        # Stream from orchestrator
        accumulated_response = ""
        interactions = []
        active_agents = set()
        
        orchestrator = get_orchestrator()
        async for event in orchestrator.stream_multi_agent_request(
            user_id=user_id,
            request=authenticated_request,
            db=db
        ):
            event_type = event.get("type")
            
            if event_type == "agent_start":
                agent_name = event.get("agent")
                active_agents.add(agent_name)
                yield StreamingEvent.agent_start(agent_name, event.get("query", ""))
                yield StreamingEvent.progress(
                    event.get("progress", 0.3),
                    f"{agent_name} started processing..."
                )
            
            elif event_type == "agent_chunk":
                agent_name = event.get("agent")
                chunk = event.get("chunk", "")
                accumulated_response += chunk
                yield StreamingEvent.agent_chunk(agent_name, chunk)
            
            elif event_type == "agent_complete":
                agent_name = event.get("agent")
                response = event.get("response", "")
                accumulated_response += response
                yield StreamingEvent.agent_complete(
                    agent_name,
                    response,
                    event.get("metadata")
                )
                yield StreamingEvent.progress(
                    event.get("progress", 0.7),
                    f"{agent_name} completed"
                )
            
            elif event_type == "interaction":
                interaction = {
                    "from_agent": event.get("from_agent"),
                    "to_agent": event.get("to_agent"),
                    "query": event.get("query", ""),
                    "response": event.get("response", ""),
                    "timestamp": event.get("timestamp", datetime.utcnow().isoformat()),
                    "metadata": event.get("metadata", {})  # Include metadata from interaction
                }
                interactions.append(interaction)
                yield StreamingEvent.interaction(
                    interaction["from_agent"],
                    interaction["to_agent"],
                    interaction["query"],
                    interaction["response"],
                    interaction.get("metadata")  # Pass metadata to interaction event
                )
            
            elif event_type == "error":
                error_msg = event.get("error", "Unknown error")
                error_type = event.get("error_type", "UnknownError")
                # Don't return immediately - allow partial results to be sent
                yield StreamingEvent.error(
                    f"{error_type}: {error_msg}" if error_type != "UnknownError" else error_msg,
                    event.get("agent")
                )
                # Continue to check for partial results instead of returning
                # The coordinator will send a complete event with partial results if available
            
            elif event_type == "complete":
                # Final completion
                yield StreamingEvent.complete(
                    accumulated_response,
                    interactions,
                    event.get("metadata", {})
                )
                break
        
        # Save conversation to database asynchronously (don't block streaming)
        asyncio.create_task(save_conversation_async(
            user_id, request, accumulated_response, interactions, db
        ))
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_type = type(e).__name__
        error_message = str(e) if str(e) else f"{error_type} occurred"
        error_repr = repr(e) if repr(e) else error_message
        
        # Use the most descriptive error message available
        final_error_message = error_message if error_message and error_message != "" else error_repr
        if not final_error_message or final_error_message == "":
            final_error_message = f"{error_type} occurred during streaming"
        
        logger.error(
            "streaming_error",
            error=final_error_message,
            error_type=error_type,
            error_repr=error_repr,
            traceback=error_trace,
            user_id=str(user_id)
        )
        # Send error event but don't break the stream immediately
        yield StreamingEvent.error(f"Streaming error: {final_error_message}")
        # Try to send a completion event with partial results if available
        if accumulated_response:
            yield StreamingEvent.complete(
                accumulated_response,
                interactions,
                {"error": final_error_message, "error_type": error_type, "partial": True}
            )


async def save_conversation_async(
    user_id: UUID,
    request: MultiAgentRequest,
    response: str,
    interactions: list,
    db: AsyncSession
):
    """Save conversation to database asynchronously."""
    try:
        from backend.api.database import router as db_router
        from sqlalchemy import text
        import uuid
        
        # Save user message
        user_message_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO conversation_history 
                (id, product_id, user_id, message_type, content, agent_name, created_at)
                VALUES (:id, :product_id, :user_id, 'user', :content, NULL, NOW())
            """),
            {
                "id": user_message_id,
                "product_id": str(request.product_id) if request.product_id else None,
                "user_id": str(user_id),
                "content": request.query
            }
        )
        
        # Save assistant response
        assistant_message_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO conversation_history 
                (id, product_id, user_id, message_type, content, agent_name, created_at)
                VALUES (:id, :product_id, :user_id, 'assistant', :content, :agent_name, NOW())
            """),
            {
                "id": assistant_message_id,
                "product_id": str(request.product_id) if request.product_id else None,
                "user_id": str(user_id),
                "content": response,
                "agent_name": request.primary_agent or "multi-agent"
            }
        )
        
        await db.commit()
        logger.info("conversation_saved", user_id=str(user_id), message_count=2)
    except Exception as e:
        logger.error("failed_to_save_conversation", error=str(e))
        await db.rollback()


@router.post("/multi-agent/stream")
async def stream_multi_agent(
    request: MultiAgentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream multi-agent response using Server-Sent Events (SSE).
    Returns a streaming response that sends events as agents process.
    """
    user_id = UUID(str(current_user["id"]))
    
    return StreamingResponse(
        stream_multi_agent_response(request, user_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info("websocket_connected", connection_id=connection_id)
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info("websocket_disconnected", connection_id=connection_id)
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """Send message to specific connection."""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_json(message)
            except Exception as e:
                logger.error("websocket_send_error", connection_id=connection_id, error=str(e))
                self.disconnect(connection_id)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("websocket_broadcast_error", connection_id=connection_id, error=str(e))
                disconnected.append(connection_id)
        
        for conn_id in disconnected:
            self.disconnect(conn_id)


manager = ConnectionManager()


@router.websocket("/ws/{connection_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_id: str
):
    """
    WebSocket endpoint for bidirectional real-time communication.
    Supports streaming multi-agent responses and receiving user messages.
    """
    await manager.connect(websocket, connection_id)
    
    try:
        # Authenticate via token in query params or first message
        user_id = None
        # Get token from query params
        from fastapi import Query
        token = websocket.query_params.get("token")
        if token:
            # Validate token and get user_id
            try:
                from backend.api.auth import get_user_from_token
                user_data = await get_user_from_token(token)
                user_id = UUID(str(user_data["id"]))
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": "Authentication failed"
                })
                manager.disconnect(connection_id)
                return
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Handle messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "multi_agent_request":
                # Process multi-agent request and stream response
                request_data = data.get("request", {})
                multi_agent_request = MultiAgentRequest(**request_data)
                
                # Stream response back
                orchestrator = get_orchestrator()
                async for event in orchestrator.stream_multi_agent_request(
                    user_id=user_id or UUID(str(data.get("user_id", "00000000-0000-0000-0000-000000000000"))),
                    request=multi_agent_request,
                    db=None  # WebSocket doesn't have direct DB access, use connection pool
                ):
                    await websocket.send_json(event)
            
            elif message_type == "ping":
                # Heartbeat
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif message_type == "disconnect":
                break
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error("websocket_error", connection_id=connection_id, error=str(e))
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass
        manager.disconnect(connection_id)

