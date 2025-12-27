"""
Comprehensive Phase 3 test script.

Tests Phase 3 components:
1. Architecture Generator (Claude-powered)
2. Architecture Validator
3. Error handling and retry logic
4. Complete pipeline with real architecture generation
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
from app.services.generation.architecture_generator import architecture_generator
from app.services.generation.architecture_validator import architecture_validator
from app.services.pipeline import default_pipeline


class Phase3TestRunner:
    """Test runner for Phase 3"""
    
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


runner = Phase3TestRunner()


async def test_architecture_generator():
    """Test Claude-powered architecture generation"""
    runner.print_header("ARCHITECTURE GENERATOR (Phase 3)")
    
    test_cases = [
        ("Create a simple counter app", "single-page", 1),
        ("Build a todo list with add and delete", "single-page", 1),
        ("Make a weather app with multiple cities", "multi-page", 2),
    ]
    
    for prompt, expected_type, expected_screens in test_cases:
        runner.print_test(f"Generate: '{prompt[:40]}...'")
        
        try:
            start = time.time()
            architecture, metadata = await architecture_generator.generate(prompt)
            duration = int((time.time() - start) * 1000)
            
            # Verify architecture
            if architecture.app_type == expected_type:
                runner.pass_test(f"Generate: '{prompt[:40]}...'", duration)
            else:
                runner.fail_test(
                    f"Generate: '{prompt[:40]}...'",
                    f"Expected {expected_type}, got {architecture.app_type}"
                )
            
            # Log details
            print(f"      Type: {architecture.app_type}")
            print(f"      Screens: {len(architecture.screens)}")
            print(f"      API time: {metadata['api_duration_ms']}ms")
            print(f"      Tokens: {metadata['tokens_used']}")
            
        except Exception as e:
            runner.fail_test(f"Generate: '{prompt[:40]}...'", str(e))


async def test_architecture_validator():
    """Test architecture validation"""
    runner.print_header("ARCHITECTURE VALIDATOR (Phase 3)")
    
    # Test 1: Valid architecture
    runner.print_test("Validate correct architecture")
    
    try:
        from app.models.schemas import (
            ArchitectureDesign,
            ScreenDefinition,
            NavigationStructure,
            StateDefinition,
            DataFlowDiagram
        )
        
        valid_arch = ArchitectureDesign(
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
        
        is_valid, warnings = await architecture_validator.validate(valid_arch)
        
        if is_valid:
            runner.pass_test("Validate correct architecture")
            print(f"      Warnings: {len(warnings)}")
        else:
            runner.fail_test("Validate correct architecture", "Should be valid")
            
    except Exception as e:
        runner.fail_test("Validate correct architecture", str(e))
    
    # Test 2: Invalid architecture
    runner.print_test("Detect invalid architecture")
    
    try:
        invalid_arch = ArchitectureDesign(
            app_type="single-page",
            screens=[
                ScreenDefinition(
                    id="screen_1",
                    name="Test",
                    purpose="",  # Empty purpose
                    components=["InvalidComponent"],  # Unsupported
                    navigation=["screen_999"]  # Non-existent
                )
            ],
            navigation=NavigationStructure(type="stack", routes=[]),
            state_management=[],
            data_flow=DataFlowDiagram(
                user_interactions=[],
                api_calls=[],
                local_storage=[]
            )
        )
        
        is_valid, warnings = await architecture_validator.validate(invalid_arch)
        
        if not is_valid:
            errors = [w for w in warnings if w.level == "error"]
            runner.pass_test("Detect invalid architecture")
            print(f"      Errors detected: {len(errors)}")
        else:
            runner.fail_test("Detect invalid architecture", "Should be invalid")
            
    except Exception as e:
        runner.fail_test("Detect invalid architecture", str(e))


async def test_error_handling():
    """Test error handling and retry logic"""
    runner.print_header("ERROR HANDLING (Phase 3)")
    
    # Test 1: JSON parsing
    runner.print_test("Handle malformed JSON")
    
    try:
        from app.services.generation.architecture_generator import ArchitectureGenerator
        
        gen = ArchitectureGenerator()
        
        # Test with markdown code blocks
        markdown_json = """```json
{
  "app_type": "single-page",
  "screens": []
}
```"""
        
        parsed = await gen._parse_architecture_json(markdown_json)
        
        if 'app_type' in parsed:
            runner.pass_test("Handle malformed JSON")
        else:
            runner.fail_test("Handle malformed JSON", "Parsing failed")
            
    except Exception as e:
        runner.fail_test("Handle malformed JSON", str(e))
    
    # Test 2: Auto-correction
    runner.print_test("Auto-correct JSON")
    
    try:
        gen = ArchitectureGenerator()
        
        # JSON with trailing comma
        bad_json = """{
  "app_type": "single-page",
  "screens": [],
}"""
        
        corrected = await gen._attempt_json_correction(bad_json)
        
        if corrected and 'app_type' in corrected:
            runner.pass_test("Auto-correct JSON")
        else:
            runner.fail_test("Auto-correct JSON", "Correction failed")
            
    except Exception as e:
        runner.fail_test("Auto-correct JSON", str(e))


async def test_complete_pipeline():
    """Test complete Phase 3 pipeline"""
    runner.print_header("COMPLETE PIPELINE (Phase 3)")
    
    # Test 1: Simple app
    runner.print_test("Pipeline with simple prompt")
    
    try:
        start = time.time()
        
        request = AIRequest(
            user_id="test_user_phase3",
            session_id="test_session_phase3",
            socket_id="test_socket_phase3",
            prompt="Create a simple counter app with + and - buttons"
        )
        
        result = await default_pipeline.execute(request)
        duration = int((time.time() - start) * 1000)
        
        # Verify architecture was generated
        if 'architecture' in result:
            arch = result['architecture']
            if arch.get('app_type') and len(arch.get('screens', [])) > 0:
                runner.pass_test("Pipeline with simple prompt", duration)
                print(f"      Architecture: {arch['app_type']}")
                print(f"      Screens: {len(arch['screens'])}")
            else:
                runner.fail_test("Pipeline with simple prompt", "Invalid architecture")
        else:
            runner.fail_test("Pipeline with simple prompt", "No architecture generated")
            
    except Exception as e:
        runner.fail_test("Pipeline with simple prompt", str(e))
    
    # Test 2: Complex app
    runner.print_test("Pipeline with complex prompt")
    
    try:
        start = time.time()
        
        request = AIRequest(
            user_id="test_user_phase3",
            session_id="test_session_phase3",
            socket_id="test_socket_phase3",
            prompt="Build a todo list app with input field, add button, list of todos, "
                   "delete button for each item, and mark complete functionality"
        )
        
        result = await default_pipeline.execute(request)
        duration = int((time.time() - start) * 1000)
        
        # Verify architecture
        if 'architecture' in result:
            arch = result['architecture']
            screens = arch.get('screens', [])
            state = arch.get('state_management', [])
            
            if len(screens) > 0 and len(state) > 0:
                runner.pass_test("Pipeline with complex prompt", duration)
                print(f"      Screens: {len(screens)}")
                print(f"      State variables: {len(state)}")
            else:
                runner.fail_test("Pipeline with complex prompt", "Incomplete architecture")
        else:
            runner.fail_test("Pipeline with complex prompt", "No architecture")
            
    except Exception as e:
        runner.fail_test("Pipeline with complex prompt", str(e))
    
    # Test 3: Verify warnings captured
    runner.print_test("Architecture warnings captured")
    
    try:
        if 'architecture_warnings' in result:
            warnings = result['architecture_warnings']
            runner.pass_test("Architecture warnings captured")
            print(f"      Warnings: {len(warnings)}")
            
            if warnings:
                for w in warnings[:3]:  # Show first 3
                    print(f"         - {w['level']}: {w['message'][:50]}...")
        else:
            runner.fail_test("Architecture warnings captured", "No warnings field")
            
    except Exception as e:
        runner.fail_test("Architecture warnings captured", str(e))


async def test_statistics():
    """Test generator statistics"""
    runner.print_header("STATISTICS (Phase 3)")
    
    runner.print_test("Generator statistics tracking")
    
    try:
        stats = architecture_generator.get_statistics()
        
        if 'total_requests' in stats and 'successful' in stats:
            runner.pass_test("Generator statistics tracking")
            print(f"      Total requests: {stats['total_requests']}")
            print(f"      Successful: {stats['successful']}")
            print(f"      Failed: {stats['failed']}")
            print(f"      Success rate: {stats['success_rate']:.1f}%")
            print(f"      Auto-corrections: {stats['corrections']}")
        else:
            runner.fail_test("Generator statistics tracking", "Missing stats")
            
    except Exception as e:
        runner.fail_test("Generator statistics tracking", str(e))


async def main():
    """Run all Phase 3 tests"""
    print("\n" + "=" * 60)
    print("  PHASE 3 COMPREHENSIVE TEST SUITE")
    print("  Architecture Generation with Claude")
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
        await test_architecture_generator()
        await test_architecture_validator()
        await test_error_handling()
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