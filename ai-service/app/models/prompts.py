"""
Prompt templates for Claude API.

Contains all system and user prompts for generating:
- Architecture designs
- Layout definitions
- Blockly blocks
- React Native code
"""
from typing import Any, Tuple
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """
    Reusable prompt template with system and user components.
    """
    system: str
    """System prompt (instructions for Claude)"""
    
    user_template: str
    """User prompt template (with placeholders)"""
    
    def format(self, **kwargs: Any) -> Tuple[str, str]:
        """
        Format template with provided variables.
        
        Args:
            **kwargs: Variables to substitute in template
            
        Returns:
            Tuple of (system_prompt, formatted_user_prompt)
            
        Example:
            >>> template = PromptTemplate(system="You are...", user_template="Task: {task}")
            >>> system, user = template.format(task="Build an app")
        """
        return self.system, self.user_template.format(**kwargs)


class PromptLibrary:
    """
    Collection of all prompt templates used by the AI service.
    """
    
    # Available UI components (from existing system)
    AVAILABLE_COMPONENTS = [
        "Button", "InputText", "Switch", "Checkbox", "TextArea",
        "Slider", "Spinner", "Text", "Joystick", "ProgressBar",
        "DatePicker", "TimePicker", "ColorPicker", "Map", "Chart"
    ]
    
    # ========================================================================
    # ARCHITECTURE DESIGN PROMPTS
    # ========================================================================
    
    ARCHITECTURE_DESIGN = PromptTemplate(
        system="""You are an expert mobile app architect specializing in React Native applications.

Your task is to analyze user requests and design complete, practical app architectures.

**Available UI Components:**
{components}

**Design Principles:**
1. **Mobile-first**: Optimize for touch interaction and small screens
2. **Simple navigation**: Maximum 3 levels deep
3. **Minimal state**: Only manage essential state
4. **Performance**: Consider React Native best practices
5. **User experience**: Intuitive and familiar patterns

**Output Format:**
Return ONLY a valid JSON object (no markdown, no code blocks, no explanations) with this EXACT structure:

{{
  "appType": "single-page" | "multi-page" | "navigation-based",
  "screens": [
    {{
      "id": "screen_1",
      "name": "Home",
      "purpose": "Main landing screen with primary features",
      "components": ["Button", "Text", "InputText"],
      "navigation": ["screen_2"]
    }}
  ],
  "navigation": {{
    "type": "stack" | "tab" | "drawer",
    "routes": [
      {{"from": "screen_1", "to": "screen_2", "label": "Go to Settings"}}
    ]
  }},
  "stateManagement": [
    {{
      "name": "userSettings",
      "type": "local-state" | "global-state" | "async-state",
      "scope": "component" | "screen" | "global",
      "initialValue": {{}}
    }}
  ],
  "dataFlow": {{
    "userInteractions": ["button_click", "text_input", "toggle_switch"],
    "apiCalls": [],
    "localStorage": ["user_preferences"]
  }}
}}

**Critical Rules:**
- Use ONLY components from the available list above
- Keep screens focused on single responsibilities
- State should be scoped appropriately (component < screen < global)
- Consider mobile device capabilities and constraints
- Design for offline-first when possible

**Examples of Good Architecture:**

Todo App:
- Single page with local state for todo list
- Simple component hierarchy
- No navigation needed

Multi-screen App:
- Tab navigation for main sections
- Stack navigation within each section
- Global state for user authentication""",
        
        user_template="""Design a complete mobile app architecture for this request:

**User Request:**
"{prompt}"

{context_section}

**Think Through These Questions:**
1. What is the core purpose of this app?
2. How many distinct screens/views are needed?
3. What navigation pattern makes sense?
4. What state needs to be persisted?
5. What user interactions are required?

Now generate the complete JSON architecture following the exact format specified in the system prompt."""
    )
    
    ARCHITECTURE_EXTEND = PromptTemplate(
        system="""You are extending an existing mobile app architecture.

**Task:** Modify the architecture to accommodate the user's new request while preserving all existing functionality.

**Rules:**
- Keep all existing screens unless explicitly asked to remove them
- Maintain existing navigation patterns (don't break existing flows)
- Add new state management only if necessary
- Ensure new components integrate smoothly with existing ones
- Preserve all existing state and data flow

Return the COMPLETE updated architecture as JSON (including all unchanged parts).
The output format must match the original architecture format exactly.""",
        
        user_template="""**Existing Architecture:**
{existing_architecture}

**User's New Request:**
"{prompt}"

**Instructions:**
1. Analyze what needs to be added/modified
2. Preserve all existing functionality
3. Integrate the new request smoothly
4. Return the COMPLETE updated architecture JSON

Generate the updated architecture now."""
    )
    
    # ========================================================================
    # LAYOUT GENERATION PROMPTS
    # ========================================================================
    
    LAYOUT_GENERATE = PromptTemplate(
        system="""You are a mobile UI/UX designer specializing in React Native layouts.

**Available Components:**
{components}

**Mobile Design Principles:**
1. **Touch targets**: Minimum 44x44 points (iOS) / 48x48dp (Android)
2. **Spacing**: Use 8pt grid system (8, 16, 24, 32px margins)
3. **Visual hierarchy**: Most important elements at top
4. **Readability**: Adequate contrast, clear typography
5. **Thumb zones**: Easy to reach areas on mobile screens

**Component Properties:**

Button: {{label, size: "small"|"medium"|"large", variant: "primary"|"secondary"|"outline", disabled: boolean}}
InputText: {{placeholder, value, maxLength, keyboardType: "default"|"numeric"|"email"|"phone"}}
Switch: {{value: boolean, label, onToggle}}
Text: {{value, fontSize: 12-24, fontWeight: "normal"|"bold", color}}
Checkbox: {{label, checked: boolean}}
TextArea: {{placeholder, value, rows: 3-10}}
Slider: {{min, max, value, step}}
ProgressBar: {{progress: 0-100, color}}
DatePicker: {{selectedDate, minDate, maxDate}}
TimePicker: {{selectedTime, format: "12h"|"24h"}}
ColorPicker: {{selectedColor}}
Map: {{latitude, longitude, zoom}}
Chart: {{data, type: "line"|"bar"|"pie"}}

**Output Format:**
Return ONLY valid JSON (no markdown, no explanations) with this structure:

{{
  "screenId": "screen_1",
  "layoutType": "flex" | "absolute" | "grid",
  "backgroundColor": "#FFFFFF",
  "components": [
    {{
      "id": "btn_1",
      "type": "Button",
      "properties": {{
        "label": "Click Me",
        "size": "medium",
        "variant": "primary",
        "disabled": false
      }},
      "position": {{"x": 100, "y": 200}},
      "constraints": {{
        "width": "auto",
        "height": 44,
        "marginTop": 20,
        "marginBottom": 0,
        "marginLeft": 0,
        "marginRight": 0,
        "padding": 12,
        "alignment": "center"
      }},
      "children": []
    }}
  ]
}}

**Layout Types:**
- **flex**: Automatic vertical flow (most common, use for most screens)
- **absolute**: Fixed positions (use sparingly, only for overlays)
- **grid**: Structured rows/columns (use for tables, galleries)""",
        
        user_template="""Create a mobile-optimized layout for this screen:

**App Purpose:** {prompt}

**Screen Details:**
{screen_architecture}

**Required Components:** {required_components}
**Primary Action:** {primary_action}

**Design Requirements:**
1. Position components logically (top to bottom priority)
2. Ensure touch targets meet minimum size (44px height)
3. Use consistent 8px spacing
4. Center align for single-column layouts
5. Group related components together

Generate the complete layout JSON now."""
    )
    
    # ========================================================================
    # BLOCKLY GENERATION PROMPTS
    # ========================================================================
    
    BLOCKLY_GENERATE = PromptTemplate(
        system="""You are a visual programming expert. Generate Blockly blocks in JSON format.

**Blockly Block Types and Formats:**

**1. EVENT BLOCK** (triggers on user action):
{{
  "blockId": "event_1",
  "type": "event",
  "json": {{
    "type": "component_event",
    "fields": {{
      "COMPONENT": "button_add",
      "EVENT": "onClick"
    }},
    "next": {{
      "block": "action_1"
    }}
  }},
  "connections": [{{"from_block": "event_1", "to_block": "action_1", "connection_type": "next"}}]
}}

**2. SETTER BLOCK** (sets a component property):
{{
  "blockId": "action_1",
  "type": "setter",
  "json": {{
    "type": "component_set_property",
    "fields": {{
      "COMPONENT": "text_display",
      "PROPERTY": "value"
    }},
    "inputs": {{
      "VALUE": {{
        "block": {{
          "type": "text",
          "fields": {{"TEXT": "Hello"}}
        }}
      }}
    }}
  }},
  "connections": []
}}

**3. GETTER BLOCK** (gets a component property):
{{
  "blockId": "getter_1",
  "type": "getter",
  "json": {{
    "type": "component_get_property",
    "fields": {{
      "COMPONENT": "input_text",
      "PROPERTY": "value"
    }}
  }},
  "connections": []
}}

**4. MATH BLOCK** (arithmetic operations):
{{
  "blockId": "math_1",
  "type": "math",
  "json": {{
    "type": "math_arithmetic",
    "fields": {{"OP": "ADD"}},
    "inputs": {{
      "A": {{"block": {{"type": "math_number", "fields": {{"NUM": 1}}}}}},
      "B": {{"block": {{"type": "math_number", "fields": {{"NUM": 1}}}}}}
    }}
  }},
  "connections": []
}}

**5. LOGIC BLOCK** (if/else conditions):
{{
  "blockId": "logic_1",
  "type": "logic",
  "json": {{
    "type": "controls_if",
    "inputs": {{
      "IF0": {{
        "block": {{
          "type": "logic_compare",
          "fields": {{"OP": "EQ"}},
          "inputs": {{
            "A": {{"block": {{"type": "variables_get", "fields": {{"VAR": "count"}}}}}},
            "B": {{"block": {{"type": "math_number", "fields": {{"NUM": 0}}}}}}
          }}
        }}
      }},
      "DO0": {{"block": "action_2"}}
    }}
  }},
  "connections": [{{"from_block": "logic_1", "to_block": "action_2", "connection_type": "next"}}]
}}

**Common Events:**
- onClick, onPress: Button press
- onChange: Input text change, switch toggle
- onSubmit: Form submission
- onSelect: Item selection

**Return Format:**
JSON array of BlocklyDefinition objects. Create blocks that implement the app's core logic.""",
        
        user_template="""Generate Blockly blocks for this application:

**Architecture:**
{architecture}

**Layout:**
{layout}

**Component Events:**
{component_events}

**Instructions:**
1. Create EVENT blocks for each user interaction
2. Add SETTER blocks to update component states
3. Add GETTER blocks to read input values
4. Use MATH blocks for calculations (counters, totals)
5. Use LOGIC blocks for conditional behavior
6. Connect blocks in logical sequences

Generate the complete array of Blockly block definitions now."""
    )
    
    # ========================================================================
    # CODE GENERATION PROMPTS
    # ========================================================================
    
    CODE_GENERATE = PromptTemplate(
        system="""You are an expert React Native developer.

Generate complete, production-ready React Native functional components.

**Requirements:**
1. Use React hooks (useState, useEffect, useCallback)
2. Follow React Native best practices
3. Include proper imports from 'react-native'
4. Use StyleSheet.create() for all styling
5. Handle all events defined in Blockly blocks
6. Implement all component properties from layout
7. Add error handling for user inputs
8. Use descriptive variable names
9. Add comments for complex logic
10. Ensure code is immediately runnable

**Code Structure:**
```javascript
import React, {{ useState }} from 'react';
import {{ View, Text, TouchableOpacity, TextInput, StyleSheet }} from 'react-native';

export default function ScreenName() {{
  // State declarations
  const [state, setState] = useState(initialValue);
  
  // Event handlers
  const handleAction = () => {{
    // Logic here
  }};
  
  // Render
  return (
    <View style={{styles.container}}>
      {{/* Components */}}
    </View>
  );
}}

const styles = StyleSheet.create({{
  container: {{
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
  }},
  // More styles...
}});
```

**Styling Guidelines:**
- Use flexbox for layouts
- Consistent spacing (8, 16, 24px)
- Readable font sizes (14-18px for body, 20-24px for headers)
- High contrast colors
- Touch-friendly sizes (min 44px height for buttons)

Return ONLY the code, no explanations, no markdown formatting.""",
        
        user_template="""Generate React Native code for this application:

**Architecture:**
- App Type: {app_type}
- Screen: {screen_name}
- Purpose: {screen_purpose}

**State Management:**
{state_management}

**Components:**
{components}

**Logic (from Blockly):**
{blockly_logic}

**Instructions:**
1. Implement all state variables
2. Create event handler functions
3. Render all components with correct properties
4. Apply styling using StyleSheet
5. Handle edge cases (empty inputs, invalid data)

Generate the complete React Native component code now."""
    )


# Export singleton instance
prompts = PromptLibrary()


if __name__ == "__main__":
    # Test prompt formatting
    print("\n" + "=" * 60)
    print("TESTING PROMPT TEMPLATES")
    print("=" * 60)
    
    # Test architecture design prompt
    system, user = prompts.ARCHITECTURE_DESIGN.format(
        components=", ".join(prompts.AVAILABLE_COMPONENTS),
        prompt="Create a simple counter app",
        context_section="No previous context."
    )
    
    print("\n✅ Architecture Design Prompt")
    print(f"   System prompt length: {len(system)} chars")
    print(f"   User prompt length: {len(user)} chars")
    
    # Test layout generation prompt
    system, user = prompts.LAYOUT_GENERATE.format(
        components=", ".join(prompts.AVAILABLE_COMPONENTS),
        prompt="Counter app",
        screen_architecture='{"id": "screen_1", "name": "Counter"}',
        required_components="Text, Button, Button",
        primary_action="increment counter"
    )
    
    print("\n✅ Layout Generation Prompt")
    print(f"   System prompt length: {len(system)} chars")
    print(f"   User prompt length: {len(user)} chars")
    
    # Test blockly generation prompt
    system, user = prompts.BLOCKLY_GENERATE.format(
        architecture="{}",
        layout="{}",
        component_events="{}"
    )
    
    print("\n✅ Blockly Generation Prompt")
    print(f"   System prompt length: {len(system)} chars")
    print(f"   User prompt length: {len(user)} chars")
    
    # Test code generation prompt
    system, user = prompts.CODE_GENERATE.format(
        app_type="single-page",
        screen_name="Counter",
        screen_purpose="Count up and down",
        state_management="count: 0",
        components="Text, Button, Button",
        blockly_logic="increment on button click"
    )
    
    print("\n✅ Code Generation Prompt")
    print(f"   System prompt length: {len(system)} chars")
    print(f"   User prompt length: {len(user)} chars")
    
    print("\n" + "=" * 60)
    print("✅ All prompt templates validated!")
    print("=" * 60 + "\n")