"""
Architecture Validator - Comprehensive validation and correction.

Validates generated architectures for:
- Logical consistency
- Component availability
- Navigation integrity
- State management correctness
- Performance considerations
"""
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger

from app.config import settings
from app.models.schemas import ArchitectureDesign, ScreenDefinition


class ValidationWarning:
    """Represents a validation warning"""
    
    def __init__(self, level: str, component: str, message: str, suggestion: str = ""):
        self.level = level  # "info", "warning", "error"
        self.component = component
        self.message = message
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, str]:
        return {
            'level': self.level,
            'component': self.component,
            'message': self.message,
            'suggestion': self.suggestion
        }
    
    def __str__(self) -> str:
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}
        s = f"{emoji.get(self.level, '•')} [{self.level.upper()}] {self.component}: {self.message}"
        if self.suggestion:
            s += f"\n   → {self.suggestion}"
        return s


class ArchitectureValidator:
    """
    Comprehensive architecture validation.
    
    Performs multiple validation passes:
    1. Schema validation (Pydantic)
    2. Logical consistency
    3. Component availability
    4. Navigation integrity
    5. State management
    6. Performance considerations
    """
    
    def __init__(self):
        self.warnings: List[ValidationWarning] = []
        self.available_components = set(settings.available_components)
    
    async def validate(
        self,
        architecture: ArchitectureDesign
    ) -> Tuple[bool, List[ValidationWarning]]:
        """
        Comprehensive validation of architecture.
        
        Args:
            architecture: Architecture to validate
            
        Returns:
            Tuple of (is_valid, warnings_list)
        """
        self.warnings = []
        
        logger.info("🔍 Validating architecture...")
        
        # Run all validation checks
        await self._validate_screens(architecture)
        await self._validate_components(architecture)
        await self._validate_navigation(architecture)
        await self._validate_state_management(architecture)
        await self._validate_performance(architecture)
        await self._validate_user_experience(architecture)
        
        # Determine if architecture is valid
        has_errors = any(w.level == "error" for w in self.warnings)
        is_valid = not has_errors
        
        if is_valid:
            logger.info("✅ Architecture validation passed")
        else:
            error_count = sum(1 for w in self.warnings if w.level == "error")
            logger.error(f"❌ Architecture validation failed: {error_count} error(s)")
        
        warning_count = sum(1 for w in self.warnings if w.level == "warning")
        info_count = sum(1 for w in self.warnings if w.level == "info")
        
        if warning_count > 0:
            logger.warning(f"⚠️  {warning_count} warning(s) found")
        if info_count > 0:
            logger.info(f"ℹ️  {info_count} info message(s)")
        
        return is_valid, self.warnings
    
    async def _validate_screens(self, architecture: ArchitectureDesign) -> None:
        """Validate screen definitions"""
        
        if len(architecture.screens) == 0:
            self.warnings.append(ValidationWarning(
                level="error",
                component="screens",
                message="No screens defined",
                suggestion="Add at least one screen to the architecture"
            ))
            return
        
        # Check for duplicate screen IDs
        screen_ids = [s.id for s in architecture.screens]
        duplicates = [id for id in screen_ids if screen_ids.count(id) > 1]
        
        if duplicates:
            self.warnings.append(ValidationWarning(
                level="error",
                component="screens",
                message=f"Duplicate screen IDs: {set(duplicates)}",
                suggestion="Ensure all screen IDs are unique"
            ))
        
        # Check screen purposes
        for screen in architecture.screens:
            if not screen.purpose or len(screen.purpose.strip()) < 10:
                self.warnings.append(ValidationWarning(
                    level="warning",
                    component=f"screen:{screen.id}",
                    message=f"Screen '{screen.name}' has unclear purpose",
                    suggestion="Add a clear description of the screen's purpose"
                ))
            
            # Check if screen has components
            if len(screen.components) == 0:
                self.warnings.append(ValidationWarning(
                    level="warning",
                    component=f"screen:{screen.id}",
                    message=f"Screen '{screen.name}' has no components",
                    suggestion="Add UI components to make the screen functional"
                ))
        
        # Warn about too many screens
        if len(architecture.screens) > 10:
            self.warnings.append(ValidationWarning(
                level="warning",
                component="screens",
                message=f"Large number of screens ({len(architecture.screens)})",
                suggestion="Consider simplifying the navigation or using tab/drawer patterns"
            ))
    
    async def _validate_components(self, architecture: ArchitectureDesign) -> None:
        """Validate component usage"""
        
        all_components = []
        for screen in architecture.screens:
            all_components.extend(screen.components)
        
        # Check for unsupported components
        for component in set(all_components):
            if component not in self.available_components:
                self.warnings.append(ValidationWarning(
                    level="error",
                    component="components",
                    message=f"Unsupported component: '{component}'",
                    suggestion=f"Use one of: {', '.join(sorted(self.available_components))}"
                ))
        
        # Check for component variety
        unique_components = set(all_components)
        
        if len(unique_components) == 1:
            self.warnings.append(ValidationWarning(
                level="info",
                component="components",
                message=f"App uses only one component type: {unique_components.pop()}",
                suggestion="Consider adding more component types for richer UI"
            ))
        
        # Check for common patterns
        has_input = any(c in all_components for c in ['InputText', 'TextArea'])
        has_button = 'Button' in all_components
        
        if has_input and not has_button:
            self.warnings.append(ValidationWarning(
                level="warning",
                component="components",
                message="App has input fields but no buttons",
                suggestion="Add buttons for form submission or actions"
            ))
    
    async def _validate_navigation(self, architecture: ArchitectureDesign) -> None:
        """Validate navigation structure"""
        
        screen_ids = {s.id for s in architecture.screens}
        
        # Validate navigation routes
        for route in architecture.navigation.routes:
            from_screen = route.get('from')
            to_screen = route.get('to')
            
            if from_screen and from_screen not in screen_ids:
                self.warnings.append(ValidationWarning(
                    level="error",
                    component="navigation",
                    message=f"Route from non-existent screen: {from_screen}",
                    suggestion=f"Valid screens: {', '.join(sorted(screen_ids))}"
                ))
            
            if to_screen and to_screen not in screen_ids:
                self.warnings.append(ValidationWarning(
                    level="error",
                    component="navigation",
                    message=f"Route to non-existent screen: {to_screen}",
                    suggestion=f"Valid screens: {', '.join(sorted(screen_ids))}"
                ))
        
        # Check for orphaned screens (no way to reach them)
        if len(architecture.screens) > 1:
            reachable = {architecture.screens[0].id}  # Assume first screen is entry point
            
            # Build reachability graph
            for route in architecture.navigation.routes:
                from_screen = route.get('from')
                to_screen = route.get('to')
                if from_screen in reachable and to_screen:
                    reachable.add(to_screen)
            
            # Check screen navigation lists
            for screen in architecture.screens:
                if screen.id in reachable:
                    for nav_target in screen.navigation:
                        if nav_target in screen_ids:
                            reachable.add(nav_target)
            
            orphaned = screen_ids - reachable
            if orphaned:
                self.warnings.append(ValidationWarning(
                    level="warning",
                    component="navigation",
                    message=f"Unreachable screens: {', '.join(sorted(orphaned))}",
                    suggestion="Add navigation routes to make these screens accessible"
                ))
        
        # Check navigation depth
        if architecture.navigation.type == "stack":
            max_depth = self._calculate_max_navigation_depth(architecture)
            if max_depth > 5:
                self.warnings.append(ValidationWarning(
                    level="warning",
                    component="navigation",
                    message=f"Deep navigation stack (depth: {max_depth})",
                    suggestion="Consider using tab or drawer navigation for better UX"
                ))
    
    def _calculate_max_navigation_depth(self, architecture: ArchitectureDesign) -> int:
        """Calculate maximum navigation depth"""
        # Simple depth calculation based on navigation routes
        screen_ids = {s.id for s in architecture.screens}
        
        # Build adjacency list
        adjacency = {sid: [] for sid in screen_ids}
        for route in architecture.navigation.routes:
            from_screen = route.get('from')
            to_screen = route.get('to')
            if from_screen and to_screen and from_screen in adjacency:
                adjacency[from_screen].append(to_screen)
        
        # DFS to find max depth
        def dfs(screen_id: str, visited: set, depth: int) -> int:
            if screen_id in visited:
                return depth
            
            visited.add(screen_id)
            max_child_depth = depth
            
            for child in adjacency.get(screen_id, []):
                child_depth = dfs(child, visited.copy(), depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            
            return max_child_depth
        
        # Start from first screen
        if architecture.screens:
            return dfs(architecture.screens[0].id, set(), 1)
        
        return 0
    
    async def _validate_state_management(self, architecture: ArchitectureDesign) -> None:
        """Validate state management"""
        
        if len(architecture.state_management) == 0:
            self.warnings.append(ValidationWarning(
                level="info",
                component="state",
                message="No state management defined",
                suggestion="Consider if the app needs to maintain any state"
            ))
            return
        
        # Check for duplicate state names
        state_names = [s.name for s in architecture.state_management]
        duplicates = [name for name in state_names if state_names.count(name) > 1]
        
        if duplicates:
            self.warnings.append(ValidationWarning(
                level="error",
                component="state",
                message=f"Duplicate state variable names: {set(duplicates)}",
                suggestion="Use unique names for each state variable"
            ))
        
        # Check state scope consistency
        for state in architecture.state_management:
            if state.scope == "component" and state.type == "global-state":
                self.warnings.append(ValidationWarning(
                    level="error",
                    component="state",
                    message=f"Inconsistent state '{state.name}': component-scoped but global-state",
                    suggestion="Change scope to 'global' or type to 'local-state'"
                ))
            
            # Check for reasonable initial values
            if state.initial_value is None and state.type != "async-state":
                self.warnings.append(ValidationWarning(
                    level="warning",
                    component="state",
                    message=f"State '{state.name}' has no initial value",
                    suggestion="Provide a default initial value"
                ))
        
        # Warn about too many global state variables
        global_states = [s for s in architecture.state_management if s.scope == "global"]
        if len(global_states) > 10:
            self.warnings.append(ValidationWarning(
                level="warning",
                component="state",
                message=f"Large number of global state variables ({len(global_states)})",
                suggestion="Consider grouping related state or using component-level state"
            ))
    
    async def _validate_performance(self, architecture: ArchitectureDesign) -> None:
        """Validate performance considerations"""
        
        # Check total component count
        total_components = sum(len(s.components) for s in architecture.screens)
        
        if total_components > 100:
            self.warnings.append(ValidationWarning(
                level="warning",
                component="performance",
                message=f"High total component count ({total_components})",
                suggestion="Consider simplifying the UI or using pagination"
            ))
        
        # Check for screens with too many components
        for screen in architecture.screens:
            if len(screen.components) > 20:
                self.warnings.append(ValidationWarning(
                    level="warning",
                    component=f"screen:{screen.id}",
                    message=f"Screen '{screen.name}' has many components ({len(screen.components)})",
                    suggestion="Consider breaking into multiple screens or using tabs"
                ))
        
        # Check async state usage
        async_states = [s for s in architecture.state_management if s.type == "async-state"]
        if len(async_states) > 5:
            self.warnings.append(ValidationWarning(
                level="info",
                component="performance",
                message=f"Multiple async state variables ({len(async_states)})",
                suggestion="Ensure proper loading states and error handling"
            ))
    
    async def _validate_user_experience(self, architecture: ArchitectureDesign) -> None:
        """Validate user experience considerations"""
        
        # Check for input validation
        has_inputs = False
        for screen in architecture.screens:
            if any(c in screen.components for c in ['InputText', 'TextArea']):
                has_inputs = True
                break
        
        if has_inputs:
            # Check if there's state to store input values
            has_input_state = any(
                'input' in s.name.lower() or 'text' in s.name.lower() or 'value' in s.name.lower()
                for s in architecture.state_management
            )
            
            if not has_input_state:
                self.warnings.append(ValidationWarning(
                    level="info",
                    component="ux",
                    message="App has inputs but no obvious input state",
                    suggestion="Add state variables to store user input"
                ))
        
        # Check for feedback mechanisms
        has_progress = any('ProgressBar' in s.components or 'Spinner' in s.components for s in architecture.screens)
        
        if len(architecture.state_management) > 0 and not has_progress:
            has_async = any(s.type == "async-state" for s in architecture.state_management)
            if has_async:
                self.warnings.append(ValidationWarning(
                    level="info",
                    component="ux",
                    message="Async operations without progress indicators",
                    suggestion="Add Spinner or ProgressBar for better feedback"
                ))
        
        # Check for empty state handling
        has_lists = any('list' in s.name.lower() or 'items' in s.name.lower() for s in architecture.state_management)
        
        if has_lists:
            self.warnings.append(ValidationWarning(
                level="info",
                component="ux",
                message="App manages lists",
                suggestion="Consider adding empty state UI when lists are empty"
            ))


# Global validator instance
architecture_validator = ArchitectureValidator()


if __name__ == "__main__":
    # Test validator
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
        print("ARCHITECTURE VALIDATOR TEST")
        print("=" * 60)
        
        # Test 1: Valid architecture
        print("\n[TEST 1] Valid architecture")
        
        valid_arch = ArchitectureDesign(
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
        
        is_valid, warnings = await architecture_validator.validate(valid_arch)
        
        print(f"Valid: {is_valid}")
        print(f"Warnings: {len(warnings)}")
        for w in warnings:
            print(f"  {w}")
        
        # Test 2: Invalid architecture
        print("\n[TEST 2] Invalid architecture (missing components, bad navigation)")
        
        invalid_arch = ArchitectureDesign(
            app_type="multi-page",
            screens=[
                ScreenDefinition(
                    id="screen_1",
                    name="Home",
                    purpose="",
                    components=["InvalidComponent"],
                    navigation=["screen_999"]
                ),
                ScreenDefinition(
                    id="screen_1",  # Duplicate ID
                    name="Settings",
                    purpose="User settings",
                    components=[],
                    navigation=[]
                )
            ],
            navigation=NavigationStructure(
                type="stack",
                routes=[{"from": "screen_1", "to": "non_existent"}]
            ),
            state_management=[
                StateDefinition(
                    name="data",
                    type="global-state",
                    scope="component",  # Inconsistent
                    initial_value=None
                )
            ],
            data_flow=DataFlowDiagram(
                user_interactions=[],
                api_calls=[],
                local_storage=[]
            )
        )
        
        is_valid, warnings = await architecture_validator.validate(invalid_arch)
        
        print(f"Valid: {is_valid}")
        print(f"Warnings: {len(warnings)}")
        for w in warnings:
            print(f"  {w}")
        
        print("\n" + "=" * 60)
        print("✅ Validator test complete!")
        print("=" * 60 + "\n")
    
    asyncio.run(test())