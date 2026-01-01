"""
Blockly Generator - Visual programming block generation.

Generates Blockly blocks for app logic from architecture and layout.
Phase 5 implementation with event handlers, state management, and logic flows.
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
import anthropic

from app.config import settings
from app.models.schemas import ArchitectureDesign
from app.models.enhanced_schemas import EnhancedLayoutDefinition
from app.models.prompts import prompts


class BlocklyGenerationError(Exception):
    """Base exception for Blockly generation errors"""
    pass


class BlocklyGenerator:
    """
    Generates Blockly visual programming blocks using Claude API.
    
    Features:
    - Event block generation (onClick, onChange, etc.)
    - Action block creation (setState, navigation)
    - Logic blocks (if/else, loops)
    - Math operations (arithmetic, comparisons)
    - Variable management
    - Block connection validation
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        
        # Block ID counter
        self.block_id_counter = 0
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'blocks_generated': 0,
            'variables_created': 0
        }
    
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
        
        logger.info("🧩 Generating Blockly blocks...")
        
        try:
            # Generate blocks with Claude
            blockly_data, metadata = await self._generate_with_claude(
                architecture=architecture,
                layouts=layouts
            )
            
            # Validate block structure
            validated = await self._validate_blocks(blockly_data)
            
            # Add custom block definitions
            validated['custom_blocks'] = self._generate_custom_blocks(architecture)
            
            self.stats['successful'] += 1
            self.stats['blocks_generated'] = len(validated['blocks']['blocks'])
            self.stats['variables_created'] = len(validated['variables'])
            
            logger.info(f"✅ Blockly generated: {self.stats['blocks_generated']} blocks")
            
            return validated, metadata
            
        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Blockly generation failed: {e}")
            raise BlocklyGenerationError(f"Failed to generate Blockly: {e}")
    
    async def _generate_with_claude(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate Blockly blocks using Claude API.
        
        Args:
            architecture: Architecture design
            layouts: Layout definitions
            
        Returns:
            Tuple of (blockly_dict, metadata)
        """
        logger.debug("Calling Claude API for Blockly generation...")
        
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
        
        # Call Claude API
        start_time = asyncio.get_event_loop().time()
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=settings.anthropic_max_tokens,
            temperature=settings.anthropic_temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        api_duration = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Parse response
        response_text = response.content[0].text.strip()
        blockly_data = await self._parse_blockly_json(response_text)
        
        # Build metadata
        metadata = {
            'model': self.model,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'api_duration_ms': api_duration,
            'screens': list(layouts.keys())
        }
        
        return blockly_data, metadata
    
    def _extract_component_events(
        self,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> Dict[str, List[str]]:
        """
        Extract events from components in layouts.
        
        Args:
            layouts: Layout definitions
            
        Returns:
            Map of component_id -> list of event types
        """
        events = {}
        
        for screen_id, layout in layouts.items():
            for component in layout.components:
                comp_events = []
                
                # Check component type for default events
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
        """
        Parse Blockly JSON from Claude response.
        
        Args:
            response_text: Raw response from Claude
            
        Returns:
            Parsed Blockly dictionary
        """
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
            
            # Ensure it's a list of block definitions
            if isinstance(data, list):
                # Convert to expected format
                return {
                    'blocks': {
                        'languageVersion': 0,
                        'blocks': data
                    },
                    'variables': []
                }
            elif isinstance(data, dict):
                # Check if it's already in the right format
                if 'blocks' in data:
                    return data
                else:
                    # Assume it's a workspace
                    return {
                        'blocks': data if 'blocks' in data else {'languageVersion': 0, 'blocks': []},
                        'variables': data.get('variables', [])
                    }
            else:
                raise ValueError("Unexpected Blockly format")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise BlocklyGenerationError(f"Could not parse Blockly JSON: {e}")
    
    async def _validate_blocks(self, blockly_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Blockly block structure.
        
        Args:
            blockly_data: Raw Blockly data
            
        Returns:
            Validated Blockly data
        """
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
            """Recursively extract variables"""
            # Check fields for variable references
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
            
            # Check nested blocks
            inputs = block.get('inputs', {})
            for input_data in inputs.values():
                if isinstance(input_data, dict) and 'block' in input_data:
                    extract_from_block(input_data['block'])
            
            # Check next block
            if 'next' in block and isinstance(block['next'], dict):
                if 'block' in block['next']:
                    extract_from_block(block['next']['block'])
        
        for block in blocks:
            extract_from_block(block)
        
        return variables
    
    def _generate_custom_blocks(self, architecture: ArchitectureDesign) -> List[Dict[str, Any]]:
        """
        Generate custom block type definitions.
        
        Args:
            architecture: Architecture design
            
        Returns:
            List of custom block definitions
        """
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
            'total_requests': total,
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'blocks_generated': self.stats['blocks_generated'],
            'variables_created': self.stats['variables_created']
        }


# Global Blockly generator instance
blockly_generator = BlocklyGenerator()


if __name__ == "__main__":
    # Test Blockly generator
    import asyncio
    from app.models.schemas import (
        ArchitectureDesign,
        ScreenDefinition,
        NavigationStructure,
        StateDefinition,
        DataFlowDiagram
    )
    from app.models.enhanced_schemas import (
        EnhancedLayoutDefinition,
        EnhancedComponentDefinition,
        PropertyValue
    )
    
    async def test():
        print("\n" + "=" * 60)
        print("BLOCKLY GENERATOR TEST")
        print("=" * 60)
        
        # Create test architecture
        architecture = ArchitectureDesign(
            app_type="single-page",
            screens=[
                ScreenDefinition(
                    id="screen_1",
                    name="Counter",
                    purpose="Simple counter with increment and decrement",
                    components=["Text", "Button", "Button"],
                    navigation=[]
                )
            ],
            navigation=NavigationStructure(type="stack", routes=[]),
            state_management=[
                StateDefinition(
                    name="count",
                    type="local-state",
                    scope="screen",
                    initial_value=0
                )
            ],
            data_flow=DataFlowDiagram(
                user_interactions=["increment", "decrement"],
                api_calls=[],
                local_storage=[]
            )
        )
        
        # Create test layout
        layout = EnhancedLayoutDefinition(
            screen_id="screen_1",
            components=[
                EnhancedComponentDefinition(
                    component_id="text_count",
                    component_type="Text",
                    properties={
                        "value": PropertyValue(type="variable", value="count"),
                        "style": PropertyValue(type="literal", value={
                            "left": 97, "top": 100, "width": 180, "height": 40
                        })
                    }
                ),
                EnhancedComponentDefinition(
                    component_id="btn_increment",
                    component_type="Button",
                    properties={
                        "value": PropertyValue(type="literal", value="+"),
                        "style": PropertyValue(type="literal", value={
                            "left": 50, "top": 160, "width": 120, "height": 44
                        })
                    }
                ),
                EnhancedComponentDefinition(
                    component_id="btn_decrement",
                    component_type="Button",
                    properties={
                        "value": PropertyValue(type="literal", value="-"),
                        "style": PropertyValue(type="literal", value={
                            "left": 200, "top": 160, "width": 120, "height": 44
                        })
                    }
                )
            ]
        )
        
        try:
            # Generate Blockly
            blockly, metadata = await blockly_generator.generate(
                architecture=architecture,
                layouts={"screen_1": layout}
            )
            
            print("\n✅ Blockly generated successfully!")
            print(f"\nBlockly:")
            print(f"  Blocks: {len(blockly['blocks']['blocks'])}")
            print(f"  Variables: {len(blockly['variables'])}")
            
            # Show blocks
            for idx, block in enumerate(blockly['blocks']['blocks'][:5], 1):
                print(f"    {idx}. {block['type']} (id: {block['id']})")
            
            # Show variables
            for var in blockly['variables']:
                print(f"  Variable: {var['name']}")
            
            # Show custom blocks
            print(f"  Custom blocks: {len(blockly.get('custom_blocks', []))}")
            
            print(f"\nMetadata:")
            print(f"  Model: {metadata['model']}")
            print(f"  Tokens: {metadata['tokens_used']}")
            print(f"  Duration: {metadata['api_duration_ms']}ms")
            
            # Statistics
            stats = blockly_generator.get_statistics()
            print(f"\nStatistics:")
            print(f"  Success rate: {stats['success_rate']:.1f}%")
            print(f"  Blocks generated: {stats['blocks_generated']}")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        
        print("\n" + "=" * 60 + "\n")
    
    asyncio.run(test())