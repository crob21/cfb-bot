"""AI Integration Module"""

import os
import logging

logger = logging.getLogger('CFBBot.AI')

# Initialize AI assistant if API keys are available
ai_assistant = None
AI_AVAILABLE = False

try:
    from .ai_integration import AICharterAssistant

    # Check if we have at least one AI API key
    if os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'):
        ai_assistant = AICharterAssistant()
        AI_AVAILABLE = True
        logger.info("✅ AI assistant initialized")
    else:
        logger.info("ℹ️ AI keys not configured (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
except Exception as e:
    logger.warning(f"⚠️ Could not initialize AI assistant: {e}")

__all__ = ['ai_assistant', 'AI_AVAILABLE', 'AICharterAssistant']
