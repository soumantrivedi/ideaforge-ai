"""
AI Gateway Model Discovery
Discovers available models from AI Gateway API and finds ChatGPT-5 models.
"""
import asyncio
from typing import List, Dict, Any, Optional
import structlog
from backend.services.ai_gateway_client import AIGatewayClient
from backend.services.provider_registry import provider_registry

logger = structlog.get_logger()


async def discover_chatgpt5_models() -> List[str]:
    """
    Discover ChatGPT-5 models from AI Gateway API.
    
    Returns:
        List of ChatGPT-5 model IDs (e.g., ['gpt-5', 'gpt-5.1', 'gpt-5.1-chat-latest'])
    """
    gateway_client = provider_registry.get_ai_gateway_client()
    if not gateway_client:
        logger.warning("ai_gateway_not_configured_for_model_discovery")
        return []
    
    try:
        models = await gateway_client.list_models()
        chatgpt5_models = []
        
        for model in models:
            model_id = model.get('id', '').lower()
            model_name = model.get('name', '').lower()
            
            # Look for GPT-5 models (gpt-5, gpt-5.1, gpt-5.1-chat-latest, etc.)
            if 'gpt-5' in model_id or 'gpt-5' in model_name:
                original_id = model.get('id', '')
                chatgpt5_models.append(original_id)
                logger.info("chatgpt5_model_discovered", model_id=original_id, model_name=model.get('name'))
        
        # Sort by version (prefer gpt-5.1 over gpt-5)
        chatgpt5_models.sort(key=lambda x: (
            '5.1' in x.lower(),
            'chat-latest' in x.lower(),
            x.lower()
        ), reverse=True)
        
        logger.info("chatgpt5_models_discovered", count=len(chatgpt5_models), models=chatgpt5_models)
        return chatgpt5_models
        
    except Exception as e:
        logger.error("chatgpt5_model_discovery_failed", error=str(e))
        return []


async def get_best_chatgpt5_model() -> Optional[str]:
    """
    Get the best available ChatGPT-5 model from AI Gateway.
    
    Returns:
        Best ChatGPT-5 model ID, or None if not available
    """
    models = await discover_chatgpt5_models()
    if models:
        return models[0]  # First model is the best (sorted)
    return None


async def update_ai_gateway_default_models():
    """
    Update AI Gateway default models based on discovered ChatGPT-5 models.
    This should be called at startup to set the best available models.
    """
    gateway_client = provider_registry.get_ai_gateway_client()
    if not gateway_client:
        return
    
    try:
        chatgpt5_models = await discover_chatgpt5_models()
        if not chatgpt5_models:
            logger.warning("no_chatgpt5_models_found", message="Using default models from config")
            return
        
        best_model = chatgpt5_models[0]
        
        # Find fast model (look for mini, flash, or instant variants)
        fast_model = best_model
        for model in chatgpt5_models:
            model_lower = model.lower()
            if any(keyword in model_lower for keyword in ['mini', 'flash', 'instant', 'chat-latest']):
                fast_model = model
                break
        
        # Update settings if possible (this is a best-effort update)
        from backend.config import settings
        if hasattr(settings, 'ai_gateway_default_model'):
            logger.info(
                "ai_gateway_models_updated",
                default_model=best_model,
                fast_model=fast_model,
                available_models=chatgpt5_models
            )
        
        return {
            'default': best_model,
            'fast': fast_model,
            'standard': best_model,
            'premium': best_model,
            'available': chatgpt5_models
        }
        
    except Exception as e:
        logger.error("ai_gateway_model_update_failed", error=str(e))
        return None

