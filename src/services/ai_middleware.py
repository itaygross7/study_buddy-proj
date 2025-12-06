"""
AI Middleware - Lightweight Microservice Layer

MICROSERVICE PRINCIPLE: Keep it small, focused, and async
- This service ONLY handles prompt optimization and response adaptation
- All processing flows through RabbitMQ queues
- No blocking operations
- Fast forwarding to workers

ARCHITECTURE:
User Request → Queue → Prompt Optimizer → Main AI Queue → Output Adapter → User

Cost: ~2 small gpt-4o-mini calls (~300-500 tokens each) = $0.0002
Benefit: 10x better UX for non-tech users
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pymongo.database import Database
import openai
import json

from src.infrastructure.config import settings
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger


@dataclass
class UserPreferences:
    """Lightweight user preferences - stored in DB, cached in memory."""
    user_id: str
    language: str = "he"
    proficiency_level: str = "intermediate"  # beginner, intermediate, advanced
    explanation_style: str = "detailed"  # concise, detailed, step_by_step
    use_examples: bool = True
    use_analogies: bool = True
    baby_mode: bool = False
    preferred_formats: list = None
    
    def __post_init__(self):
        if self.preferred_formats is None:
            self.preferred_formats = ['bullet_points']
    
    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dict."""
        return cls(**data)


class PromptOptimizer:
    """
    Microservice: Prompt Optimization
    Input: Raw user request → Output: Optimized prompt
    Fast, lightweight, single responsibility
    """
    
    @staticmethod
    def optimize(user_request: str, task_type: str, user_prefs: UserPreferences) -> Dict[str, str]:
        """
        FAST optimization: 200-300 tokens, <0.5s response time
        
        Args:
            user_request: Raw user input
            task_type: Type of task
            user_prefs: User preferences
            
        Returns:
            Dict with optimized_prompt and system_context
        """
        if not settings.OPENAI_API_KEY:
            return {'optimized_prompt': user_request, 'system_context': ''}
        
        # Ultra-concise meta-prompt for speed
        meta_prompt = f"""Optimize for {user_prefs.proficiency_level} {user_prefs.language} speaker:
"{user_request}"
Task: {task_type}

JSON: {{"optimized_prompt": "...", "system_context": "..."}}"""

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY, timeout=5.0)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": meta_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=250  # SMALL: keep it fast
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"✓ Prompt optimized (fast)")
            return {
                'optimized_prompt': result.get('optimized_prompt', user_request),
                'system_context': result.get('system_context', '')
            }
            
        except Exception as e:
            logger.warning(f"Prompt optimization failed: {e}")
            return {'optimized_prompt': user_request, 'system_context': ''}


class ResponseAdapter:
    """
    Microservice: Response Adaptation
    Input: Raw AI response → Output: User-optimized response
    Fast, lightweight, single responsibility
    """
    
    @staticmethod
    def adapt(ai_response: str, user_prefs: UserPreferences, task_type: str) -> str:
        """
        FAST adaptation: Smart token sizing, <0.8s response time
        
        Args:
            ai_response: Raw AI output
            user_prefs: User preferences
            task_type: Type of task
            
        Returns:
            Adapted response
        """
        if not settings.OPENAI_API_KEY:
            return ai_response
        
        # Skip if already optimized or too short
        if len(ai_response) < 100 or "🍼" in ai_response:
            return ai_response
        
        # Ultra-concise adaptation prompt
        adaptation_prompt = f"""Adapt for {user_prefs.proficiency_level}:
{ai_response}

Style: {user_prefs.explanation_style}
{"Add examples" if user_prefs.use_examples else ""}

Output only adapted text."""

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY, timeout=8.0)
            
            # Smart sizing: don't waste tokens
            input_tokens = len(ai_response.split())
            max_tokens = min(800, input_tokens + 200)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": adaptation_prompt}],
                temperature=0.3,
                max_tokens=max_tokens
            )
            
            adapted = response.choices[0].message.content.strip()
            logger.debug(f"✓ Response adapted (fast)")
            return adapted
            
        except Exception as e:
            logger.warning(f"Response adaptation failed: {e}")
            return ai_response


class PreferencesService:
    """
    Microservice: User Preferences Management
    Single responsibility: Load/save user preferences
    """
    
    def __init__(self, db_conn: Database = None):
        self.db = db_conn or flask_db
        self._cache = {}  # Simple cache for performance
    
    def get(self, user_id: str, use_cache: bool = True) -> UserPreferences:
        """Load preferences (cached)."""
        if use_cache and user_id in self._cache:
            return self._cache[user_id]
        
        try:
            doc = self.db.user_preferences.find_one({"user_id": user_id})
            prefs = UserPreferences.from_dict(doc) if doc else UserPreferences(user_id=user_id)
            self._cache[user_id] = prefs
            return prefs
        except Exception as e:
            logger.error(f"Failed to load preferences: {e}")
            return UserPreferences(user_id=user_id)
    
    def save(self, prefs: UserPreferences):
        """Save preferences and update cache."""
        try:
            self.db.user_preferences.update_one(
                {"user_id": prefs.user_id},
                {"$set": prefs.to_dict()},
                upsert=True
            )
            self._cache[prefs.user_id] = prefs
            logger.debug(f"✓ Saved preferences for {prefs.user_id}")
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
    
    def clear_cache(self, user_id: Optional[str] = None):
        """Clear cache."""
        if user_id:
            self._cache.pop(user_id, None)
        else:
            self._cache.clear()


class AIMiddleware:
    """
    LIGHTWEIGHT Microservice Orchestrator
    
    DESIGN PRINCIPLES:
    - Single Responsibility: Coordinate prompt optimization + response adaptation
    - Stateless: No heavy processing, just orchestration
    - Fast: All operations are async-ready
    - Microservice: Small, focused, one job
    
    FLOW:
    1. User request → optimize_prompt() → queue message
    2. Queue worker → AI processing → result
    3. Result → adapt_response() → user
    """
    
    def __init__(self, db_conn: Database = None):
        self.prefs_service = PreferencesService(db_conn)
        self.prompt_optimizer = PromptOptimizer()
        self.response_adapter = ResponseAdapter()
    
    def prepare_request(
        self,
        user_request: str,
        task_context: str,
        task_type: str,
        user_id: str,
        optimize: bool = True
    ) -> Dict[str, Any]:
        """
        STEP 1: Prepare request for queue (microservice pattern)
        
        This is FAST - just optimization, no heavy processing
        Returns data structure ready for RabbitMQ
        
        Args:
            user_request: Raw user input
            task_context: Context
            task_type: Task type
            user_id: User ID
            optimize: Whether to optimize
            
        Returns:
            Dict ready for queue message
        """
        user_prefs = self.prefs_service.get(user_id)
        
        if optimize:
            optimized = self.prompt_optimizer.optimize(
                user_request=user_request,
                task_type=task_type,
                user_prefs=user_prefs
            )
        else:
            optimized = {
                'optimized_prompt': user_request,
                'system_context': task_context
            }
        
        return {
            'prompt': optimized['optimized_prompt'],
            'context': optimized['system_context'],
            'user_prefs': user_prefs.to_dict(),
            'task_type': task_type,
            'original_request': user_request
        }
    
    def finalize_response(
        self,
        ai_response: str,
        request_data: Dict[str, Any],
        adapt: bool = True
    ) -> str:
        """
        STEP 2: Finalize response after AI processing (microservice pattern)
        
        This is FAST - just adaptation, no heavy processing
        
        Args:
            ai_response: Raw AI output
            request_data: Data from prepare_request
            adapt: Whether to adapt
            
        Returns:
            Final response for user
        """
        if not adapt:
            return ai_response
        
        try:
            user_prefs = UserPreferences.from_dict(request_data.get('user_prefs', {}))
            task_type = request_data.get('task_type', 'standard')
            
            adapted = self.response_adapter.adapt(
                ai_response=ai_response,
                user_prefs=user_prefs,
                task_type=task_type
            )
            return adapted
        except Exception as e:
            logger.error(f"Response finalization failed: {e}")
            return ai_response


# Global lightweight service instances
preferences_service = PreferencesService()
ai_middleware = AIMiddleware()


def get_user_preferences(user_id: str) -> UserPreferences:
    """Helper: Get user preferences."""
    return preferences_service.get(user_id)


def save_user_preferences(prefs: UserPreferences):
    """Helper: Save user preferences."""
    preferences_service.save(prefs)


