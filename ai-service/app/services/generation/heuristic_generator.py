"""
Heuristic Architecture Generator.

Used as a fallback when LLM-based generation fails.
Generates a valid, minimal architecture deterministically.
"""

from typing import Dict, Any
from loguru import logger
from uuid import uuid4

from app.models.schemas import ArchitectureDesign


class HeuristicArchitectureGenerator:
    """
    Deterministic fallback architecture generator.
    """

    async def generate(self, prompt: str) -> ArchitectureDesign:
        logger.warning("⚠️ Using HEURISTIC architecture fallback")

        prompt_lower = prompt.lower()

        # Very simple intent detection
        if "todo" in prompt_lower or "task" in prompt_lower:
            return self._todo_app()
        elif "counter" in prompt_lower:
            return self._counter_app()
        elif "calculator" in prompt_lower:
            return self._calculator_app()
        else:
            return self._generic_app(prompt)

    # -----------------------
    # App templates
    # -----------------------

    def _counter_app(self) -> ArchitectureDesign:
        return ArchitectureDesign(
            app_type="counter_app",
            screens=[
                {
                    "id": "main",
                    "name": "CounterScreen",
                    "purpose": "Display and update counter value",
                    "components": ["Text", "Button", "Button"],
                    "navigation": []
                }
            ],
            navigation={
                "type": "single_screen",
                "routes": []
            },
            state_management=[
                {
                    "name": "counter",
                    "type": "number",
                    "scope": "screen"
                }
            ]
        )

    def _todo_app(self) -> ArchitectureDesign:
        return ArchitectureDesign(
            app_type="todo_app",
            screens=[
                {
                    "id": "list",
                    "name": "TodoListScreen",
                    "purpose": "View and manage tasks",
                    "components": ["List", "TextInput", "Button", "Checkbox"],
                    "navigation": []
                }
            ],
            navigation={
                "type": "single_screen",
                "routes": []
            },
            state_management=[
                {
                    "name": "todos",
                    "type": "list",
                    "scope": "screen"
                }
            ]
        )

    def _calculator_app(self) -> ArchitectureDesign:
        return ArchitectureDesign(
            app_type="calculator_app",
            screens=[
                {
                    "id": "calculator",
                    "name": "CalculatorScreen",
                    "purpose": "Perform arithmetic operations",
                    "components": ["Text", "Button"],
                    "navigation": []
                }
            ],
            navigation={
                "type": "single_screen",
                "routes": []
            },
            state_management=[
                {
                    "name": "displayValue",
                    "type": "string",
                    "scope": "screen"
                }
            ]
        )

    def _generic_app(self, prompt: str) -> ArchitectureDesign:
        return ArchitectureDesign(
            app_type="generic_app",
            screens=[
                {
                    "id": "home",
                    "name": "HomeScreen",
                    "purpose": f"Main screen for: {prompt[:50]}",
                    "components": ["Text"],
                    "navigation": []
                }
            ],
            navigation={
                "type": "single_screen",
                "routes": []
            },
            state_management=[]
        )


# Global instance
heuristic_architecture_generator = HeuristicArchitectureGenerator()
