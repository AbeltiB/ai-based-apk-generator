"""
Groq (Llama 3.1 8B) tier implementation.

Tier 2 - Fallback classification using Groq's fast inference.
"""
import json
import httpx
from typing import Dict, Any, Optional
from loguru import logger

from app.services.analysis.intent_config import config, ClassificationTier
from app.services.analysis.intent_schemas import (
    IntentAnalysisResult, IntentType, ComplexityLevel,
    ExtractedEntities, ConfidenceBreakdown, SafetyStatus,
    ActionRecommendation, ClassificationRequest
)
from app.services.analysis.tier_base import ClassificationTierBase


class GroqTier(ClassificationTierBase):
    """
    Groq Llama 3.1 8B classification tier.
    
    Fast, free alternative to Claude for classification.
    """
    
    def __init__(self, api_key: str):
        super().__init__(
            tier=ClassificationTier.GROQ,
            retry_config=config.TIERS["groq"].retry_config
        )
        self.api_key = api_key
        self.model = "llama-3.1-8b-instant"
        self.base_url = "https://api.groq.com/openai/v1"
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt optimized for Llama"""
        return """You are an intent classification expert for mobile apps.

Analyze user requests and output ONLY valid JSON (no markdown, no text).

Intent types: new_app, extend_app, modify_app, clarification, help, unsafe
Complexity: simple, medium, complex
Safety: safe, suspicious, unsafe

Output format:
{
  "intent_type": "new_app",
  "complexity": "simple",
  "confidence": {
    "overall": 0.85,
    "intent_confidence": 0.9,
    "complexity_confidence": 0.8,
    "entity_confidence": 0.85,
    "safety_confidence": 0.95
  },
  "extracted_entities": {
    "components": ["Button", "Text"],
    "actions": ["click"],
    "data_types": ["counter"],
    "features": ["increment"],
    "screens": [],
    "integrations": []
  },
  "safety_status": "safe",
  "requires_context": false,
  "multi_turn": false,
  "reasoning": "Simple counter app request"
}

Rules:
- Be conservative with confidence scores
- Mark unsafe if harmful (hacking, malware, exploits)
- Extract all relevant components and features
- Output ONLY JSON, nothing else"""
    
    async def _classify_internal(
        self,
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Classify using Groq API"""
        
        # Build messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Classify: \"{request.prompt}\""}
        ]
        
        # Add context if available
        if request.context and request.context.get('has_existing_project'):
            messages.append({
                "role": "system",
                "content": "Note: User has existing project"
            })
        
        # Call Groq API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"}
                },
                timeout=config.TIERS["groq"].timeout
            )
            
            response.raise_for_status()
            data = response.json()
        
        # Extract response
        response_text = data["choices"][0]["message"]["content"]
        
        # Parse JSON
        result_data = self._parse_response(response_text)
        
        # Build result
        result = self._build_result(result_data, request)
        
        # Add token usage
        usage = data.get("usage", {})
        result.tokens_used = usage.get("total_tokens", 0)
        
        return result
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Groq's JSON response"""
        try:
            # Groq should return pure JSON with response_format setting
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq response: {e}")
            logger.error(f"Response was: {response_text}")
            raise ValueError(f"Invalid JSON from Groq: {e}")
    
    def _build_result(
        self,
        data: Dict[str, Any],
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Build IntentAnalysisResult from parsed data"""
        
        # Parse confidence (with defaults if missing)
        confidence_data = data.get("confidence", {})
        confidence = ConfidenceBreakdown(
            overall=confidence_data.get("overall", 0.6),
            intent_confidence=confidence_data.get("intent_confidence", 0.6),
            complexity_confidence=confidence_data.get("complexity_confidence", 0.6),
            entity_confidence=confidence_data.get("entity_confidence", 0.5),
            safety_confidence=confidence_data.get("safety_confidence", 0.7)
        )
        
        # Parse entities (with defaults)
        entities_data = data.get("extracted_entities", {})
        entities = ExtractedEntities(
            components=entities_data.get("components", []),
            actions=entities_data.get("actions", []),
            data_types=entities_data.get("data_types", []),
            features=entities_data.get("features", []),
            screens=entities_data.get("screens", []),
            integrations=entities_data.get("integrations", [])
        )
        
        # Validate intent type
        try:
            intent_type = IntentType(data["intent_type"])
        except (KeyError, ValueError):
            logger.warning(f"Invalid intent type: {data.get('intent_type')}")
            intent_type = IntentType.CLARIFICATION
            confidence.intent_confidence = 0.3
            confidence.overall = 0.4
        
        # Validate complexity
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
        
        # Generate message
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
            reasoning=data.get("reasoning", "Classified by Groq"),
            tier_used=self.tier,
            tier_attempts=[],
            total_latency_ms=0,
            total_cost_usd=0.0
        )
    
    def _determine_action(
        self,
        intent_type: IntentType,
        safety: SafetyStatus,
        confidence: ConfidenceBreakdown
    ) -> ActionRecommendation:
        """Determine action (same logic as Claude tier)"""
        if safety == SafetyStatus.UNSAFE:
            return ActionRecommendation.REJECT
        
        if intent_type == IntentType.MODIFY_APP:
            if confidence.overall < config.CONFIDENCE.block_dangerous:
                return ActionRecommendation.BLOCK_MODIFY
        
        if intent_type == IntentType.EXTEND_APP:
            if confidence.overall < config.CONFIDENCE.block_dangerous:
                return ActionRecommendation.BLOCK_EXTEND
        
        if confidence.overall < config.CONFIDENCE.clarification:
            return ActionRecommendation.CLARIFY
        
        return ActionRecommendation.PROCEED
    
    def _generate_user_message(
        self,
        action: ActionRecommendation,
        intent_type: IntentType,
        confidence: ConfidenceBreakdown
    ) -> Optional[str]:
        """Generate user message (same logic as Claude)"""
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
    
    def get_name(self) -> str:
            return "groq"
