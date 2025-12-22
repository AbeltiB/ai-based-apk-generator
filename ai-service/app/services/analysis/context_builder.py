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
from datetime import datetime

from app.core.database import db_manager
from app.models.enhanced_schemas import IntentAnalysis, EnrichedContext


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
        original_request: Dict[str, Any]
    ) -> EnrichedContext:
        """
        Build comprehensive enriched context.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            prompt: User's prompt
            intent: Intent analysis results
            original_request: Original AIRequest dict
            
        Returns:
            EnrichedContext with all relevant data
        """
        logger.info("🔨 Building enriched context...")
        
        context = EnrichedContext(
            original_request=original_request,
            intent_analysis=intent,
            conversation_history=[],
            existing_project=None,
            user_preferences={},
            timestamp=datetime.utcnow()
        )
        
        # Load conversation history
        context.conversation_history = await self._load_conversation_history(
            user_id=user_id,
            session_id=session_id,
            limit=10
        )
        
        # Load existing project if needed
        if intent.requires_context:
            context.existing_project = await self._load_existing_project(
                user_id=user_id,
                session_id=session_id
            )
        
        # Load user preferences
        context.user_preferences = await self._load_user_preferences(user_id)
        
        logger.info("✅ Context built successfully")
        logger.info(f"   History messages: {len(context.conversation_history)}")
        logger.info(f"   Has existing project: {context.existing_project is not None}")
        logger.info(f"   User preferences: {len(context.user_preferences)} settings")
        
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
        logger.debug(f"Loading conversation history for {user_id}/{session_id}...")
        
        try:
            conversations = await db_manager.get_conversation_history(
                user_id=user_id,
                session_id=session_id,
                limit=limit
            )
            
            # Flatten messages from all conversations
            all_messages = []
            for conv in conversations:
                messages = conv.get('messages', [])
                if isinstance(messages, list):
                    all_messages.extend(messages)
            
            # Sort by timestamp if available
            all_messages.sort(
                key=lambda m: m.get('timestamp', 0),
                reverse=False  # Oldest first
            )
            
            logger.debug(f"Loaded {len(all_messages)} messages from {len(conversations)} conversations")
            return all_messages
            
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")
            return []
    
    async def _load_existing_project(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load the most recent project for this session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Project data or None
        """
        logger.debug(f"Loading existing project for {user_id}/{session_id}...")
        
        try:
            # Get user's recent projects
            projects = await db_manager.get_user_projects(
                user_id=user_id,
                limit=5
            )
            
            if not projects or len(projects) == 0:
                logger.debug("No existing projects found")
                return None
            
            # For now, return the most recent project
            # In the future, we could match by session_id or project name
            latest_project = projects[0]
            
            project_data = {
                'project_id': latest_project['id'],
                'project_name': latest_project.get('project_name'),
                'architecture': latest_project.get('architecture'),
                'layout': latest_project.get('layout'),
                'blockly': latest_project.get('blockly'),
                'created_at': latest_project.get('created_at'),
                'updated_at': latest_project.get('updated_at')
            }
            
            logger.debug(f"Loaded project: {project_data['project_id']}")
            return project_data
            
        except Exception as e:
            logger.warning(f"Failed to load existing project: {e}")
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
            parts.append(f"**Existing Project:** {proj.get('project_name', 'Unnamed')}")
            
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