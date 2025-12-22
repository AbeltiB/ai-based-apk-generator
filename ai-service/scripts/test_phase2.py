"""
Comprehensive Phase 2 test script.

Tests all Phase 2 components:
1. Intent Analyzer (Claude-powered)
2. Context Builder (Enhanced)
3. Semantic Cache
4. Rate Limiter
5. Complete Pipeline
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
from app.services.analysis.intent_analyzer import intent_analyzer
from app.services.analysis.context_builder import context_builder
from app.services.generation.cache_manager import semantic_cache
from app.utils.rate_limiter import rate_limiter
from app.services.pipeline import default_pipeline


class Phase2TestRunner:
    """Test runner for Phase 2"""
    
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


runner = Phase2TestRunner()


async def test_intent_analyzer():
    """Test Claude-powered intent analysis"""
    runner.print_header("INTENT ANALYZER (Claude-Powered)")
    
    test_cases = [
        ("Create a simple counter app", "new_app", "simple"),
        ("Add a delete button to each todo item", "extend_app", "simple"),
        ("Build a complete e-commerce app with cart and checkout", "new_app", "complex"),
        ("Change the button color to blue", "modify_app", "simple")
    ]
    
    for prompt, expected_intent, expected_complexity in test_cases:
        runner.print_test(f"Analyze: '{prompt[:40]}...'")
        
        try:
            start = time.time()
            intent = await intent_analyzer.analyze(prompt)
            duration = int((time.time() - start) * 1000)
            
            if intent.intent_type == expected_intent and intent.complexity == expected_complexity:
                runner.pass_test(f"Analyze: '{prompt[:40]}...'", duration)
            else:
                runner.fail_test(
                    f"Analyze: '{prompt[:40]}...'",
                    f"Expected {expected_intent}/{expected_complexity}, got {intent.intent_type}/{intent.complexity}"
                )
        except Exception as e:
            runner.fail_test(f"Analyze: '{prompt[:40]}...'", str(e))


async def test_context_builder():
    """Test enhanced context builder"""
    runner.print_header("CONTEXT BUILDER (Enhanced)")
    
    # Save test data first
    await db_manager.save_conversation(
        user_id="test_user_phase2_ctx",
        session_id="test_session_phase2_ctx",
        messages=[
            {"role": "user", "content": "Previous message 1"},
            {"role": "assistant", "content": "Response 1"}
        ]
    )
    
    await db_manager.save_user_preferences(
        user_id="test_user_phase2_ctx",
        preferences={"theme": "dark", "component_style": "minimal"}
    )
    
    # Test 1: Build context
    runner.print_test("Build enriched context")
    
    try:
        from app.models.enhanced_schemas import IntentAnalysis
        
        intent = IntentAnalysis(
            intent_type="new_app",
            complexity="medium",
            confidence=0.9,
            extracted_entities={"components": ["Button"]},
            requires_context=False,
            multi_turn=False
        )
        
        start = time.time()
        context = await context_builder.build_context(
            user_id="test_user_phase2_ctx",
            session_id="test_session_phase2_ctx",
            prompt="Create a todo app",
            intent=intent,
            original_request={"prompt": "Create a todo app"}
        )
        duration = int((time.time() - start) * 1000)
        
        if len(context.conversation_history) > 0 and len(context.user_preferences) > 0:
            runner.pass_test("Build enriched context", duration)
        else:
            runner.fail_test("Build enriched context", "Missing history or preferences")
    except Exception as e:
        runner.fail_test("Build enriched context", str(e))
    
    # Test 2: Format for prompt
    runner.print_test("Format context for prompt")
    
    try:
        formatted = context_builder.format_context_for_prompt(context)
        
        if len(formatted) > 0 and "Intent:" in formatted:
            runner.pass_test("Format context for prompt")
        else:
            runner.fail_test("Format context for prompt", "Invalid format")
    except Exception as e:
        runner.fail_test("Format context for prompt", str(e))


async def test_semantic_cache():
    """Test semantic cache"""
    runner.print_header("SEMANTIC CACHE")
    
    # Test 1: Cache and retrieve
    runner.print_test("Cache and retrieve exact match")
    
    try:
        test_result = {
            'architecture': {'app_type': 'single-page'},
            'layout': {},
            'blockly': {}
        }
        
        # Cache
        cached = await semantic_cache.cache_result(
            prompt="Create a simple counter app",
            user_id="test_user_cache",
            result=test_result
        )
        
        # Retrieve
        retrieved = await semantic_cache.get_cached_result(
            prompt="Create a simple counter app",
            user_id="test_user_cache"
        )
        
        if cached and retrieved:
            runner.pass_test("Cache and retrieve exact match")
        else:
            runner.fail_test("Cache and retrieve exact match", "Cache or retrieval failed")
    except Exception as e:
        runner.fail_test("Cache and retrieve exact match", str(e))
    
    # Test 2: Cache miss
    runner.print_test("Cache miss detection")
    
    try:
        no_result = await semantic_cache.get_cached_result(
            prompt="Completely different prompt",
            user_id="test_user_cache"
        )
        
        if no_result is None:
            runner.pass_test("Cache miss detection")
        else:
            runner.fail_test("Cache miss detection", "Got result when shouldn't")
    except Exception as e:
        runner.fail_test("Cache miss detection", str(e))
    
    # Test 3: Get stats
    runner.print_test("Cache statistics")
    
    try:
        stats = await semantic_cache.get_cache_stats()
        
        if 'hits' in stats and 'misses' in stats:
            runner.pass_test("Cache statistics")
        else:
            runner.fail_test("Cache statistics", "Missing stats")
    except Exception as e:
        runner.fail_test("Cache statistics", str(e))


async def test_rate_limiter():
    """Test rate limiter"""
    runner.print_header("RATE LIMITER")
    
    # Reset for clean test
    await rate_limiter.reset_rate_limit("test_user_rate")
    
    # Test 1: Normal requests
    runner.print_test("Normal requests (within limit)")
    
    try:
        allowed_count = 0
        
        for i in range(5):
            allowed, info = await rate_limiter.check_rate_limit(
                user_id="test_user_rate",
                limit=10
            )
            
            if allowed:
                allowed_count += 1
        
        if allowed_count == 5:
            runner.pass_test("Normal requests (within limit)")
        else:
            runner.fail_test("Normal requests (within limit)", f"Only {allowed_count}/5 allowed")
    except Exception as e:
        runner.fail_test("Normal requests (within limit)", str(e))
    
    # Test 2: Exceed limit
    runner.print_test("Rate limit enforcement")
    
    try:
        # Make requests until limit exceeded
        blocked = False
        
        for i in range(10):
            allowed, info = await rate_limiter.check_rate_limit(
                user_id="test_user_rate",
                limit=10
            )
            
            if not allowed:
                blocked = True
                break
        
        if blocked:
            runner.pass_test("Rate limit enforcement")
        else:
            runner.fail_test("Rate limit enforcement", "Limit not enforced")
    except Exception as e:
        runner.fail_test("Rate limit enforcement", str(e))
    
    # Test 3: Reset
    runner.print_test("Rate limit reset")
    
    try:
        reset = await rate_limiter.reset_rate_limit("test_user_rate")
        info = await rate_limiter.get_rate_limit_info("test_user_rate")
        
        if reset and info.get('count', 1) == 0:
            runner.pass_test("Rate limit reset")
        else:
            runner.fail_test("Rate limit reset", "Reset failed")
    except Exception as e:
        runner.fail_test("Rate limit reset", str(e))


async def test_complete_pipeline():
    """Test complete Phase 2 pipeline"""
    runner.print_header("COMPLETE PIPELINE (Phase 2)")
    
    # Test 1: First request (no cache)
    runner.print_test("Pipeline execution (no cache)")
    
    try:
        start = time.time()
        
        request = AIRequest(
            user_id="test_user_pipeline_phase2",
            session_id="test_session_pipeline_phase2",
            socket_id="test_socket_pipeline_phase2",
            prompt="Create a simple todo list with add and delete features"
        )
        
        result = await default_pipeline.execute(request)
        duration = int((time.time() - start) * 1000)
        
        if 'architecture' in result and 'intent' in result:
            runner.pass_test("Pipeline execution (no cache)", duration)
        else:
            runner.fail_test("Pipeline execution (no cache)", "Missing outputs")
    except Exception as e:
        runner.fail_test("Pipeline execution (no cache)", str(e))
    
    # Test 2: Same request (should hit cache)
    runner.print_test("Pipeline execution (with cache)")
    
    try:
        start = time.time()
        
        request2 = AIRequest(
            user_id="test_user_pipeline_phase2",
            session_id="test_session_pipeline_phase2",
            socket_id="test_socket_pipeline_phase2",
            prompt="Create a simple todo list with add and delete features"
        )
        
        result2 = await default_pipeline.execute(request2)
        duration2 = int((time.time() - start) * 1000)
        
        if result2.get('cache_hit'):
            runner.pass_test("Pipeline execution (with cache)", duration2)
        else:
            runner.fail_test("Pipeline execution (with cache)", "Cache not hit")
    except Exception as e:
        runner.fail_test("Pipeline execution (with cache)", str(e))


async def main():
    """Run all Phase 2 tests"""
    print("\n" + "=" * 60)
    print("  PHASE 2 COMPREHENSIVE TEST SUITE")
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
        await test_intent_analyzer()
        await test_context_builder()
        await test_semantic_cache()
        await test_rate_limiter()
        await test_complete_pipeline()
        
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