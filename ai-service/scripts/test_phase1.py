"""
Comprehensive Phase 1 test script.

Tests all Phase 1 components:
1. Database operations
2. Pipeline execution
3. Schema validation
4. End-to-end flow
"""
import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.core.database import db_manager
from app.core.messaging import queue_manager
from app.core.cache import cache_manager
from app.models.schemas import AIRequest
from app.models.enhanced_schemas import (
    EnhancedComponentDefinition,
    EnhancedLayoutDefinition,
    PropertyValue,
    IntentAnalysis
)
from app.services.pipeline import default_pipeline


class TestRunner:
    """Test runner for Phase 1 validation"""
    
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


runner = TestRunner()


async def test_database_operations():
    """Test database operations"""
    runner.print_header("DATABASE OPERATIONS")
    
    # Test 1: Connection
    runner.print_test("Database connection")
    try:
        await db_manager.connect()
        if db_manager.is_connected:
            runner.pass_test("Database connection")
        else:
            runner.fail_test("Database connection", "Not connected")
    except Exception as e:
        runner.fail_test("Database connection", str(e))
        return
    
    # Test 2: Save conversation
    runner.print_test("Save conversation")
    try:
        start = time.time()
        conv_id = await db_manager.save_conversation(
            user_id="test_user_phase1",
            session_id="test_session_phase1",
            messages=[
                {"role": "user", "content": "Test message"},
                {"role": "assistant", "content": "Test response"}
            ]
        )
        duration = int((time.time() - start) * 1000)
        
        if conv_id:
            runner.pass_test("Save conversation", duration)
        else:
            runner.fail_test("Save conversation", "No ID returned")
    except Exception as e:
        runner.fail_test("Save conversation", str(e))
    
    # Test 3: Retrieve conversation
    runner.print_test("Retrieve conversation history")
    try:
        start = time.time()
        history = await db_manager.get_conversation_history(
            user_id="test_user_phase1",
            session_id="test_session_phase1",
            limit=5
        )
        duration = int((time.time() - start) * 1000)
        
        if len(history) > 0:
            runner.pass_test("Retrieve conversation history", duration)
        else:
            runner.fail_test("Retrieve conversation history", "No history found")
    except Exception as e:
        runner.fail_test("Retrieve conversation history", str(e))
    
    # Test 4: Save project
    runner.print_test("Save project")
    try:
        start = time.time()
        project_id = await db_manager.save_project(
            user_id="test_user_phase1",
            project_name="Test Project Phase 1",
            architecture={"app_type": "single-page"},
            layout={"screen_id": "screen_1"},
            blockly={"blocks": {"languageVersion": 0, "blocks": []}}
        )
        duration = int((time.time() - start) * 1000)
        
        if project_id:
            runner.pass_test("Save project", duration)
        else:
            runner.fail_test("Save project", "No ID returned")
    except Exception as e:
        runner.fail_test("Save project", str(e))
    
    # Test 5: User preferences
    runner.print_test("Save/retrieve user preferences")
    try:
        # Save
        saved = await db_manager.save_user_preferences(
            user_id="test_user_phase1",
            preferences={"theme": "dark", "component_style": "minimal"}
        )
        
        # Retrieve
        prefs = await db_manager.get_user_preferences("test_user_phase1")
        
        if saved and prefs and prefs.get("theme") == "dark":
            runner.pass_test("Save/retrieve user preferences")
        else:
            runner.fail_test("Save/retrieve user preferences", "Mismatch")
    except Exception as e:
        runner.fail_test("Save/retrieve user preferences", str(e))
    
    # Test 6: Request metrics
    runner.print_test("Save request metrics")
    try:
        await db_manager.save_request_metric(
            task_id="test_task_phase1",
            user_id="test_user_phase1",
            stage="validation",
            duration_ms=150,
            success=True,
            error_message=None
        )
        runner.pass_test("Save request metrics")
    except Exception as e:
        runner.fail_test("Save request metrics", str(e))


async def test_schema_validation():
    """Test enhanced schema validation"""
    runner.print_header("SCHEMA VALIDATION")
    
    # Test 1: Component definition
    runner.print_test("Component definition validation")
    try:
        comp = EnhancedComponentDefinition(
            component_id="btn_test",
            component_type="Button",
            properties={
                "text": PropertyValue(type="literal", value="Test Button"),
                "size": PropertyValue(type="literal", value="medium"),
                "color": PropertyValue(type="literal", value="#FFFFFF"),
                "backgroundColor": PropertyValue(type="literal", value="#007AFF"),
                "style": PropertyValue(type="literal", value={
                    "left": 50,
                    "top": 100,
                    "width": 120,
                    "height": 44
                })
            }
        )
        runner.pass_test("Component definition validation")
    except Exception as e:
        runner.fail_test("Component definition validation", str(e))
    
    # Test 2: Layout validation
    runner.print_test("Layout definition validation")
    try:
        layout = EnhancedLayoutDefinition(
            screen_id="screen_test",
            components=[comp]
        )
        runner.pass_test("Layout definition validation")
    except Exception as e:
        runner.fail_test("Layout definition validation", str(e))
    
    # Test 3: Collision detection
    runner.print_test("Collision detection")
    try:
        # Create overlapping components
        comp1 = EnhancedComponentDefinition(
            component_id="comp1",
            component_type="Button",
            properties={
                "text": PropertyValue(type="literal", value="Button 1"),
                "style": PropertyValue(type="literal", value={
                    "left": 0, "top": 0, "width": 100, "height": 50
                })
            }
        )
        
        comp2 = EnhancedComponentDefinition(
            component_id="comp2",
            component_type="Button",
            properties={
                "text": PropertyValue(type="literal", value="Button 2"),
                "style": PropertyValue(type="literal", value={
                    "left": 50, "top": 25, "width": 100, "height": 50
                })
            }
        )
        
        # This should raise a collision error
        try:
            layout = EnhancedLayoutDefinition(
                screen_id="collision_test",
                components=[comp1, comp2]
            )
            runner.fail_test("Collision detection", "Collision not detected")
        except ValueError as collision_error:
            if "collision" in str(collision_error).lower():
                runner.pass_test("Collision detection")
            else:
                runner.fail_test("Collision detection", f"Wrong error: {collision_error}")
    except Exception as e:
        runner.fail_test("Collision detection", str(e))
    
    # Test 4: Intent analysis schema
    runner.print_test("Intent analysis schema")
    try:
        intent = IntentAnalysis(
            intent_type="new_app",
            complexity="medium",
            confidence=0.85,
            extracted_entities={"components": ["Button", "InputText"]},
            requires_context=False,
            multi_turn=False
        )
        runner.pass_test("Intent analysis schema")
    except Exception as e:
        runner.fail_test("Intent analysis schema", str(e))


async def test_pipeline_execution():
    """Test pipeline execution"""
    runner.print_header("PIPELINE EXECUTION")
    
    # Connect dependencies
    await queue_manager.connect()
    await cache_manager.connect()
    
    # Test 1: Simple request
    runner.print_test("Pipeline with simple request")
    try:
        start = time.time()
        
        request = AIRequest(
            user_id="test_user_phase1",
            session_id="test_session_phase1",
            socket_id="test_socket_phase1",
            prompt="Create a simple button that says hello"
        )
        
        result = await default_pipeline.execute(request)
        duration = int((time.time() - start) * 1000)
        
        if 'architecture' in result and 'layout' in result and 'blockly' in result:
            runner.pass_test("Pipeline with simple request", duration)
        else:
            runner.fail_test("Pipeline with simple request", "Missing output components")
    except Exception as e:
        runner.fail_test("Pipeline with simple request", str(e))
    
    # Test 2: Complex request
    runner.print_test("Pipeline with complex request")
    try:
        start = time.time()
        
        request = AIRequest(
            user_id="test_user_phase1",
            session_id="test_session_phase1",
            socket_id="test_socket_phase1",
            prompt="Create a todo list app with add, delete, and complete features, "
                   "including input field, buttons, and list display"
        )
        
        result = await default_pipeline.execute(request)
        duration = int((time.time() - start) * 1000)
        
        if result.get('intent', {}).get('complexity') == "complex":
            runner.pass_test("Pipeline with complex request", duration)
        else:
            runner.fail_test("Pipeline with complex request", "Complexity not detected")
    except Exception as e:
        runner.fail_test("Pipeline with complex request", str(e))
    
    # Test 3: Error handling
    runner.print_test("Pipeline error handling")
    try:
        # Request with invalid prompt (too short)
        request = AIRequest(
            user_id="test_user_phase1",
            session_id="test_session_phase1",
            socket_id="test_socket_phase1",
            prompt="Hi"
        )
        
        try:
            result = await default_pipeline.execute(request)
            runner.fail_test("Pipeline error handling", "Validation should have failed")
        except ValueError as validation_error:
            if "at least 10 characters" in str(validation_error):
                runner.pass_test("Pipeline error handling")
            else:
                runner.fail_test("Pipeline error handling", f"Wrong error: {validation_error}")
    except Exception as e:
        runner.fail_test("Pipeline error handling", str(e))
    
    # Disconnect
    await queue_manager.disconnect()
    await cache_manager.disconnect()


async def test_infrastructure():
    """Test infrastructure connections"""
    runner.print_header("INFRASTRUCTURE")
    
    # Test 1: RabbitMQ
    runner.print_test("RabbitMQ connection")
    try:
        if not queue_manager.is_connected:
            await queue_manager.connect()
        
        if queue_manager.is_connected:
            runner.pass_test("RabbitMQ connection")
        else:
            runner.fail_test("RabbitMQ connection", "Not connected")
    except Exception as e:
        runner.fail_test("RabbitMQ connection", str(e))
    
    # Test 2: Redis
    runner.print_test("Redis connection")
    try:
        if not cache_manager._connected:
            await cache_manager.connect()
        
        if cache_manager._connected:
            runner.pass_test("Redis connection")
        else:
            runner.fail_test("Redis connection", "Not connected")
    except Exception as e:
        runner.fail_test("Redis connection", str(e))
    
    # Test 3: PostgreSQL
    runner.print_test("PostgreSQL connection")
    try:
        if not db_manager.is_connected:
            await db_manager.connect()
        
        if db_manager.is_connected:
            runner.pass_test("PostgreSQL connection")
        else:
            runner.fail_test("PostgreSQL connection", "Not connected")
    except Exception as e:
        runner.fail_test("PostgreSQL connection", str(e))


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  PHASE 1 COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print(f"  Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Run test suites
        await test_infrastructure()
        await test_database_operations()
        await test_schema_validation()
        await test_pipeline_execution()
        
        # Cleanup
        await db_manager.disconnect()
        
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