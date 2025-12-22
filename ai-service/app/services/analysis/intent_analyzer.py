"""
Intent Analyzer - Claude-powered request classification.

Uses Claude API to intelligently classify user requests and extract
key entities for downstream processing.
"""
import json
from typing import Dict, Any, List
from loguru import logger
import anthropic

from app.config import settings
from app.models.enhanced_schemas import IntentAnalysis


class IntentAnalyzer:
    """
    Analyzes user prompts to determine intent and complexity.
    
    Uses Claude API for intelligent classification of:
    - Intent type (new app, extend app, modify app, etc.)
    - Complexity level (simple, medium, complex)
    - Extracted entities (components, actions, data types)
    - Context requirements
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for intent analysis"""
        return """You are an expert at analyzing mobile app development requests.

Your task is to analyze user prompts and classify them into structured intent data.

**Intent Types:**
- new_app: User wants to create a new application from scratch
- extend_app: User wants to add features to existing app
- modify_app: User wants to change/update existing features
- clarification: User is asking for clarification or help
- help: User needs assistance understanding something

**Complexity Levels:**
- simple: Single screen, 1-3 components, basic interactions
- medium: 1-2 screens, 4-8 components, moderate logic
- complex: Multiple screens, 8+ components, complex logic, API integration

**Entity Extraction:**
Extract mentions of:
- Components: UI elements (Button, InputText, etc.)
- Actions: User interactions (click, input, swipe, etc.)
- Data: Data types being managed (todos, users, products, etc.)
- Features: Specific functionality (authentication, search, notifications)

**Output Format:**
Return ONLY a valid JSON object (no markdown, no explanations):
{
  "intent_type": "new_app" | "extend_app" | "modify_app" | "clarification" | "help",
  "complexity": "simple" | "medium" | "complex",
  "confidence": 0.0-1.0,
  "extracted_entities": {
    "components": ["Button", "InputText", ...],
    "actions": ["click", "input", ...],
    "data": ["todo", "user", ...],
    "features": ["authentication", "search", ...]
  },
  "requires_context": true | false,
  "multi_turn": true | false,
  "reasoning": "Brief explanation of classification"
}

**Examples:**

Prompt: "Create a simple counter app"
{
  "intent_type": "new_app",
  "complexity": "simple",
  "confidence": 0.95,
  "extracted_entities": {
    "components": ["Button", "Text"],
    "actions": ["click"],
    "data": ["count"],
    "features": ["increment", "decrement"]
  },
  "requires_context": false,
  "multi_turn": false,
  "reasoning": "Simple single-screen app with basic counter functionality"
}

Prompt: "Add a delete button to each todo item"
{
  "intent_type": "extend_app",
  "complexity": "simple",
  "confidence": 0.90,
  "extracted_entities": {
    "components": ["Button"],
    "actions": ["click", "delete"],
    "data": ["todo"],
    "features": ["delete"]
  },
  "requires_context": true,
  "multi_turn": true,
  "reasoning": "Extending existing todo app with delete functionality"
}

Now analyze the following prompt."""
    
    async def analyze(self, prompt: str, context: Dict[str, Any] = None) -> IntentAnalysis:
        """
        Analyze user prompt to determine intent.
        
        Args:
            prompt: User's natural language request
            context: Optional context (conversation history, existing project)
            
        Returns:
            IntentAnalysis object with classification results
        """
        logger.info("🔍 Analyzing intent...")
        logger.debug(f"Prompt: {prompt[:100]}...")
        
        try:
            # Build user message with context
            user_message = f"Prompt: \"{prompt}\""
            
            if context and context.get('has_existing_project'):
                user_message += "\n\nNote: User has an existing project in this session."
            
            if context and context.get('conversation_history'):
                history_summary = self._summarize_history(context['conversation_history'])
                user_message += f"\n\nRecent conversation: {history_summary}"
            
            # Call Claude API
            response = self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1000,
                temperature=0.2,  # Low temperature for consistent classification
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Extract response text
            response_text = response.content[0].text.strip()
            logger.debug(f"Claude response: {response_text[:200]}...")
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                intent_data = json.loads(response_text)
                
                # Create IntentAnalysis object
                intent = IntentAnalysis(
                    intent_type=intent_data['intent_type'],
                    complexity=intent_data['complexity'],
                    confidence=intent_data['confidence'],
                    extracted_entities=intent_data.get('extracted_entities', {}),
                    requires_context=intent_data.get('requires_context', False),
                    multi_turn=intent_data.get('multi_turn', False)
                )
                
                logger.info(f"✅ Intent analyzed: {intent.intent_type} ({intent.complexity})")
                logger.info(f"   Confidence: {intent.confidence:.2f}")
                logger.info(f"   Entities: {len(intent.extracted_entities)} types")
                if intent_data.get('reasoning'):
                    logger.debug(f"   Reasoning: {intent_data['reasoning']}")
                
                return intent
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse intent JSON: {e}")
                logger.error(f"Response was: {response_text}")
                
                # Fallback to heuristic analysis
                return self._fallback_analysis(prompt)
        
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            
            # Fallback to heuristic analysis
            return self._fallback_analysis(prompt)
    
    def _summarize_history(self, history: List[Dict[str, Any]]) -> str:
        """Summarize conversation history for context"""
        if not history or len(history) == 0:
            return "No previous conversation"
        
        # Get last 3 messages
        recent = history[-3:] if len(history) > 3 else history
        
        summary_parts = []
        for msg in recent:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, str):
                # Truncate long messages
                content = content[:100] + "..." if len(content) > 100 else content
                summary_parts.append(f"{role}: {content}")
        
        return " | ".join(summary_parts)
    
    def _fallback_analysis(self, prompt: str) -> IntentAnalysis:
        """
        Fallback heuristic-based intent analysis.
        
        Used when Claude API fails or returns invalid data.
        """
        logger.warning("Using fallback heuristic intent analysis")
        
        prompt_lower = prompt.lower()
        
        # Determine intent type
        if any(word in prompt_lower for word in ['create', 'build', 'make', 'new', 'generate']):
            intent_type = "new_app"
        elif any(word in prompt_lower for word in ['add', 'extend', 'include', 'also']):
            intent_type = "extend_app"
        elif any(word in prompt_lower for word in ['change', 'modify', 'update', 'fix', 'replace']):
            intent_type = "modify_app"
        elif any(word in prompt_lower for word in ['what', 'how', 'why', 'explain']):
            intent_type = "clarification"
        else:
            intent_type = "new_app"
        
        # Determine complexity
        word_count = len(prompt.split())
        component_mentions = sum(1 for comp in settings.available_components 
                                if comp.lower() in prompt_lower)
        
        if word_count < 10 and component_mentions <= 2:
            complexity = "simple"
        elif word_count < 30 and component_mentions <= 5:
            complexity = "medium"
        else:
            complexity = "complex"
        
        # Extract basic entities
        components = [comp for comp in settings.available_components 
                     if comp.lower() in prompt_lower]
        
        return IntentAnalysis(
            intent_type=intent_type,
            complexity=complexity,
            confidence=0.6,  # Lower confidence for heuristic
            extracted_entities={
                "components": components,
                "actions": [],
                "data": [],
                "features": []
            },
            requires_context=intent_type in ["extend_app", "modify_app"],
            multi_turn=False
        )


# Global intent analyzer instance
intent_analyzer = IntentAnalyzer()


if __name__ == "__main__":
    # Test intent analyzer
    import asyncio
    
    async def test_intent_analyzer():
        """Test intent analysis"""
        print("\n" + "=" * 60)
        print("INTENT ANALYZER TEST")
        print("=" * 60)
        
        test_prompts = [
            "Create a simple counter app with increment and decrement buttons",
            "Add a delete button to each todo item",
            "Make the login button blue instead of red",
            "Build a complete e-commerce app with product listings, cart, and checkout",
            "How do I add a map component?"
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n[{i}/{len(test_prompts)}] Analyzing: \"{prompt}\"")
            
            intent = await intent_analyzer.analyze(prompt)
            
            print(f"   Intent: {intent.intent_type}")
            print(f"   Complexity: {intent.complexity}")
            print(f"   Confidence: {intent.confidence:.2f}")
            print(f"   Requires Context: {intent.requires_context}")
            print(f"   Multi-turn: {intent.multi_turn}")
            
            if intent.extracted_entities:
                for entity_type, entities in intent.extracted_entities.items():
                    if entities:
                        print(f"   {entity_type.capitalize()}: {', '.join(entities)}")
        
        print("\n" + "=" * 60)
        print("✅ Intent analyzer test complete!")
        print("=" * 60 + "\n")
    
    asyncio.run(test_intent_analyzer())