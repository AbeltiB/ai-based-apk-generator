"""
Architecture Generator - FIXED with Async Client

This replaces the synchronous Anthropic client with the async wrapper.
"""
import json
import asyncio
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.schemas import ArchitectureDesign
from app.models.enhanced_schemas import EnrichedContext
from app.models.prompts import prompts
from app.services.generation.architecture_validator import architecture_validator
from app.core.async_anthropic_client import get_async_client


class ArchitectureGenerationError(Exception):
    """Base exception for architecture generation errors"""
    pass


class InvalidArchitectureError(ArchitectureGenerationError):
    """Raised when generated architecture is invalid"""
    pass


class ArchitectureGenerator:
    """
    FIXED: Now uses async Anthropic client for true non-blocking operation.
    
    Changes:
    1. Replaced sync client with AsyncAnthropicClient
    2. All Claude API calls are now truly async
    3. Added proper error handling for circuit breaker
    4. Delegated ALL validation to ArchitectureValidator
    """
    
    def __init__(self):
        # Use async client wrapper
        self.client = get_async_client()
        self.model = settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        self.temperature = settings.anthropic_temperature
        
        # Statistics tracking
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'retries': 0,
            'corrections': 0
        }
    
    async def generate(
        self,
        prompt: str,
        context: Optional[EnrichedContext] = None
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """
        Generate architecture from user prompt.
        
        FIXED: Now fully async, no blocking calls.
        
        Args:
            prompt: User's natural language request
            context: Optional enriched context
            
        Returns:
            Tuple of (ArchitectureDesign, metadata)
            
        Raises:
            ArchitectureGenerationError: If generation fails after retries
        """
        self.stats['total_requests'] += 1
        
        logger.info("architecture.generation.started")
        logger.debug(f"Prompt: {prompt[:100]}...")
        
        try:
            # Determine generation mode
            intent_type = context.intent_analysis.intent_type if context else "new_app"
            
            if intent_type == "new_app":
                architecture, metadata = await self._generate_new_architecture(
                    prompt, context
                )
            elif intent_type == "extend_app":
                architecture, metadata = await self._extend_architecture(
                    prompt, context
                )
            elif intent_type == "modify_app":
                architecture, metadata = await self._modify_architecture(
                    prompt, context
                )
            else:
                # Default to new app
                architecture, metadata = await self._generate_new_architecture(
                    prompt, context
                )
            
            # FIXED: Delegate ALL validation to ArchitectureValidator
            is_valid, warnings = await architecture_validator.validate(architecture)
            
            if not is_valid:
                error_count = sum(1 for w in warnings if w.level == "error")
                raise InvalidArchitectureError(
                    f"Generated architecture has {error_count} validation error(s)"
                )
            
            self.stats['successful'] += 1
            
            logger.info(
                "architecture.generation.success",
                extra={
                    "app_type": architecture.app_type,
                    "screens": len(architecture.screens),
                    "state_vars": len(architecture.state_management),
                    "warnings": len(warnings)
                }
            )
            
            return architecture, metadata
            
        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Architecture generation failed: {e}")
            raise ArchitectureGenerationError(f"Failed to generate architecture: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _generate_new_architecture(
        self,
        prompt: str,
        context: Optional[EnrichedContext]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate new app architecture.
        
        FIXED: Now uses async client.
        """
        logger.info("architecture.new.generating")
        
        # Build context section
        context_section = ""
        if context:
            from app.services.analysis.context_builder import context_builder
            context_section = context_builder.format_context_for_prompt(context)
        else:
            context_section = "No previous context."
        
        # Format prompt
        system_prompt, user_prompt = prompts.ARCHITECTURE_DESIGN.format(
            components=", ".join(settings.available_components),
            prompt=prompt,
            context_section=context_section
        )
        
        # FIXED: Use async client
        start_time = asyncio.get_event_loop().time()
        
        response = await self.client.create_message(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            temperature=self.temperature
        )
        
        api_duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Extract response
        response_text = response.content[0].text.strip()
        logger.debug(f"Claude response length: {len(response_text)} chars")
        
        # Parse JSON
        architecture_data = await self._parse_architecture_json(response_text)
        
        # Build metadata
        metadata = {
            'model': self.model,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'api_duration_ms': api_duration,
            'generation_mode': 'new_app',
            'retries': 0
        }
        
        return architecture_data, metadata
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _extend_architecture(
        self,
        prompt: str,
        context: EnrichedContext
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extend existing architecture.
        
        FIXED: Now uses async client.
        """
        logger.info("architecture.extend.generating")
        
        if not context.existing_project:
            logger.warning("No existing project found, generating new instead")
            return await self._generate_new_architecture(prompt, context)
        
        # Get existing architecture
        existing_arch = context.existing_project.get('architecture', {})
        
        # Format prompt
        system_prompt, user_prompt = prompts.ARCHITECTURE_EXTEND.format(
            existing_architecture=json.dumps(existing_arch, indent=2),
            prompt=prompt
        )
        
        # FIXED: Use async client
        start_time = asyncio.get_event_loop().time()
        
        response = await self.client.create_message(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            temperature=self.temperature
        )
        
        api_duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Extract and parse response
        response_text = response.content[0].text.strip()
        architecture_data = await self._parse_architecture_json(response_text)
        
        # Build metadata
        metadata = {
            'model': self.model,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'api_duration_ms': api_duration,
            'generation_mode': 'extend_app',
            'retries': 0,
            'base_architecture_id': context.existing_project.get('project_id')
        }
        
        return architecture_data, metadata
    
    async def _modify_architecture(
        self,
        prompt: str,
        context: EnrichedContext
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Modify existing architecture.
        
        For now, treat similar to extend.
        """
        logger.info("architecture.modify.generating")
        return await self._extend_architecture(prompt, context)
    
    async def _parse_architecture_json(self, response_text: str) -> Dict[str, Any]:
        """
        Parse architecture JSON from Claude response.
        
        Handles:
        - Markdown code blocks
        - Extra whitespace
        - Malformed JSON (with correction attempts)
        """
        # Remove markdown code blocks
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 3:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
        
        # Try parsing
        try:
            architecture_data = json.loads(response_text)
            return architecture_data
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            
            # Try auto-correction
            corrected = await self._attempt_json_correction(response_text)
            
            if corrected:
                self.stats['corrections'] += 1
                logger.info("JSON auto-corrected successfully")
                return corrected
            
            raise InvalidArchitectureError(f"Could not parse architecture JSON: {e}")
    
    async def _attempt_json_correction(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to auto-correct malformed JSON.
        """
        logger.debug("Attempting JSON auto-correction...")
        
        # Remove comments
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            if '//' in line:
                line = line[:line.index('//')]
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Remove trailing commas
        import re
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        # Try parsing again
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.debug("Auto-correction failed")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics"""
        total = self.stats['total_requests']
        
        return {
            'total_requests': total,
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'retries': self.stats['retries'],
            'corrections': self.stats['corrections']
        }


# Global architecture generator instance
architecture_generator = ArchitectureGenerator()