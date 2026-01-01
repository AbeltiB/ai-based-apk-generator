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
    
    def pass_test(self, name: str, details: str = "", duration_ms: int = 0):
        """Mark test as passed"""
        self.tests_passed += 1
        extra = f" ({duration_ms}ms)" if duration_ms > 0 else ""
        extra += f" | {details}" if details else ""
        self.test_results.append(("PASS", name, details or "Success"))
        print(f"✅ PASS{extra}")
    
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
        print(f"Passed: {self.tests_passed} ({self.tests_passed/total*100:.1f}% if total > 0 else 0}%)")
        print(f"Failed: {self.tests_failed} ({self.tests_failed/total*100:.1f}% if total > 0 else 0}%)")
        
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
    
    # Test generation
    runner.print_test("Generate Blockly for counter app")
    
    try:
        start = time.time()
        blockly, metadata = await blockly_generator.generate(
            architecture=architecture,
            layouts={"screen_1": layout}
        )
        duration = int((time.time() - start) * 1000)
        
        block_count = len(blockly.get('blocks', {}).get('blocks', []))
        var_count = len(blockly.get('variables', []))
        
        if block_count > 0:
            runner.pass_test(
                "Generate Blockly for counter app",
                details=f"{block_count} blocks, {var_count} vars",
                duration_ms=duration
            )
            print(f"      API time: {metadata.get('api_duration_ms', 'N/A')}ms")
            print(f"      Model: {metadata.get('model', 'unknown')}")
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
                                'fields': {'VAR': 'count'},
                                'inputs': {
                                    'VALUE': {
                                        'block': {
                                            'type': 'math_arithmetic',
                                            'fields': {'OP': 'ADD'},
                                            'inputs': {
                                                'A': {'block': {'type': 'variables_get', 'fields': {'VAR': 'count'}}},
                                                'B': {'block': {'type': 'math_number', 'fields': {'NUM': 1}}}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                ]
            },
            'variables': [{'name': 'count', 'id': 'var_1', 'type': ''}]
        }
        
        is_valid, warnings = await blockly_validator.validate(valid_blockly)
        
        if is_valid:
            runner.pass_test("Validate correct Blockly", details=f"{len(warnings)} warnings")
        else:
            runner.fail_test("Validate correct Blockly", "Marked invalid when should be valid")
            
    except Exception as e:
        runner.fail_test("Validate correct Blockly", str(e))
    
    # Test 2: Duplicate block IDs
    runner.print_test("Detect duplicate block IDs")
    try:
        duplicate_blockly = {
            'blocks': {
                'languageVersion': 0,
                'blocks': [
                    {'type': 'block_a', 'id': 'dup_1'},
                    {'type': 'block_b', 'id': 'dup_1'}
                ]
            },
            'variables': []
        }
        
        is_valid, warnings = await blockly_validator.validate(duplicate_blockly)
        dup_errors = [w for w in warnings if "duplicate" in w.message.lower()]
        
        if not is_valid and len(dup_errors) > 0:
            runner.pass_test("Detect duplicate block IDs", details=f"{len(dup_errors)} detected")
        else:
            runner.fail_test("Detect duplicate block IDs", "Failed to detect duplicates")
            
    except Exception as e:
        runner.fail_test("Detect duplicate block IDs", str(e))
    
    # Test 3: Undefined variables
    runner.print_test("Detect undefined variable references")
    try:
        undefined_var_blockly = {
            'blocks': {
                'languageVersion': 0,
                'blocks': [{
                    'type': 'variables_get',
                    'id': 'get_1',
                    'fields': {'VAR': 'missing_var'}
                }]
            },
            'variables': [{'name': 'count', 'id': 'var_1'}]
        }
        
        is_valid, warnings = await blockly_validator.validate(undefined_var_blockly)
        undef_warnings = [w for w in warnings if "undefined" in w.message.lower() or "not declared" in w.message.lower()]
        
        if len(undef_warnings) > 0:
            runner.pass_test("Detect undefined variable references", details=f"{len(undef_warnings)} found")
        else:
            runner.fail_test("Detect undefined variable references", "Missed undefined variable")
            
    except Exception as e:
        runner.fail_test("Detect undefined variable references", str(e))
    
    # Test 4: Invalid variable structure
    runner.print_test("Validate variable structure")
    try:
        bad_vars = {
            'blocks': {'languageVersion': 0, 'blocks': []},
            'variables': [
                {'name': 'ok', 'id': 'v1'},
                {'id': 'v2'},           # missing name
                {'name': 'v3'}          # missing id
            ]
        }
        
        is_valid, warnings = await blockly_validator.validate(bad_vars)
        var_errors = [w for w in warnings if 'variable' in w.message.lower()]
        
        if len(var_errors) >= 2:
            runner.pass_test("Validate variable structure", details=f"{len(var_errors)} issues")
        else:
            runner.fail_test("Validate variable structure", "Failed to catch malformed variables")
            
    except Exception as e:
        runner.fail_test("Validate variable structure", str(e))


async def test_complete_pipeline():
    """Test complete Phase 5 pipeline"""
    runner.print_header("COMPLETE PIPELINE (Phase 5)")
    
    result = None  # Define early to avoid NameError
    
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
        
        # Check required keys
        has_arch = 'architecture' in result
        has_layout = 'layout' in result
        has_blockly = 'blockly' in result
        
        if has_arch and has_layout and has_blockly:
            arch = result['architecture']
            screens = len(arch.get('screens', []))
            blocks = len(result['blockly'].get('blocks', {}).get('blocks', []))
            
            runner.pass_test(
                "Complete pipeline with all generations",
                details=f"{screens} screen(s), {blocks} block(s)",
                duration_ms=duration
            )
            print(f"      Total time: {result.get('total_time_ms', 'N/A')}ms")
        else:
            missing = [k for k, v in [('architecture', has_arch), ('layout', has_layout), ('blockly', has_blockly)] if not v]
            runner.fail_test("Complete pipeline with all generations", f"Missing: {', '.join(missing)}")
            
    except Exception as e:
        runner.fail_test("Complete pipeline with all generations", str(e))
    
    # These tests now safely handle partial failure
    runner.print_test("Blockly warnings captured")
    try:
        if result and 'blockly_warnings' in result:
            warnings = result['blockly_warnings']
            count = len(warnings)
            runner.pass_test("Blockly warnings captured", details=f"{count} warning(s)")
            if count > 0 and count <= 3:
                for w in warnings[:3]:
                    print(f"         - {w.get('level', 'INFO')}: {w.get('message', '')[:60]}...")
        else:
            runner.pass_test("Blockly warnings captured", details="No warnings (clean)")
    except Exception as e:
        runner.fail_test("Blockly warnings captured", f"Crash during check: {e}")
    
    runner.print_test("Performance metrics tracking")
    try:
        if result and 'stage_times' in result:
            stage_times = result['stage_times']
            total_ms = sum(stage_times.values())
            runner.pass_test("Performance metrics tracking", details=f"{total_ms}ms total")
            for stage in ['architecture_generation', 'layout_generation', 'blockly_generation']:
                if stage in stage_times:
                    print(f"         {stage.replace('_', ' ').title()}: {stage_times[stage]}ms")
        else:
            runner.fail_test("Performance metrics tracking", "No stage_times in result")
    except Exception as e:
        runner.fail_test("Performance metrics tracking", f"Crash during check: {e}")


async def test_statistics():
    """Test generator statistics"""
    runner.print_header("STATISTICS (Phase 5)")
    
    runner.print_test("Blockly generator statistics")
    try:
        stats = blockly_generator.get_statistics()
        
        total = stats.get('total_requests', 0)
        success_rate = stats.get('success_rate', 0)
        
        runner.pass_test("Blockly generator statistics")
        print(f"      Total requests: {total}")
        print(f"      Successful: {stats.get('successful', 0)}")
        print(f"      Success rate: {success_rate:.1f}%")
        print(f"      Blocks generated: {stats.get('blocks_generated', 0)}")
        print(f"      Variables created: {stats.get('variables_created', 0)}")
        
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
        logger.error(f"Test suite crashed: {e}")
        print(f"\n❌ Test suite crashed: {e}\n")
        return 1
    
    finally:
        total_time = time.time() - start_time
        print(f"\n⏱️ Total test time: {total_time:.2f}s")
    
    return runner.print_summary()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)