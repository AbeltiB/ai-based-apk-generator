"""
Main pipeline orchestrator for AI request processing - Phase 5 COMPLETE.

All generation stages now operational:
- Phase 3: Architecture generation (Claude)
- Phase 4: Layout generation (Claude)
- Phase 5: Blockly generation (Claude)
"""
import asyncio
import time
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime

from app.models.schemas import AIRequest, ProgressUpdate, ErrorResponse
from app.core.messaging import queue_manager
from app.core.database import db_manager
from app.core.cache import cache_manager
from app.config import settings
from app.services.analysis.intent_analyzer import intent_analyzer
from app.services.analysis.context_builder import context_builder
from app.services.generation.cache_manager import semantic_cache
from app.utils.rate_limiter import rate_limiter


class PipelineStage:
    """Base class for pipeline stages"""
    
    def __init__(self, name: str):
        self.name = name
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute this stage"""
        raise NotImplementedError
    
    async def on_error(self, context: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Handle stage error"""
        logger.error(f"Error in stage {self.name}: {error}")
        context['errors'] = context.get('errors', [])
        context['errors'].append({
            'stage': self.name,
            'error': str(error),
            'timestamp': datetime.utcnow().isoformat()
        })
        return context


class Pipeline:
    """Main pipeline orchestrator - Phase 5 Complete"""
    
    def __init__(self):
        self.stages: list[PipelineStage] = []
    
    def add_stage(self, stage: PipelineStage) -> 'Pipeline':
        """Add a stage to the pipeline"""
        self.stages.append(stage)
        return self
    
    async def send_progress(
        self,
        task_id: str,
        socket_id: str,
        stage: str,
        progress: int,
        message: str
    ) -> None:
        """Send progress update to frontend"""
        try:
            update = ProgressUpdate(
                task_id=task_id,
                socket_id=socket_id,
                stage=stage,
                progress=progress,
                message=message
            )
            
            await queue_manager.publish_response(update.dict())
            logger.debug(f"📊 Progress [{task_id}]: {stage} - {progress}% - {message}")
            
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")
    
    async def send_error(
        self,
        task_id: str,
        socket_id: str,
        error: str,
        details: Optional[str] = None
    ) -> None:
        """Send error response to frontend"""
        try:
            error_response = ErrorResponse(
                task_id=task_id,
                socket_id=socket_id,
                error=error,
                details=details
            )
            
            await queue_manager.publish_response(error_response.dict())
            logger.error(f"❌ Error [{task_id}]: {error}")
            
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
    
    async def execute(self, request: AIRequest) -> Dict[str, Any]:
        """Execute the complete pipeline"""
        start_time = time.time()
        
        # Initialize context
        context = {
            'request': request,
            'task_id': request.task_id,
            'socket_id': request.socket_id,
            'user_id': request.user_id,
            'session_id': request.session_id,
            'prompt': request.prompt,
            'context_data': request.context,
            'start_time': start_time,
            'stage_times': {},
            'errors': [],
            'warnings': [],
            'substitutions': []
        }
        
        logger.info(f"🚀 Starting pipeline for task: {request.task_id}")
        logger.info(f"   User: {request.user_id}")
        logger.info(f"   Prompt: {request.prompt[:100]}...")
        
        # Send initial progress
        await self.send_progress(
            task_id=request.task_id,
            socket_id=request.socket_id,
            stage="initializing",
            progress=0,
            message="Starting AI processing..."
        )
        
        # Execute all stages
        for i, stage in enumerate(self.stages):
            stage_start = time.time()
            
            try:
                logger.info(f"▶️  Stage {i+1}/{len(self.stages)}: {stage.name}")
                
                # Execute stage
                context = await stage.execute(context)
                
                # Record timing
                stage_duration = int((time.time() - stage_start) * 1000)
                context['stage_times'][stage.name] = stage_duration
                
                logger.info(f"✅ Stage {stage.name} completed in {stage_duration}ms")
                
            except Exception as e:
                logger.error(f"❌ Stage {stage.name} failed: {e}")
                
                # Handle error
                context = await stage.on_error(context, e)
                
                # Record error timing
                stage_duration = int((time.time() - stage_start) * 1000)
                context['stage_times'][f"{stage.name}_error"] = stage_duration
                
                # Check if we should continue
                if not context.get('continue_on_error', False):
                    # Critical error - stop pipeline
                    await self.send_error(
                        task_id=request.task_id,
                        socket_id=request.socket_id,
                        error=f"Pipeline failed at stage: {stage.name}",
                        details=str(e)
                    )
                    
                    # Save error metrics
                    try:
                        await db_manager.save_request_metric(
                            task_id=request.task_id,
                            user_id=request.user_id,
                            stage=stage.name,
                            duration_ms=stage_duration,
                            success=False,
                            error_message=str(e)
                        )
                    except Exception as metric_error:
                        logger.error(f"Failed to save error metrics: {metric_error}")
                    
                    raise
        
        # Calculate total time
        total_time = int((time.time() - start_time) * 1000)
        context['total_time_ms'] = total_time
        
        logger.info(f"✅ Pipeline completed in {total_time}ms")
        logger.info(f"   Stage breakdown: {context['stage_times']}")
        
        # Send final progress
        await self.send_progress(
            task_id=request.task_id,
            socket_id=request.socket_id,
            stage="finalizing",
            progress=100,
            message="Processing complete!"
        )
        
        return context


# ============================================================================
# PIPELINE STAGES (Phase 5 Complete)
# ============================================================================

class RateLimitStage(PipelineStage):
    """Stage 0: Rate limiting check"""
    
    def __init__(self):
        super().__init__("rate_limiting")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check rate limits"""
        logger.info("🚦 Checking rate limits...")
        
        allowed, info = await rate_limiter.check_rate_limit(context['user_id'])
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {context['user_id']}")
            raise ValueError(
                f"Rate limit exceeded. Please try again in {info.get('retry_after', 0)} seconds. "
                f"Limit: {info.get('limit')} requests per hour."
            )
        
        context['rate_limit_info'] = info
        logger.info(f"✅ Rate limit OK: {info.get('remaining')}/{info.get('limit')} remaining")
        
        return context


class ValidationStage(PipelineStage):
    """Stage 1: Request validation"""
    
    def __init__(self):
        super().__init__("validation")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming request"""
        logger.info("Validating request...")
        
        request: AIRequest = context['request']
        
        if not request.prompt or len(request.prompt.strip()) < 10:
            raise ValueError("Prompt must be at least 10 characters")
        
        if not request.user_id:
            raise ValueError("User ID is required")
        
        context['validated'] = True
        
        await asyncio.sleep(0.05)  # Minimal processing time
        return context


class CacheCheckStage(PipelineStage):
    """Stage 2: Check semantic cache"""
    
    def __init__(self):
        super().__init__("cache_check")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if we have cached result"""
        logger.info("🔍 Checking cache...")
        
        # Try to get cached result
        cached_result = await semantic_cache.get_cached_result(
            prompt=context['prompt'],
            user_id=context['user_id']
        )
        
        if cached_result:
            logger.info("✅ Cache hit! Using cached result")
            
            # Extract result data
            result_data = cached_result.get('result', {})
            
            context['architecture'] = result_data.get('architecture')
            context['layout'] = result_data.get('layout')
            context['blockly'] = result_data.get('blockly')
            context['cache_hit'] = True
            context['skip_generation'] = True
            
            return context
        
        logger.info("Cache miss - will generate new result")
        context['cache_hit'] = False
        context['skip_generation'] = False
        
        return context


class IntentAnalysisStage(PipelineStage):
    """Stage 3: Intent classification with Claude"""
    
    def __init__(self):
        super().__init__("intent_analysis")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent"""
        
        # Skip if we have cached result
        if context.get('skip_generation'):
            logger.info("Skipping intent analysis (cached result)")
            return context
        
        logger.info("🔍 Analyzing intent with Claude...")
        
        # Prepare context for intent analyzer
        analysis_context = {
            'has_existing_project': context.get('context_data') is not None,
            'conversation_history': []
        }
        
        # Analyze intent
        intent = await intent_analyzer.analyze(
            prompt=context['prompt'],
            context=analysis_context
        )
        
        context['intent'] = intent
        
        logger.info(f"✅ Intent: {intent.intent_type} ({intent.complexity})")
        logger.info(f"   Confidence: {intent.confidence:.2f}")
        
        return context


class ContextBuildingStage(PipelineStage):
    """Stage 4: Build enriched context"""
    
    def __init__(self):
        super().__init__("context_building")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build enriched context"""
        
        # Skip if we have cached result
        if context.get('skip_generation'):
            logger.info("Skipping context building (cached result)")
            return context
        
        logger.info("🔨 Building enriched context...")
        
        # Build context
        enriched_context = await context_builder.build_context(
            user_id=context['user_id'],
            session_id=context['session_id'],
            prompt=context['prompt'],
            intent=context['intent'],
            original_request=context['request'].dict()
        )
        
        context['enriched_context'] = enriched_context
        
        logger.info("✅ Context enriched")
        logger.info(f"   History: {len(enriched_context.conversation_history)} messages")
        logger.info(f"   Existing project: {enriched_context.existing_project is not None}")
        
        return context


class ArchitectureGenerationStage(PipelineStage):
    """Stage 5: Architecture generation with Claude (Phase 3)"""
    
    def __init__(self):
        super().__init__("architecture_generation")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate architecture using Claude"""
        
        # Skip if we have cached result
        if context.get('skip_generation'):
            logger.info("Skipping architecture generation (cached result)")
            return context
        
        logger.info("🏗️  Generating architecture with Claude...")
        
        from app.services.generation.architecture_generator import architecture_generator
        from app.services.generation.architecture_validator import architecture_validator
        
        try:
            # Generate architecture
            architecture, metadata = await architecture_generator.generate(
                prompt=context['prompt'],
                context=context.get('enriched_context')
            )
            
            # Validate architecture
            is_valid, warnings = await architecture_validator.validate(architecture)
            
            if not is_valid:
                error_warnings = [w for w in warnings if w.level == "error"]
                raise ValueError(f"Invalid architecture: {len(error_warnings)} error(s)")
            
            # Store results
            context['architecture'] = architecture.dict()
            context['architecture_metadata'] = metadata
            context['architecture_warnings'] = [w.to_dict() for w in warnings]
            
            # Log warnings
            warning_count = sum(1 for w in warnings if w.level == "warning")
            if warning_count > 0:
                logger.warning(f"Architecture has {warning_count} warning(s)")
                for w in warnings:
                    if w.level == "warning":
                        logger.debug(str(w))
            
            logger.info(f"✅ Architecture generated: {architecture.app_type}, {len(architecture.screens)} screen(s)")
            
            return context
            
        except Exception as e:
            logger.error(f"Architecture generation failed: {e}")
            raise


class LayoutGenerationStage(PipelineStage):
    """Stage 6: Layout generation with Claude (Phase 4)"""
    
    def __init__(self):
        super().__init__("layout_generation")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate layout for each screen"""
        
        # Skip if we have cached result
        if context.get('skip_generation'):
            logger.info("Skipping layout generation (cached result)")
            return context
        
        logger.info("📐 Generating layouts with Claude...")
        
        from app.services.generation.layout_generator import layout_generator
        from app.services.generation.layout_validator import layout_validator
        
        try:
            architecture = context.get('architecture')
            if not architecture:
                raise ValueError("No architecture found in context")
            
            # Parse architecture
            from app.models.schemas import ArchitectureDesign
            arch_design = ArchitectureDesign(**architecture)
            
            # Generate layout for each screen
            layouts = {}
            all_warnings = []
            
            for screen in arch_design.screens:
                logger.info(f"Generating layout for screen: {screen.name}")
                
                # Generate layout
                layout, metadata = await layout_generator.generate(
                    architecture=arch_design,
                    screen_id=screen.id
                )
                
                # Validate layout
                is_valid, warnings = await layout_validator.validate(layout)
                
                if not is_valid:
                    error_warnings = [w for w in warnings if w.level == "error"]
                    raise ValueError(f"Invalid layout for {screen.name}: {len(error_warnings)} error(s)")
                
                # Store layout
                layouts[screen.id] = layout.dict()
                
                # Collect warnings
                all_warnings.extend([
                    {**w.to_dict(), 'screen_id': screen.id}
                    for w in warnings
                ])
                
                # Log warnings
                warning_count = sum(1 for w in warnings if w.level == "warning")
                if warning_count > 0:
                    logger.warning(f"Layout for {screen.name} has {warning_count} warning(s)")
            
            # Store results
            context['layout'] = layouts if len(layouts) > 1 else list(layouts.values())[0]
            context['layout_warnings'] = all_warnings
            
            logger.info(f"✅ Generated layouts for {len(layouts)} screen(s)")
            
            return context
            
        except Exception as e:
            logger.error(f"Layout generation failed: {e}")
            raise


class BlocklyGenerationStage(PipelineStage):
    """Stage 7: Blockly generation with Claude (Phase 5)"""
    
    def __init__(self):
        super().__init__("blockly_generation")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Blockly blocks"""
        
        # Skip if we have cached result
        if context.get('skip_generation'):
            logger.info("Skipping blockly generation (cached result)")
            return context
        
        logger.info("🧩 Generating Blockly blocks with Claude...")
        
        from app.services.generation.blockly_generator import blockly_generator
        from app.services.generation.blockly_validator import blockly_validator
        
        try:
            architecture = context.get('architecture')
            layout = context.get('layout')
            
            if not architecture or not layout:
                raise ValueError("No architecture or layout found in context")
            
            # Parse architecture
            from app.models.schemas import ArchitectureDesign
            arch_design = ArchitectureDesign(**architecture)
            
            # Parse layouts
            from app.models.enhanced_schemas import EnhancedLayoutDefinition
            
            layouts = {}
            if isinstance(layout, dict):
                if 'components' in layout:
                    # Single screen layout
                    layouts[layout['screen_id']] = EnhancedLayoutDefinition(**layout)
                else:
                    # Multiple screens
                    for screen_id, screen_layout in layout.items():
                        layouts[screen_id] = EnhancedLayoutDefinition(**screen_layout)
            
            # Generate Blockly
            blockly, metadata = await blockly_generator.generate(
                architecture=arch_design,
                layouts=layouts
            )
            
            # Validate Blockly
            is_valid, warnings = await blockly_validator.validate(blockly)
            
            if not is_valid:
                error_warnings = [w for w in warnings if w.level == "error"]
                raise ValueError(f"Invalid Blockly: {len(error_warnings)} error(s)")
            
            # Store results
            context['blockly'] = blockly
            context['blockly_metadata'] = metadata
            context['blockly_warnings'] = [w.to_dict() for w in warnings]
            
            # Log warnings
            warning_count = sum(1 for w in warnings if w.level == "warning")
            if warning_count > 0:
                logger.warning(f"Blockly has {warning_count} warning(s)")
            
            logger.info(f"✅ Blockly generated: {len(blockly['blocks']['blocks'])} blocks")
            
            return context
            
        except Exception as e:
            logger.error(f"Blockly generation failed: {e}")
            raise


class CacheStoreStage(PipelineStage):
    """Stage 8: Store result in cache"""
    
    def __init__(self):
        super().__init__("cache_store")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Cache the generated result"""
        
        # Skip if result was from cache
        if context.get('cache_hit'):
            logger.info("Skipping cache store (result was from cache)")
            return context
        
        logger.info("💾 Caching result...")
        
        # Prepare result for caching
        result = {
            'architecture': context.get('architecture'),
            'layout': context.get('layout'),
            'blockly': context.get('blockly')
        }
        
        # Cache it
        cached = await semantic_cache.cache_result(
            prompt=context['prompt'],
            user_id=context['user_id'],
            result=result
        )
        
        if cached:
            logger.info("✅ Result cached successfully")
        else:
            logger.warning("Failed to cache result")
        
        return context


class PersistenceStage(PipelineStage):
    """Stage 9: Save to database"""
    
    def __init__(self):
        super().__init__("persistence")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Save conversation and results"""
        logger.info("💾 Persisting data...")
        
        # Save conversation
        try:
            messages = [
                {
                    "role": "user",
                    "content": context['prompt'],
                    "timestamp": context['start_time']
                },
                {
                    "role": "assistant",
                    "content": "Generated architecture, layout, and blockly",
                    "timestamp": time.time(),
                    "metadata": {
                        "cache_hit": context.get('cache_hit', False),
                        "intent": context.get('intent', {}).dict() if hasattr(context.get('intent'), 'dict') else {}
                    }
                }
            ]
            
            conversation_id = await db_manager.save_conversation(
                user_id=context['user_id'],
                session_id=context['session_id'],
                messages=messages
            )
            
            context['conversation_id'] = conversation_id
            logger.info(f"✅ Conversation saved: {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            # Non-critical, continue
        
        # Save metrics
        try:
            for stage_name, duration in context['stage_times'].items():
                await db_manager.save_request_metric(
                    task_id=context['task_id'],
                    user_id=context['user_id'],
                    stage=stage_name,
                    duration_ms=duration,
                    success=True,
                    error_message=None
                )
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
        
        return context


class PublishingStage(PipelineStage):
    """Stage 10: Publish response"""
    
    def __init__(self):
        super().__init__("publishing")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Publish final response"""
        logger.info("📤 Publishing response...")
        
        # Build complete response
        response = {
            "task_id": context['task_id'],
            "socket_id": context['socket_id'],
            "type": "complete",
            "status": "success" if not context['errors'] else "partial_success",
            "result": {
                "architecture": context.get('architecture', {}),
                "layout": context.get('layout', {}),
                "blockly": context.get('blockly', {})
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "processing_time_ms": context.get('total_time_ms', 0),
                "ai_model": settings.anthropic_model,
                "stages_completed": list(context['stage_times'].keys()),
                "warnings": context.get('warnings', []),
                "substitutions": context.get('substitutions', []),
                "cache_hit": context.get('cache_hit', False),
                "intent": {
                    "type": context.get('intent', {}).intent_type if hasattr(context.get('intent'), 'intent_type') else "unknown",
                    "complexity": context.get('intent', {}).complexity if hasattr(context.get('intent'), 'complexity') else "unknown"
                },
                # Phase-specific metadata
                "architecture_metadata": context.get('architecture_metadata', {}),
                "layout_warnings": context.get('layout_warnings', []),
                "blockly_warnings": context.get('blockly_warnings', [])
            },
            "conversation": {
                "message_id": context.get('conversation_id', ''),
                "saved": 'conversation_id' in context
            }
        }
        
        # Publish to RabbitMQ
        await queue_manager.publish_response(response)
        
        logger.info(f"✅ Response published for task: {context['task_id']}")
        
        return context


# ============================================================================
# CREATE PHASE 5 COMPLETE PIPELINE
# ============================================================================

def create_phase5_pipeline() -> Pipeline:
    """
    Create Phase 5 complete pipeline with all generation stages.
    
    Returns:
        Configured pipeline with all Phase 5 features (COMPLETE)
    """
    pipeline = Pipeline()
    
    # Add all stages (Phase 5 COMPLETE)
    pipeline.add_stage(RateLimitStage())                  # Stage 0
    pipeline.add_stage(ValidationStage())                 # Stage 1
    pipeline.add_stage(CacheCheckStage())                 # Stage 2
    pipeline.add_stage(IntentAnalysisStage())             # Stage 3
    pipeline.add_stage(ContextBuildingStage())            # Stage 4
    pipeline.add_stage(ArchitectureGenerationStage())     # Stage 5 (Phase 3) ✅
    pipeline.add_stage(LayoutGenerationStage())           # Stage 6 (Phase 4) ✅
    pipeline.add_stage(BlocklyGenerationStage())          # Stage 7 (Phase 5) ✅
    pipeline.add_stage(CacheStoreStage())                 # Stage 8
    pipeline.add_stage(PersistenceStage())                # Stage 9
    pipeline.add_stage(PublishingStage())                 # Stage 10
    
    return pipeline


# Global pipeline instance (Phase 5 COMPLETE!)
default_pipeline = create_phase5_pipeline()


if __name__ == "__main__":
    # Test Phase 5 complete pipeline
    import asyncio
    from app.models.schemas import AIRequest
    
    async def test_phase5_pipeline():
        """Test Phase 5 complete pipeline"""
        print("\n" + "=" * 60)
        print("PHASE 5 COMPLETE PIPELINE TEST")
        print("=" * 60)
        
        # Connect dependencies
        await queue_manager.connect()
        await cache_manager.connect()
        await db_manager.connect()
        
        # Create test request
        request = AIRequest(
            user_id="test_user_phase5",
            session_id="test_session_phase5",
            socket_id="test_socket_phase5",
            prompt="Create a counter app with number display and + - buttons"
        )
        
        # Execute pipeline
        try:
            result = await default_pipeline.execute(request)
            print(f"\n✅ Pipeline completed successfully")
            print(f"   Total time: {result['total_time_ms']}ms")
            print(f"   Cache hit: {result.get('cache_hit', False)}")
            print(f"   Stages: {len(result['stage_times'])}")
            
            # Show generated components
            if 'architecture' in result:
                print(f"\n✅ Architecture: {result['architecture']['app_type']}")
            if 'layout' in result:
                layout = result['layout']
                comp_count = len(layout.get('components', [])) if isinstance(layout, dict) and 'components' in layout else 0
                print(f"✅ Layout: {comp_count} components")
            if 'blockly' in result:
                block_count = len(result['blockly']['blocks']['blocks'])
                print(f"✅ Blockly: {block_count} blocks")
                
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Disconnect
        await queue_manager.disconnect()
        await cache_manager.disconnect()
        await db_manager.disconnect()
        
        print("\n" + "=" * 60 + "\n")
    
    asyncio.run(test_phase5_pipeline())