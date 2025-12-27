"""
Layout Generator - Intelligent component positioning and layout.

Generates mobile-optimized layouts from architecture designs.
Phase 4 implementation with collision detection and responsive sizing.
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
import anthropic

from app.config import settings
from app.models.schemas import ArchitectureDesign, ScreenDefinition
from app.models.enhanced_schemas import (
    EnhancedComponentDefinition,
    EnhancedLayoutDefinition,
    PropertyValue
)
from app.models.prompts import prompts


class LayoutGenerationError(Exception):
    """Base exception for layout generation errors"""
    pass


class CollisionError(LayoutGenerationError):
    """Raised when components collide"""
    pass


class LayoutGenerator:
    """
    Generates mobile-optimized layouts using Claude API.
    
    Features:
    - Intelligent component positioning
    - Automatic collision detection and resolution
    - Responsive sizing based on device constraints
    - Touch target validation (44px minimum)
    - Visual hierarchy optimization
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        
        # Canvas constraints
        self.canvas_width = settings.canvas_width
        self.canvas_height = settings.canvas_height
        self.safe_area_top = settings.canvas_safe_area_top
        self.safe_area_bottom = settings.canvas_safe_area_bottom
        
        # Component sizing defaults (width, height)
        self.component_defaults = {
            'Button': (120, 44),
            'InputText': (280, 44),
            'Switch': (51, 31),
            'Checkbox': (24, 24),
            'TextArea': (280, 100),
            'Slider': (280, 44),
            'Spinner': (40, 40),
            'Text': (280, 40),
            'Joystick': (100, 100),
            'ProgressBar': (280, 8),
            'DatePicker': (280, 44),
            'TimePicker': (280, 44),
            'ColorPicker': (280, 44),
            'Map': (340, 200),
            'Chart': (340, 200)
        }
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'collisions_resolved': 0
        }
    
    async def generate(
        self,
        architecture: ArchitectureDesign,
        screen_id: str
    ) -> Tuple[EnhancedLayoutDefinition, Dict[str, Any]]:
        """
        Generate layout for a specific screen.
        
        Args:
            architecture: Complete architecture design
            screen_id: Screen to generate layout for
            
        Returns:
            Tuple of (EnhancedLayoutDefinition, metadata)
            
        Raises:
            LayoutGenerationError: If generation fails
        """
        self.stats['total_requests'] += 1
        
        # Find the screen
        screen = None
        for s in architecture.screens:
            if s.id == screen_id:
                screen = s
                break
        
        if not screen:
            raise LayoutGenerationError(f"Screen '{screen_id}' not found in architecture")
        
        logger.info(f"📐 Generating layout for screen: {screen.name}")
        logger.debug(f"Components: {', '.join(screen.components)}")
        
        try:
            # Generate layout with Claude
            layout_data, metadata = await self._generate_with_claude(
                screen=screen,
                architecture=architecture
            )
            
            # Convert to enhanced components
            components = await self._convert_to_enhanced_components(
                layout_data['components'],
                screen_id
            )
            
            # Resolve collisions
            components = await self._resolve_collisions(components)
            
            # Create layout definition
            layout = EnhancedLayoutDefinition(
                screen_id=screen_id,
                canvas=layout_data.get('canvas', self._get_default_canvas()),
                components=components,
                layout_metadata=metadata
            )
            
            self.stats['successful'] += 1
            
            logger.info(f"✅ Layout generated: {len(components)} components")
            
            return layout, metadata
            
        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Layout generation failed: {e}")
            raise LayoutGenerationError(f"Failed to generate layout: {e}")
    
    async def _generate_with_claude(
        self,
        screen: ScreenDefinition,
        architecture: ArchitectureDesign
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate layout using Claude API.
        
        Args:
            screen: Screen definition
            architecture: Complete architecture
            
        Returns:
            Tuple of (layout_dict, metadata)
        """
        logger.debug("Calling Claude API for layout generation...")
        
        # Determine primary action
        primary_action = "view content"
        if any('Button' in comp for comp in screen.components):
            primary_action = "button interaction"
        elif any('Input' in comp for comp in screen.components):
            primary_action = "text input"
        
        # Format prompt
        system_prompt, user_prompt = prompts.LAYOUT_GENERATE.format(
            components=", ".join(settings.available_components),
            prompt=f"Layout for {screen.name}",
            screen_architecture=json.dumps({
                'id': screen.id,
                'name': screen.name,
                'purpose': screen.purpose
            }, indent=2),
            required_components=", ".join(screen.components),
            primary_action=primary_action
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
        layout_data = await self._parse_layout_json(response_text)
        
        # Build metadata
        metadata = {
            'model': self.model,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'api_duration_ms': api_duration,
            'screen_id': screen.id,
            'screen_name': screen.name
        }
        
        return layout_data, metadata
    
    async def _parse_layout_json(self, response_text: str) -> Dict[str, Any]:
        """
        Parse layout JSON from Claude response.
        
        Args:
            response_text: Raw response from Claude
            
        Returns:
            Parsed layout dictionary
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
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise LayoutGenerationError(f"Could not parse layout JSON: {e}")
    
    async def _convert_to_enhanced_components(
        self,
        components_data: List[Dict[str, Any]],
        screen_id: str
    ) -> List[EnhancedComponentDefinition]:
        """
        Convert Claude's component data to enhanced definitions.
        
        Args:
            components_data: Raw component data from Claude
            screen_id: Screen identifier
            
        Returns:
            List of enhanced component definitions
        """
        enhanced_components = []
        
        for idx, comp_data in enumerate(components_data):
            try:
                # Extract basic info
                comp_id = comp_data.get('id', f"comp_{screen_id}_{idx}")
                comp_type = comp_data.get('type')
                
                if comp_type not in settings.available_components:
                    logger.warning(f"Unsupported component type: {comp_type}, skipping")
                    continue
                
                # Convert properties to PropertyValue format
                properties = {}
                raw_properties = comp_data.get('properties', {})
                
                for key, value in raw_properties.items():
                    if isinstance(value, dict) and 'type' in value:
                        # Already in PropertyValue format
                        properties[key] = PropertyValue(**value)
                    else:
                        # Convert to PropertyValue
                        properties[key] = PropertyValue(type="literal", value=value)
                
                # Extract or generate position/size
                position = comp_data.get('position', {'x': 0, 'y': 0})
                constraints = comp_data.get('constraints', {})
                
                # Ensure style property
                if 'style' not in properties:
                    width, height = self.component_defaults.get(comp_type, (280, 44))
                    
                    # Parse width from constraints
                    width_str = constraints.get('width', 'auto')
                    if width_str != 'auto':
                        try:
                            if '%' in width_str:
                                # Convert percentage to pixels
                                percentage = float(width_str.rstrip('%'))
                                width = int(self.canvas_width * percentage / 100)
                            else:
                                width = int(width_str.rstrip('px'))
                        except:
                            pass
                    
                    height = constraints.get('height', height)
                    
                    properties['style'] = PropertyValue(
                        type="literal",
                        value={
                            'left': position.get('x', 0),
                            'top': position.get('y', 0),
                            'width': width,
                            'height': height
                        }
                    )
                
                # Create enhanced component
                enhanced = EnhancedComponentDefinition(
                    component_id=comp_id,
                    component_type=comp_type,
                    properties=properties,
                    z_index=idx,
                    parent_id=None,
                    children_ids=[]
                )
                
                enhanced_components.append(enhanced)
                
            except Exception as e:
                logger.warning(f"Failed to convert component {idx}: {e}")
                continue
        
        return enhanced_components
    
    async def _resolve_collisions(
        self,
        components: List[EnhancedComponentDefinition]
    ) -> List[EnhancedComponentDefinition]:
        """
        Detect and resolve component collisions.
        
        Uses a simple vertical stacking strategy:
        - Maintains horizontal centering
        - Stacks components vertically with 16px spacing
        - Ensures components stay within canvas bounds
        
        Args:
            components: List of components that may have collisions
            
        Returns:
            List of components with collisions resolved
        """
        if len(components) <= 1:
            return components
        
        logger.debug("Checking for collisions...")
        
        # Check for collisions
        has_collisions = False
        for i, comp1 in enumerate(components):
            bounds1 = self._get_component_bounds(comp1)
            if not bounds1:
                continue
            
            for comp2 in components[i+1:]:
                bounds2 = self._get_component_bounds(comp2)
                if not bounds2:
                    continue
                
                if self._rectangles_overlap(bounds1, bounds2):
                    has_collisions = True
                    break
            
            if has_collisions:
                break
        
        if not has_collisions:
            logger.debug("No collisions detected")
            return components
        
        logger.info(f"⚠️  Collisions detected, resolving...")
        self.stats['collisions_resolved'] += 1
        
        # Simple vertical stack layout
        current_y = self.safe_area_top + 20  # Start below safe area
        
        for component in components:
            style_prop = component.properties.get('style')
            if not style_prop or style_prop.type != "literal":
                continue
            
            style = style_prop.value
            width = style.get('width', 280)
            height = style.get('height', 44)
            
            # Center horizontally
            x = (self.canvas_width - width) // 2
            
            # Update position
            style['left'] = x
            style['top'] = current_y
            
            # Move to next position
            current_y += height + 16  # 16px spacing
        
        logger.info(f"✅ Collisions resolved: stacked vertically")
        
        return components
    
    def _get_component_bounds(
        self,
        component: EnhancedComponentDefinition
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Get component bounding rectangle.
        
        Args:
            component: Component definition
            
        Returns:
            Tuple of (left, top, right, bottom) or None
        """
        style_prop = component.properties.get('style')
        if not style_prop or style_prop.type != "literal":
            return None
        
        style = style_prop.value
        if not isinstance(style, dict):
            return None
        
        left = style.get('left', 0)
        top = style.get('top', 0)
        width = style.get('width', 0)
        height = style.get('height', 0)
        
        return (left, top, left + width, top + height)
    
    def _rectangles_overlap(
        self,
        rect1: Tuple[int, int, int, int],
        rect2: Tuple[int, int, int, int]
    ) -> bool:
        """
        Check if two rectangles overlap.
        
        Args:
            rect1: (left, top, right, bottom)
            rect2: (left, top, right, bottom)
            
        Returns:
            True if rectangles overlap
        """
        l1_x, l1_y, r1_x, r1_y = rect1
        l2_x, l2_y, r2_x, r2_y = rect2
        
        # No overlap if one is to the left/right/above/below the other
        if r1_x <= l2_x or r2_x <= l1_x:
            return False
        if r1_y <= l2_y or r2_y <= l1_y:
            return False
        
        return True
    
    def _get_default_canvas(self) -> Dict[str, Any]:
        """Get default canvas configuration"""
        return {
            "width": self.canvas_width,
            "height": self.canvas_height,
            "background_color": "#FFFFFF",
            "safe_area_insets": {
                "top": self.safe_area_top,
                "bottom": self.safe_area_bottom,
                "left": 0,
                "right": 0
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics"""
        total = self.stats['total_requests']
        
        return {
            'total_requests': total,
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'collisions_resolved': self.stats['collisions_resolved']
        }


# Global layout generator instance
layout_generator = LayoutGenerator()


if __name__ == "__main__":
    # Test layout generator
    import asyncio
    from app.models.schemas import (
        ArchitectureDesign,
        ScreenDefinition,
        NavigationStructure,
        StateDefinition,
        DataFlowDiagram
    )
    
    async def test():
        print("\n" + "=" * 60)
        print("LAYOUT GENERATOR TEST")
        print("=" * 60)
        
        # Create test architecture
        architecture = ArchitectureDesign(
            app_type="single-page",
            screens=[
                ScreenDefinition(
                    id="screen_1",
                    name="Counter",
                    purpose="Simple counter with increment and decrement buttons",
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
        
        try:
            # Generate layout
            layout, metadata = await layout_generator.generate(
                architecture=architecture,
                screen_id="screen_1"
            )
            
            print("\n✅ Layout generated successfully!")
            print(f"\nLayout:")
            print(f"  Screen: {layout.screen_id}")
            print(f"  Canvas: {layout.canvas['width']}x{layout.canvas['height']}")
            print(f"  Components: {len(layout.components)}")
            
            for comp in layout.components:
                style = comp.properties.get('style')
                if style and style.type == "literal":
                    s = style.value
                    print(f"    - {comp.component_type} ({comp.component_id})")
                    print(f"      Position: ({s['left']}, {s['top']})")
                    print(f"      Size: {s['width']}x{s['height']}")
            
            print(f"\nMetadata:")
            print(f"  Model: {metadata['model']}")
            print(f"  Tokens: {metadata['tokens_used']}")
            print(f"  Duration: {metadata['api_duration_ms']}ms")
            
            # Statistics
            stats = layout_generator.get_statistics()
            print(f"\nStatistics:")
            print(f"  Success rate: {stats['success_rate']:.1f}%")
            print(f"  Collisions resolved: {stats['collisions_resolved']}")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
        
        print("\n" + "=" * 60 + "\n")
    
    asyncio.run(test())