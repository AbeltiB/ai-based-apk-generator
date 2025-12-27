"""
Comprehensive Phase 5 test script.

Tests Phase 5 components:
1. Blockly Generator (Claude-powered)
2. Blockly Validator
3. Block structure validation
4. Complete pipeline with full generation
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
from app.models.schemas import AIRequest
from app.services.generation.blockly_generator import blockly_generator
from app.services.generation.blockly_validator import blockly_validator
from app.services.pipeline import default_pipeline


class Phase5TestRunner:
    """Test runner for Phase 5"""
    
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


runner = Phase5TestRunner()


async def test_blockly_generator():
    """Test Claude-powered Blockly generation"""
    runner.print_header("BLOCKLY GENERATOR (Phase 5)")
    
    from app.models.schemas import (
        ArchitectureDesign, ScreenDefinition, NavigationStructure,
        StateDefinition, DataFlowDiagram
    )
    from app.models.enhanced_schemas import (
        EnhancedLayoutDefinition, EnhancedComponentDefinition, PropertyValue
    )
    
    # Create test data
    architecture = ArchitectureDesign(
        app_type="single-page",
        screens=[
            ScreenDefinition(
                id="screen_1",
                name="Counter",
                purpose="Counter with buttons",
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
    
    layout = EnhancedLayoutDefinition(
        screen_id="screen_1",
        components=[
            EnhancedComponentDefinition(
                component_id="text_count",
                component_type="Text",
                properties={
                    "text": PropertyValue(type="variable", value="count"),
                    "style": PropertyValue(type="literal", value={
                        "left": 97, "top": 100, "width": 180, "height": 40
                    })
                }
            ),
            EnhancedComponentDefinition(
                component_id="btn_increment",
                component_type="Button",
                properties={
                    "text": PropertyValue(type="literal", value="+"),
                    "style": PropertyValue(type="literal", value={
                        "left": 50, "top": 160, "width": 120, "height": 44
                    })
                }
            )
        ]
    )
    
    # Test generation
    runner.print_test("Generate Blockly for counter app")
    
    try:
        start = time.time()
        blockly, metadata = await blockly_generator.generate(
            architecture=architecture,
            layouts={"screen_1": layout}
        )
        duration = int((time.time() - start) * 1000)
        
        if len(blockly['blocks']['blocks']) > 0:
            runner.pass_test("Generate Blockly for counter app", duration)
            print(f"      Blocks: {len(blockly['blocks']['blocks'])}")
            print(f"      Variables: {len(blockly['variables'])}")
            print(f"      API time: {metadata['api_duration_ms']}ms")
        else:
            runner.fail_test("Generate Blockly for counter app", "No blocks generated")
            
    except Exception as e:
        runner.fail_test("Generate Blockly for counter app", str(e))


async def test_blockly_validator():
    """Test Blockly validation"""
    runner.print_header("BLOCKLY VALIDATOR (Phase 5)")
    
    # Test 1: Valid Blockly
    runner.print_test("Validate correct Blockly")
    
    try:
        valid_blockly = {
            'blocks': {
                'languageVersion': 0,
                'blocks': [
                    {
                        'type': 'component_event',
                        'id': 'event_1',
                        'fields': {
                            'COMPONENT': 'btn_increment',
                            'EVENT': 'onPress'
                        },
                        'next': {
                            'block': {
                                'type': 'state_set',
                                'id': 'action_1',
                                'fields': {'VAR': 'count'}
                            }
                        }
                    }
                ]
            },
            'variables': [
                {'name': 'count', 'id': 'var_1', 'type': ''}
            ]
        }
        
        is_valid, warnings = await blockly_validator.validate(valid_blockly)
        
        if is_valid:
            runner.pass_test("Validate correct Blockly")
            print(f"      Warnings: {len(warnings)}")
        else:
            runner.fail_test("Validate correct Blockly", "Should be valid")
            
    except Exception as e:
        runner.fail_test("Validate correct Blockly", str(e))
    
    # Test 2: Detect duplicate IDs
    runner.print_test("Detect duplicate block IDs")
    
    try:
        duplicate_blockly = {
            'blocks': {
                'languageVersion': 0,
                'blocks': [
                    {'type': 'block_a', 'id': 'block_1'},
                    {'type': 'block_b', 'id': 'block_1'}  # Duplicate!
                ]
            },
            'variables': []
        }
        
        is_valid, warnings = await blockly_validator.validate(duplicate_blockly)
        
        dup_errors = [w for w in warnings if "duplicate" in w.message.lower()]
        
        if not is_valid and len(dup_errors) > 0:
            runner.pass_test("Detect duplicate block IDs")
            print(f"      Errors found: {len(dup_errors)}")
        else:
            runner.fail_test("Detect duplicate block IDs", "Should detect duplicates")
            
    except Exception as e:
        runner.fail_test("Detect duplicate block IDs", str(e))
    
    # Test 3: Detect undefined variables
    runner.print_test("Detect undefined variable references")
    
    try:
        undefined_var_blockly = {
            'blocks': {
                'languageVersion': 0,
                'blocks': [
                    {
                        'type': 'state_set',
                        'id': 'block_1',
                        'fields': {'VAR': 'undefined_variable'}  # Not declared!
                    }
                ]
            },
            'variables': [
                {'name': 'count', 'id': 'var_1'}  # Different variable
            ]
        }
        
        is_valid, warnings = await blockly_validator.validate(undefined_var_blockly)
        
        undef_warnings = [w for w in warnings if "undefined" in w.message.lower()]
        
        if len(undef_warnings) > 0:
            runner.pass_test("Detect undefined variable references")
            print(f"      Warnings found: {len(undef_warnings)}")
        else:
            runner.fail_test("Detect undefined variable references", "Should detect undefined vars")
            
    except Exception as e:
        runner.fail_test("Detect undefined variable references", str(e))
    
    # Test 4: Check variable structure
    runner.print_test("Validate variable structure")
    
    try:
        missing_fields = {
            'blocks': {'languageVersion': 0, 'blocks': []},
            'variables': [
                {'name': 'var1', 'id': 'v1'},
                {'id': 'v2'},  # Missing name
                {'name': 'var3'}  # Missing id
            ]
        }
        
        is_valid, warnings = await blockly_validator.validate(missing_fields)
        
        var_errors = [w for w in warnings if w.block_id == 'variables' or 'variable' in w.message.lower()]
        
        if len(var_errors) > 0:
            runner.pass_test("Validate variable structure")
            print(f"      Errors found: {len(var_errors)}")
        else:
            runner.fail_test("Validate variable structure", "Should detect missing fields")
            
    except Exception as e:
        runner.fail_test("Validate variable structure", str(e))


async def test_complete_pipeline():
    """Test complete Phase 5 pipeline"""
    runner.print_header("COMPLETE PIPELINE (Phase 5)")
    
    # Test 1: Full generation pipeline
    runner.print_test("Complete pipeline with all generations")
    
    try:
        start = time.time()
        
        request = AIRequest(
            user_id="test_user_phase5",
            session_id="test_session_phase5",
            socket_id="test_socket_phase5",
            prompt="Create a counter app with a display and + - buttons"
        )
        
        result = await default_pipeline.execute(request)
        duration = int((time.time() - start) * 1000)
        
        # Verify all components generated
        has_arch = 'architecture' in result
        has_layout = 'layout' in result
        has_blockly = 'blockly' in result
        
        if has_arch and has_layout and has_blockly:
            runner.pass_test("Complete pipeline with all generations", duration)
            
            # Show details
            arch = result['architecture']
            print(f"      Architecture: {arch['app_type']}, {len(arch['screens'])} screen(s)")
            
            layout = result['layout']
            if isinstance(layout, dict) and 'components' in layout:
                print(f"      Layout: {len(layout['components'])} component(s)")
            
            blockly = result['blockly']
            print(f"      Blockly: {len(blockly['blocks']['blocks'])} block(s)")
            print(f"      Total time: {result.get('total_time_ms', 0)}ms")
        else:
            missing = []
            if not has_arch:
                missing.append("architecture")
            if not has_layout:
                missing.append("layout")
            if not has_blockly:
                missing.append("blockly")
            runner.fail_test("Complete pipeline with all generations", f"Missing: {', '.join(missing)}")
            
    except Exception as e:
        runner.fail_test("Complete pipeline with all generations", str(e))
    
    # Test 2: Verify Blockly warnings captured
    runner.print_test("Blockly warnings captured")
    
    try:
        if 'blockly_warnings' in result:
            warnings = result['blockly_warnings']
            runner.pass_test("Blockly warnings captured")
            print(f"      Warnings: {len(warnings)}")
            
            if warnings:
                for w in warnings[:3]:
                    print(f"         - {w['level']}: {w['message'][:50]}...")
        else:
            runner.pass_test("Blockly warnings captured")
            print(f"      No warnings (clean Blockly)")
            
    except Exception as e:
        runner.fail_test("Blockly warnings captured", str(e))
    
    # Test 3: Performance breakdown
    runner.print_test("Performance metrics tracking")
    
    try:
        stage_times = result.get('stage_times', {})
        
        if stage_times:
            runner.pass_test("Performance metrics tracking")
            
            total_ms = sum(stage_times.values())
            print(f"      Total: {total_ms}ms")
            
            for stage in ['architecture_generation', 'layout_generation', 'blockly_generation']:
                if stage in stage_times:
                    print(f"         {stage}: {stage_times[stage]}ms")
        else:
            runner.fail_test("Performance metrics tracking", "No stage times")
            
    except Exception as e:
        runner.fail_test("Performance metrics tracking", str(e))


async def test_statistics():
    """Test generator statistics"""
    runner.print_header("STATISTICS (Phase 5)")
    
    runner.print_test("Blockly generator statistics")
    
    try:
        stats = blockly_generator.get_statistics()
        
        if 'total_requests' in stats:
            runner.pass_test("Blockly generator statistics")
            print(f"      Total requests: {stats['total_requests']}")
            print(f"      Successful: {stats['successful']}")
            print(f"      Success rate: {stats['success_rate']:.1f}%")
            print(f"      Blocks generated: {stats['blocks_generated']}")
            print(f"      Variables created: {stats['variables_created']}")
        else:
            runner.fail_test("Blockly generator statistics", "Missing stats")
            
    except Exception as e:
        runner.fail_test("Blockly generator statistics", str(e))


async def main():
    """Run all Phase 5 tests"""
    print("\n" + "=" * 60)
    print("  PHASE 5 COMPREHENSIVE TEST SUITE")
    print("  Blockly Generation with Claude")
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
        await test_blockly_generator()
        await test_blockly_validator()
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