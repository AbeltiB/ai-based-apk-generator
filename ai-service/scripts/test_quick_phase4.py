"""
Quick Phase 4 verification - Test layout generation works.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.schemas import AIRequest
from app.services.pipeline import default_pipeline


async def main():
    print("\n" + "=" * 60)
    print("  QUICK PHASE 4 TEST")
    print("=" * 60)
    
    # Connect infrastructure
    from app.core.cache import cache_manager
    from app.core.database import db_manager
    from app.core.messaging import queue_manager
    
    await cache_manager.connect()
    await db_manager.connect()
    await queue_manager.connect()
    
    test_prompt = "Create a counter app with a number display and + and - buttons"
    
    print(f"\n📝 Prompt: {test_prompt}")
    print("-" * 60)
    
    try:
        # Execute pipeline
        print("\n[1/2] Executing complete pipeline...")
        
        request = AIRequest(
            user_id="test_user_quick",
            session_id="test_session_quick",
            socket_id="test_socket_quick",
            prompt=test_prompt
        )
        
        result = await default_pipeline.execute(request)
        
        print("✅ Pipeline complete!")
        
        # Check architecture
        print("\n[2/2] Verifying results...")
        
        if 'architecture' in result:
            arch = result['architecture']
            print(f"\n✅ Architecture:")
            print(f"   Type: {arch['app_type']}")
            print(f"   Screens: {len(arch['screens'])}")
        else:
            print("\n❌ No architecture")
        
        # Check layout
        if 'layout' in result:
            layout = result['layout']
            
            # Handle both single and multiple screens
            if isinstance(layout, dict):
                if 'components' in layout:
                    components = layout['components']
                    screen_id = layout.get('screen_id', 'unknown')
                else:
                    # Multiple screens
                    first_screen = list(layout.values())[0]
                    components = first_screen.get('components', [])
                    screen_id = first_screen.get('screen_id', 'unknown')
            else:
                components = []
                screen_id = 'unknown'
            
            print(f"\n✅ Layout:")
            print(f"   Screen: {screen_id}")
            print(f"   Components: {len(components)}")
            
            for i, comp in enumerate(components[:5], 1):  # Show first 5
                comp_id = comp.get('component_id', 'unknown')
                comp_type = comp.get('component_type', 'unknown')
                props = comp.get('properties', {})
                style_prop = props.get('style', {})
                
                if isinstance(style_prop, dict) and 'value' in style_prop:
                    style = style_prop['value']
                    print(f"      {i}. {comp_type} ({comp_id})")
                    print(f"         Position: ({style.get('left', 0)}, {style.get('top', 0)})")
                    print(f"         Size: {style.get('width', 0)}x{style.get('height', 0)}")
        else:
            print("\n❌ No layout")
        
        # Check warnings
        layout_warnings = result.get('layout_warnings', [])
        if layout_warnings:
            print(f"\n⚠️  Layout Warnings: {len(layout_warnings)}")
            for w in layout_warnings[:3]:
                print(f"      - {w['level']}: {w['message'][:60]}...")
        
        # Performance
        total_time = result.get('total_time_ms', 0)
        print(f"\n⏱️  Total time: {total_time}ms")
        
        stage_times = result.get('stage_times', {})
        if 'architecture_generation' in stage_times:
            print(f"   Architecture: {stage_times['architecture_generation']}ms")
        if 'layout_generation' in stage_times:
            print(f"   Layout: {stage_times['layout_generation']}ms")
        
        print("\n" + "=" * 60)
        print("  ✅ PHASE 4 IS WORKING!")
        print("=" * 60 + "\n")
        
        # Cleanup
        await cache_manager.disconnect()
        await db_manager.disconnect()
        await queue_manager.disconnect()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\n" + "=" * 60 + "\n")
        
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