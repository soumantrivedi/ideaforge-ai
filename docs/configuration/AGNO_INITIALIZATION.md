# Agno Framework Initialization

## Overview

The Agno framework is automatically initialized at application startup using API keys from the `.env` file. Users can override these keys in Settings, which will automatically reinitialize the Agno framework with the new keys.

## Automatic Initialization from .env

### Default Behavior

1. **At Startup**: The application reads API keys from `.env` file via the `Settings` class
2. **Provider Registry**: API keys are loaded into `ProviderRegistry` from environment variables
3. **Agno Initialization**: If at least one AI provider (OpenAI, Claude, or Gemini) is configured in `.env`, Agno framework is automatically initialized
4. **No User Action Required**: Users don't need to configure API keys in Settings if `.env` has them

### Required .env Variables

```bash
# Default AI provider (OpenAI)
OPENAI_API_KEY=sk-...

# Optional: Additional providers
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Feature flag (default: true)
FEATURE_AGNO_FRAMEWORK=true
```

### Startup Logs

When the application starts, you'll see logs indicating:

```
startup_provider_status:
  providers: ["openai"]
  has_openai: true
  source: "environment_variables"

startup_orchestrator_status:
  orchestrator_type: "AgnoAgenticOrchestrator"
  agno_enabled: true
  has_providers: true

agno_framework_ready_at_startup:
  providers: ["openai"]
  message: "Agno framework initialized automatically from .env file API keys"
```

## User Override in Settings

### How It Works

1. **User Saves API Key**: User provides a different API key in Settings
2. **Database Storage**: Key is encrypted and stored in `user_api_keys` table
3. **Provider Registry Update**: `ProviderRegistry` is updated with user's key (overrides .env key)
4. **Agno Reinitialization**: Orchestrator is automatically reinitialized with new keys
5. **Immediate Effect**: New keys are used for all subsequent agent requests

### API Key Priority

1. **User API Keys** (from database) - Highest priority
2. **Environment Variables** (from .env) - Fallback

If a user deletes their API key, the system falls back to the `.env` key.

### Reinitialization Process

When a user saves an AI provider API key:

```python
# 1. Key is saved to database
await _save_api_key_internal(provider, api_key, user_id, db)

# 2. User's keys are loaded
user_keys = await load_user_api_keys_from_db(db, user_id)

# 3. Provider registry is updated (user keys override .env)
provider_registry.update_keys(
    openai_key=user_keys.get("openai"),
    claude_key=user_keys.get("claude"),
    gemini_key=user_keys.get("gemini"),
)

# 4. Orchestrator is reinitialized
reinitialize_orchestrator()
```

### Logs

When a user updates an API key:

```
agno_reinitialized_after_api_key_update:
  provider: "openai"
  user_id: "..."
  has_openai: true
  has_claude: false
  has_gemini: false
  configured_providers: ["openai"]
```

## Supported Providers

### OpenAI (Default)

- **Environment Variable**: `OPENAI_API_KEY`
- **Database Provider**: `openai`
- **Default Model**: `gpt-5.1` (ChatGPT 5.1)

### Anthropic Claude

- **Environment Variable**: `ANTHROPIC_API_KEY`
- **Database Provider**: `anthropic`
- **Default Model**: `claude-sonnet-4-20250522` (Claude 4 Sonnet)

### Google Gemini

- **Environment Variable**: `GOOGLE_API_KEY`
- **Database Provider**: `google`
- **Default Model**: `gemini-3.0-pro` (Gemini 3.0 Pro)

## Manual Initialization

If Agno is not automatically initialized (e.g., no .env keys), users can manually initialize:

```bash
POST /api/agno/initialize
```

This endpoint:
1. Loads user's API keys from database
2. Falls back to .env keys if user keys not found
3. Initializes Agno framework
4. Returns initialization status

## Troubleshooting

### Agno Not Initializing

1. **Check .env file**: Ensure `OPENAI_API_KEY` (or other provider keys) are set
2. **Check feature flag**: Ensure `FEATURE_AGNO_FRAMEWORK=true` in .env
3. **Check logs**: Look for `startup_orchestrator_status` in backend logs
4. **Check provider registry**: Verify keys are loaded correctly

### User Keys Not Working

1. **Check database**: Verify keys are saved in `user_api_keys` table
2. **Check encryption**: Ensure encryption key is configured
3. **Check logs**: Look for `agno_reinitialized_after_api_key_update` after saving
4. **Verify provider**: Ensure provider name matches (openai, anthropic, google)

### Fallback to .env

If user deletes their API key:
1. Key is marked as inactive in database
2. Provider registry falls back to .env key
3. Agno is reinitialized with .env key
4. User can continue using the application

## Best Practices

1. **Production**: Use Kubernetes Secrets or environment variables for default keys
2. **Development**: Use .env file for local development
3. **User Override**: Allow users to override for testing different providers
4. **Logging**: Monitor logs for initialization status
5. **Error Handling**: Gracefully handle missing keys

## Related Documentation

- [API Keys Setup](./API_KEYS_SETUP.md)
- [Environment Variables](./environment-variables.md)
- [Multi-Agent System](../guides/multi-agent-system.md)
- [Agno Framework Migration](../guides/agno-migration.md)

