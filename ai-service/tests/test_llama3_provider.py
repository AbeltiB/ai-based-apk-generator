"""
tests/phase2/test_llama3_provider.py
Tests for Llama3 LLM provider
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.llm import (
    Llama3Provider,
    LLMMessage,
    LLMProvider
)


@pytest.fixture
def config():
    """Test configuration"""
    return {
        "llama3_api_url": "https://fastchat.ideeza.com/v1/chat/completions",
        "llama3_model": "llama-3",
        "timeout": 30.0
    }


@pytest.fixture
def provider(config):
    """Create Llama3 provider instance"""
    return Llama3Provider(config)


@pytest.fixture
def test_messages():
    """Test messages"""
    return [
        LLMMessage(role="system", content="You are helpful"),
        LLMMessage(role="user", content="Hello")
    ]


class TestLlama3Initialization:
    """Test Llama3 provider initialization"""
    
    def test_initialization(self, provider):
        """Test provider initializes with correct settings"""
        assert provider.api_url == "https://fastchat.ideeza.com/v1/chat/completions"
        assert provider.model == "llama-3"
        assert provider.timeout == 30.0
        assert provider.get_provider_type() == LLMProvider.LLAMA3
    
    def test_custom_config(self):
        """Test initialization with custom config"""
        custom_config = {
            "llama3_api_url": "https://custom.api.com/v1/chat",
            "llama3_model": "llama-3-70b",
            "timeout": 60.0,
            "llama3_api_key": "test-key"
        }
        provider = Llama3Provider(custom_config)
        
        assert provider.api_url == "https://custom.api.com/v1/chat"
        assert provider.model == "llama-3-70b"
        assert provider.api_key == "test-key"


class TestMessageFormatting:
    """Test message formatting"""
    
    def test_format_messages(self, provider, test_messages):
        """Test message formatting for API"""
        formatted = provider.format_messages(test_messages)
        
        assert len(formatted) == 2
        assert formatted[0] == {"role": "system", "content": "You are helpful"}
        assert formatted[1] == {"role": "user", "content": "Hello"}
    
    def test_format_empty_messages(self, provider):
        """Test formatting empty message list"""
        formatted = provider.format_messages([])
        assert formatted == []


class TestGeneration:
    """Test generation functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_generation(self, provider, test_messages):
        """Test successful API call"""
        mock_response_data = {
            "id": "chatcmpl-123",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            response = await provider.generate(test_messages)
            
            assert response.content == "Hello! How can I help you?"
            assert response.provider == LLMProvider.LLAMA3
            assert response.tokens_used == 18
            assert response.finish_reason == "stop"
            assert response.model == "llama-3"
    
    @pytest.mark.asyncio
    async def test_generation_with_parameters(self, provider, test_messages):
        """Test generation with custom parameters"""
        mock_response_data = {
            "choices": [{
                "message": {"content": "Response"},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 20}
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await provider.generate(
                test_messages,
                temperature=0.5,
                max_tokens=100
            )
            
            # Verify API call parameters
            call_args = mock_post.call_args
            payload = call_args.kwargs['json']
            
            assert payload['temperature'] == 0.5
            assert payload['max_tokens'] == 100
            assert payload['model'] == 'llama-3'
    
    @pytest.mark.asyncio
    async def test_generation_api_request_format(self, provider, test_messages):
        """Test that API request is formatted correctly"""
        mock_response_data = {
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 10}
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await provider.generate(test_messages, temperature=0.7)
            
            # Verify request structure
            call_args = mock_post.call_args
            assert call_args.args[0] == "https://fastchat.ideeza.com/v1/chat/completions"
            
            payload = call_args.kwargs['json']
            assert payload['model'] == 'llama-3'
            assert 'messages' in payload
            assert isinstance(payload['messages'], list)
            assert payload['temperature'] == 0.7


class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, provider, test_messages):
        """Test handling of timeout errors"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            
            with pytest.raises(Exception, match="Llama3 timeout"):
                await provider.generate(test_messages)
    
    @pytest.mark.asyncio
    async def test_http_error(self, provider, test_messages):
        """Test handling of HTTP errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Error",
                    request=Mock(),
                    response=mock_response
                )
            )
            
            with pytest.raises(Exception, match="Llama3 HTTP error: 500"):
                await provider.generate(test_messages)
    
    @pytest.mark.asyncio
    async def test_invalid_response_format(self, provider, test_messages):
        """Test handling of invalid response format"""
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "format"}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(Exception):
                await provider.generate(test_messages)
    
    @pytest.mark.asyncio
    async def test_network_error(self, provider, test_messages):
        """Test handling of network errors"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Network error")
            )
            
            with pytest.raises(Exception, match="Llama3 error"):
                await provider.generate(test_messages)


class TestHealthCheck:
    """Test health check functionality"""
    
    @pytest.mark.asyncio
    async def test_healthy_provider(self, provider):
        """Test health check when provider is healthy"""
        mock_response_data = {
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 5}
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            is_healthy = await provider.health_check()
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_unhealthy_provider(self, provider):
        """Test health check when provider is unhealthy"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Service unavailable")
            )
            
            is_healthy = await provider.health_check()
            assert is_healthy is False


class TestAPIKeyHandling:
    """Test API key handling"""
    
    @pytest.mark.asyncio
    async def test_with_api_key(self):
        """Test request includes API key when configured"""
        config = {
            "llama3_api_url": "https://api.test.com/v1/chat",
            "llama3_model": "llama-3",
            "llama3_api_key": "secret-key-123"
        }
        provider = Llama3Provider(config)
        
        mock_response_data = {
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 10}
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            messages = [LLMMessage(role="user", content="test")]
            await provider.generate(messages)
            
            # Verify Authorization header
            headers = mock_post.call_args.kwargs['headers']
            assert headers['Authorization'] == 'Bearer secret-key-123'
    
    @pytest.mark.asyncio
    async def test_without_api_key(self, provider, test_messages):
        """Test request without API key"""
        mock_response_data = {
            "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 10}
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await provider.generate(test_messages)
            
            # Verify no Authorization header
            headers = mock_post.call_args.kwargs['headers']
            assert 'Authorization' not in headers