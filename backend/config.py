from pydantic_settings import BaseSettings
from typing import Optional
import os


def _get_database_url() -> str:
    """Construct DATABASE_URL from individual components if not set or contains placeholder."""
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url or "$(POSTGRES_PASSWORD)" in database_url:
        # Construct from individual environment variables
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_user = os.getenv("POSTGRES_USER", "agentic_pm")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "devpassword")
        postgres_db = os.getenv("POSTGRES_DB", "agentic_pm_db")
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    return database_url


def _clean_api_key(key: Optional[str]) -> Optional[str]:
    """Clean API key by removing quotes and whitespace."""
    if not key:
        return None
    key = key.strip()
    # Remove surrounding quotes if present
    if (key.startswith('"') and key.endswith('"')) or (
        key.startswith("'") and key.endswith("'")
    ):
        key = key[1:-1].strip()
    return key if key else None


def get_openai_completion_param(model: str) -> str:
    """
    Get the correct completion parameter name based on the OpenAI model.

    GPT-5.1 models (gpt-5.1, gpt-5.1-chat-latest) require 'max_completion_tokens'.
    Older models (gpt-4o-mini, gpt-4o, gpt-5, etc.) use 'max_tokens'.

    Args:
        model: The model name (e.g., 'gpt-5.1', 'gpt-4o-mini')

    Returns:
        str: The parameter name ('max_completion_tokens' or 'max_tokens')
        Example: 'max_completion_tokens' for GPT-5.1 models, 'max_tokens' for others
    """
    # GPT-5.1 models require max_completion_tokens
    if model and ("gpt-5.1" in model.lower() or "gpt-5" in model.lower()):
        return "max_completion_tokens"
    # All other models use max_tokens
    return "max_tokens"


class Settings(BaseSettings):
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Database Configuration
    database_url: str = _get_database_url()

    # AI Provider API Keys (strip whitespace and quotes to ensure proper detection)
    openai_api_key: Optional[str] = _clean_api_key(os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = _clean_api_key(os.getenv("ANTHROPIC_API_KEY"))
    google_api_key: Optional[str] = _clean_api_key(os.getenv("GOOGLE_API_KEY"))
    
    # AI Gateway Configuration (Service Account)
    ai_gateway_client_id: Optional[str] = _clean_api_key(os.getenv("AI_GATEWAY_CLIENT_ID"))
    ai_gateway_client_secret: Optional[str] = _clean_api_key(os.getenv("AI_GATEWAY_CLIENT_SECRET"))
    ai_gateway_instance_id: Optional[str] = os.getenv("AI_GATEWAY_INSTANCE_ID", "1d8095ae-5ef9-4e61-885c-f5b031f505a4")
    ai_gateway_env: str = os.getenv("AI_GATEWAY_ENV", "prod")  # Environment: prod, dev, etc.
    # Provider-specific base URLs (constructed from instance_id and env)
    ai_gateway_openai_base_url: Optional[str] = os.getenv("AI_GATEWAY_OPENAI_BASE_URL")
    ai_gateway_anthropic_base_url: Optional[str] = os.getenv("AI_GATEWAY_ANTHROPIC_BASE_URL")
    # Legacy base_url for OAuth token endpoint (if needed)
    ai_gateway_base_url: Optional[str] = os.getenv("AI_GATEWAY_BASE_URL", "https://ai-gateway.quantumblack.com")
    ai_gateway_enabled: bool = os.getenv("AI_GATEWAY_ENABLED", "true").lower() == "true"  # Default to enabled
    ai_gateway_default_model: Optional[str] = os.getenv("AI_GATEWAY_DEFAULT_MODEL", "gpt-5.1")
    ai_gateway_fast_model: Optional[str] = os.getenv("AI_GATEWAY_FAST_MODEL")
    ai_gateway_standard_model: Optional[str] = os.getenv("AI_GATEWAY_STANDARD_MODEL", "gpt-5.1")
    ai_gateway_premium_model: Optional[str] = os.getenv("AI_GATEWAY_PREMIUM_MODEL", "gpt-5.1")

    # McKinsey OIDC/SSO Configuration
    mckinsey_client_id: str = os.getenv("MCKINSEY_CLIENT_ID", "")
    mckinsey_client_secret: str = os.getenv("MCKINSEY_CLIENT_SECRET", "")
    mckinsey_authorization_endpoint: str = os.getenv(
        "MCKINSEY_AUTHORIZATION_ENDPOINT",
        "https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/auth",
    )
    mckinsey_token_endpoint: str = os.getenv(
        "MCKINSEY_TOKEN_ENDPOINT",
        "https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/token",
    )
    mckinsey_jwks_uri: str = os.getenv(
        "MCKINSEY_JWKS_URI",
        "https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/certs",
    )
    mckinsey_redirect_uri: str = os.getenv("MCKINSEY_REDIRECT_URI", "")
    mckinsey_token_encryption_key: str = os.getenv("MCKINSEY_TOKEN_ENCRYPTION_KEY", "")

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
    session_secret: str = os.getenv(
        "SESSION_SECRET", "your_secure_random_secret_key_here"
    )
    session_expires_in: int = int(os.getenv("SESSION_EXPIRES_IN", "86400"))

    # Agent Configuration
    # Updated to latest models as of November 2025:
    # - GPT-5.1 (gpt-5.1): Released November 12, 2025 - Best for product requirements, ideation, reasoning, and discovery
    # - GPT-5 (gpt-5): Released August 7, 2025 - Enhanced reasoning with "Thinking" mode
    # - Claude 4 Sonnet: Advanced reasoning and ideation capabilities
    # - Gemini 3.0 Pro: Enhanced multimodal reasoning and discovery
    # Default to GPT-5.1 for best reasoning, with Gemini 3.0 Pro as secondary option
    agent_model_primary: str = os.getenv(
        "AGENT_MODEL_PRIMARY", "gpt-5.1"
    )  # GPT-5.1 for best reasoning (or gpt-5 as fallback)
    agent_model_secondary: str = os.getenv(
        "AGENT_MODEL_SECONDARY", "claude-sonnet-4-20250522"
    )
    agent_model_tertiary: str = os.getenv(
        "AGENT_MODEL_TERTIARY", "gemini-3.0-pro"
    )  # Gemini 3.0 Pro
    
    # Model tier overrides for direct OpenAI API (Dec 2025 GPT-5.1 models)
    # These values come from env.kind or environment variables
    # Default to agent_model_primary if not set (no hardcoded model names)
    agent_model_fast: Optional[str] = os.getenv("AGENT_MODEL_FAST")
    agent_model_standard: Optional[str] = os.getenv("AGENT_MODEL_STANDARD")
    agent_model_premium: Optional[str] = os.getenv("AGENT_MODEL_PREMIUM")

    # AI Response Timeout (seconds) - Set to 50s to avoid Cloudflare 60s timeout
    agent_response_timeout: float = float(os.getenv("AGENT_RESPONSE_TIMEOUT", "50.0"))

    # MCP Server Configuration
    mcp_github_url: str = os.getenv("MCP_GITHUB_URL", "http://mcp-github:8001")
    mcp_jira_url: str = os.getenv("MCP_JIRA_URL", "http://mcp-jira:8002")
    mcp_confluence_url: str = os.getenv(
        "MCP_CONFLUENCE_URL", "http://mcp-confluence:8003"
    )

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
    feature_agno_framework: bool = (
        os.getenv("FEATURE_AGNO_FRAMEWORK", "true").lower() == "true"
    )
    feature_fast_mcp: bool = os.getenv("FEATURE_FAST_MCP", "true").lower() == "true"
    feature_multi_tenant: bool = (
        os.getenv("FEATURE_MULTI_TENANT", "true").lower() == "true"
    )
    feature_leadership_view: bool = (
        os.getenv("FEATURE_LEADERSHIP_VIEW", "true").lower() == "true"
    )

    # SSL Verification (for API key verification)
    verify_ssl: bool = os.getenv("VERIFY_SSL", "false").lower() == "true"

    # Enterprise Settings
    tenant_mode: str = os.getenv("TENANT_MODE", "multi")
    max_products_per_user: int = int(os.getenv("MAX_PRODUCTS_PER_USER", "10"))
    max_team_members: int = int(os.getenv("MAX_TEAM_MEMBERS", "50"))

    # McKinsey CodeBeyond Standards
    codebeyond_templates_path: str = os.getenv(
        "CODEBEYOND_TEMPLATES_PATH", "./templates/codebeyond"
    )
    prd_validation_strict_mode: bool = (
        os.getenv("PRD_VALIDATION_STRICT_MODE", "true").lower() == "true"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
