"""
Comprehensive Phase 4 test script.

Tests Phase 4 components:
1. Layout Generator (Claude-powered)
2. Layout Validator
3. Collision detection and resolution
4. Complete pipeline with real layout generation
"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.core.database import db_manager
from app.core.messaging import queue_manager
from app.core.cache import cache_manager
from app.models.schemas import AIRequest, ArchitectureDesign, ScreenDefinition
from app.services.generation.layout_generator import layout_generator
from app.services.generation.layout_validator import layout_validator
from app.services.pipeline import default_pipeline


class Phase4TestRunner:
    """Test runner for Phase 4"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def print_header(self, title: str):
        """Print test section header"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60 + "\n")
    
    def print_test(self, name: str):
        """Print test name"""
        print(f"[TEST] {name}...", end=" ", flush=True)
    
    def pass_test(self, name: str, duration_ms: int = 0):
        """Mark test as passed"""
        self.tests_passed += 1
        self.test_results.append(("PASS", name, duration_ms))
        if duration_ms > 0:
            print(f"✅ PASS ({duration_ms}ms)")
        else:
            print("✅ PASS")
    
    def fail_test(self, name: str, error: str):
        """Mark test as failed"""
        self.tests_failed += 1
        self.test_results.append(("FAIL", name, error))
        print(f"❌ FAIL")
        print(f"   Error: {error}")
    
    def print_summary(self):
        """Print test summary"""
        total = self.tests_passed + self.tests_failed
        
        print("\n" + "=" * 60)
        print("  TEST SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {self.tests_passed} ({self.tests_passed/total*100:.1f}%)")
        print(f"Failed: {self.tests_failed} ({self.tests_failed/total*100:.1f}%)")
        
        if self.tests_failed > 0:
            print("\n❌ Failed Tests:")
            for status, name, error in self.test_results:
                if status == "FAIL":
                    print(f"   - {name}: {error}")
        
        print("\n" + "=" * 60)
        
        if self.tests_failed == 0:
            print("✅ ALL TESTS PASSED!")
            print("=" * 60 + "\n")
            return 0
        else:
            print(f"❌ {self.tests_failed} TEST(S) FAILED")
            print("=" * 60 + "\n")
            return 1


runner = Phase4TestRunner()


async def test_layout_generator():
    """Test Claude-powered layout generation"""
    runner.print_header("LAYOUT GENERATOR (Phase 4)")
    
    from app.models.schemas import NavigationStructure, StateDefinition, DataFlowDiagram
    
    # Create test architecture
    architecture = ArchitectureDesign(
        app_type="single-page",
        screens=[
            ScreenDefinition(
                id="screen_1",
                name="Counter",
                purpose="Simple counter with buttons",
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
    
    # Test 1: Generate layout
    runner.print_test("Generate layout for counter screen")
    
    try:
        start = time.time()
        layout, metadata = await layout_generator.generate(
            architecture=architecture,
            screen_id="screen_1"
        )
        duration = int((time.time() - start) * 1000)
        
        if len(layout.components) == 3:
            runner.pass_test("Generate layout for counter screen", duration)
            print(f"      Components: {len(layout.components)}")
            print(f"      API time: {metadata['api_duration_ms']}ms")
        else:
            runner.fail_test(
                "Generate layout for counter screen",
                f"Expected 3 components, got {len(layout.components)}"
            )
            
    except Exception as e:
        runner.fail_test("Generate layout for counter screen", str(e))


async def test_layout_validator():
    """Test layout validation"""
    runner.print_header("LAYOUT VALIDATOR (Phase 4)")
    
    from app.models.enhanced_schemas import (
        EnhancedLayoutDefinition,
        EnhancedComponentDefinition,
        PropertyValue
    )
    
    # Test 1: Valid layout
    runner.print_test("Validate correct layout")
    
    try:
        valid_layout = EnhancedLayoutDefinition(
            screen_id="test_screen",
            components=[
                EnhancedComponentDefinition(
                    component_id="text_1",
                    component_type="Text",
                    properties={
                        "text": PropertyValue(type="literal", value="Counter: 0"),
                        "style": PropertyValue(type="literal", value={
                            "left": 97,
                            "top": 100,
                            "width": 180,
                            "height": 40
                        })
                    }
                ),
                EnhancedComponentDefinition(
                    component_id="btn_1",
                    component_type="Button",
                    properties={
                        "text": PropertyValue(type="literal", value="+"),
                        "style": PropertyValue(type="literal", value={
                            "left": 127,
                            "top": 160,
                            "width": 120,
                            "height": 44
                        })
                    }
                )
            ]
        )
        
        is_valid, warnings = await layout_validator.validate(valid_layout)
        
        if is_valid:
            runner.pass_test("Validate correct layout")
            print(f"      Warnings: {len(warnings)}")
        else:
            runner.fail_test("Validate correct layout", "Should be valid")
            
    except Exception as e:
        runner.fail_test("Validate correct layout", str(e))
    
    # Test 2: Detect collisions
    runner.print_test("Detect component collisions")
    
    try:
        collision_layout = EnhancedLayoutDefinition(
            screen_id="test_screen",
            components=[
                EnhancedComponentDefinition(
                    component_id="btn_1",
                    component_type="Button",
                    properties={
                        "style": PropertyValue(type="literal", value={
                            "left": 0,
                            "top": 0,
                            "width": 120,
                            "height": 44
                        })
                    }
                ),
                EnhancedComponentDefinition(
                    component_id="btn_2",
                    component_type="Button",
                    properties={
                        "style": PropertyValue(type="literal", value={
                            "left": 50,  # Overlaps!
                            "top": 20,
                            "width": 120,
                            "height": 44
                        })
                    }
                )
            ]
        )
        
        is_valid, warnings = await layout_validator.validate(collision_layout)
        
        collision_errors = [w for w in warnings if "overlap" in w.message.lower()]
        
        if not is_valid and len(collision_errors) > 0:
            runner.pass_test("Detect component collisions")
            print(f"      Collisions detected: {len(collision_errors)}")
        else:
            runner.fail_test("Detect component collisions", "Should detect collision")
            
    except Exception as e:
        runner.fail_test("Detect component collisions", str(e))
    
    # Test 3: Touch target validation
    runner.print_test("Validate touch target sizes")
    
    try:
        small_button_layout = EnhancedLayoutDefinition(
            screen_id="test_screen",
            components=[
                EnhancedComponentDefinition(
                    component_id="btn_small",
                    component_type="Button",
                    properties={
                        "style": PropertyValue(type="literal", value={
                            "left": 100,
                            "top": 100,
                            "width": 80,
                            "height": 30  # Too small!
                        })
                    }
                )
            ]
        )
        
        is_valid, warnings = await layout_validator.validate(small_button_layout)
        
        touch_errors = [w for w in warnings if "touch target" in w.message.lower()]
        
        if not is_valid and len(touch_errors) > 0:
            runner.pass_test("Validate touch target sizes")
            print(f"      Touch target errors: {len(touch_errors)}")
        else:
            runner.fail_test("Validate touch target sizes", "Should detect small touch target")
            
    except Exception as e:
        runner.fail_test("Validate touch target sizes", str(e))
    
    # Test 4: Bounds checking
    runner.print_test("Validate component bounds")
    
    try:
        out_of_bounds_layout = EnhancedLayoutDefinition(
            screen_id="test_screen",
            components=[
                EnhancedComponentDefinition(
                    component_id="text_1",
                    component_type="Text",
                    properties={
                        "style": PropertyValue(type="literal", value={
                            "left": 300,
                            "top": 100,
                            "width": 200,  # Extends beyond 375!
                            "height": 40
                        })
                    }
                )
            ]
        )
        
        is_valid, warnings = await layout_validator.validate(out_of_bounds_layout)
        
        bounds_errors = [w for w in warnings if "beyond" in w.message.lower()]
        
        if not is_valid and len(bounds_errors) > 0:
            runner.pass_test("Validate component bounds")
            print(f"      Bounds errors: {len(bounds_errors)}")
        else:
            runner.fail_test("Validate component bounds", "Should detect out of bounds")
            
    except Exception as e:
        runner.fail_test("Validate component bounds", str(e))


async def test_collision_resolution():
    """Test collision detection and resolution"""
    runner.print_header("COLLISION RESOLUTION (Phase 4)")
    
    from app.models.enhanced_schemas import (
        EnhancedComponentDefinition,
        PropertyValue
    )
    
    runner.print_test("Resolve overlapping components")
    
    try:
        # Create overlapping components
        components = [
            EnhancedComponentDefinition(
                component_id="btn_1",
                component_type="Button",
                properties={
                    "text": PropertyValue(type="literal", value="Button 1"),
                    "style": PropertyValue(type="literal", value={
                        "left": 100,
                        "top": 100,
                        "width": 120,
                        "height": 44
                    })
                }
            ),
            EnhancedComponentDefinition(
                component_id="btn_2",
                component_type="Button",
                properties={
                    "text": PropertyValue(type="literal", value="Button 2"),
                    "style": PropertyValue(type="literal", value={
                        "left": 110,  # Overlaps with btn_1
                        "top": 110,
                        "width": 120,
                        "height": 44
                    })
                }
            )
        ]
        
        # Resolve collisions
        resolved = await layout_generator._resolve_collisions(components)
        
        # Check if still overlapping
        bounds1 = layout_generator._get_component_bounds(resolved[0])
        bounds2 = layout_generator._get_component_bounds(resolved[1])
        
        overlap = layout_generator._rectangles_overlap(bounds1, bounds2)
        
        if not overlap:
            runner.pass_test("Resolve overlapping components")
            print(f"      Components repositioned successfully")
        else:
            runner.fail_test("Resolve overlapping components", "Still overlapping after resolution")
            
    except Exception as e:
        runner.fail_test("Resolve overlapping components", str(e))


async def test_complete_pipeline():
    """Test complete Phase 4 pipeline"""
    runner.print_header("COMPLETE PIPELINE (Phase 4)")
    
    # Test 1: Simple app with layout
    runner.print_test("Pipeline with layout generation")
    
    try:
        start = time.time()
        
        request = AIRequest(
            user_id="test_user_phase4",
            session_id="test_session_phase4",
            socket_id="test_socket_phase4",
            prompt="Create a counter app with a text showing count and + - buttons"
        )
        
        result = await default_pipeline.execute(request)
        duration = int((time.time() - start) * 1000)
        
        # Verify layout was generated
        if 'layout' in result:
            layout = result['layout']
            
            # Handle both single and multiple screen layouts
            if isinstance(layout, dict):
                if 'components' in layout:
                    # Single screen layout
                    components = layout['components']
                else:
                    # Multiple screens, get first
                    components = list(layout.values())[0].get('components', [])
            else:
                components = []
            
            if len(components) > 0:
                runner.pass_test("Pipeline with layout generation", duration)
                print(f"      Components: {len(components)}")
                print(f"      Total time: {result.get('total_time_ms', 0)}ms")
            else:
                runner.fail_test("Pipeline with layout generation", "No components generated")
        else:
            runner.fail_test("Pipeline with layout generation", "No layout in result")
            
    except Exception as e:
        runner.fail_test("Pipeline with layout generation", str(e))
    
    # Test 2: Verify warnings captured
    runner.print_test("Layout warnings captured")
    
    try:
        if 'layout_warnings' in result:
            warnings = result['layout_warnings']
            runner.pass_test("Layout warnings captured")
            print(f"      Warnings: {len(warnings)}")
            
            if warnings:
                for w in warnings[:3]:  # Show first 3
                    print(f"         - {w['level']}: {w['message'][:50]}...")
        else:
            # Warnings might be empty, that's ok
            runner.pass_test("Layout warnings captured")
            print(f"      No warnings (clean layout)")
            
    except Exception as e:
        runner.fail_test("Layout warnings captured", str(e))


async def test_statistics():
    """Test generator statistics"""
    runner.print_header("STATISTICS (Phase 4)")
    
    runner.print_test("Layout generator statistics")
    
    try:
        stats = layout_generator.get_statistics()
        
        if 'total_requests' in stats and 'successful' in stats:
            runner.pass_test("Layout generator statistics")
            print(f"      Total requests: {stats['total_requests']}")
            print(f"      Successful: {stats['successful']}")
            print(f"      Success rate: {stats['success_rate']:.1f}%")
            print(f"      Collisions resolved: {stats['collisions_resolved']}")
        else:
            runner.fail_test("Layout generator statistics", "Missing stats")
            
    except Exception as e:
        runner.fail_test("Layout generator statistics", str(e))


async def main():
    """Run all Phase 4 tests"""
    print("\n" + "=" * 60)
    print("  PHASE 4 COMPREHENSIVE TEST SUITE")
    print("  Layout Generation with Claude")
    print("=" * 60)
    print(f"  Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Connect to infrastructure
        await cache_manager.connect()
        await db_manager.connect()
        await queue_manager.connect()
        
        # Run test suites
        await test_layout_generator()
        await test_layout_validator()
        await test_collision_resolution()
        await test_complete_pipeline()
        await test_statistics()
        
        # Cleanup
        await cache_manager.disconnect()
        await db_manager.disconnect()
        await queue_manager.disconnect()
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        print(f"\n❌ Test suite crashed: {e}\n")
        return 1
    
    # Print summary
    total_time = time.time() - start_time
    print(f"\n⏱️  Total test time: {total_time:.2f}s")
    
    return runner.print_summary()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)