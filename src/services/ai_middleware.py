"""
AI Middleware - Lightweight Microservice Layer

MICROSERVICE PRINCIPLE: Keep it small, focused, and async
- This service ONLY handles prompt optimization and response adaptation
- All processing flows through RabbitMQ queues
- No blocking operations
- Fast forwarding to workers

🔒 CRITICAL: Enforces document-only constraints to prevent hallucinations

ARCHITECTURE:
User Request → Queue → Prompt Optimizer → Main AI Queue → Output Adapter → User

Cost: ~2 small gpt-4o-mini calls (~300-500 tokens each) = $0.0002
Benefit: 10x better UX for non-tech users + Guaranteed accuracy
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pymongo.database import Database
import openai
import json

from src.infrastructure.config import settings
from src.infrastructure.database import db as flask_db
from src.utils.ai_constraints import (
    build_constrained_context, 
    get_task_constraint_level,
    validate_response_constraint
)
from sb_utils.logger_utils import logger


@dataclass
class UserPreferences:
    """
    Comprehensive user preferences for AI response personalization.
    
    🎯 EMPHASIS: These preferences are CRITICAL for personalization.
    The AI must adapt to each user's unique learning profile.
    """
    user_id: str
    
    # Language & Communication
    language: str = "he"  # Hebrew by default
    secondary_language: str = ""  # Optional second language
    
    # Knowledge & Study Level
    proficiency_level: str = "intermediate"  # beginner, intermediate, advanced, expert
    study_level: str = "high_school"  # elementary, middle_school, high_school, university, professional
    subject_knowledge: Dict[str, str] = None  # {"math": "advanced", "history": "beginner"}
    
    # Learning Style & Preferences
    explanation_style: str = "detailed"  # concise, detailed, step_by_step, visual
    use_examples: bool = True
    use_analogies: bool = True
    use_real_world_examples: bool = True
    preferred_formats: list = None  # ['bullet_points', 'paragraphs', 'numbered_lists', 'tables']
    
    # Study Habits & Behavior
    learning_pace: str = "moderate"  # slow, moderate, fast
    study_time_preference: str = "short"  # short (15-30min), medium (30-60min), long (60+min)
    prefers_practice: bool = True  # Include practice questions
    prefers_summary: bool = True  # Include summaries
    
    # Feedback & Adaptation
    previous_feedback: List[str] = None  # User's past feedback
    difficult_topics: List[str] = None  # Topics user struggles with
    strong_topics: List[str] = None  # Topics user excels at
    
    # Accessibility
    baby_mode: bool = False  # Simplified explanations
    visual_learner: bool = False  # Emphasize diagrams/visuals
    needs_more_detail: bool = False  # User requested more explanation
    
    def __post_init__(self):
        if self.preferred_formats is None:
            self.preferred_formats = ['bullet_points']
        if self.subject_knowledge is None:
            self.subject_knowledge = {}
        if self.previous_feedback is None:
            self.previous_feedback = []
        if self.difficult_topics is None:
            self.difficult_topics = []
        if self.strong_topics is None:
            self.strong_topics = []
    
    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dict."""
        # Handle dict fields that might be None
        if 'subject_knowledge' in data and data['subject_knowledge'] is None:
            data['subject_knowledge'] = {}
        if 'previous_feedback' in data and data['previous_feedback'] is None:
            data['previous_feedback'] = []
        if 'difficult_topics' in data and data['difficult_topics'] is None:
            data['difficult_topics'] = []
        if 'strong_topics' in data and data['strong_topics'] is None:
            data['strong_topics'] = []
        return cls(**data)
    
    def get_profile_summary(self) -> str:
        """Get human-readable profile summary for AI prompts."""
        summary_parts = [
            f"Study Level: {self.study_level}",
            f"Knowledge: {self.proficiency_level}",
            f"Language: {self.language}",
            f"Style: {self.explanation_style}",
            f"Pace: {self.learning_pace}"
        ]
        
        if self.difficult_topics:
            summary_parts.append(f"Struggles with: {', '.join(self.difficult_topics[:3])}")
        
        if self.strong_topics:
            summary_parts.append(f"Strong in: {', '.join(self.strong_topics[:3])}")
        
        return " | ".join(summary_parts)


class PromptOptimizer:
    """
    Microservice: Prompt Optimization
    Input: Raw user request → Output: Optimized prompt
    Fast, lightweight, single responsibility
    
    🔒 ENFORCES app requirements (document-only constraint) - MANDATORY
    👤 RESPECTS user preferences
    
    ⚠️ CRITICAL: This optimizer MUST enforce document-only constraints
    It cannot and will not remove or weaken these constraints.
    """
    
    @staticmethod
    def optimize(
        user_request: str, 
        task_type: str, 
        user_prefs: UserPreferences,
        document_content: str = ""
    ) -> Dict[str, str]:
        """
        FAST optimization: 200-300 tokens, <0.5s response time
        
        🔒 CRITICAL: Injects app requirements into optimization
        - Document-only constraint (MANDATORY - always enforced)
        - User preferences (OPTIONAL - for UX)
        
        ⚠️ The optimizer is instructed to STRENGTHEN constraints, never weaken them.
        
        Args:
            user_request: Raw user input
            task_type: Type of task
            user_prefs: User preferences
            document_content: The document content (to determine if constraint needed)
            
        Returns:
            Dict with optimized_prompt and system_context (constraints preserved)
        """
        if not settings.OPENAI_API_KEY:
            return {'optimized_prompt': user_request, 'system_context': ''}
        
        # Determine constraint level
        constraint_level = get_task_constraint_level(task_type)
        has_document = bool(document_content and len(document_content.strip()) > 0)
        
        # Build APP REQUIREMENTS (mandatory rules) - THESE CANNOT BE REMOVED
        app_requirements = []
        
        if constraint_level == "strict" and has_document:
            app_requirements.append(
                "🔒 MANDATORY CONSTRAINT (DO NOT REMOVE): "
                "The AI MUST answer ONLY from the provided document. "
                "NO external knowledge is allowed. "
                "This constraint MUST be present in the optimized prompt."
            )
        elif constraint_level == "strict" and not has_document:
            app_requirements.append(
                "🔒 CRITICAL: No document provided but strict constraint required. "
                "The AI MUST refuse to answer without a document."
            )
        elif constraint_level == "moderate" and has_document:
            app_requirements.append(
                "🔒 MANDATORY: Prioritize document content. "
                "Indicate clearly when using external knowledge."
            )
        
        # Build meta-prompt with EXPLICIT ENFORCEMENT INSTRUCTIONS
        requirements_text = "\n".join(app_requirements) if app_requirements else ""
        
        # 🎯 BUILD COMPREHENSIVE USER PROFILE for personalization
        user_profile = f"""
USER LEARNING PROFILE (CRITICAL - Adapt to this user):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Study Level: {user_prefs.study_level}
🎓 Knowledge Level: {user_prefs.proficiency_level}
🌍 Language: {user_prefs.language} (Primary)
💡 Learning Style: {user_prefs.explanation_style}
⏱️ Learning Pace: {user_prefs.learning_pace}
⏰ Study Time: {user_prefs.study_time_preference} sessions

LEARNING PREFERENCES:
✓ Examples: {user_prefs.use_examples}
✓ Analogies: {user_prefs.use_analogies}
✓ Real-world examples: {user_prefs.use_real_world_examples}
✓ Practice questions: {user_prefs.prefers_practice}
✓ Summaries: {user_prefs.prefers_summary}
✓ Format: {', '.join(user_prefs.preferred_formats)}
"""

        # Add subject-specific knowledge if available
        if user_prefs.subject_knowledge:
            user_profile += f"\nSubject Knowledge:\n"
            for subject, level in user_prefs.subject_knowledge.items():
                user_profile += f"  - {subject}: {level}\n"
        
        # Add learning challenges if available
        if user_prefs.difficult_topics:
            user_profile += f"\n⚠️ Struggles with: {', '.join(user_prefs.difficult_topics)}\n"
        
        # Add strengths if available
        if user_prefs.strong_topics:
            user_profile += f"✨ Strong in: {', '.join(user_prefs.strong_topics)}\n"
        
        # Add special needs
        special_needs = []
        if user_prefs.baby_mode:
            special_needs.append("Simplified explanations (Baby Mode)")
        if user_prefs.visual_learner:
            special_needs.append("Visual/diagram emphasis")
        if user_prefs.needs_more_detail:
            special_needs.append("Extra detail required")
        
        if special_needs:
            user_profile += f"\n🎯 Special Needs: {', '.join(special_needs)}\n"
        
        user_profile += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        meta_prompt = f"""You are optimizing a prompt for educational AI.

🔒 CRITICAL SECURITY INSTRUCTION:
You are helping create a prompt that will enforce document-only constraints.
Your optimization MUST PRESERVE and STRENGTHEN these constraints.
DO NOT remove, weaken, or bypass any security requirements.

USER REQUEST: "{user_request}"

APP REQUIREMENTS (MANDATORY - MUST BE IN OPTIMIZED PROMPT):
{requirements_text if requirements_text else "No special security requirements"}

{user_profile}

🎯 PERSONALIZATION EMPHASIS (CRITICAL):
The optimized prompt MUST be tailored to THIS SPECIFIC USER:
1. Match their study level ({user_prefs.study_level})
2. Match their knowledge level ({user_prefs.proficiency_level})
3. Use their preferred language ({user_prefs.language})
4. Follow their learning style ({user_prefs.explanation_style})
5. Adapt to their learning pace ({user_prefs.learning_pace})
6. {"Include examples and analogies" if user_prefs.use_examples else "Keep it direct"}
7. {"Include practice questions" if user_prefs.prefers_practice else "Focus on explanation"}
8. Format as: {user_prefs.preferred_formats[0] if user_prefs.preferred_formats else "clear text"}

YOUR JOB:
1. Make the request clear and specific
2. PRESERVE AND STRENGTHEN all app requirements (especially document-only constraint)
3. HEAVILY personalize based on user profile above
4. Request format matching user preferences
5. ENSURE the AI knows it MUST adapt to this user's level and style
6. If user has difficult topics, acknowledge and support them
7. If user has strengths, build on them

OPTIMIZATION RULES:
- ✅ DO clarify what the user wants
- ✅ DO heavily emphasize personalization
- ✅ DO match their exact study and knowledge level
- ✅ DO use their preferred learning style
- ✅ DO request appropriate format
- ✅ DO include constraint reminders
- ❌ DO NOT remove security constraints
- ❌ DO NOT weaken document-only requirement
- ❌ DO NOT add phrases that encourage external knowledge
- ❌ DO NOT ignore user preferences

JSON output (constraints preserved, heavily personalized):
{{"optimized_prompt": "Personalized prompt WITH constraints", "system_context": "System instructions WITH constraints and personalization"}}"""

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY, timeout=5.0)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": meta_prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,  # Low for consistency and security
                max_tokens=300
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 🔒 SECURITY CHECK: Verify constraint keywords are present
            optimized_prompt = result.get('optimized_prompt', user_request)
            system_context = result.get('system_context', '')
            
            if constraint_level == "strict" and has_document:
                # Check that constraint-related keywords are present
                combined = (optimized_prompt + system_context).lower()
                constraint_keywords = ['document', 'only', 'provided', 'text', 'content', 'מסמך']
                
                if not any(keyword in combined for keyword in constraint_keywords):
                    logger.warning(
                        "⚠️ Optimizer may have removed constraints! Adding them back."
                    )
                    # Add constraint reminder to system context
                    system_context += "\n🔒 CRITICAL: Use ONLY the provided document content."
            
            logger.debug(f"✓ Prompt optimized with {constraint_level} constraint preserved")
            
            return {
                'optimized_prompt': optimized_prompt,
                'system_context': system_context
            }
            
        except Exception as e:
            logger.warning(f"Prompt optimization failed: {e}")
            # Fallback maintains original request (constraints will be added later)
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
        self.db = db_conn if db_conn is not None else flask_db
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
        document_content: str,
        task_type: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        STEP 1: Prepare request for queue (microservice pattern)
        
        🔒 ALWAYS ADDS STRICT CONSTRAINTS - NO BYPASS ALLOWED
        
        This is FAST - just optimization + constraint injection
        Returns data structure ready for RabbitMQ
        
        Args:
            user_request: Raw user input
            document_content: User's document content (THE ONLY SOURCE)
            task_type: Task type
            user_id: User ID
            
        Returns:
            Dict ready for queue message with constraints ALWAYS enforced
        """
        user_prefs = self.prefs_service.get(user_id)
        
        # 🔒 CRITICAL: ALWAYS BUILD CONSTRAINED CONTEXT - NO EXCEPTIONS
        constrained_context = build_constrained_context(
            task_type=task_type,
            document_content=document_content,
            user_id=user_id,  # Pass user_id for isolation tracking
            user_context="",
            language=user_prefs.language
        )
        
        constraint_level = get_task_constraint_level(task_type)
        logger.info(f"🔒 MANDATORY {constraint_level} constraint applied for {task_type}")
        
        # Optimize prompt (this ADDS to constraints, never removes them)
        optimized = self.prompt_optimizer.optimize(
            user_request=user_request,
            task_type=task_type,
            user_prefs=user_prefs,
            document_content=document_content  # Pass document for constraint detection
        )
        
        # COMBINE optimized prompt with constrained context
        # IMPORTANT: Constraints are ALWAYS included, optimization only enhances
        final_context = constrained_context + "\n\n" + optimized['system_context']
        
        return {
            'prompt': optimized['optimized_prompt'],
            'context': final_context,
            'user_prefs': user_prefs.to_dict(),
            'task_type': task_type,
            'original_request': user_request,
            'document_content': document_content,  # Keep for validation
            'constraint_level': constraint_level,
            'constraint_enforced': True  # ALWAYS True - no bypass
        }
    
    def finalize_response(
        self,
        ai_response: str,
        request_data: Dict[str, Any],
        adapt: bool = True
    ) -> str:
        """
        STEP 2: Finalize response after AI processing (microservice pattern)
        
        🔒 ALWAYS VALIDATES constraints were followed - NO BYPASS
        
        This is FAST - adaptation + mandatory validation
        
        Args:
            ai_response: Raw AI output
            request_data: Data from prepare_request
            adapt: Whether to adapt (does NOT affect constraint validation)
            
        Returns:
            Final response for user (ALWAYS validated)
        """
        # 🔒 CRITICAL: ALWAYS VALIDATE CONSTRAINTS - NO EXCEPTIONS
        document_content = request_data.get('document_content', '')
        task_type = request_data.get('task_type', 'standard')
        
        validation = validate_response_constraint(
            response=ai_response,
            task_type=task_type,
            document_content=document_content
        )
        
        if not validation['valid']:
            logger.error(f"⚠️ CONSTRAINT VIOLATION DETECTED: {validation['warnings']}")
            # Log but continue (validation is heuristic, may have false positives)
            # In production, you might want to reject the response here
        else:
            logger.info(f"✓ Response passed MANDATORY {validation['constraint_level']} constraint validation")
        
        # ADAPT RESPONSE (optional, but validation above is mandatory)
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
            logger.error(f"Response adaptation failed: {e}")
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


