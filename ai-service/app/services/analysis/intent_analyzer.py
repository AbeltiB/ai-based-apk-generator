"""

Usage:
    from intent_analyzer import intent_analyzer
    
    # Works exactly like your existing code
    result = await intent_analyzer.analyze(prompt, context)
"""
from typing import Dict, Any, Optional
from loguru import logger

from app.services.analysis.intent_orchestrator import IntentClassificationOrchestrator
from intent_schemas import IntentAnalysisResult as ProductionResult
from app.models.enhanced_schemas import IntentAnalysis
from app.config import settings


class ProductionIntentAnalyzer:
    """
    Production-grade intent analyzer with multi-tier fallback.
    
    Drop-in replacement for your existing IntentAnalyzer class.
    Maintains the same interface but adds enterprise features:
    - Multi-tier fallback (Claude → Groq → Heuristic)
    - Intelligent caching
    - Performance monitoring
    - Never crashes
    """
    
    def __init__(self):
        """Initialize with API keys from settings"""
        
        # Initialize orchestrator
        self.orchestrator = IntentClassificationOrchestrator(
            claude_api_key=settings.anthropic_api_key,
            groq_api_key=getattr(settings, 'groq_api_key', None)
        )
        
        logger.info("✅ Production Intent Analyzer initialized")
        logger.info(f"   Available tiers: {len(self.orchestrator.tiers)}")
    
    async def analyze(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysis:
        """
        Analyze user prompt to determine intent.
        
        This method signature matches your existing IntentAnalyzer
        for seamless integration.
        
        Args:
            prompt: User's natural language request
            context: Optional context (conversation history, existing project)
            
        Returns:
            IntentAnalysis object (your existing schema)
        """
        try:
            # Use orchestrator for classification
            production_result = await self.orchestrator.classify(
                prompt=prompt,
                user_id=context.get('user_id', 'unknown') if context else 'unknown',
                session_id=context.get('session_id', 'unknown') if context else 'unknown',
                context=context
            )
            
            # Convert to your existing IntentAnalysis schema
            legacy_result = self._convert_to_legacy_schema(production_result)
            
            # Log success
            logger.info(
                f"✅ Intent analyzed: {legacy_result.intent_type} "
                f"(confidence: {legacy_result.confidence:.2f}, "
                f"tier: {production_result.tier_used})"
            )
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"❌ Intent analysis error: {e}")
            
            # This should never happen (orchestrator never fails)
            # But just in case, provide a safe fallback
            return self._create_safe_fallback(prompt)
    
    def _convert_to_legacy_schema(
        self,
        production_result: ProductionResult
    ) -> IntentAnalysis:
        """
        Convert production result to your existing IntentAnalysis schema.
        
        This ensures compatibility with your existing pipeline.
        """
        
        # Map production schema to legacy schema
        return IntentAnalysis(
            intent_type=production_result.intent_type.value,
            complexity=production_result.complexity.value,
            confidence=production_result.confidence.overall,
            extracted_entities={
                "components": production_result.extracted_entities.components,
                "actions": production_result.extracted_entities.actions,
                "data": production_result.extracted_entities.data_types,
                "features": production_result.extracted_entities.features
            },
            requires_context=production_result.requires_context,
            multi_turn=production_result.multi_turn
        )
    
    def _create_safe_fallback(self, prompt: str) -> IntentAnalysis:
        """Create safe fallback (should never be needed)"""
        logger.warning("⚠️  Using emergency fallback")
        
        return IntentAnalysis(
            intent_type="clarification",
            complexity="medium",
            confidence=0.3,
            extracted_entities={
                "components": [],
                "actions": [],
                "data": [],
                "features": []
            },
            requires_context=False,
            multi_turn=False
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return self.orchestrator.get_stats()
    
    def reset_stats(self):
        """Reset statistics"""
        self.orchestrator.reset_stats()
    
    def clear_cache(self):
        """Clear classification cache"""
        self.orchestrator.clear_cache()


# ============================================================================
# GLOBAL INSTANCE - Drop-in replacement
# ============================================================================

intent_analyzer = ProductionIntentAnalyzer()


# ============================================================================
# MIGRATION GUIDE
# ============================================================================

"""
MIGRATION GUIDE - How to integrate this into your existing code:

1. INSTALL DEPENDENCIES:
   ```bash
   poetry add rapidfuzz httpx
   ```

2. ADD GROQ API KEY (Optional, for Tier 2):
   In your .env file:
   ```
   GROQ_API_KEY=your-groq-key-here
   ```
   
   In app/config.py, add:
   ```python
   groq_api_key: Optional[str] = None
   ```

3. REPLACE YOUR EXISTING INTENT ANALYZER:
   
   OLD (app/services/analysis/intent_analyzer.py):
   ```python
   from app.models.enhanced_schemas import IntentAnalysis
   
   class IntentAnalyzer:
       async def analyze(self, prompt, context):
           # ... old code ...
   
   intent_analyzer = IntentAnalyzer()
   ```
   
   NEW (just replace the file content):
   ```python
   from intent_analyzer_production import intent_analyzer
   ```
   
   That's it! The interface is identical.

4. COPY NEW FILES to your project:
   - intent_config.py → app/services/analysis/intent/
   - intent_schemas.py → app/services/analysis/intent/
   - tier_base.py → app/services/analysis/intent/
   - tier_claude.py → app/services/analysis/intent/
   - tier_groq.py → app/services/analysis/intent/
   - tier_heuristic.py → app/services/analysis/intent/
   - intent_orchestrator.py → app/services/analysis/intent/
   - intent_analyzer_production.py → app/services/analysis/

5. UPDATE IMPORTS in your pipeline:
   ```python
   # In app/services/pipeline.py
   from app.services.analysis.intent_analyzer_production import intent_analyzer
   ```

6. THAT'S IT! Your existing code works unchanged.

MONITORING:
Access statistics anytime:
```python
stats = intent_analyzer.get_stats()
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Avg latency: {stats['avg_latency_ms']:.0f}ms")
```

BENEFITS:
✅ Drop-in replacement - no code changes needed
✅ Multi-tier fallback - never fails
✅ Intelligent caching - faster responses
✅ Cost tracking - monitor API usage
✅ Performance monitoring - built-in metrics
✅ Safety checks - blocks malicious requests
✅ Confidence-based decisions - automatic clarification
✅ Production-ready - enterprise-grade reliability
"""


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_production_analyzer():
        """Test the production analyzer"""
        
        print("\n" + "=" * 70)
        print("TESTING PRODUCTION INTENT ANALYZER")
        print("=" * 70)
        
        test_cases = [
            {
                "prompt": "Create a simple todo list app",
                "context": {"user_id": "test_user", "session_id": "test_session"}
            },
            {
                "prompt": "Add delete buttons to existing app",
                "context": {
                    "user_id": "test_user",
                    "session_id": "test_session",
                    "has_existing_project": True
                }
            },
            {
                "prompt": "Build e-commerce with payment and auth",
                "context": {"user_id": "test_user", "session_id": "test_session"}
            }
        ]
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] Testing: \"{test['prompt']}\"")
            
            result = await intent_analyzer.analyze(
                prompt=test['prompt'],
                context=test['context']
            )
            
            print(f"   Intent: {result.intent_type}")
            print(f"   Complexity: {result.complexity}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Entities: {len(result.extracted_entities.get('components', []))} components")
        
        # Show stats
        print("\n" + "=" * 70)
        print("STATISTICS")
        print("=" * 70)
        
        stats = intent_analyzer.get_stats()
        print(f"Total: {stats['total_classifications']}")
        print(f"Cache Hit Rate: {stats.get('cache_hit_rate', 0):.1f}%")
        print(f"Success Rate: {stats.get('success_rate', 100):.1f}%")
        
        print("\n" + "=" * 70 + "\n")
    
    asyncio.run(test_production_analyzer())