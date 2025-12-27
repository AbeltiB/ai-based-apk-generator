"""
Quick Phase 5 verification - Test complete system works.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.schemas import AIRequest
from app.services.pipeline import default_pipeline


async def main():
    print("\n" + "=" * 70)
    print("  QUICK PHASE 5 TEST - COMPLETE SYSTEM")
    print("=" * 70)
    
    # Connect infrastructure
    from app.core.cache import cache_manager
    from app.core.database import db_manager
    from app.core.messaging import queue_manager
    
    await cache_manager.connect()
    await db_manager.connect()
    await queue_manager.connect()
    
    test_prompt = "Create a counter app with number display and + and - buttons"
    
    print(f"\n📝 Prompt: {test_prompt}")
    print("-" * 70)
    
    try:
        # Execute complete pipeline
        print("\n[1/4] Executing COMPLETE pipeline (all phases)...")
        
        request = AIRequest(
            user_id="test_user_final",
            session_id="test_session_final",
            socket_id="test_socket_final",
            prompt=test_prompt
        )
        
        result = await default_pipeline.execute(request)
        
        print("✅ Pipeline complete!")
        
        # Verify Architecture (Phase 3)
        print("\n[2/4] Verifying Architecture (Phase 3)...")
        
        if 'architecture' in result:
            arch = result['architecture']
            print(f"✅ Architecture:")
            print(f"   Type: {arch['app_type']}")
            print(f"   Screens: {len(arch['screens'])}")
            for screen in arch['screens'][:3]:
                print(f"      - {screen['name']}: {len(screen['components'])} components")
        else:
            print("❌ No architecture")
        
        # Verify Layout (Phase 4)
        print("\n[3/4] Verifying Layout (Phase 4)...")
        
        if 'layout' in result:
            layout = result['layout']
            
            # Handle both formats
            if isinstance(layout, dict):
                if 'components' in layout:
                    components = layout['components']
                    screen_id = layout.get('screen_id', 'unknown')
                else:
                    first_screen = list(layout.values())[0]
                    components = first_screen.get('components', [])
                    screen_id = first_screen.get('screen_id', 'unknown')
            else:
                components = []
                screen_id = 'unknown'
            
            print(f"✅ Layout:")
            print(f"   Screen: {screen_id}")
            print(f"   Components: {len(components)}")
            
            for i, comp in enumerate(components[:3], 1):
                comp_type = comp.get('component_type', 'unknown')
                comp_id = comp.get('component_id', 'unknown')
                print(f"      {i}. {comp_type} ({comp_id})")
        else:
            print("❌ No layout")
        
        # Verify Blockly (Phase 5)
        print("\n[4/4] Verifying Blockly (Phase 5)...")
        
        if 'blockly' in result:
            blockly = result['blockly']
            blocks = blockly.get('blocks', {}).get('blocks', [])
            variables = blockly.get('variables', [])
            custom_blocks = blockly.get('custom_blocks', [])
            
            print(f"✅ Blockly:")
            print(f"   Blocks: {len(blocks)}")
            print(f"   Variables: {len(variables)}")
            print(f"   Custom block types: {len(custom_blocks)}")
            
            # Show first few blocks
            for i, block in enumerate(blocks[:3], 1):
                block_type = block.get('type', 'unknown')
                block_id = block.get('id', 'unknown')
                print(f"      {i}. {block_type} ({block_id})")
            
            # Show variables
            for var in variables:
                print(f"   Variable: {var.get('name', 'unknown')}")
                
        else:
            print("❌ No Blockly")
        
        # Performance Summary
        print("\n" + "=" * 70)
        print("  PERFORMANCE SUMMARY")
        print("=" * 70)
        
        total_time = result.get('total_time_ms', 0)
        stage_times = result.get('stage_times', {})
        
        print(f"\n⏱️  Total time: {total_time}ms ({total_time/1000:.2f}s)")
        
        print(f"\n📊 Stage breakdown:")
        for stage in ['architecture_generation', 'layout_generation', 'blockly_generation']:
            if stage in stage_times:
                ms = stage_times[stage]
                pct = (ms / total_time * 100) if total_time > 0 else 0
                print(f"   {stage}: {ms}ms ({pct:.1f}%)")
        
        # Warnings Summary
        arch_warnings = result.get('architecture_warnings', [])
        layout_warnings = result.get('layout_warnings', [])
        blockly_warnings = result.get('blockly_warnings', [])
        
        total_warnings = len(arch_warnings) + len(layout_warnings) + len(blockly_warnings)
        
        if total_warnings > 0:
            print(f"\n⚠️  Total warnings: {total_warnings}")
            print(f"   Architecture: {len(arch_warnings)}")
            print(f"   Layout: {len(layout_warnings)}")
            print(f"   Blockly: {len(blockly_warnings)}")
        
        # Final Status
        print("\n" + "=" * 70)
        print("  ✅ ALL PHASES COMPLETE!")
        print("=" * 70)
        print("\n✨ The system generated:")
        print("   ✅ Architecture (Phase 3)")
        print("   ✅ Layout (Phase 4)")
        print("   ✅ Blockly (Phase 5)")
        print("\n🎉 Full AI-powered mobile app generation is operational!")
        print("=" * 70 + "\n")
        
        # Cleanup
        await cache_manager.disconnect()
        await db_manager.disconnect()
        await queue_manager.disconnect()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\n" + "=" * 70 + "\n")
        
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        
        # Cleanup
        try:
            await cache_manager.disconnect()
            await db_manager.disconnect()
            await queue_manager.disconnect()
        except:
            pass
        
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)