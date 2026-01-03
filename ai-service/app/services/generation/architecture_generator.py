"""
Architecture Generator - Claude-powered app architecture design.

Generates complete, validated mobile app architectures from user prompts.
Phase 3 implementation with robust error handling and validation.
"""
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.config import settings
from app.models.schemas import ArchitectureDesign
from app.models.enhanced_schemas import EnrichedContext
from app.models.prompts import prompts


class ArchitectureGenerationError(Exception):
    """Base exception for architecture generation errors"""
    pass


class InvalidArchitectureError(ArchitectureGenerationError):
    """Raised when generated architecture is invalid"""
    pass


class ArchitectureGenerator:
    """
    Generates mobile app architectures using Claude API.
    
    Features:
    - Intelligent prompt engineering
    - Retry logic with exponential backoff
    - Schema validation
    - Auto-correction for common issues
    - Context-aware generation (new/extend/modify)
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
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
        
        Args:
            prompt: User's natural language request
            context: Optional enriched context
            
        Returns:
            Tuple of (ArchitectureDesign, metadata)
            
        Raises:
            ArchitectureGenerationError: If generation fails after retries
        """
        self.stats['total_requests'] += 1
        
        logger.info("🏗️  Generating architecture...")
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
            
            # Validate generated architecture
            validated = await self._validate_architecture(architecture)
            
            self.stats['successful'] += 1
            
            logger.info("✅ Architecture generated successfully")
            logger.info(f"   App type: {validated.app_type}")
            logger.info(f"   Screens: {len(validated.screens)}")
            logger.info(f"   State variables: {len(validated.state_management)}")
            
            return validated, metadata
            
        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Architecture generation failed: {e}")
            logger.warning("🔁 Falling back to heuristic architecture generator")

            from app.services.generation.heuristic_generator import (
                heuristic_architecture_generator
            )

            fallback_arch = await heuristic_architecture_generator.generate(prompt)

            metadata = {
                "generation_mode": "heuristic_fallback",
                "reason": str(e)
            }

            return fallback_arch, metadata

    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIError, json.JSONDecodeError)),
        reraise=True
    )
    async def _generate_new_architecture(
        self,
        prompt: str,
        context: Optional[EnrichedContext]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate new app architecture.
        
        Args:
            prompt: User prompt
            context: Enriched context
            
        Returns:
            Tuple of (architecture_dict, metadata)
        """
        logger.info("Generating NEW architecture...")
        
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
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
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
        retry=retry_if_exception_type((anthropic.APIError, json.JSONDecodeError)),
        reraise=True
    )
    async def _extend_architecture(
        self,
        prompt: str,
        context: EnrichedContext
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extend existing architecture.
        
        Args:
            prompt: User prompt
            context: Enriched context with existing project
            
        Returns:
            Tuple of (architecture_dict, metadata)
        """
        logger.info("EXTENDING existing architecture...")
        
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
        
        # Call Claude API
        start_time = asyncio.get_event_loop().time()
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
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
        
        For Phase 3, we treat modify similar to extend.
        Will enhance in later phases.
        """
        logger.info("MODIFYING architecture (using extend logic)...")
        return await self._extend_architecture(prompt, context)
    
    async def _parse_architecture_json(self, response_text: str) -> Dict[str, Any]:
        """
        Parse architecture JSON from Claude response.
        
        Handles:
        - Markdown code blocks
        - Extra whitespace
        - Malformed JSON (with correction attempts)
        
        Args:
            response_text: Raw response from Claude
            
        Returns:
            Parsed architecture dictionary
            
        Raises:
            InvalidArchitectureError: If JSON cannot be parsed
        """
        # Remove markdown code blocks
        if response_text.startswith("```"):
            # Split by ``` and take the content between first and second
            parts = response_text.split("```")
            if len(parts) >= 3:
                response_text = parts[1]
                # Remove language identifier if present
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
        
        # Try parsing
        try:
            architecture_data = json.loads(response_text)
            return architecture_data
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            logger.warning(f"Response was: {response_text[:500]}...")
            
            # Try auto-correction
            corrected = await self._attempt_json_correction(response_text)
            
            if corrected:
                self.stats['corrections'] += 1
                logger.info("✅ JSON auto-corrected successfully")
                return corrected
            
            raise InvalidArchitectureError(f"Could not parse architecture JSON: {e}")
    
    async def _attempt_json_correction(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to auto-correct malformed JSON.
        
        Common issues:
        - Missing closing braces
        - Trailing commas
        - Unescaped quotes
        - Comments
        
        Args:
            text: Malformed JSON text
            
        Returns:
            Corrected dict or None
        """
        logger.debug("Attempting JSON auto-correction...")
        
        # Remove comments
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove line comments
            if '//' in line:
                line = line[:line.index('//')]
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Remove trailing commas before closing braces/brackets
        import re
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        # Try parsing again
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.debug("Auto-correction failed")
            return None
    
    async def _validate_architecture(
        self,
        architecture_data: Dict[str, Any]
    ) -> ArchitectureDesign:
        """
        Validate architecture against schema.
        
        Args:
            architecture_data: Raw architecture dictionary
            
        Returns:
            Validated ArchitectureDesign object
            
        Raises:
            InvalidArchitectureError: If validation fails
        """
        logger.debug("Validating architecture schema...")
        
        try:
            # Pydantic validation
            architecture = ArchitectureDesign(**architecture_data)
            
            # Additional custom validations
            await self._validate_components(architecture)
            await self._validate_navigation(architecture)
            await self._validate_state_management(architecture)
            
            logger.debug("✅ Architecture validation passed")
            return architecture
            
        except Exception as e:
            logger.error(f"Architecture validation failed: {e}")
            raise InvalidArchitectureError(f"Invalid architecture: {e}")
    
    async def _validate_components(self, architecture: ArchitectureDesign) -> None:
        """
        Validate that all components are supported.
        
        Args:
            architecture: Architecture to validate
            
        Raises:
            InvalidArchitectureError: If unsupported components found
        """
        available = set(settings.available_components)
        
        for screen in architecture.screens:
            for component in screen.components:
                if component not in available:
                    raise InvalidArchitectureError(
                        f"Unsupported component '{component}' in screen '{screen.name}'. "
                        f"Available: {', '.join(sorted(available))}"
                    )
    
    async def _validate_navigation(self, architecture: ArchitectureDesign) -> None:
        """
        Validate navigation structure.
        
        Args:
            architecture: Architecture to validate
            
        Raises:
            InvalidArchitectureError: If navigation is invalid
        """
        screen_ids = {screen.id for screen in architecture.screens}
        
        # Check navigation routes reference valid screens
        for route in architecture.navigation.routes:
            from_screen = route.get('from')
            to_screen = route.get('to')
            
            if from_screen and from_screen not in screen_ids:
                raise InvalidArchitectureError(
                    f"Navigation route references non-existent screen: {from_screen}"
                )
            
            if to_screen and to_screen not in screen_ids:
                raise InvalidArchitectureError(
                    f"Navigation route references non-existent screen: {to_screen}"
                )
        
        # Check screen navigation references
        for screen in architecture.screens:
            for nav_target in screen.navigation:
                if nav_target not in screen_ids:
                    raise InvalidArchitectureError(
                        f"Screen '{screen.name}' navigates to non-existent screen: {nav_target}"
                    )
    
    async def _validate_state_management(self, architecture: ArchitectureDesign) -> None:
        """
        Validate state management definitions.
        
        Args:
            architecture: Architecture to validate
            
        Raises:
            InvalidArchitectureError: If state definitions are invalid
        """
        # Check for duplicate state variable names
        state_names = [state.name for state in architecture.state_management]
        
        if len(state_names) != len(set(state_names)):
            duplicates = [name for name in state_names if state_names.count(name) > 1]
            raise InvalidArchitectureError(
                f"Duplicate state variable names: {set(duplicates)}"
            )
        
        # Validate state scopes
        for state in architecture.state_management:
            if state.scope == "component" and state.type == "global-state":
                raise InvalidArchitectureError(
                    f"State '{state.name}' cannot be component-scoped and global-state"
                )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get generation statistics.
        
        Returns:
            Statistics dictionary
        """
        total = self.stats['total_requests']
        
        return {
            'total_requests': total,
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'retries': self.stats['retries'],
            'corrections': self.stats['corrections']
        }
    
    async def test_generation(self, prompt: str) -> None:
        """
        Test architecture generation with a prompt.
        
        Args:
            prompt: Test prompt
        """
        print(f"\n🧪 Testing architecture generation...")
        print(f"Prompt: {prompt}")
        print("-" * 60)
        
        try:
            architecture, metadata = await self.generate(prompt)
            
            print("\n✅ Generation successful!")
            print(f"\nArchitecture:")
            print(f"  Type: {architecture.app_type}")
            print(f"  Screens: {len(architecture.screens)}")
            for screen in architecture.screens:
                print(f"    - {screen.name}: {screen.purpose}")
                print(f"      Components: {', '.join(screen.components)}")
            
            print(f"\n  Navigation: {architecture.navigation.type}")
            print(f"  Routes: {len(architecture.navigation.routes)}")
            
            print(f"\n  State Management:")
            for state in architecture.state_management:
                print(f"    - {state.name}: {state.type} ({state.scope})")
            
            print(f"\nMetadata:")
            print(f"  Model: {metadata['model']}")
            print(f"  Tokens: {metadata['tokens_used']}")
            print(f"  Duration: {metadata['api_duration_ms']}ms")
            
        except Exception as e:
            print(f"\n❌ Generation failed: {e}")
            raise


# Global architecture generator instance
architecture_generator = ArchitectureGenerator()


if __name__ == "__main__":
    # Test architecture generator
    import asyncio
    
    async def test():
        print("\n" + "=" * 60)
        print("ARCHITECTURE GENERATOR TEST")
        print("=" * 60)
        
        test_prompts = [
            "Create a simple counter app with increment and decrement buttons",
            "Build a todo list app with add, delete, and mark complete features",
            "Make a calculator with basic operations"
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n[TEST {i}/{len(test_prompts)}]")
            try:
                await architecture_generator.test_generation(prompt)
            except Exception as e:
                print(f"Test failed: {e}")
            
            if i < len(test_prompts):
                print("\n" + "-" * 60)
        
        # Print statistics
        stats = architecture_generator.get_statistics()
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)
        print(f"Total requests: {stats['total_requests']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print(f"Auto-corrections: {stats['corrections']}")
        print("=" * 60 + "\n")
    
    asyncio.run(test())