"""
tests/phase2/test_heuristic_provider.py
Tests for heuristic fallback provider
"""
import pytest
import json

from app.llm import (
    HeuristicProvider,
    LLMMessage,
    LLMProvider
)


@pytest.fixture
def config():
    """Test configuration"""
    return {}


@pytest.fixture
def provider(config):
    """Create heuristic provider instance"""
    return HeuristicProvider(config)


class TestHeuristicInitialization:
    """Test heuristic provider initialization"""
    
    def test_initialization(self, provider):
        """Test provider initializes correctly"""
        assert provider.get_provider_type() == LLMProvider.HEURISTIC
        assert len(provider.templates) > 0
    
    def test_available_templates(self, provider):
        """Test all expected templates are available"""
        expected_templates = ["simple", "todo", "dashboard", "form", "default"]
        for template in expected_templates:
            assert template in provider.templates


class TestTemplateDetection:
    """Test template type detection"""
    
    def test_detect_todo_template(self, provider):
        """Test detection of todo app template"""
        messages = [LLMMessage(role="user", content="Create a todo list app")]
        template = provider._detect_template_type(messages[0].content.lower())
        assert template == "todo"
    
    def test_detect_dashboard_template(self, provider):
        """Test detection of dashboard template"""
        messages = [LLMMessage(role="user", content="Build a dashboard with stats")]
        template = provider._detect_template_type(messages[0].content.lower())
        assert template == "dashboard"
    
    def test_detect_form_template(self, provider):
        """Test detection of form template"""
        messages = [LLMMessage(role="user", content="Create a registration form")]
        template = provider._detect_template_type(messages[0].content.lower())
        assert template == "form"
    
    def test_detect_simple_template(self, provider):
        """Test detection of simple template"""
        messages = [LLMMessage(role="user", content="Make a simple hello world app")]
        template = provider._detect_template_type(messages[0].content.lower())
        assert template == "simple"
    
    def test_detect_default_template(self, provider):
        """Test default template for unrecognized input"""
        messages = [LLMMessage(role="user", content="Some random request")]
        template = provider._detect_template_type(messages[0].content.lower())
        assert template == "default"


class TestGeneration:
    """Test generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_todo_app(self, provider):
        """Test generating todo app"""
        messages = [LLMMessage(role="user", content="Create a todo app")]
        response = await provider.generate(messages)
        
        assert response.provider == LLMProvider.HEURISTIC
        assert response.finish_reason == "heuristic"
        assert response.model == "rule-based"
        
        # Validate JSON structure
        app_spec = json.loads(response.content)
        assert app_spec["type"] == "todo_app"
        assert "screens" in app_spec
        assert "dataModel" in app_spec
    
    @pytest.mark.asyncio
    async def test_generate_dashboard(self, provider):
        """Test generating dashboard"""
        messages = [LLMMessage(role="user", content="Build an analytics dashboard")]
        response = await provider.generate(messages)
        
        app_spec = json.loads(response.content)
        assert app_spec["type"] == "dashboard_app"
        assert len(app_spec["screens"]) > 0
    
    @pytest.mark.asyncio
    async def test_generate_form(self, provider):
        """Test generating form app"""
        messages = [LLMMessage(role="user", content="Create a form")]
        response = await provider.generate(messages)
        
        app_spec = json.loads(response.content)
        assert app_spec["type"] == "form_app"
        assert any(c["type"] == "input" for s in app_spec["screens"] for c in s["components"])
    
    @pytest.mark.asyncio
    async def test_generate_simple_app(self, provider):
        """Test generating simple app"""
        messages = [LLMMessage(role="user", content="Simple app")]
        response = await provider.generate(messages)
        
        app_spec = json.loads(response.content)
        assert app_spec["type"] == "simple_app"
    
    @pytest.mark.asyncio
    async def test_generate_default(self, provider):
        """Test generating default app"""
        messages = [LLMMessage(role="user", content="Something unusual")]
        response = await provider.generate(messages)
        
        app_spec = json.loads(response.content)
        assert app_spec["type"] == "default_app"


class TestResponseFormat:
    """Test response format validation"""
    
    @pytest.mark.asyncio
    async def test_valid_json_output(self, provider):
        """Test all templates produce valid JSON"""
        test_cases = [
            "todo app",
            "dashboard",
            "form",
            "simple app",
            "random request"
        ]
        
        for test_input in test_cases:
            messages = [LLMMessage(role="user", content=test_input)]
            response = await provider.generate(messages)
            
            # Should not raise exception
            app_spec = json.loads(response.content)
            assert isinstance(app_spec, dict)
    
    @pytest.mark.asyncio
    async def test_required_fields(self, provider):
        """Test all templates have required fields"""
        messages = [LLMMessage(role="user", content="any app")]
        response = await provider.generate(messages)
        
        app_spec = json.loads(response.content)
        assert "type" in app_spec
        assert "description" in app_spec
        assert "screens" in app_spec
        assert "theme" in app_spec
    
    @pytest.mark.asyncio
    async def test_screen_structure(self, provider):
        """Test screen structure is valid"""
        messages = [LLMMessage(role="user", content="todo app")]
        response = await provider.generate(messages)
        
        app_spec = json.loads(response.content)
        screens = app_spec["screens"]
        
        assert len(screens) > 0
        for screen in screens:
            assert "name" in screen
            assert "type" in screen
            assert "components" in screen
            assert isinstance(screen["components"], list)
    
    @pytest.mark.asyncio
    async def test_theme_structure(self, provider):
        """Test theme structure is valid"""
        messages = [LLMMessage(role="user", content="simple app")]
        response = await provider.generate(messages)
        
        app_spec = json.loads(response.content)
        theme = app_spec["theme"]
        
        assert "primaryColor" in theme
        assert "backgroundColor" in theme
        assert theme["primaryColor"].startswith("#")
        assert theme["backgroundColor"].startswith("#")


class TestParameterHandling:
    """Test parameter handling"""
    
    @pytest.mark.asyncio
    async def test_ignore_temperature(self, provider):
        """Test temperature parameter is accepted but ignored"""
        messages = [LLMMessage(role="user", content="simple app")]
        response = await provider.generate(messages, temperature=0.9)
        
        # Should work without error
        assert response is not None
        assert response.provider == LLMProvider.HEURISTIC
    
    @pytest.mark.asyncio
    async def test_ignore_max_tokens(self, provider):
        """Test max_tokens parameter is accepted but ignored"""
        messages = [LLMMessage(role="user", content="todo app")]
        response = await provider.generate(messages, max_tokens=1000)
        
        assert response is not None
        assert response.tokens_used is None


class TestHealthCheck:
    """Test health check"""
    
    @pytest.mark.asyncio
    async def test_always_healthy(self, provider):
        """Test heuristic provider is always healthy"""
        is_healthy = await provider.health_check()
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_multiple_calls(self, provider):
        """Test multiple health checks"""
        for _ in range(5):
            is_healthy = await provider.health_check()
            assert is_healthy is True


class TestMetadata:
    """Test metadata tracking"""
    
    @pytest.mark.asyncio
    async def test_metadata_includes_template(self, provider):
        """Test metadata includes template type used"""
        messages = [LLMMessage(role="user", content="todo app")]
        response = await provider.generate(messages)
        
        assert response.metadata is not None
        assert "template_used" in response.metadata
        assert response.metadata["template_used"] == "todo"
    
    @pytest.mark.asyncio
    async def test_different_templates_tracked(self, provider):
        """Test different templates are tracked in metadata"""
        test_cases = {
            "todo app": "todo",
            "dashboard": "dashboard",
            "form": "form",
            "simple": "simple"
        }
        
        for input_text, expected_template in test_cases.items():
            messages = [LLMMessage(role="user", content=input_text)]
            response = await provider.generate(messages)
            assert response.metadata["template_used"] == expected_template


class TestEdgeCases:
    """Test edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_message(self, provider):
        """Test handling of empty message"""
        messages = [LLMMessage(role="user", content="")]
        response = await provider.generate(messages)
        
        # Should use default template
        app_spec = json.loads(response.content)
        assert app_spec["type"] == "default_app"
    
    @pytest.mark.asyncio
    async def test_multiple_keywords(self, provider):
        """Test message with multiple template keywords"""
        messages = [LLMMessage(role="user", content="Create a todo dashboard with forms")]
        response = await provider.generate(messages)
        
        # Should match first detected template (todo)
        app_spec = json.loads(response.content)
        assert app_spec["type"] == "todo_app"
    
    @pytest.mark.asyncio
    async def test_case_insensitive(self, provider):
        """Test case insensitive keyword matching"""
        test_cases = ["TODO App", "ToDo LIST", "todo app"]
        
        for test_input in test_cases:
            messages = [LLMMessage(role="user", content=test_input)]
            response = await provider.generate(messages)
            
            app_spec = json.loads(response.content)
            assert app_spec["type"] == "todo_app"