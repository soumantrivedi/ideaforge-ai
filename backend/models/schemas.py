from pydantic import BaseModel, Field, field_serializer, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


class UserProfile(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    persona: Literal["product_manager", "leadership", "tech_lead"] = "product_manager"
    created_at: datetime
    updated_at: datetime


class Product(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    status: Literal["ideation", "build", "operate", "learn", "govern", "sunset"] = "ideation"
    created_at: datetime
    updated_at: datetime


class PRDDocument(BaseModel):
    id: UUID
    product_id: UUID
    title: str
    content: Dict[str, Any]
    version: int = 1
    status: Literal["draft", "in_review", "approved", "published"] = "draft"
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class AgentMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    agent_role: Optional[str] = None
    timestamp: Optional[datetime] = None


class AgentRequest(BaseModel):
    user_id: UUID
    product_id: Optional[UUID] = None
    agent_type: str
    messages: List[AgentMessage]
    context: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    agent_type: str
    response: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationSession(BaseModel):
    id: UUID
    user_id: UUID
    product_id: Optional[UUID] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JiraIssue(BaseModel):
    key: str
    summary: str
    description: Optional[str] = None
    issue_type: str
    status: str
    assignee: Optional[str] = None
    created: datetime


class JiraEpic(BaseModel):
    key: str
    name: str
    summary: str
    description: Optional[str] = None
    status: str
    stories: List[JiraIssue] = []


class ConfluencePage(BaseModel):
    id: str
    title: str
    space: str
    content: str
    version: int
    created: datetime
    updated: datetime


class GitHubRepository(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    url: str
    default_branch: str
    created_at: datetime


class KnowledgeArticle(BaseModel):
    id: UUID
    product_id: UUID
    title: str
    content: str
    source: Literal["manual", "jira", "confluence", "github"]
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class FeedbackEntry(BaseModel):
    id: UUID
    product_id: UUID
    agent_type: str
    user_feedback: str
    rating: int = Field(ge=1, le=5)
    context: Optional[Dict[str, Any]] = None
    created_at: datetime


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, bool]


class AgentInteraction(BaseModel):
    """Represents interaction between agents"""
    from_agent: str
    to_agent: str
    query: str
    response: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class MultiAgentRequest(BaseModel):
    """Request for multi-agent coordination"""
    user_id: UUID
    product_id: Optional[UUID] = None
    query: str
    coordination_mode: Literal["sequential", "parallel", "collaborative", "debate", "enhanced_collaborative"] = "collaborative"
    primary_agent: Optional[str] = None
    supporting_agents: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class MultiAgentResponse(BaseModel):
    """Response from multi-agent coordination"""
    primary_agent: str
    response: str
    agent_interactions: List[AgentInteraction] = []
    coordination_mode: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentCapability(BaseModel):
    """Agent capability definition"""
    agent_type: str
    capabilities: List[str]
    confidence_scores: Dict[str, float] = {}
    description: str


# Async Job Schemas for long-running multi-agent requests


class JobSubmitRequest(BaseModel):
    """Request to submit an async multi-agent job"""
    request: MultiAgentRequest  # The original multi-agent request


class JobSubmitResponse(BaseModel):
    """Response when submitting a job"""
    job_id: str
    status: str = "pending"
    message: str = "Job submitted successfully"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion_seconds: Optional[int] = 300  # Default 5 minutes


class JobStatusResponse(BaseModel):
    """Response for job status check"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() if v else None})
    
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: Optional[float] = None  # 0.0 to 1.0
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    estimated_remaining_seconds: Optional[int] = None
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime, _info):
        """Serialize datetime to ISO format string"""
        if value is None:
            return None
        return value.isoformat()


class JobResultResponse(BaseModel):
    """Response containing job result"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() if v else None})
    
    job_id: str
    status: Literal["completed", "failed"]
    result: Optional[MultiAgentResponse] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    @field_serializer('created_at', 'completed_at')
    def serialize_datetime(self, value: datetime, _info):
        """Serialize datetime to ISO format string"""
        if value is None:
            return None
        return value.isoformat()
