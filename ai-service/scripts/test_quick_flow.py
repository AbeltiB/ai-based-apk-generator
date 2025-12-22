"""
Quick flow test - Verify complete working flow with 0 errors.

This tests the entire pipeline end-to-end with real infrastructure.
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


async def test_complete_flow():
    """Test complete flow with all components"""
    
    print("\n" + "=" * 70)
    print("  COMPLETE FLOW TEST - Phase 2")
    print("=" * 70)
    
    try:
        # Step 1: Connect to infrastructure
        print("\n[1/5] Connecting to infrastructure...")
        
        print("   - Connecting to RabbitMQ...", end=" ", flush=True)
        await queue_manager.connect()
        print("✅")
        
        print("   - Connecting to Redis...", end=" ", flush=True)
        await cache_manager.connect()
        print("✅")
        
        print("   - Connecting to PostgreSQL...", end=" ", flush=True)
        await db_manager.connect()
        print("✅")
        
        # Step 2: Import pipeline (after connections are ready)
        print("\n[2/5] Loading pipeline...")
        from app.services.pipeline import default_pipeline
        print("   ✅ Pipeline loaded")
        
        # Step 3: Create test request
        print("\n[3/5] Creating test request...")
        request = AIRequest(
            user_id="test_user_flow",
            session_id="test_session_flow",
            socket_id="test_socket_flow",
            prompt="Create a simple todo list app with add and delete buttons"
        )
        print(f"   ✅ Request created: {request.task_id}")
        
        # Step 4: Execute pipeline
        print("\n[4/5] Executing pipeline...")
        start_time = time.time()
        
        result = await default_pipeline.execute(request)
        
        duration = time.time() - start_time
        
        print(f"   ✅ Pipeline completed in {duration:.2f}s")
        
        # Step 5: Verify results
        print("\n[5/5] Verifying results...")
        
        checks = []
        
        # Check architecture
        if 'architecture' in result:
            checks.append(("Architecture generated", True))
        else:
            checks.append(("Architecture generated", False))
        
        # Check layout
        if 'layout' in result:
            checks.append(("Layout generated", True))
        else:
            checks.append(("Layout generated", False))
        
        # Check blockly
        if 'blockly' in result:
            checks.append(("Blockly generated", True))
        else:
            checks.append(("Blockly generated", False))
        
        # Check intent
        if 'intent' in result:
            intent = result['intent']
            checks.append(("Intent analyzed", True))
            checks.append((f"Intent type: {intent.intent_type}", True))
            checks.append((f"Complexity: {intent.complexity}", True))
        else:
            checks.append(("Intent analyzed", False))
        
        # Check conversation saved
        if 'conversation_id' in result:
            checks.append(("Conversation saved", True))
        else:
            checks.append(("Conversation saved", False))
        
        # Check stages completed
        if 'stage_times' in result:
            stages = len(result['stage_times'])
            checks.append((f"Stages completed: {stages}", True))
        else:
            checks.append(("Stages tracked", False))
        
        # Print results
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}")
        
        # Summary
        all_passed = all(passed for _, passed in checks)
        
        print("\n" + "=" * 70)
        if all_passed:
            print("  ✅ ALL CHECKS PASSED - Flow is working perfectly!")
        else:
            failed = sum(1 for _, passed in checks if not passed)
            print(f"  ❌ {failed} CHECK(S) FAILED")
        print("=" * 70)
        
        # Performance details
        print("\n📊 Performance Details:")
        if 'stage_times' in result:
            total_ms = sum(result['stage_times'].values())
            print(f"   Total time: {total_ms}ms")
            print(f"   Stages:")
            for stage, ms in result['stage_times'].items():
                print(f"      - {stage}: {ms}ms")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        await queue_manager.disconnect()
        await cache_manager.disconnect()
        await db_manager.disconnect()
        print("   ✅ All connections closed")
        
        print("\n" + "=" * 70)
        print("  TEST COMPLETE!")
        print("=" * 70 + "\n")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"   {type(e).__name__}: {e}")
        print("\n" + "=" * 70)
        
        # Try to cleanup
        try:
            await queue_manager.disconnect()
            await cache_manager.disconnect()
            await db_manager.disconnect()
        except:
            pass
        
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_complete_flow())
    sys.exit(exit_code)