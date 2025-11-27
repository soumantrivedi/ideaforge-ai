from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/agentic_pm_db")

    # AI Provider API Keys (strip whitespace to ensure proper detection)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", "").strip() or None
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY", "").strip() or None
    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY", "").strip() or None

    # Okta OAuth/SSO Configuration
    okta_client_id: str = os.getenv("OKTA_CLIENT_ID", "")
    okta_client_secret: str = os.getenv("OKTA_CLIENT_SECRET", "")
    okta_issuer: str = os.getenv("OKTA_ISSUER", "")

    # Jira Integration
    jira_url: str = os.getenv("JIRA_URL", "")
    jira_email: str = os.getenv("JIRA_EMAIL", "")
    jira_api_token: str = os.getenv("JIRA_API_TOKEN", "")

    # Confluence Integration
    confluence_url: str = os.getenv("CONFLUENCE_URL", "")
    confluence_email: str = os.getenv("CONFLUENCE_EMAIL", "")
    confluence_api_token: str = os.getenv("CONFLUENCE_API_TOKEN", "")

    # GitHub Integration
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_org: str = os.getenv("GITHUB_ORG", "")

    # Design Tool Integration
    v0_api_key: Optional[str] = os.getenv("V0_API_KEY")
    lovable_api_key: Optional[str] = os.getenv("LOVABLE_API_KEY")

    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Session Configuration
    session_secret: str = os.getenv("SESSION_SECRET", "your_secure_random_secret_key_here")
    session_expires_in: int = int(os.getenv("SESSION_EXPIRES_IN", "86400"))

    # Agent Configuration
    # Updated to latest models as of November 2025:
    # - GPT-5.1 (gpt-5.1): Released November 12, 2025 - Best for product requirements, ideation, reasoning, and discovery
    # - GPT-5 (gpt-5): Released August 7, 2025 - Enhanced reasoning with "Thinking" mode
    # - Claude 4 Sonnet: Advanced reasoning and ideation capabilities
    # - Gemini 3.0 Pro: Enhanced multimodal reasoning and discovery
    # Default to GPT-5.1 for best reasoning, with Gemini 3.0 Pro as secondary option
    agent_model_primary: str = os.getenv("AGENT_MODEL_PRIMARY", "gpt-5.1")  # GPT-5.1 for best reasoning (or gpt-5 as fallback)
    agent_model_secondary: str = os.getenv("AGENT_MODEL_SECONDARY", "claude-sonnet-4-20250522")
    agent_model_tertiary: str = os.getenv("AGENT_MODEL_TERTIARY", "gemini-3.0-pro")  # Gemini 3.0 Pro

    # MCP Server Configuration
    mcp_github_url: str = os.getenv("MCP_GITHUB_URL", "http://mcp-github:8001")
    mcp_jira_url: str = os.getenv("MCP_JIRA_URL", "http://mcp-jira:8002")
    mcp_confluence_url: str = os.getenv("MCP_CONFLUENCE_URL", "http://mcp-confluence:8003")

    # Backend Configuration
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    # Frontend URL - Environment-specific default:
    # - docker-compose: http://localhost:3001 (frontend on port 3001)
    # - kind/eks: Set via ConfigMap (external URL or ingress URL)
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3001")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "info")
    log_format: str = os.getenv("LOG_FORMAT", "json")

    # Feature Flags
    feature_agno_framework: bool = os.getenv("FEATURE_AGNO_FRAMEWORK", "true").lower() == "true"
    feature_fast_mcp: bool = os.getenv("FEATURE_FAST_MCP", "true").lower() == "true"
    feature_multi_tenant: bool = os.getenv("FEATURE_MULTI_TENANT", "true").lower() == "true"
    feature_leadership_view: bool = os.getenv("FEATURE_LEADERSHIP_VIEW", "true").lower() == "true"

    # SSL Verification (for API key verification)
    verify_ssl: bool = os.getenv("VERIFY_SSL", "false").lower() == "true"

    # Enterprise Settings
    tenant_mode: str = os.getenv("TENANT_MODE", "multi")
    max_products_per_user: int = int(os.getenv("MAX_PRODUCTS_PER_USER", "10"))
    max_team_members: int = int(os.getenv("MAX_TEAM_MEMBERS", "50"))

    # McKinsey CodeBeyond Standards
    codebeyond_templates_path: str = os.getenv("CODEBEYOND_TEMPLATES_PATH", "./templates/codebeyond")
    prd_validation_strict_mode: bool = os.getenv("PRD_VALIDATION_STRICT_MODE", "true").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
