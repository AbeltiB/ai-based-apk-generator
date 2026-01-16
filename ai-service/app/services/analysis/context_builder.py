"""
Enhanced Context Builder - Comprehensive context enrichment.

Loads and structures all relevant context for AI generation:
- Conversation history
- Existing projects
- User preferences
- Intent analysis results
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime, timezone, timezone

from app.core.database import db_manager
from app.models.enhanced_schemas import IntentAnalysis, EnrichedContext


class ContextRelevanceScore:
    """
    Calculate confidence that a project is relevant to current request.
    """
    
    @staticmethod
    def calculate(
        project: Dict[str, Any],
        user_id: str,
        session_id: str,
        intent: IntentAnalysis
    ) -> float:
        """
        Calculate relevance score (0.0 to 1.0).
        
        Args:
            project: Project data
            user_id: Current user ID
            session_id: Current session ID
            intent: Intent analysis
            
        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0.0
        
        # CRITICAL: Ownership verification (mandatory)
        if project.get('user_id') != user_id:
            return 0.0  # Wrong user - NEVER return
        
        # Session match (highest weight)
        project_metadata = project.get('metadata', {})
        if project_metadata.get('session_id') == session_id:
            score += 0.6  # Same session = very relevant
        
        # Recency (within last hour)
        updated_at = project.get('updated_at')
        if updated_at:
            import datetime as dt
            age_hours = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600
            if age_hours < 1:
                score += 0.3
            elif age_hours < 24:
                score += 0.1
        
        # Intent match
        if intent.requires_context:
            score += 0.1
        
        return min(score, 1.0)
    
class ContextBuilder:
    """
    Builds enriched context for AI generation.
    
    Aggregates all relevant information:
    - Recent conversation history
    - Existing project data (for extend/modify intents)
    - User preferences and settings
    - Intent analysis results
    - Session metadata
    """
    
    async def build_context(
        self,
        user_id: str,
        session_id: str,
        prompt: str,
        intent: IntentAnalysis,
        original_request: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> EnrichedContext:
        """
        Build comprehensive enriched context.
        Fixes: Now requires explicit project_id or high-confidence match.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            prompt: User's prompt
            intent: Intent analysis results
            original_request: Original AIRequest dict
            
        Returns:
            EnrichedContext with all relevant data
        """
        logger.info("🔨 Building enriched context...",
                    extra={
                        "user_id": user_id,
                        "session_id": session_id,
                        "requires_context": intent.requires_context,
                        "explicit_project_id": project_id is not None,
                        "intent_type": intent.intent_type,
                        "complexity": intent.complexity
                    })
        
        context = EnrichedContext(
            original_request=original_request,
            intent_analysis=intent,
            conversation_history=[],
            existing_project=None,
            user_preferences={},
            timestamp=datetime.now(timezone.utc)
        )
        
        # Load conversation history
        context.conversation_history = await self._load_conversation_history(
            user_id=user_id,
            session_id=session_id,
            limit=10 #TODO: make configurable
        )
        
        # Load existing project with strict validation
        if intent.requires_context or project_id:
            context.existing_project = await self._load_existing_project_safe(
                user_id=user_id,
                session_id=session_id,
                intent=intent,
                explicit_project_id=project_id
            )
            
            if context.existing_project:
                logger.info(
                    "   ✅ Existing project loaded for context"
                    "context.project.loaded",
                    extra={
                        "project_id": context.existing_project['project_id'],
                        "confidence": context.existing_project.get('confidence', 0.0)
                    }
                )
            elif intent.requires_context:
                logger.warning(
                    "   ⚠️ Existing project required but not found or confidence too low"
                    "context.project.missing",
                    extra={
                        "user_id": user_id,
                        "session_id": session_id,
                        "message": "⚠️ Intent requires context but no valid project found.",
                        "intent_type": intent.intent_type,
                        "complexity": intent.complexity
                    }
                )
        
        # Load user preferences
        context.user_preferences = await self._load_user_preferences(user_id)
        
        logger.info(
            "✅ Context built successfully"
            "context.build.completed",
            extra={
                "history_messages": len(context.conversation_history),
                "has_project": context.existing_project is not None,
                "preferences_loaded": len(context.user_preferences) > 0
            }
        )
        
        return context
    
    async def _load_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Load recent conversation history.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            limit: Maximum conversations to load
            
        Returns:
            List of conversation messages
        """
        logger.debug(
                    "context.history.loading",
                    extra={"user_id": user_id, "session_id": session_id}
                )        
        
        try:
            # Case 1: Explicit project ID provided (highest priority)
            if explicit_project_id:
                project = await db_manager.get_project(explicit_project_id)
                
                if not project:
                    logger.warning(
                        "context.project.not_found",
                        extra={"project_id": explicit_project_id}
                    )
                    return None
                
                # CRITICAL: Verify ownership
                if project.get('user_id') != user_id:
                    logger.error(
                        "context.project.ownership_violation",
                        extra={
                            "project_id": explicit_project_id,
                            "requested_by": user_id,
                            "owned_by": project.get('user_id')
                        }
                    )
                    return None  # Security violation - wrong user
                
                # Add confidence (explicit reference = 1.0)
                project['_confidence'] = 1.0
                project['_match_reason'] = 'explicit_project_id'
                
                logger.info(
                    "context.project.loaded_explicit",
                    extra={"project_id": explicit_project_id}
                )
                
                return project
            
            # Case 2: Match by session_id (medium priority)
            projects = await db_manager.get_user_projects(
                user_id=user_id,
                limit=5
            )
            
            if not projects:
                logger.debug("context.project.none_found")
                return None
            
            # Find projects matching session
            session_matches = []
            
            for project in projects:
                # Calculate confidence
                confidence = ContextRelevanceScore.calculate(
                    project=project,
                    user_id=user_id,
                    session_id=session_id,
                    intent=intent
                )
                
                if confidence >= self.MIN_CONFIDENCE_THRESHOLD:
                    project['_confidence'] = confidence
                    project['_match_reason'] = 'session_match'
                    session_matches.append(project)
            
            if not session_matches:
                logger.warning(
                    "context.project.no_confident_match",
                    extra={
                        "candidates": len(projects),
                        "threshold": self.MIN_CONFIDENCE_THRESHOLD
                    }
                )
                return None
            
            # Return highest confidence match
            best_match = max(session_matches, key=lambda p: p['_confidence'])
            
            logger.info(
                "context.project.loaded_session",
                extra={
                    "project_id": best_match['id'],
                    "confidence": best_match['_confidence'],
                    "candidates_evaluated": len(projects)
                }
            )
            
            return best_match
            
        except Exception as e:
            logger.error(f"Failed to load existing project: {e}", exc_info=True)
            return None
    
    async def _load_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Load user preferences.
        
        Args:
            user_id: User identifier
            
        Returns:
            User preferences dict
        """
        logger.debug(f"Loading preferences for {user_id}...")
        
        try:
            preferences = await db_manager.get_user_preferences(user_id)
            
            if preferences:
                logger.debug(f"Loaded {len(preferences)} preference settings")
                return preferences
            else:
                logger.debug("No preferences found, using defaults")
                return self._get_default_preferences()
                
        except Exception as e:
            logger.warning(f"Failed to load user preferences: {e}")
            return self._get_default_preferences()
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
            "theme": "light",
            "component_style": "detailed",
            "preferred_colors": {
                "primary": "#007AFF",
                "secondary": "#5856D6",
                "background": "#FFFFFF",
                "text": "#000000"
            },
            "layout_style": "modern",
            "enable_animations": True
        }
    
    def format_context_for_prompt(self, context: EnrichedContext) -> str:
        """
        Format enriched context into a string for Claude prompts.
        
        Args:
            context: EnrichedContext object
            
        Returns:
            Formatted context string
        """
        parts = []
        
        # Intent information
        parts.append(f"**Intent:** {context.intent_analysis.intent_type}")
        parts.append(f"**Complexity:** {context.intent_analysis.complexity}")
        
        # Extracted entities
        if context.intent_analysis.extracted_entities:
            entities = context.intent_analysis.extracted_entities
            if entities.get('components'):
                parts.append(f"**Requested Components:** {', '.join(entities['components'])}")
            if entities.get('features'):
                parts.append(f"**Requested Features:** {', '.join(entities['features'])}")
        
        # Conversation history
        if context.conversation_history:
            recent = context.conversation_history[-3:]  # Last 3 messages
            history_str = "\n".join([
                f"  - {msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}"
                for msg in recent
            ])
            parts.append(f"**Recent Conversation:**\n{history_str}")
        
        # Existing project
        if context.existing_project:
            proj = context.existing_project
            confidence = proj.get('_confidence', 0.0)
            match_reason = proj.get('_match_reason', 'unknown')
            
            
            parts.append(f"**Existing Project:** {proj.get('project_name', 'Unnamed')}")
            parts.append(f"  - Confidence: {confidence:.2f} (matched by {match_reason})")
            
            if proj.get('architecture'):
                arch = proj['architecture']
                parts.append(f"  - Type: {arch.get('app_type', 'unknown')}")
                parts.append(f"  - Screens: {len(arch.get('screens', []))}")
        
        # User preferences
        if context.user_preferences:
            prefs = context.user_preferences
            parts.append(f"**User Preferences:**")
            if 'theme' in prefs:
                parts.append(f"  - Theme: {prefs['theme']}")
            if 'component_style' in prefs:
                parts.append(f"  - Style: {prefs['component_style']}")
        
        return "\n".join(parts)


# Global context builder instance
context_builder = ContextBuilder()


if __name__ == "__main__":
    # Test context builder
    import asyncio
    from app.models.enhanced_schemas import IntentAnalysis
    
    async def test_context_builder():
        """Test context building"""
        print("\n" + "=" * 60)
        print("CONTEXT BUILDER TEST")
        print("=" * 60)
        
        # Connect to database
        await db_manager.connect()
        
        # Create test intent
        intent = IntentAnalysis(
            intent_type="new_app",
            complexity="medium",
            confidence=0.9,
            extracted_entities={
                "components": ["Button", "InputText"],
                "actions": ["click", "input"],
                "data": ["todo"],
                "features": ["add", "list"]
            },
            requires_context=False,
            multi_turn=False
        )
        
        # Build context
        context = await context_builder.build_context(
            user_id="test_user_phase2",
            session_id="test_session_phase2",
            prompt="Create a todo list app",
            intent=intent,
            original_request={"prompt": "Create a todo list app"}
        )
        
        print(f"\n✅ Context built:")
        print(f"   Intent: {context.intent_analysis.intent_type}")
        print(f"   Complexity: {context.intent_analysis.complexity}")
        print(f"   History: {len(context.conversation_history)} messages")
        print(f"   Existing project: {context.existing_project is not None}")
        print(f"   Preferences: {len(context.user_preferences)} settings")
        
        # Format for prompt
        print("\n📝 Formatted context for prompt:")
        print("-" * 60)
        formatted = context_builder.format_context_for_prompt(context)
        print(formatted)
        print("-" * 60)
        
        # Disconnect
        await db_manager.disconnect()
        
        print("\n" + "=" * 60)
        print("✅ Context builder test complete!")
        print("=" * 60 + "\n")
    
    asyncio.run(test_context_builder())