"""
tests/phase2/test_llm_orchestrator.py
Tests for LLM orchestrator
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from app.llm import (
    LLMOrchestrator,
    LLMMessage,
    LLMResponse,
    LLMProvider
)


@pytest.fixture
def config():
    """Test configuration"""
    return {
        "llama3_api_url": "https://fastchat.ideeza.com/v1/chat/completions",
        "llama3_model": "llama-3",
        "failure_threshold": 3,
        "failure_window_minutes": 5
    }


@pytest.fixture
def orchestrator(config):
    """Create orchestrator instance"""
    return LLMOrchestrator(config)


@pytest.fixture
def test_messages():
    """Test messages"""
    return [
        LLMMessage(role="system", content="You are a helpful assistant"),
        LLMMessage(role="user", content="Create a todo app")
    ]


class TestOrchestratorInitialization:
    """Test orchestrator initialization"""
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initializes correctly"""
        assert orchestrator.primary_provider is not None
        assert orchestrator.fallback_provider is not None
        assert orchestrator.failure_threshold == 3
        assert orchestrator.failure_count == 0
        assert orchestrator.force_fallback is False
    
    def test_custom_config(self):
        """Test custom configuration"""
        custom_config = {
            "failure_threshold": 5,
            "failure_window_minutes": 10
        }
        orch = LLMOrchestrator(custom_config)
        assert orch.failure_threshold == 5
        assert orch.failure_window == 10


class TestPrimaryGeneration:
    """Test primary provider (Llama3) generation"""
    
    @pytest.mark.asyncio
    async def test_successful_generation(self, orchestrator, test_messages):
        """Test successful generation with primary provider"""
        mock_response = LLMResponse(
            content="Generated app content",
            provider=LLMProvider.LLAMA3,
            tokens_used=100
        )
        
        with patch.object(
            orchestrator.primary_provider,
            'generate',
            return_value=mock_response
        ):
            response = await orchestrator.generate(test_messages)
            
            assert response.provider == LLMProvider.LLAMA3
            assert response.content == "Generated app content"
            assert orchestrator.failure_count == 0
            assert orchestrator.force_fallback is False
    
    @pytest.mark.asyncio
    async def test_generation_with_parameters(self, orchestrator, test_messages):
        """Test generation with custom parameters"""
        mock_response = LLMResponse(
            content="Generated content",
            provider=LLMProvider.LLAMA3
        )
        
        with patch.object(
            orchestrator.primary_provider,
            'generate',
            return_value=mock_response
        ) as mock_gen:
            await orchestrator.generate(
                test_messages,
                temperature=0.5,
                max_tokens=500
            )
            
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs['temperature'] == 0.5
            assert call_kwargs['max_tokens'] == 500


class TestFallbackMechanism:
    """Test fallback mechanism"""
    
    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, orchestrator, test_messages):
        """Test fallback when primary fails"""
        fallback_response = LLMResponse(
            content="Fallback content",
            provider=LLMProvider.HEURISTIC
        )
        
        with patch.object(
            orchestrator.primary_provider,
            'generate',
            side_effect=Exception("Primary failed")
        ), patch.object(
            orchestrator.fallback_provider,
            'generate',
            return_value=fallback_response
        ):
            response = await orchestrator.generate(test_messages)
            
            assert response.provider == LLMProvider.HEURISTIC
            assert orchestrator.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_forced_fallback_after_threshold(self, orchestrator, test_messages):
        """Test forced fallback after reaching failure threshold"""
        # Simulate failures to reach threshold
        orchestrator.failure_count = 3
        orchestrator.force_fallback = True
        
        fallback_response = LLMResponse(
            content="Fallback content",
            provider=LLMProvider.HEURISTIC
        )
        
        with patch.object(
            orchestrator.fallback_provider,
            'generate',
            return_value=fallback_response
        ) as mock_fallback:
            response = await orchestrator.generate(test_messages)
            
            assert response.provider == LLMProvider.HEURISTIC
            mock_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_force_provider_parameter(self, orchestrator, test_messages):
        """Test forcing specific provider"""
        fallback_response = LLMResponse(
            content="Forced fallback",
            provider=LLMProvider.HEURISTIC
        )
        
        with patch.object(
            orchestrator.fallback_provider,
            'generate',
            return_value=fallback_response
        ):
            response = await orchestrator.generate(
                test_messages,
                force_provider=LLMProvider.HEURISTIC
            )
            
            assert response.provider == LLMProvider.HEURISTIC


class TestFailureTracking:
    """Test failure tracking and recovery"""
    
    @pytest.mark.asyncio
    async def test_failure_count_increment(self, orchestrator, test_messages):
        """Test failure count increments correctly"""
        with patch.object(
            orchestrator.primary_provider,
            'generate',
            side_effect=Exception("Error")
        ), patch.object(
            orchestrator.fallback_provider,
            'generate',
            return_value=LLMResponse(content="fallback", provider=LLMProvider.HEURISTIC)
        ):
            await orchestrator.generate(test_messages)
            assert orchestrator.failure_count == 1
            
            await orchestrator.generate(test_messages)
            assert orchestrator.failure_count == 2
            
            await orchestrator.generate(test_messages)
            assert orchestrator.failure_count == 3
            assert orchestrator.force_fallback is True
    
    def test_failure_window_reset(self, orchestrator):
        """Test failure count resets after window expires"""
        orchestrator.failure_count = 2
        orchestrator.last_failure_time = datetime.now() - timedelta(minutes=10)
        
        orchestrator._check_failure_window()
        
        assert orchestrator.failure_count == 0
        assert orchestrator.force_fallback is False
    
    def test_manual_reset(self, orchestrator):
        """Test manual failure reset"""
        orchestrator.failure_count = 3
        orchestrator.force_fallback = True
        orchestrator.last_failure_time = datetime.now()
        
        orchestrator.reset_failures()
        
        assert orchestrator.failure_count == 0
        assert orchestrator.force_fallback is False
        assert orchestrator.last_failure_time is None
    
    @pytest.mark.asyncio
    async def test_success_resets_failures(self, orchestrator, test_messages):
        """Test successful generation resets failure count"""
        orchestrator.failure_count = 2
        orchestrator.force_fallback = False
        
        mock_response = LLMResponse(
            content="Success",
            provider=LLMProvider.LLAMA3
        )
        
        with patch.object(
            orchestrator.primary_provider,
            'generate',
            return_value=mock_response
        ):
            await orchestrator.generate(test_messages)
            
            assert orchestrator.failure_count == 0
            assert orchestrator.force_fallback is False


class TestHealthCheck:
    """Test health check functionality"""
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, orchestrator):
        """Test health check when all providers healthy"""
        with patch.object(
            orchestrator.primary_provider,
            'health_check',
            return_value=True
        ), patch.object(
            orchestrator.fallback_provider,
            'health_check',
            return_value=True
        ):
            health = await orchestrator.health_check()
            
            assert health["llama3"] is True
            assert health["heuristic"] is True
            assert health["orchestrator"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_primary_unhealthy(self, orchestrator):
        """Test health check when primary is unhealthy"""
        with patch.object(
            orchestrator.primary_provider,
            'health_check',
            return_value=False
        ), patch.object(
            orchestrator.fallback_provider,
            'health_check',
            return_value=True
        ):
            health = await orchestrator.health_check()
            
            assert health["llama3"] is False
            assert health["heuristic"] is True


class TestStatus:
    """Test status reporting"""
    
    def test_get_status(self, orchestrator):
        """Test getting orchestrator status"""
        orchestrator.failure_count = 2
        orchestrator.force_fallback = True
        orchestrator.last_failure_time = datetime.now()
        
        status = orchestrator.get_status()
        
        assert status["failure_count"] == 2
        assert status["force_fallback"] is True
        assert status["failure_threshold"] == 3
        assert status["last_failure"] is not None
    
    def test_status_no_failures(self, orchestrator):
        """Test status with no failures"""
        status = orchestrator.get_status()
        
        assert status["failure_count"] == 0
        assert status["force_fallback"] is False
        assert status["last_failure"] is None


class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self, orchestrator, test_messages):
        """Test when all providers fail"""
        with patch.object(
            orchestrator.primary_provider,
            'generate',
            side_effect=Exception("Primary failed")
        ), patch.object(
            orchestrator.fallback_provider,
            'generate',
            side_effect=Exception("Fallback failed")
        ):
            with pytest.raises(Exception, match="All LLM providers failed"):
                await orchestrator.generate(test_messages)