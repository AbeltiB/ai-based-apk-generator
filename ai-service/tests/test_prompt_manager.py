"""
tests/phase2/test_prompt_manager.py
Tests for prompt template management and versioning
"""
import pytest

from app.llm import (
    PromptManager,
    PromptType,
    PromptVersion,
    LLMMessage
)


@pytest.fixture
def manager():
    """Create prompt manager instance"""
    return PromptManager()


@pytest.fixture
def manager_v1():
    """Create prompt manager with V1 default"""
    return PromptManager(default_version=PromptVersion.V1)


class TestInitialization:
    """Test prompt manager initialization"""
    
    def test_default_initialization(self, manager):
        """Test default initialization uses V2"""
        assert manager.default_version == PromptVersion.V2
    
    def test_custom_version(self, manager_v1):
        """Test initialization with custom version"""
        assert manager_v1.default_version == PromptVersion.V1
    
    def test_templates_loaded(self, manager):
        """Test all templates are loaded"""
        assert len(manager.templates) == 2  # V1 and V2
        assert PromptVersion.V1 in manager.templates
        assert PromptVersion.V2 in manager.templates


class TestGetPrompt:
    """Test getting prompt templates"""
    
    def test_get_app_generation_v2(self, manager):
        """Test getting V2 app generation prompt"""
        prompt = manager.get_prompt(PromptType.APP_GENERATION)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "mobile app" in prompt.lower()
    
    def test_get_app_generation_v1(self, manager):
        """Test getting V1 app generation prompt"""
        prompt = manager.get_prompt(
            PromptType.APP_GENERATION,
            version=PromptVersion.V1
        )
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
    
    def test_get_code_generation(self, manager):
        """Test getting code generation prompt"""
        prompt = manager.get_prompt(PromptType.CODE_GENERATION)
        assert "production-ready" in prompt.lower()
    
    def test_get_description(self, manager):
        """Test getting description prompt"""
        prompt = manager.get_prompt(PromptType.DESCRIPTION)
        assert "description" in prompt.lower() or "analyze" in prompt.lower()
    
    def test_version_fallback(self, manager):
        """Test fallback to default version for invalid version"""
        prompt = manager.get_prompt(
            PromptType.APP_GENERATION,
            version="invalid_version"  # type: ignore
        )
        
        # Should fall back to default version
        assert isinstance(prompt, str)
    
    def test_invalid_prompt_type(self, manager):
        """Test error on invalid prompt type"""
        with pytest.raises(ValueError, match="Prompt type .* not found"):
            manager.get_prompt("invalid_type")  # type: ignore


class TestVariableSubstitution:
    """Test variable substitution in templates"""
    
    def test_code_generation_with_variables(self, manager):
        """Test variable substitution in code generation"""
        variables = {
            "language": "Python",
            "framework": "FastAPI"
        }
        
        prompt = manager.get_prompt(
            PromptType.CODE_GENERATION,
            variables=variables
        )
        
        assert "Python" in prompt
        assert "FastAPI" in prompt
    
    def test_missing_variable_error(self, manager):
        """Test error when required variable is missing"""
        # CODE_GENERATION template requires 'language' and 'framework'
        variables = {"language": "Python"}  # Missing 'framework'
        
        with pytest.raises(ValueError, match="Missing required variable"):
            manager.get_prompt(
                PromptType.CODE_GENERATION,
                variables=variables
            )
    
    def test_no_variables_when_not_needed(self, manager):
        """Test templates that don't need variables"""
        prompt = manager.get_prompt(PromptType.APP_GENERATION)
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestBuildMessages:
    """Test building message lists"""
    
    def test_build_basic_messages(self, manager):
        """Test building basic message list"""
        messages = manager.build_messages(
            PromptType.APP_GENERATION,
            "Create a todo app"
        )
        
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[1].content == "Create a todo app"
    
    def test_build_messages_with_variables(self, manager):
        """Test building messages with variable substitution"""
        variables = {
            "language": "TypeScript",
            "framework": "Next.js"
        }
        
        messages = manager.build_messages(
            PromptType.CODE_GENERATION,
            "Create an API endpoint",
            variables=variables
        )
        
        assert len(messages) == 2
        assert "TypeScript" in messages[0].content
        assert "Next.js" in messages[0].content
    
    def test_build_messages_with_version(self, manager):
        """Test building messages with specific version"""
        messages_v1 = manager.build_messages(
            PromptType.APP_GENERATION,
            "Create an app",
            version=PromptVersion.V1
        )
        
        messages_v2 = manager.build_messages(
            PromptType.APP_GENERATION,
            "Create an app",
            version=PromptVersion.V2
        )
        
        # System prompts should be different between versions
        assert messages_v1[0].content != messages_v2[0].content
    
    def test_system_override(self, manager):
        """Test overriding system prompt"""
        custom_system = "You are a specialized app builder."
        
        messages = manager.build_messages(
            PromptType.APP_GENERATION,
            "Create an app",
            system_override=custom_system
        )
        
        assert messages[0].content == custom_system
        assert messages[1].content == "Create an app"


class TestVersionComparison:
    """Test differences between versions"""
    
    def test_v1_vs_v2_app_generation(self, manager):
        """Test V1 and V2 app generation prompts differ"""
        prompt_v1 = manager.get_prompt(
            PromptType.APP_GENERATION,
            version=PromptVersion.V1
        )
        prompt_v2 = manager.get_prompt(
            PromptType.APP_GENERATION,
            version=PromptVersion.V2
        )
        
        assert prompt_v1 != prompt_v2
        # V2 should be more detailed
        assert len(prompt_v2) > len(prompt_v1)
    
    def test_v1_vs_v2_code_generation(self, manager):
        """Test V1 and V2 code generation prompts differ"""
        variables = {"language": "Python", "framework": "FastAPI"}
        
        prompt_v1 = manager.get_prompt(
            PromptType.CODE_GENERATION,
            variables=variables,
            version=PromptVersion.V1
        )
        prompt_v2 = manager.get_prompt(
            PromptType.CODE_GENERATION,
            variables=variables,
            version=PromptVersion.V2
        )
        
        assert prompt_v1 != prompt_v2


class TestAvailableVersionsAndTypes:
    """Test listing available versions and types"""
    
    def test_get_available_versions(self, manager):
        """Test getting list of available versions"""
        versions = manager.get_available_versions()
        
        assert isinstance(versions, list)
        assert "v1" in versions
        assert "v2" in versions
    
    def test_get_available_types(self, manager):
        """Test getting list of available prompt types"""
        types = manager.get_available_types()
        
        assert isinstance(types, list)
        assert "app_generation" in types
        assert "code_generation" in types
        assert "description" in types


class TestPromptContent:
    """Test prompt content quality"""
    
    def test_v2_prompts_comprehensive(self, manager):
        """Test V2 prompts are comprehensive"""
        prompts_to_check = [
            PromptType.APP_GENERATION,
            PromptType.CODE_GENERATION,
            PromptType.DESCRIPTION
        ]
        
        for prompt_type in prompts_to_check:
            if prompt_type == PromptType.CODE_GENERATION:
                variables = {"language": "Python", "framework": "FastAPI"}
                prompt = manager.get_prompt(prompt_type, variables=variables, version=PromptVersion.V2)
            else:
                prompt = manager.get_prompt(prompt_type, version=PromptVersion.V2)
            
            # V2 prompts should be detailed
            assert len(prompt) > 200
            # Should have clear structure
            assert "\n" in prompt
    
    def test_app_generation_includes_requirements(self, manager):
        """Test app generation prompt includes key requirements"""
        prompt = manager.get_prompt(PromptType.APP_GENERATION, version=PromptVersion.V2)
        
        key_terms = ["json", "screen", "component", "theme"]
        for term in key_terms:
            assert term.lower() in prompt.lower()
    
    def test_code_generation_includes_best_practices(self, manager):
        """Test code generation prompt mentions best practices"""
        variables = {"language": "Python", "framework": "FastAPI"}
        prompt = manager.get_prompt(
            PromptType.CODE_GENERATION,
            variables=variables,
            version=PromptVersion.V2
        )
        
        key_terms = ["production", "error handling", "best practices"]
        for term in key_terms:
            assert term.lower() in prompt.lower()


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_variables_dict(self, manager):
        """Test with empty variables dictionary"""
        prompt = manager.get_prompt(
            PromptType.APP_GENERATION,
            variables={}
        )
        assert isinstance(prompt, str)
    
    def test_extra_variables_ignored(self, manager):
        """Test extra variables are ignored"""
        variables = {
            "language": "Python",
            "framework": "FastAPI",
            "extra_var": "ignored"
        }
        
        prompt = manager.get_prompt(
            PromptType.CODE_GENERATION,
            variables=variables
        )
        
        assert "Python" in prompt
        assert "FastAPI" in prompt
        # Extra variable shouldn't cause error
    
    def test_none_variables(self, manager):
        """Test None variables parameter"""
        prompt = manager.get_prompt(
            PromptType.APP_GENERATION,
            variables=None
        )
        assert isinstance(prompt, str)


class TestMessageTypes:
    """Test message type validation"""
    
    def test_messages_are_llm_message_objects(self, manager):
        """Test messages are LLMMessage objects"""
        messages = manager.build_messages(
            PromptType.APP_GENERATION,
            "Create app"
        )
        
        for msg in messages:
            assert isinstance(msg, LLMMessage)
            assert hasattr(msg, 'role')
            assert hasattr(msg, 'content')
    
    def test_system_message_first(self, manager):
        """Test system message is always first"""
        messages = manager.build_messages(
            PromptType.APP_GENERATION,
            "User input"
        )
        
        assert messages[0].role == "system"
    
    def test_user_message_last(self, manager):
        """Test user message is always last"""
        messages = manager.build_messages(
            PromptType.APP_GENERATION,
            "User input"
        )
        
        assert messages[-1].role == "user"
        assert messages[-1].content == "User input"