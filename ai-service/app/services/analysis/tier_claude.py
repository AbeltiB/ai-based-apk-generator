"""
Claude (Anthropic) tier implementation.

Tier 1 - Primary classification using Claude Sonnet 4.
"""
import json
from typing import Dict, Any, Optional
from loguru import logger
import anthropic

from app.services.analysis.intent_config import config, ClassificationTier
from app.services.analysis.intent_schemas import (
    IntentAnalysisResult, IntentType, ComplexityLevel,
    ExtractedEntities, ConfidenceBreakdown, SafetyStatus,
    ActionRecommendation, ClassificationRequest
)
from app.services.analysis.tier_base import ClassificationTierBase


class ClaudeTier(ClassificationTierBase):
    """
    Claude Sonnet 4 classification tier.
    
    Primary tier with highest accuracy and best understanding.
    """
    
    def __init__(self, api_key: str):
        super().__init__(
            tier=ClassificationTier.CLAUDE,
            retry_config=config.TIERS["claude"].retry_config
        )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.system_prompt = self._build_system_prompt()
    
    def get_name(self) -> str:
        return "Claude Sonnet 4"
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt for Claude"""
        return """You are an expert intent classification system for mobile app generation.

Analyze user requests and classify them with high accuracy.

**Intent Types:**
- new_app: Creating a completely new app
- extend_app: Adding features to existing app
- modify_app: Changing existing app features
- clarification: Needs more information
- help: General help request
- unsafe: Malicious/harmful request

**Complexity Levels:**
- simple: Single feature, 1-3 components, no state
- medium: Multiple features, 4-8 components, some state
- complex: Advanced features, 8+ components, complex state

**Output Format (ONLY JSON, no markdown):**
{
  "intent_type": "new_app",
  "complexity": "medium",
  "confidence": {
    "overall": 0.85,
    "intent_confidence": 0.9,
    "complexity_confidence": 0.8,
    "entity_confidence": 0.85,
    "safety_confidence": 0.95
  },
  "extracted_entities": {
    "components": ["Button", "InputText", "Text"],
    "actions": ["click", "submit", "display"],
    "data_types": ["todo", "task"],
    "features": ["add", "delete", "list"],
    "screens": ["main", "settings"],
    "integrations": []
  },
  "safety_status": "safe",
  "requires_context": false,
  "multi_turn": false,
  "reasoning": "User wants to create a new todo app with CRUD operations"
}

**Guidelines:**
- Be confident but not overconfident
- Mark unsafe any requests for hacking, malware, exploitation
- Extract all relevant entities
- Consider mobile constraints
- Reasoning should be concise (1-2 sentences)"""
    
    async def _classify_internal(
        self,
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Classify using Claude API"""
        
        # Build user message
        user_message = self._build_user_message(request)
        
        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            temperature=0.1,
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Extract response
        response_text = response.content[0].text.strip()
        
        # Parse JSON
        result_data = self._parse_response(response_text)
        
        # Build result
        result = self._build_result(result_data, request)
        
        # Add token usage and cost
        result.tokens_used = response.usage.input_tokens + response.usage.output_tokens
        result.cost_usd = self._calculate_cost(result.tokens_used)
        
        return result
    
    def _build_user_message(self, request: ClassificationRequest) -> str:
        """Build user message with context"""
        message = f"Classify this user request:\n\n\"{request.prompt}\""
        
        # Add context if available
        if request.context:
            if request.context.get('has_existing_project'):
                message += "\n\nNote: User has an existing project"
            
            if request.context.get('conversation_history'):
                history = request.context['conversation_history'][-2:]  # Last 2 messages
                message += "\n\nRecent conversation:"
                for msg in history:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:100]
                    message += f"\n  {role}: {content}"
        
        return message
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's response"""
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 3:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            raise ValueError(f"Invalid JSON from Claude: {e}")
    
    def _build_result(
        self,
        data: Dict[str, Any],
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Build IntentAnalysisResult from parsed data"""
        from datetime import datetime, timezone
        
        # Parse confidence
        confidence_data = data.get("confidence", {})
        confidence = ConfidenceBreakdown(
            overall=confidence_data.get("overall", 0.7),
            intent_confidence=confidence_data.get("intent_confidence", 0.7),
            complexity_confidence=confidence_data.get("complexity_confidence", 0.7),
            entity_confidence=confidence_data.get("entity_confidence", 0.7),
            safety_confidence=confidence_data.get("safety_confidence", 0.9)
        )
        
        # Parse entities
        entities_data = data.get("extracted_entities", {})
        entities = ExtractedEntities(
            components=entities_data.get("components", []),
            actions=entities_data.get("actions", []),
            data_types=entities_data.get("data_types", []),
            features=entities_data.get("features", []),
            screens=entities_data.get("screens", []),
            integrations=entities_data.get("integrations", [])
        )
        
        # Validate and parse intent type
        try:
            intent_type = IntentType(data["intent_type"])
        except (KeyError, ValueError):
            logger.warning(f"Invalid intent type: {data.get('intent_type')}")
            intent_type = IntentType.CLARIFICATION
            confidence.intent_confidence = 0.3
            confidence.overall = min(confidence.overall, 0.5)
        
        # Validate and parse complexity
        try:
            complexity = ComplexityLevel(data["complexity"])
        except (KeyError, ValueError):
            logger.warning(f"Invalid complexity: {data.get('complexity')}")
            complexity = ComplexityLevel.MEDIUM
            confidence.complexity_confidence = 0.3
        
        # Validate safety
        try:
            safety = SafetyStatus(data.get("safety_status", "safe"))
        except ValueError:
            safety = SafetyStatus.SAFE
        
        # Determine action
        action = self._determine_action(intent_type, safety, confidence)
        
        # Generate user message
        user_message = self._generate_user_message(action, intent_type, confidence)
        
        return IntentAnalysisResult(
            intent_type=intent_type,
            complexity=complexity,
            confidence=confidence,
            extracted_entities=entities,
            action_recommendation=action,
            safety_status=safety,
            requires_context=data.get("requires_context", False),
            multi_turn=data.get("multi_turn", False),
            user_message=user_message,
            reasoning=data.get("reasoning", "Classified by Claude"),
            tier_used=self.tier,
            tier_attempts=[],
            total_latency_ms=0,
            total_cost_usd=0.0,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _determine_action(
        self,
        intent_type: IntentType,
        safety: SafetyStatus,
        confidence: ConfidenceBreakdown
    ) -> ActionRecommendation:
        """Determine recommended action"""
        # Block unsafe
        if safety == SafetyStatus.UNSAFE:
            return ActionRecommendation.REJECT
        
        # Block dangerous operations with low confidence
        if intent_type == IntentType.MODIFY_APP:
            if confidence.overall < config.CONFIDENCE.block_dangerous:
                return ActionRecommendation.BLOCK_MODIFY
        
        if intent_type == IntentType.EXTEND_APP:
            if confidence.overall < config.CONFIDENCE.block_dangerous:
                return ActionRecommendation.BLOCK_EXTEND
        
        # Request clarification for low confidence
        if confidence.overall < config.CONFIDENCE.clarification:
            return ActionRecommendation.CLARIFY
        
        # Proceed
        return ActionRecommendation.PROCEED
    
    def _generate_user_message(
        self,
        action: ActionRecommendation,
        intent_type: IntentType,
        confidence: ConfidenceBreakdown
    ) -> Optional[str]:
        """Generate user-facing message"""
        if action == ActionRecommendation.PROCEED:
            return None
        
        if action == ActionRecommendation.REJECT:
            return config.USER_MESSAGES["unsafe_request"]
        
        if action == ActionRecommendation.BLOCK_MODIFY:
            return config.USER_MESSAGES["modify_blocked"]
        
        if action == ActionRecommendation.BLOCK_EXTEND:
            return config.USER_MESSAGES["extend_blocked"]
        
        if action == ActionRecommendation.CLARIFY:
            intent_guess = intent_type.value.replace("_", " ")
            return config.USER_MESSAGES["low_confidence_clarification"].format(
                intent_guess=intent_guess
            )
        
        return None
    
    def _calculate_cost(self, tokens: int) -> float:
        """Calculate API cost"""
        cost_per_1k = config.TIERS["claude"].cost_per_1k_tokens
        return (tokens / 1000) * cost_per_1k