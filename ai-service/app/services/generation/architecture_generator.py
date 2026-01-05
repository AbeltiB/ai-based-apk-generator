"""
Enhanced Architecture Generator with Heuristic Fallback

Improvements:
1. ✅ Async Anthropic client wrapper for non-blocking operations
2. ✅ Heuristic fallback integration with automatic triggering
3. ✅ Enhanced error handling with detailed logging
4. ✅ Schema validation alignment between Claude and heuristic
5. ✅ Performance tracking and metrics
"""
import json
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.config import settings
from app.models.schemas import ArchitectureDesign
from app.models.enhanced_schemas import EnrichedContext
from app.models.prompts import prompts
from app.services.generation.architecture_validator import architecture_validator
from app.services.generation.heuristic_generator import heuristic_architecture_generator
from app.core.async_anthropic_client import get_async_client
from app.utils.logging import get_logger, log_context, trace_async

logger = get_logger(__name__)


class ArchitectureGenerationError(Exception):
    """Base exception for architecture generation errors"""
    pass


class InvalidArchitectureError(ArchitectureGenerationError):
    """Raised when generated architecture is invalid"""
    pass


class ArchitectureGenerator:
    """
    Enhanced Architecture Generator with multi-tier fallback.
    
    Generation Flow:
    1. 🎯 Try Claude API (primary)
    2. 🔄 Retry with corrections if needed
    3. 🛡️ Fall back to heuristic if all retries fail
    4. ✅ Validate final result
    
    Features:
    - Non-blocking async operations
    - Automatic heuristic fallback
    - Comprehensive error handling
    - Performance monitoring
    - Detailed structured logging
    """
    
    def __init__(self):
        self.client = get_async_client()
        self.model = settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        self.temperature = settings.anthropic_temperature
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'retries': 0,
            'corrections': 0,
            'heuristic_fallbacks': 0,
            'claude_successes': 0
        }
        
        logger.info(
            "architecture.generator.initialized",
            extra={
                "model": self.model,
                "max_retries": self.max_retries,
                "heuristic_fallback_enabled": True
            }
        )
    
    @trace_async("architecture.generation")
    async def generate(
        self,
        prompt: str,
        context: Optional[EnrichedContext] = None
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """
        Generate architecture with automatic fallback.
        
        Flow:
        1. Try Claude API with retries
        2. On failure, fall back to heuristic
        3. Validate result
        4. Return architecture + metadata
        
        Args:
            prompt: User's natural language request
            context: Optional enriched context
            
        Returns:
            Tuple of (ArchitectureDesign, metadata)
            
        Raises:
            ArchitectureGenerationError: Only if both Claude and heuristic fail
        """
        self.stats['total_requests'] += 1
        
        with log_context(operation="architecture_generation"):
            logger.info(
                "🏗️ architecture.generation.started",
                extra={
                    "prompt_length": len(prompt),
                    "has_context": context is not None,
                    "intent_type": context.intent_analysis.intent_type if context else "unknown"
                }
            )
            
            # Determine generation mode
            intent_type = context.intent_analysis.intent_type if context else "new_app"
            generation_mode = self._determine_generation_mode(intent_type)
            
            logger.debug(
                "architecture.mode.determined",
                extra={
                    "mode": generation_mode,
                    "intent_type": intent_type
                }
            )
            
            # Try Claude first
            architecture = None
            metadata = {}
            used_heuristic = False
            
            try:
                architecture, metadata = await self._generate_with_claude(
                    prompt=prompt,
                    context=context,
                    mode=generation_mode
                )
                
                self.stats['claude_successes'] += 1
                logger.info(
                    "✅ architecture.claude.success",
                    extra={
                        "app_type": architecture.app_type,
                        "screens": len(architecture.screens)
                    }
                )
                
            except Exception as claude_error:
                logger.warning(
                    "⚠️ architecture.claude.failed",
                    extra={"error": str(claude_error)},
                    exc_info=claude_error
                )
                
                # Fall back to heuristic
                logger.info("🛡️ architecture.fallback.initiating")
                
                try:
                    architecture = await self._generate_with_heuristic(prompt)
                    metadata = {
                        'generation_method': 'heuristic',
                        'fallback_reason': str(claude_error),
                        'model': 'heuristic',
                        'tokens_used': 0,
                        'api_duration_ms': 0
                    }
                    
                    used_heuristic = True
                    self.stats['heuristic_fallbacks'] += 1
                    
                    logger.info(
                        "✅ architecture.heuristic.success",
                        extra={
                            "app_type": architecture.app_type,
                            "fallback_reason": str(claude_error)[:100]
                        }
                    )
                    
                except Exception as heuristic_error:
                    logger.error(
                        "❌ architecture.heuristic.failed",
                        extra={"error": str(heuristic_error)},
                        exc_info=heuristic_error
                    )
                    
                    self.stats['failed'] += 1
                    raise ArchitectureGenerationError(
                        f"Both Claude and heuristic generation failed. "
                        f"Claude: {claude_error}, Heuristic: {heuristic_error}"
                    )
            
            # Validate architecture
            logger.info("🔍 architecture.validation.starting")
            
            try:
                is_valid, warnings = await architecture_validator.validate(architecture)
                
                error_count = sum(1 for w in warnings if w.level == "error")
                warning_count = sum(1 for w in warnings if w.level == "warning")
                
                if not is_valid:
                    logger.error(
                        "❌ architecture.validation.failed",
                        extra={
                            "errors": error_count,
                            "warnings": warning_count,
                            "used_heuristic": used_heuristic
                        }
                    )
                    raise InvalidArchitectureError(
                        f"Generated architecture has {error_count} validation error(s)"
                    )
                
                logger.info(
                    "✅ architecture.validation.passed",
                    extra={
                        "warnings": warning_count,
                        "used_heuristic": used_heuristic
                    }
                )
                
                if warning_count > 0:
                    logger.debug(
                        "⚠️ architecture.validation.warnings",
                        extra={
                            "count": warning_count,
                            "warnings": [
                                {"level": w.level, "component": w.component, "message": w.message}
                                for w in warnings[:5]  # First 5 warnings
                            ]
                        }
                    )
                
            except InvalidArchitectureError:
                raise
            except Exception as validation_error:
                logger.error(
                    "❌ architecture.validation.error",
                    extra={"error": str(validation_error)},
                    exc_info=validation_error
                )
                raise ArchitectureGenerationError(
                    f"Validation failed: {validation_error}"
                )
            
            # Update metadata
            metadata.update({
                'used_heuristic': used_heuristic,
                'validation_warnings': len(warnings),
                'generated_at': datetime.utcnow().isoformat() + "Z"
            })
            
            self.stats['successful'] += 1
            
            logger.info(
                "🎉 architecture.generation.completed",
                extra={
                    "app_type": architecture.app_type,
                    "screens": len(architecture.screens),
                    "state_vars": len(architecture.state_management),
                    "used_heuristic": used_heuristic,
                    "warnings": len(warnings)
                }
            )
            
            return architecture, metadata
    
    def _determine_generation_mode(self, intent_type: str) -> str:
        """Determine which generation mode to use"""
        
        mode_map = {
            "new_app": "new",
            "extend_app": "extend",
            "modify_app": "modify"
        }
        
        return mode_map.get(intent_type, "new")
    
    async def _generate_with_claude(
        self,
        prompt: str,
        context: Optional[EnrichedContext],
        mode: str
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """
        Generate architecture using Claude API with retries.
        
        Implements exponential backoff and automatic error correction.
        """
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    f"🔄 architecture.claude.attempt",
                    extra={
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "mode": mode
                    }
                )
                
                if mode == "new":
                    return await self._generate_new_architecture(prompt, context)
                elif mode == "extend":
                    return await self._extend_architecture(prompt, context)
                elif mode == "modify":
                    return await self._modify_architecture(prompt, context)
                else:
                    return await self._generate_new_architecture(prompt, context)
                    
            except Exception as e:
                last_error = e
                self.stats['retries'] += 1
                
                logger.warning(
                    f"⚠️ architecture.claude.retry",
                    extra={
                        "attempt": attempt,
                        "error": str(e)[:200],
                        "will_retry": attempt < self.max_retries
                    }
                )
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "❌ architecture.claude.exhausted",
                        extra={
                            "total_attempts": attempt,
                            "final_error": str(last_error)
                        }
                    )
                    raise last_error
        
        raise last_error or ArchitectureGenerationError("All retries failed")
    
    async def _generate_new_architecture(
        self,
        prompt: str,
        context: Optional[EnrichedContext]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Generate new app architecture using Claude"""
        
        logger.debug("🆕 architecture.new.generating")
        
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
        
        # Call Claude API
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
        
        logger.debug(
            "architecture.claude.response_received",
            extra={
                "response_length": len(response_text),
                "api_duration_ms": api_duration
            }
        )
        
        # Parse JSON
        architecture_data = await self._parse_architecture_json(response_text)
        
        # Build metadata
        metadata = {
            'generation_method': 'claude',
            'model': self.model,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'api_duration_ms': api_duration,
            'generation_mode': 'new_app',
            'retries': 0
        }
        
        return architecture_data, metadata
    
    async def _extend_architecture(
        self,
        prompt: str,
        context: EnrichedContext
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Extend existing architecture"""
        
        logger.debug("➕ architecture.extend.generating")
        
        if not context.existing_project:
            logger.warning(
                "architecture.extend.no_project",
                message="No existing project found, generating new instead"
            )
            return await self._generate_new_architecture(prompt, context)
        
        # Get existing architecture
        existing_arch = context.existing_project.get('architecture', {})
        
        logger.debug(
            "architecture.extend.base",
            extra={
                "base_type": existing_arch.get('app_type'),
                "base_screens": len(existing_arch.get('screens', []))
            }
        )
        
        # Format prompt
        system_prompt, user_prompt = prompts.ARCHITECTURE_EXTEND.format(
            existing_architecture=json.dumps(existing_arch, indent=2),
            prompt=prompt
        )
        
        # Call Claude API
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
            'generation_method': 'claude',
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
        """Modify existing architecture"""
        
        logger.debug("🔧 architecture.modify.generating")
        
        # For now, treat similar to extend
        return await self._extend_architecture(prompt, context)
    
    async def _generate_with_heuristic(
        self,
        prompt: str
    ) -> ArchitectureDesign:
        """
        Generate architecture using heuristic fallback.
        
        This is a deterministic rule-based generator that always succeeds
        and produces valid (though basic) architectures.
        """
        
        logger.info(
            "🛡️ architecture.heuristic.generating",
            extra={"prompt_length": len(prompt)}
        )
        
        architecture = await heuristic_architecture_generator.generate(prompt)
        
        logger.info(
            "architecture.heuristic.generated",
            extra={
                "app_type": architecture.app_type,
                "screens": len(architecture.screens)
            }
        )
        
        return architecture
    
    async def _parse_architecture_json(self, response_text: str) -> Dict[str, Any]:
        """
        Parse architecture JSON from Claude response with auto-correction.
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
            logger.warning(
                "⚠️ architecture.json.parse_error",
                extra={
                    "error": str(e),
                    "attempting_correction": True
                }
            )
            
            # Try auto-correction
            corrected = await self._attempt_json_correction(response_text)
            
            if corrected:
                self.stats['corrections'] += 1
                logger.info("✅ architecture.json.corrected")
                return corrected
            
            logger.error(
                "❌ architecture.json.correction_failed",
                extra={"original_error": str(e)}
            )
            raise InvalidArchitectureError(f"Could not parse architecture JSON: {e}")
    
    async def _attempt_json_correction(self, text: str) -> Optional[Dict[str, Any]]:
        """Attempt to auto-correct malformed JSON"""
        
        logger.debug("🔧 architecture.json.correcting")
        
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
            logger.debug("architecture.json.correction_failed")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics"""
        total = self.stats['total_requests']
        
        return {
            **self.stats,
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'heuristic_fallback_rate': (self.stats['heuristic_fallbacks'] / total * 100) if total > 0 else 0,
            'claude_success_rate': (self.stats['claude_successes'] / total * 100) if total > 0 else 0
        }


# Global architecture generator instance
architecture_generator = ArchitectureGenerator()