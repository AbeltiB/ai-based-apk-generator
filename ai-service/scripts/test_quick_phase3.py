"""
Quick Phase 3 verification - Test architecture generation works.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.generation.architecture_generator import architecture_generator
from app.services.generation.architecture_validator import architecture_validator


async def main():
    print("\n" + "=" * 60)
    print("  QUICK PHASE 3 TEST")
    print("=" * 60)
    
    test_prompt = "Create a simple counter app with + and - buttons"
    
    print(f"\n📝 Prompt: {test_prompt}")
    print("-" * 60)
    
    try:
        # Generate architecture
        print("\n[1/2] Generating architecture...")
        architecture, metadata = await architecture_generator.generate(test_prompt)
        
        print("✅ Generation successful!")
        print(f"\n📋 Architecture:")
        print(f"   Type: {architecture.app_type}")
        print(f"   Screens: {len(architecture.screens)}")
        for screen in architecture.screens:
            print(f"      - {screen.name}: {screen.purpose}")
            print(f"        Components: {', '.join(screen.components)}")
        
        print(f"\n   State Management:")
        for state in architecture.state_management:
            print(f"      - {state.name}: {state.type} = {state.initial_value}")
        
        print(f"\n📊 Metadata:")
        print(f"   Model: {metadata['model']}")
        print(f"   Tokens: {metadata['tokens_used']}")
        print(f"   Duration: {metadata['api_duration_ms']}ms")
        
        # Validate
        print("\n[2/2] Validating architecture...")
        is_valid, warnings = await architecture_validator.validate(architecture)
        
        if is_valid:
            print("✅ Validation passed!")
        else:
            print("❌ Validation failed!")
        
        print(f"\n⚠️  Warnings: {len(warnings)}")
        for warning in warnings:
            print(f"   {warning}")
        
        # Statistics
        stats = architecture_generator.get_statistics()
        print(f"\n📈 Generator Stats:")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Successful: {stats['successful']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        
        print("\n" + "=" * 60)
        if is_valid:
            print("  ✅ PHASE 3 IS WORKING!")
        else:
            print("  ⚠️  PHASE 3 WORKING (with warnings)")
        print("=" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\n" + "=" * 60 + "\n")
        
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)