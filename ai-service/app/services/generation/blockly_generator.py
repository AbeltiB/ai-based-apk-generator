"""
Blockly Generator - Phase 3
Uses LLM Orchestrator (Llama3 → Heuristic fallback)
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import ArchitectureDesign
from app.models.enhanced_schemas import EnhancedLayoutDefinition
from app.models.prompts import prompts
from app.services.generation.blockly_validator import blockly_validator
from app.llm.orchestrator import LLMOrchestrator
from app.llm.base import LLMMessage
from app.utils.logging import get_logger, log_context, trace_async

logger = get_logger(__name__)


class BlocklyGenerationError(Exception):
    """Base exception for Blockly generation errors"""
    pass


class BlocklyGenerator:
    """
    Phase 3 Blockly Generator using LLM Orchestrator.
    
    Generation Flow:
    1. 🎯 Try Llama3 via orchestrator
    2. 🔄 Retry with corrections if needed
    3. 🛡️ Fall back to heuristic if all retries fail
    4. ✅ Validate block structure
    
    Features:
    - Llama3 as primary LLM
    - Automatic heuristic template fallback
    - Block validation
    - Variable extraction
    """
    
    def __init__(self, orchestrator: Optional[LLMOrchestrator] = None):
        # Initialize LLM orchestrator
        if orchestrator:
            self.orchestrator = orchestrator
        else:
            config = {
                "failure_threshold": 3,
                "failure_window_minutes": 5,
                "llama3_api_url": settings.llama3_api_url,
                "llama3_api_key": settings.llama3_api_key
            }
            self.orchestrator = LLMOrchestrator(config)
        
        # Block ID counter
        self.block_id_counter = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'blocks_generated': 0,
            'variables_created': 0,
            'heuristic_fallbacks': 0,
            'llama3_successes': 0
        }
        
        logger.info(
            "blockly.generator.initialized",
            extra={
                "llm_provider": "llama3",
                "heuristic_fallback_enabled": True
            }
        )
    
    @trace_async("blockly.generation")
    async def generate(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate Blockly blocks for the entire app.
        
        Args:
            architecture: Complete architecture design
            layouts: Map of screen_id -> layout definition
            
        Returns:
            Tuple of (blockly_definition, metadata)
            
        Raises:
            BlocklyGenerationError: If generation fails
        """
        self.stats['total_requests'] += 1
        self.block_id_counter = 0
        
        with log_context(operation="blockly_generation"):
            logger.info(
                "🧩 blockly.generation.started",
                extra={"screens": len(layouts)}
            )
            
            # Try LLM first
            blockly_data = None
            metadata = {}
            used_heuristic = False
            
            try:
                blockly_data, metadata = await self._generate_with_llm(
                    architecture=architecture,
                    layouts=layouts
                )
                
                self.stats['llama3_successes'] += 1
                logger.info(
                    "✅ blockly.llm.success",
                    extra={
                        "blocks": len(blockly_data.get('blocks', {}).get('blocks', [])),
                        "provider": metadata.get('provider', 'llama3')
                    }
                )
                
            except Exception as llm_error:
                logger.warning(
                    "⚠️ blockly.llm.failed",
                    extra={"error": str(llm_error)},
                    exc_info=llm_error
                )
                
                # Fall back to heuristic
                logger.info("🛡️ blockly.fallback.initiating")
                
                try:
                    blockly_data = await self._generate_heuristic_blocks(
                        architecture=architecture,
                        layouts=layouts
                    )
                    metadata = {
                        'generation_method': 'heuristic',
                        'fallback_reason': str(llm_error),
                        'provider': 'heuristic',
                        'tokens_used': 0,
                        'api_duration_ms': 0
                    }
                    
                    used_heuristic = True
                    self.stats['heuristic_fallbacks'] += 1
                    
                    logger.info(
                        "✅ blockly.heuristic.success",
                        extra={"blocks": len(blockly_data.get('blocks', {}).get('blocks', []))}
                    )
                    
                except Exception as heuristic_error:
                    logger.error(
                        "❌ blockly.heuristic.failed",
                        extra={"error": str(heuristic_error)},
                        exc_info=heuristic_error
                    )
                    
                    self.stats['failed'] += 1
                    raise BlocklyGenerationError(
                        f"Both LLM and heuristic generation failed. "
                        f"LLM: {llm_error}, Heuristic: {heuristic_error}"
                    )
            
            # Validate block structure
            validated = await self._validate_blocks(blockly_data)
            
            # Add custom block definitions
            validated['custom_blocks'] = self._generate_custom_blocks(architecture)
            
            # Validate with validator
            logger.info("🔍 blockly.validation.starting")
            
            try:
                is_valid, warnings = await blockly_validator.validate(validated)
                
                error_count = sum(1 for w in warnings if w.level == "error")
                warning_count = sum(1 for w in warnings if w.level == "warning")
                
                if not is_valid:
                    logger.warning(
                        "⚠️ blockly.validation.issues",
                        extra={
                            "errors": error_count,
                            "warnings": warning_count
                        }
                    )
                
                logger.info(
                    "✅ blockly.validation.completed",
                    extra={"warnings": warning_count}
                )
                
            except Exception as validation_error:
                logger.warning(
                    "⚠️ blockly.validation.error",
                    extra={"error": str(validation_error)}
                )
            
            # Update metadata
            metadata.update({
                'used_heuristic': used_heuristic,
                'generated_at': datetime.now(timezone.utc).isoformat() + "Z"
            })
            
            self.stats['successful'] += 1
            self.stats['blocks_generated'] = len(validated['blocks']['blocks'])
            self.stats['variables_created'] = len(validated['variables'])
            
            logger.info(
                "🎉 blockly.generation.completed",
                extra={
                    "blocks": self.stats['blocks_generated'],
                    "variables": self.stats['variables_created'],
                    "used_heuristic": used_heuristic
                }
            )
            
            return validated, metadata
    
    async def _generate_with_llm(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Generate Blockly blocks using LLM orchestrator with retries"""
        
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    f"🔄 blockly.llm.attempt",
                    extra={"attempt": attempt}
                )
                
                # Extract component events
                component_events = self._extract_component_events(layouts)
                
                # Format prompt
                system_prompt, user_prompt = prompts.BLOCKLY_GENERATE.format(
                    architecture=json.dumps(architecture.dict(), indent=2),
                    layout=json.dumps(
                        {k: v.dict() for k, v in layouts.items()} if len(layouts) > 1 
                        else list(layouts.values())[0].dict(),
                        indent=2
                    ),
                    component_events=json.dumps(component_events, indent=2)
                )
                
                # Create messages
                messages = [
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt)
                ]
                
                # Call LLM via orchestrator
                start_time = asyncio.get_event_loop().time()
                
                response = await self.orchestrator.generate(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4096
                )
                
                api_duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
                
                logger.debug(
                    "blockly.llm.response_received",
                    extra={
                        "response_length": len(response.content),
                        "api_duration_ms": api_duration,
                        "provider": response.provider.value
                    }
                )
                
                # Parse response
                blockly_data = await self._parse_blockly_json(response.content)
                
                # Build metadata
                metadata = {
                    'generation_method': 'llm',
                    'provider': response.provider.value,
                    'tokens_used': response.tokens_used,
                    'api_duration_ms': api_duration,
                    'screens': list(layouts.keys())
                }
                
                return blockly_data, metadata
                
            except Exception as e:
                last_error = e
                
                logger.warning(
                    f"⚠️ blockly.llm.retry",
                    extra={
                        "attempt": attempt,
                        "error": str(e)[:200],
                        "will_retry": attempt < self.max_retries
                    }
                )
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "❌ blockly.llm.exhausted",
                        extra={
                            "total_attempts": attempt,
                            "final_error": str(last_error)
                        }
                    )
                    raise last_error
        
        raise last_error or BlocklyGenerationError("All retries failed")
    
    def _extract_component_events(
        self,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> Dict[str, List[str]]:
        """Extract events from components in layouts"""
        events = {}
        
        for screen_id, layout in layouts.items():
            for component in layout.components:
                comp_events = []
                comp_type = component.component_type
                
                if comp_type == 'Button':
                    comp_events.append('onPress')
                elif comp_type in ['InputText', 'TextArea']:
                    comp_events.extend(['onChange', 'onSubmit'])
                elif comp_type == 'Switch':
                    comp_events.append('onToggle')
                elif comp_type == 'Checkbox':
                    comp_events.append('onChange')
                elif comp_type == 'Slider':
                    comp_events.append('onChange')
                elif comp_type in ['DatePicker', 'TimePicker']:
                    comp_events.append('onChange')
                elif comp_type == 'ColorPicker':
                    comp_events.append('onChange')
                
                if comp_events:
                    events[component.component_id] = comp_events
        
        return events
    
    async def _parse_blockly_json(self, response_text: str) -> Dict[str, Any]:
        """Parse Blockly JSON from LLM response"""
        
        # Remove markdown code blocks
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 3:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
        
        # Parse JSON
        try:
            data = json.loads(response_text)
            
            # Ensure it's in the right format
            if isinstance(data, list):
                return {
                    'blocks': {
                        'languageVersion': 0,
                        'blocks': data
                    },
                    'variables': []
                }
            elif isinstance(data, dict):
                if 'blocks' in data:
                    return data
                else:
                    return {
                        'blocks': data if 'blocks' in data else {'languageVersion': 0, 'blocks': []},
                        'variables': data.get('variables', [])
                    }
            else:
                raise ValueError("Unexpected Blockly format")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise BlocklyGenerationError(f"Could not parse Blockly JSON: {e}")
    
    async def _generate_heuristic_blocks(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> Dict[str, Any]:
        """Generate basic Blockly blocks using heuristic templates"""
        
        logger.info("🛡️ blockly.heuristic.generating")
        
        blocks = []
        variables = []
        
        # Extract state variables
        for state in architecture.state_management:
            variables.append({
                'name': state.name,
                'id': self._generate_block_id(),
                'type': ''
            })
        
        # Generate basic event blocks for buttons
        for screen_id, layout in layouts.items():
            for component in layout.components:
                if component.component_type == 'Button':
                    # Create button click event
                    block = {
                        'type': 'component_event',
                        'id': self._generate_block_id(),
                        'fields': {
                            'COMPONENT': component.component_id,
                            'EVENT': 'onPress'
                        },
                        'next': None
                    }
                    blocks.append(block)
        
        return {
            'blocks': {
                'languageVersion': 0,
                'blocks': blocks
            },
            'variables': variables
        }
    
    async def _validate_blocks(self, blockly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Blockly block structure"""
        
        logger.debug("Validating Blockly blocks...")
        
        # Ensure required structure
        if 'blocks' not in blockly_data:
            blockly_data['blocks'] = {'languageVersion': 0, 'blocks': []}
        
        if 'variables' not in blockly_data:
            blockly_data['variables'] = []
        
        # Validate each block has required fields
        blocks = blockly_data['blocks'].get('blocks', [])
        
        for idx, block in enumerate(blocks):
            if 'type' not in block:
                logger.warning(f"Block {idx} missing 'type' field")
                block['type'] = 'unknown'
            
            if 'id' not in block:
                block['id'] = self._generate_block_id()
        
        # Extract variables from state management if missing
        if not blockly_data['variables']:
            blockly_data['variables'] = self._extract_variables_from_blocks(blocks)
        
        return blockly_data
    
    def _extract_variables_from_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract variable definitions from blocks"""
        variables = []
        var_names = set()
        
        def extract_from_block(block: Dict[str, Any]):
            fields = block.get('fields', {})
            for field_name, field_value in fields.items():
                if field_name == 'VAR' or field_name == 'VARIABLE':
                    if isinstance(field_value, str) and field_value not in var_names:
                        var_names.add(field_value)
                        variables.append({
                            'name': field_value,
                            'id': self._generate_block_id(),
                            'type': ''
                        })
            
            inputs = block.get('inputs', {})
            for input_data in inputs.values():
                if isinstance(input_data, dict) and 'block' in input_data:
                    extract_from_block(input_data['block'])
            
            if 'next' in block and isinstance(block['next'], dict):
                if 'block' in block['next']:
                    extract_from_block(block['next']['block'])
        
        for block in blocks:
            extract_from_block(block)
        
        return variables
    
    def _generate_custom_blocks(self, architecture: ArchitectureDesign) -> List[Dict[str, Any]]:
        """Generate custom block type definitions"""
        custom_blocks = []
        
        # Component action blocks
        custom_blocks.append({
            'type': 'component_set_property',
            'message0': 'set %1 of %2 to %3',
            'args0': [
                {'type': 'field_dropdown', 'name': 'PROPERTY', 'options': [
                    ['text', 'text'], ['value', 'value'], ['color', 'color']
                ]},
                {'type': 'field_input', 'name': 'COMPONENT', 'text': 'component_id'},
                {'type': 'input_value', 'name': 'VALUE'}
            ],
            'previousStatement': None,
            'nextStatement': None,
            'colour': 230
        })
        
        # State management blocks
        custom_blocks.append({
            'type': 'state_set',
            'message0': 'set %1 to %2',
            'args0': [
                {'type': 'field_variable', 'name': 'VAR', 'variable': 'count'},
                {'type': 'input_value', 'name': 'VALUE'}
            ],
            'previousStatement': None,
            'nextStatement': None,
            'colour': 330
        })
        
        # Navigation blocks
        if len(architecture.screens) > 1:
            screen_options = [[s.name, s.id] for s in architecture.screens]
            custom_blocks.append({
                'type': 'navigate_to_screen',
                'message0': 'navigate to %1',
                'args0': [
                    {'type': 'field_dropdown', 'name': 'SCREEN', 'options': screen_options}
                ],
                'previousStatement': None,
                'nextStatement': None,
                'colour': 160
            })
        
        return custom_blocks
    
    def _generate_block_id(self) -> str:
        """Generate unique block ID"""
        self.block_id_counter += 1
        return f"block_{self.block_id_counter}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics"""
        total = self.stats['total_requests']
        
        return {
            **self.stats,
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'heuristic_fallback_rate': (self.stats['heuristic_fallbacks'] / total * 100) if total > 0 else 0,
            'llama3_success_rate': (self.stats['llama3_successes'] / total * 100) if total > 0 else 0
        }


# Global Blockly generator instance
blockly_generator = BlocklyGenerator()