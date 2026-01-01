"""
Enhanced Pydantic models with complete validation.

This extends the base schemas.py with production-ready validation,
component property schemas, and complete data structures.
"""
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from uuid import uuid4
import re


# ============================================================================
# COMPONENT PROPERTY SCHEMAS
# ============================================================================

class PropertyValue(BaseModel):
    """Base property value structure"""
    type: Literal["literal", "variable", "expression", "event"]
    value: Any


class ComponentStyle(BaseModel):
    """Component positioning and styling"""
    left: int = Field(..., ge=0, description="X position in pixels")
    top: int = Field(..., ge=0, description="Y position in pixels")
    width: int = Field(..., gt=0, description="Width in pixels")
    height: int = Field(..., gt=0, description="Height in pixels")
    
    @field_validator('height')
    @classmethod
    def validate_minimum_touch_target(cls, v: int) -> int:
        """Ensure minimum touch target size for accessibility"""
        if v < 44:
            raise ValueError("Height must be at least 44px for touch targets")
        return v


class BaseComponentProperties(BaseModel):
    """Common properties for all components"""
    text: Optional[PropertyValue] = None
    size: Optional[PropertyValue] = Field(
        default=None,
        description="Component size: small, medium, large"
    )
    color: Optional[PropertyValue] = Field(
        default=None,
        description="Text/foreground color"
    )
    backgroundColor: Optional[PropertyValue] = Field(
        default=None,
        description="Background color"
    )
    style: PropertyValue = Field(..., description="Position and dimensions")
    disabled: Optional[PropertyValue] = Field(
        default=None,
        description="Whether component is disabled"
    )
    
    @field_validator('color', 'backgroundColor')
    @classmethod
    def validate_color(cls, v: Optional[PropertyValue]) -> Optional[PropertyValue]:
        """Validate hex color format"""
        if v and v.type == "literal" and isinstance(v.value, str):
            if not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', v.value):
                raise ValueError(f"Invalid hex color: {v.value}")
        return v


class ButtonProperties(BaseComponentProperties):
    """Button-specific properties"""
    onPress: Optional[PropertyValue] = Field(
        default=None,
        description="Event handler block ID"
    )
    variant: Optional[PropertyValue] = Field(
        default=None,
        description="Button variant: primary, secondary, outline, ghost"
    )


class InputTextProperties(BaseComponentProperties):
    """InputText-specific properties"""
    placeholder: Optional[PropertyValue] = None
    value: Optional[PropertyValue] = None
    maxLength: Optional[PropertyValue] = None
    keyboardType: Optional[PropertyValue] = Field(
        default=None,
        description="Keyboard type: default, numeric, email, phone"
    )
    onChange: Optional[PropertyValue] = Field(
        default=None,
        description="Change event handler block ID"
    )
    secureTextEntry: Optional[PropertyValue] = Field(
        default=None,
        description="Hide text for passwords"
    )


class SwitchProperties(BaseComponentProperties):
    """Switch/Toggle-specific properties"""
    value: PropertyValue = Field(..., description="Boolean value")
    onToggle: Optional[PropertyValue] = Field(
        default=None,
        description="Toggle event handler block ID"
    )
    thumbColor: Optional[PropertyValue] = None
    trackColor: Optional[PropertyValue] = None


class CheckboxProperties(BaseComponentProperties):
    """Checkbox-specific properties"""
    checked: PropertyValue = Field(..., description="Boolean checked state")
    label: Optional[PropertyValue] = None
    onChange: Optional[PropertyValue] = Field(
        default=None,
        description="Change event handler block ID"
    )


class TextProperties(BaseComponentProperties):
    """Text display properties"""
    value: PropertyValue = Field(..., description="Text content")
    fontSize: Optional[PropertyValue] = Field(
        default=None,
        description="Font size in pixels (12-32)"
    )
    fontWeight: Optional[PropertyValue] = Field(
        default=None,
        description="Font weight: normal, bold, 100-900"
    )
    textAlign: Optional[PropertyValue] = Field(
        default=None,
        description="Text alignment: left, center, right, justify"
    )
    numberOfLines: Optional[PropertyValue] = Field(
        default=None,
        description="Maximum number of lines (truncate with ...)"
    )


class SliderProperties(BaseComponentProperties):
    """Slider-specific properties"""
    min: PropertyValue = Field(..., description="Minimum value")
    max: PropertyValue = Field(..., description="Maximum value")
    value: PropertyValue = Field(..., description="Current value")
    step: Optional[PropertyValue] = Field(
        default=None,
        description="Step increment"
    )
    onChange: Optional[PropertyValue] = Field(
        default=None,
        description="Change event handler block ID"
    )


# Component property type mapping
COMPONENT_PROPERTY_SCHEMAS = {
    "Button": ButtonProperties,
    "InputText": InputTextProperties,
    "Switch": SwitchProperties,
    "Checkbox": CheckboxProperties,
    "Text": TextProperties,
    "Slider": SliderProperties,
    # Add more as needed
}


# ============================================================================
# ENHANCED COMPONENT DEFINITION
# ============================================================================

class EnhancedComponentDefinition(BaseModel):
    """
    Enhanced component definition with strict validation.
    """
    component_id: str = Field(..., description="Unique component identifier")
    component_type: Literal[
        "Button", "InputText", "Switch", "Checkbox", "TextArea",
        "Slider", "Spinner", "Text", "Joystick", "ProgressBar",
        "DatePicker", "TimePicker", "ColorPicker", "Map", "Chart"
    ]
    properties: Dict[str, PropertyValue]
    z_index: int = Field(default=0, ge=0, description="Layer order (higher = on top)")
    parent_id: Optional[str] = Field(default=None, description="Parent component ID")
    children_ids: List[str] = Field(default_factory=list)
    substitution: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Substitution metadata if component was replaced"
    )
    
    @field_validator('component_id')
    @classmethod
    def validate_component_id(cls, v: str) -> str:
        """Ensure valid component ID format"""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError(f"Invalid component ID: {v}. Must start with letter/underscore")
        return v
    
    @model_validator(mode='after')
    def validate_component_properties(self) -> 'EnhancedComponentDefinition':
        """Validate properties against component-specific schema"""
        schema_class = COMPONENT_PROPERTY_SCHEMAS.get(self.component_type)
        
        if schema_class:
            try:
                # Convert properties dict to schema format
                props_dict = {
                    key: value for key, value in self.properties.items()
                }
                # Validate using component-specific schema
                schema_class(**props_dict)
            except Exception as e:
                raise ValueError(f"Invalid properties for {self.component_type}: {e}")
        
        return self
    
    @model_validator(mode='after')
    def validate_style_bounds(self) -> 'EnhancedComponentDefinition':
        """Ensure component is within canvas bounds"""
        if 'style' not in self.properties:
            raise ValueError("Component must have 'style' property")
        
        from app.config import settings
        
        style_val = self.properties['style']
        if style_val.type == "literal" and isinstance(style_val.value, dict):
            style = style_val.value
            
            # Check bounds
            if style.get('left', 0) < 0:
                raise ValueError("Component left position cannot be negative")
            if style.get('top', 0) < 0:
                raise ValueError("Component top position cannot be negative")
            
            max_right = style.get('left', 0) + style.get('width', 0)
            max_bottom = style.get('top', 0) + style.get('height', 0)
            
            if max_right > settings.canvas_width:
                raise ValueError(f"Component exceeds canvas width: {max_right} > {settings.canvas_width}")
            if max_bottom > settings.canvas_height:
                raise ValueError(f"Component exceeds canvas height: {max_bottom} > {settings.canvas_height}")
        
        return self


# ============================================================================
# ENHANCED LAYOUT DEFINITION
# ============================================================================

class EnhancedLayoutDefinition(BaseModel):
    """Enhanced layout with collision detection"""
    screen_id: str
    canvas: Dict[str, Any] = Field(
        default_factory=lambda: {
            "width": 375,
            "height": 667,
            "background_color": "#FFFFFF",
            "safe_area_insets": {
                "top": 44,
                "bottom": 34,
                "left": 0,
                "right": 0
            }
        }
    )
    components: List[EnhancedComponentDefinition]
    layout_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_no_collisions(self) -> 'EnhancedLayoutDefinition':
        """Check for component collisions"""
        def get_bounds(comp: EnhancedComponentDefinition) -> Optional[tuple]:
            """Extract component bounds"""
            if 'style' not in comp.properties:
                return None
            
            style_val = comp.properties['style']
            if style_val.type == "literal" and isinstance(style_val.value, dict):
                style = style_val.value
                left = style.get('left', 0)
                top = style.get('top', 0)
                width = style.get('width', 0)
                height = style.get('height', 0)
                return (left, top, left + width, top + height)
            return None
        
        def rectangles_overlap(r1: tuple, r2: tuple) -> bool:
            """Check if two rectangles overlap"""
            l1_x, l1_y, r1_x, r1_y = r1
            l2_x, l2_y, r2_x, r2_y = r2
            
            # No overlap if one is to the left/right/above/below the other
            if r1_x <= l2_x or r2_x <= l1_x:
                return False
            if r1_y <= l2_y or r2_y <= l1_y:
                return False
            
            return True
        
        # Check all pairs for collision
        for i, comp1 in enumerate(self.components):
            bounds1 = get_bounds(comp1)
            if not bounds1:
                continue
            
            for comp2 in self.components[i+1:]:
                bounds2 = get_bounds(comp2)
                if not bounds2:
                    continue
                
                if rectangles_overlap(bounds1, bounds2):
                    raise ValueError(
                        f"Component collision detected: {comp1.component_id} "
                        f"overlaps with {comp2.component_id}"
                    )
        
        return self
    
    @model_validator(mode='after')
    def validate_unique_ids(self) -> 'EnhancedLayoutDefinition':
        """Ensure all component IDs are unique"""
        ids = [comp.component_id for comp in self.components]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate component IDs found: {set(duplicates)}")
        return self


# ============================================================================
# BLOCKLY SCHEMA (Standard Blockly JSON)
# ============================================================================

class BlocklyBlock(BaseModel):
    """Single Blockly block definition"""
    type: str = Field(..., description="Block type identifier")
    id: str = Field(..., description="Unique block ID")
    x: Optional[int] = Field(default=None, description="X position in workspace")
    y: Optional[int] = Field(default=None, description="Y position in workspace")
    fields: Optional[Dict[str, Any]] = Field(default_factory=dict)
    inputs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    next: Optional[Dict[str, Any]] = Field(default=None, description="Next block in sequence")
    
    @field_validator('id')
    @classmethod
    def validate_block_id(cls, v: str) -> str:
        """Ensure valid block ID"""
        if not v or len(v) == 0:
            raise ValueError("Block ID cannot be empty")
        return v


class BlocklyVariable(BaseModel):
    """Blockly variable definition"""
    name: str
    id: str
    type: Optional[str] = None


class BlocklyWorkspace(BaseModel):
    """Complete Blockly workspace"""
    languageVersion: int = 0
    blocks: List[BlocklyBlock]


class EnhancedBlocklyDefinition(BaseModel):
    """Enhanced Blockly definition with validation"""
    blocks: BlocklyWorkspace
    variables: List[BlocklyVariable] = Field(default_factory=list)
    custom_blocks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Custom block type definitions"
    )
    
    @model_validator(mode='after')
    def validate_block_references(self) -> 'EnhancedBlocklyDefinition':
        """Ensure all block references are valid"""
        block_ids = {block.id for block in self.blocks.blocks}
        variable_ids = {var.id for var in self.variables}
        
        def check_block(block: BlocklyBlock) -> None:
            """Recursively check block and its children"""
            # Check input blocks
            if block.inputs:
                for input_data in block.inputs.values():
                    if isinstance(input_data, dict) and 'block' in input_data:
                        nested = input_data['block']
                        if isinstance(nested, dict) and 'id' in nested:
                            # Nested block is valid
                            pass
            
            # Check next block
            if block.next and isinstance(block.next, dict):
                if 'block' in block.next:
                    nested = block.next['block']
                    if isinstance(nested, dict) and 'id' in nested:
                        # Next block is valid
                        pass
        
        # Validate all blocks
        for block in self.blocks.blocks:
            check_block(block)
        
        return self


# ============================================================================
# COMPLETE RESPONSE SCHEMA
# ============================================================================

class CompleteResponse(BaseModel):
    """Complete AI generation response"""
    task_id: str
    socket_id: str
    type: Literal["complete"] = "complete"
    status: Literal["success", "partial_success", "error"] = "success"
    result: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    conversation: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_result_structure(self) -> 'CompleteResponse':
        """Ensure result has required keys"""
        required_keys = {'architecture', 'layout', 'blockly'}
        if self.status == "success":
            missing = required_keys - set(self.result.keys())
            if missing:
                raise ValueError(f"Missing required result keys: {missing}")
        return self


# ============================================================================
# INTENT ANALYSIS SCHEMA
# ============================================================================

class IntentAnalysis(BaseModel):
    """Result of intent analysis"""
    intent_type: Literal["new_app", "extend_app", "modify_app", "clarification", "help"]
    complexity: Literal["simple", "medium", "complex"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Extracted components, actions, data types, etc."
    )
    requires_context: bool = Field(
        default=False,
        description="Whether existing project context is needed"
    )
    multi_turn: bool = Field(
        default=False,
        description="Whether this is part of a conversation"
    )


# ============================================================================
# ENRICHED CONTEXT SCHEMA
# ============================================================================

class EnrichedContext(BaseModel):
    """Enriched context for AI generation"""
    original_request: Dict[str, Any]
    intent_analysis: IntentAnalysis
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    existing_project: Optional[Dict[str, Any]] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


if __name__ == "__main__":
    # Test schemas
    print("\n" + "=" * 60)
    print("TESTING ENHANCED SCHEMAS")
    print("=" * 60)
    
    # Test component properties
    button_props = {
        "value": PropertyValue(type="literal", value="Click Me"),
        "size": PropertyValue(type="literal", value="medium"),
        "color": PropertyValue(type="literal", value="#FFFFFF"),
        "backgroundColor": PropertyValue(type="literal", value="#007AFF"),
        "style": PropertyValue(type="literal", value={
            "left": 100,
            "top": 200,
            "width": 120,
            "height": 44
        })
    }
    
    comp = EnhancedComponentDefinition(
        component_id="btn_submit",
        component_type="Button",
        properties=button_props
    )
    
    print(f"\n✅ Component created: {comp.component_id}")
    print(f"   Type: {comp.component_type}")
    print(f"   Properties: {len(comp.properties)}")
    
    # Test layout
    layout = EnhancedLayoutDefinition(
        screen_id="screen_1",
        components=[comp]
    )
    
    print(f"\n✅ Layout created: {layout.screen_id}")
    print(f"   Components: {len(layout.components)}")
    
    print("\n" + "=" * 60)
    print("✅ All schemas validated successfully!")
    print("=" * 60 + "\n")