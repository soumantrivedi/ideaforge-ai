"""
Tests for AI Gateway integration.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from backend.services.ai_gateway_client import AIGatewayClient
from backend.models.ai_gateway_model import AIGatewayModel
from backend.services.provider_registry import ProviderRegistry


@pytest.fixture
def mock_gateway_client():
    """Create a mock AI Gateway client."""
    client = Mock(spec=AIGatewayClient)
    client.client_id = "test_client_id"
    client.client_secret = "test_client_secret"
    client.base_url = "https://test-gateway.example.com"
    return client


@pytest.mark.asyncio
async def test_ai_gateway_client_token_refresh():
    """Test that AI Gateway client refreshes tokens correctly."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock token response
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_token_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_token_response
        
        client = AIGatewayClient(
            client_id="test_id",
            client_secret="test_secret",
            base_url="https://test.example.com"
        )
        
        token = await client._get_access_token()
        assert token == "test_token"
        assert client._access_token == "test_token"


@pytest.mark.asyncio
async def test_ai_gateway_client_list_models():
    """Test listing models from AI Gateway."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock token response
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_token_response.raise_for_status = Mock()
        
        # Mock models response
        mock_models_response = Mock()
        mock_models_response.json.return_value = {
            "data": [
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet"}
            ]
        }
        mock_models_response.raise_for_status = Mock()
        
        mock_client.post.return_value = mock_token_response
        mock_client.get.return_value = mock_models_response
        
        client = AIGatewayClient(
            client_id="test_id",
            client_secret="test_secret"
        )
        
        models = await client.list_models()
        assert len(models) == 2
        assert models[0]["id"] == "gpt-4o"


@pytest.mark.asyncio
async def test_ai_gateway_model_generate():
    """Test AI Gateway model generation."""
    mock_client = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value={
        "choices": [{
            "message": {
                "content": "Test response"
            }
        }]
    })
    
    model = AIGatewayModel(
        id="gpt-4o",
        client=mock_client,
        temperature=0.7,
        max_tokens=1000
    )
    
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    
    response = await model.generate(messages)
    assert response == "Test response"
    mock_client.chat_completion.assert_called_once()


def test_provider_registry_ai_gateway():
    """Test ProviderRegistry with AI Gateway."""
    with patch('backend.services.provider_registry.settings') as mock_settings:
        mock_settings.ai_gateway_client_id = "test_id"
        mock_settings.ai_gateway_client_secret = "test_secret"
        mock_settings.ai_gateway_base_url = "https://test.example.com"
        
        registry = ProviderRegistry()
        
        # Check if AI Gateway is configured
        assert registry.has_ai_gateway() == True
        assert registry.get_ai_gateway_client_id() == "test_id"
        assert "ai_gateway" in registry.get_configured_providers()


@pytest.mark.asyncio
async def test_ai_gateway_verify_credentials():
    """Test AI Gateway credential verification."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful token and models responses
        mock_token_response = Mock()
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_token_response.raise_for_status = Mock()
        
        mock_models_response = Mock()
        mock_models_response.json.return_value = {"data": []}
        mock_models_response.raise_for_status = Mock()
        
        mock_client.post.return_value = mock_token_response
        mock_client.get.return_value = mock_models_response
        
        client = AIGatewayClient(
            client_id="test_id",
            client_secret="test_secret"
        )
        
        is_valid = await client.verify_credentials()
        assert is_valid == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

