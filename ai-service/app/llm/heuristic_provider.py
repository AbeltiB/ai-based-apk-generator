"""
app/llm/heuristic_provider.py
Rule-based heuristic fallback provider
"""
import logging
import json
from typing import List, Optional, Dict, Any

from .base import BaseLLMProvider, LLMResponse, LLMMessage, LLMProvider


logger = logging.getLogger(__name__)


class HeuristicProvider(BaseLLMProvider):
    """Rule-based heuristic fallback provider"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = LLMProvider.HEURISTIC
        
        # Define heuristic templates for app generation
        self.templates = {
            "simple": self._simple_app_template,
            "todo": self._todo_app_template,
            "dashboard": self._dashboard_template,
            "form": self._form_template,
            "default": self._default_template
        }
    
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using rule-based heuristics"""
        
        # Extract user request from messages
        user_message = next(
            (msg.content for msg in messages if msg.role == "user"),
            ""
        ).lower()
        
        logger.info(f"Heuristic fallback triggered for: {user_message[:100]}")
        
        # Determine template based on keywords
        template_type = self._detect_template_type(user_message)
        template_func = self.templates.get(template_type, self.templates["default"])
        
        # Generate response using template
        content = template_func(user_message)
        
        return LLMResponse(
            content=content,
            provider=self.provider_name,
            tokens_used=None,
            finish_reason="heuristic",
            model="rule-based",
            metadata={"template_used": template_type}
        )
    
    def _detect_template_type(self, message: str) -> str:
        """Detect which template to use based on keywords"""
        
        if any(word in message for word in ["todo", "task", "checklist"]):
            return "todo"
        elif any(word in message for word in ["dashboard", "stats", "analytics"]):
            return "dashboard"
        elif any(word in message for word in ["form", "input", "submit", "registration"]):
            return "form"
        elif any(word in message for word in ["simple", "basic", "hello"]):
            return "simple"
        else:
            return "default"
    
    def _simple_app_template(self, message: str) -> str:
        """Generate simple app template"""
        return json.dumps({
            "type": "simple_app",
            "description": "A simple mobile application",
            "screens": [
                {
                    "name": "Home",
                    "type": "screen",
                    "components": [
                        {"type": "text", "content": "Welcome to the App", "style": "title"},
                        {"type": "button", "label": "Get Started", "action": "navigate"}
                    ]
                }
            ],
            "theme": {
                "primaryColor": "#007AFF",
                "backgroundColor": "#FFFFFF"
            }
        }, indent=2)
    
    def _todo_app_template(self, message: str) -> str:
        """Generate todo app template"""
        return json.dumps({
            "type": "todo_app",
            "description": "A task management application",
            "screens": [
                {
                    "name": "TodoList",
                    "type": "screen",
                    "components": [
                        {"type": "text", "content": "My Tasks", "style": "header"},
                        {"type": "list", "dataSource": "todos", "itemType": "todo"},
                        {"type": "input", "placeholder": "Add new task"},
                        {"type": "button", "label": "Add Task", "action": "addTodo"}
                    ]
                }
            ],
            "dataModel": {
                "todos": [
                    {"id": 1, "text": "Sample task", "completed": False}
                ]
            },
            "theme": {
                "primaryColor": "#4CAF50",
                "backgroundColor": "#F5F5F5"
            }
        }, indent=2)
    
    def _dashboard_template(self, message: str) -> str:
        """Generate dashboard template"""
        return json.dumps({
            "type": "dashboard_app",
            "description": "An analytics dashboard application",
            "screens": [
                {
                    "name": "Dashboard",
                    "type": "screen",
                    "components": [
                        {"type": "text", "content": "Dashboard", "style": "header"},
                        {"type": "card", "title": "Total Users", "value": "1,234"},
                        {"type": "card", "title": "Revenue", "value": "$12,345"},
                        {"type": "chart", "chartType": "line", "dataSource": "metrics"}
                    ]
                }
            ],
            "theme": {
                "primaryColor": "#2196F3",
                "backgroundColor": "#FAFAFA"
            }
        }, indent=2)
    
    def _form_template(self, message: str) -> str:
        """Generate form template"""
        return json.dumps({
            "type": "form_app",
            "description": "A form-based application",
            "screens": [
                {
                    "name": "FormScreen",
                    "type": "screen",
                    "components": [
                        {"type": "text", "content": "Registration Form", "style": "header"},
                        {"type": "input", "label": "Name", "placeholder": "Enter your name"},
                        {"type": "input", "label": "Email", "placeholder": "Enter your email", "inputType": "email"},
                        {"type": "button", "label": "Submit", "action": "submitForm"}
                    ]
                }
            ],
            "theme": {
                "primaryColor": "#9C27B0",
                "backgroundColor": "#FFFFFF"
            }
        }, indent=2)
    
    def _default_template(self, message: str) -> str:
        """Generate default template"""
        return json.dumps({
            "type": "default_app",
            "description": "A basic mobile application",
            "screens": [
                {
                    "name": "Main",
                    "type": "screen",
                    "components": [
                        {"type": "text", "content": "App Content", "style": "title"},
                        {"type": "text", "content": "This is a generated app based on your request", "style": "body"},
                        {"type": "button", "label": "Action", "action": "default"}
                    ]
                }
            ],
            "theme": {
                "primaryColor": "#FF5722",
                "backgroundColor": "#FFFFFF"
            }
        }, indent=2)
    
    async def health_check(self) -> bool:
        """Heuristic provider is always available"""
        return True
    
    def get_provider_type(self) -> LLMProvider:
        """Return provider type"""
        return self.provider_name