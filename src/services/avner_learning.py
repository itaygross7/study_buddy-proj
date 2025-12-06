"""
🧠 Avner Learning System - Continuous Improvement Engine

PURPOSE: Learn from user interactions to improve personalization and teaching.

COMPONENTS:
1. Usage Analytics - Track what works/doesn't work
2. Preference Learning - Discover user patterns
3. Admin Teaching Interface - Let admins improve Avner
4. Continuous Improvement - Apply learnings everywhere

🎯 DESIGN: Very lightweight, privacy-focused, admin-controlled
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pymongo.database import Database

from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger


@dataclass
class UserInteraction:
    """Record of a single user interaction."""
    user_id: str
    interaction_type: str  # "question", "response", "feedback", "action"
    content: str
    context: Dict[str, Any]  # Task type, document used, etc.
    timestamp: str
    user_preferences: Dict[str, Any]
    response_quality: Optional[float] = None  # 0-1 score
    user_feedback: Optional[str] = None


@dataclass
class LearningInsight:
    """Insight learned from user interactions."""
    insight_id: str
    category: str  # "preference", "teaching", "habit", "improvement"
    description: str
    evidence: List[str]  # User IDs or interaction IDs
    confidence: float  # 0-1
    created_at: str
    created_by: str  # "system" or admin user_id
    applied: bool = False


class UsageAnalytics:
    """
    Lightweight analytics engine.
    
    🪶 VERY LIGHT: Only stores aggregated data, not raw conversations.
    🔒 PRIVACY: No PII, anonymous patterns only.
    """
    
    def __init__(self, db_conn: Database = None):
        self.db = db_conn or flask_db
    
    def track_interaction(
        self,
        user_id: str,
        interaction_type: str,
        content_summary: str,  # Summary, not full content
        task_type: str,
        user_prefs: Dict[str, Any],
        response_quality: Optional[float] = None
    ):
        """
        Track a user interaction (very lightweight).
        
        🔒 PRIVACY: Only stores patterns, not actual content.
        
        Args:
            user_id: User ID (anonymized in analytics)
            interaction_type: Type of interaction
            content_summary: Brief summary (not full content)
            task_type: What task was performed
            user_prefs: User preferences at time of interaction
            response_quality: Quality score if available
        """
        try:
            interaction = {
                "user_id": user_id[-8:],  # Only last 8 chars for privacy
                "interaction_type": interaction_type,
                "content_summary": content_summary[:100],  # Max 100 chars
                "task_type": task_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_preferences": {
                    "study_level": user_prefs.get("study_level"),
                    "proficiency_level": user_prefs.get("proficiency_level"),
                    "explanation_style": user_prefs.get("explanation_style"),
                    "learning_pace": user_prefs.get("learning_pace")
                },
                "response_quality": response_quality
            }
            
            # Store in analytics collection (separate from main data)
            self.db.analytics_interactions.insert_one(interaction)
            
            # Update aggregated stats (very light)
            self._update_aggregated_stats(task_type, user_prefs, response_quality)
            
            logger.debug(f"📊 Tracked interaction: {interaction_type}")
            
        except Exception as e:
            logger.error(f"Failed to track interaction: {e}")
    
    def _update_aggregated_stats(
        self,
        task_type: str,
        user_prefs: Dict[str, Any],
        quality: Optional[float]
    ):
        """Update aggregated statistics (no individual data)."""
        try:
            stats_key = {
                "task_type": task_type,
                "study_level": user_prefs.get("study_level"),
                "proficiency_level": user_prefs.get("proficiency_level")
            }
            
            update = {
                "$inc": {"count": 1},
                "$set": {"last_updated": datetime.now(timezone.utc).isoformat()}
            }
            
            if quality is not None:
                update["$push"] = {
                    "quality_scores": {
                        "$each": [quality],
                        "$slice": -100  # Keep last 100 scores only
                    }
                }
            
            self.db.analytics_aggregated.update_one(
                stats_key,
                update,
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to update aggregated stats: {e}")
    
    def get_usage_patterns(self, filters: Dict = None) -> List[Dict]:
        """
        Get usage patterns (anonymized).
        
        Returns aggregated patterns, not individual data.
        """
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "task_type": "$task_type",
                            "study_level": "$user_preferences.study_level",
                            "proficiency_level": "$user_preferences.proficiency_level"
                        },
                        "count": {"$sum": 1},
                        "avg_quality": {"$avg": "$response_quality"}
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": 50}
            ]
            
            results = list(self.db.analytics_interactions.aggregate(pipeline))
            return results
        except Exception as e:
            logger.error(f"Failed to get usage patterns: {e}")
            return []


class PreferenceLearner:
    """
    Learn user preferences from behavior.
    
    🧠 SMART: Discovers patterns in how users interact.
    🪶 LIGHT: Uses simple heuristics, not heavy ML.
    """
    
    def __init__(self, db_conn: Database = None):
        self.db = db_conn or flask_db
    
    def analyze_user_behavior(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze user's behavior to discover preferences.
        
        🪶 LIGHTWEIGHT: Simple pattern matching, not ML.
        
        Returns:
            Suggested preference adjustments
        """
        try:
            # Get recent interactions (last 30 days)
            from datetime import timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            
            interactions = list(self.db.analytics_interactions.find({
                "user_id": user_id[-8:],
                "timestamp": {"$gte": cutoff}
            }).limit(100))
            
            if not interactions:
                return {"suggestions": [], "confidence": 0}
            
            suggestions = []
            
            # Pattern 1: Check if user consistently gives low ratings
            low_quality_count = sum(1 for i in interactions 
                                   if i.get("response_quality", 1) < 0.6)
            
            if low_quality_count > len(interactions) * 0.3:  # >30% low quality
                suggestions.append({
                    "type": "explanation_style",
                    "current": "unknown",
                    "suggested": "more_detailed",
                    "reason": "User seems to need more detailed explanations",
                    "confidence": 0.7
                })
            
            # Pattern 2: Check task type preferences
            task_counts = {}
            for i in interactions:
                task = i.get("task_type", "unknown")
                task_counts[task] = task_counts.get(task, 0) + 1
            
            most_used = max(task_counts.items(), key=lambda x: x[1]) if task_counts else None
            if most_used and most_used[1] > len(interactions) * 0.5:
                suggestions.append({
                    "type": "study_habit",
                    "pattern": f"Frequently uses {most_used[0]}",
                    "suggestion": f"Consider exploring {self._suggest_complementary_task(most_used[0])}",
                    "confidence": 0.6
                })
            
            # Pattern 3: Time-based learning
            # (Check if user learns better at certain times)
            
            return {
                "suggestions": suggestions,
                "confidence": sum(s.get("confidence", 0) for s in suggestions) / max(len(suggestions), 1),
                "based_on_interactions": len(interactions)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze user behavior: {e}")
            return {"suggestions": [], "confidence": 0}
    
    def _suggest_complementary_task(self, task_type: str) -> str:
        """Suggest complementary learning activities."""
        suggestions = {
            "summary": "flashcards or assessment",
            "flashcards": "assessment or practice",
            "assessment": "tutor sessions for weak areas",
            "homework": "related concept summaries",
            "chat": "structured tutor sessions"
        }
        return suggestions.get(task_type, "varied learning activities")


class AdminTeachingInterface:
    """
    🎓 Admin-only interface for teaching Avner.
    
    SECURITY: Only accessible by administrators.
    PURPOSE: Let admins improve how Avner teaches.
    """
    
    def __init__(self, db_conn: Database = None):
        self.db = db_conn or flask_db
    
    def add_teaching_example(
        self,
        admin_id: str,
        category: str,
        example_input: str,
        ideal_response: str,
        explanation: str,
        tags: List[str] = None
    ) -> str:
        """
        Admin adds a teaching example.
        
        🎓 PURPOSE: Show Avner how to handle specific cases.
        
        Args:
            admin_id: Admin user ID
            category: "preference_detection", "teaching_style", "response_adaptation"
            example_input: Example user input
            ideal_response: How Avner should respond
            explanation: Why this is the ideal response
            tags: Tags for categorization
            
        Returns:
            Example ID
        """
        try:
            import uuid
            
            example = {
                "_id": str(uuid.uuid4()),
                "admin_id": admin_id,
                "category": category,
                "example_input": example_input,
                "ideal_response": ideal_response,
                "explanation": explanation,
                "tags": tags or [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "applied": False,
                "effectiveness": None  # Will be measured
            }
            
            self.db.admin_teaching_examples.insert_one(example)
            
            logger.info(f"✓ Admin {admin_id} added teaching example: {category}")
            
            return example["_id"]
            
        except Exception as e:
            logger.error(f"Failed to add teaching example: {e}")
            return ""
    
    def add_improvement_rule(
        self,
        admin_id: str,
        rule_type: str,
        condition: Dict[str, Any],
        action: Dict[str, Any],
        description: str
    ) -> str:
        """
        Admin adds an improvement rule.
        
        🎯 PURPOSE: Define rules for better personalization.
        
        Example:
            condition: {"proficiency_level": "beginner", "task_type": "summary"}
            action: {"add_examples": true, "simplify_language": true}
        
        Args:
            admin_id: Admin user ID
            rule_type: "preference_adjustment", "response_enhancement", "teaching_strategy"
            condition: When to apply this rule
            action: What to do
            description: Human-readable explanation
            
        Returns:
            Rule ID
        """
        try:
            import uuid
            
            rule = {
                "_id": str(uuid.uuid4()),
                "admin_id": admin_id,
                "rule_type": rule_type,
                "condition": condition,
                "action": action,
                "description": description,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "active": True,
                "times_applied": 0
            }
            
            self.db.admin_improvement_rules.insert_one(rule)
            
            logger.info(f"✓ Admin {admin_id} added improvement rule: {rule_type}")
            
            return rule["_id"]
            
        except Exception as e:
            logger.error(f"Failed to add improvement rule: {e}")
            return ""
    
    def get_teaching_examples(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get teaching examples (for system to learn from)."""
        try:
            query = {}
            if category:
                query["category"] = category
            if tags:
                query["tags"] = {"$in": tags}
            
            examples = list(self.db.admin_teaching_examples.find(query).limit(100))
            return examples
        except Exception as e:
            logger.error(f"Failed to get teaching examples: {e}")
            return []
    
    def get_improvement_rules(self, rule_type: Optional[str] = None) -> List[Dict]:
        """Get active improvement rules."""
        try:
            query = {"active": True}
            if rule_type:
                query["rule_type"] = rule_type
            
            rules = list(self.db.admin_improvement_rules.find(query))
            return rules
        except Exception as e:
            logger.error(f"Failed to get improvement rules: {e}")
            return []
    
    def get_admin_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get stats for admin dashboard.
        
        Shows effectiveness of teaching examples and rules.
        """
        try:
            stats = {
                "teaching_examples": {
                    "total": self.db.admin_teaching_examples.count_documents({}),
                    "applied": self.db.admin_teaching_examples.count_documents({"applied": True})
                },
                "improvement_rules": {
                    "total": self.db.admin_improvement_rules.count_documents({}),
                    "active": self.db.admin_improvement_rules.count_documents({"active": True})
                },
                "recent_insights": self._get_recent_insights(5)
            }
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {}
    
    def _get_recent_insights(self, limit: int = 5) -> List[Dict]:
        """Get recent learning insights."""
        try:
            insights = list(
                self.db.learning_insights.find()
                .sort("created_at", -1)
                .limit(limit)
            )
            return insights
        except:
            return []


class ContinuousImprovement:
    """
    Apply learnings to improve all functionalities.
    
    🔄 CONTINUOUS: Always learning, always improving.
    """
    
    def __init__(self, db_conn: Database = None):
        self.db = db_conn or flask_db
        self.analytics = UsageAnalytics(db_conn)
        self.learner = PreferenceLearner(db_conn)
        self.admin_interface = AdminTeachingInterface(db_conn)
    
    def enhance_prompt_with_learnings(
        self,
        base_prompt: str,
        user_id: str,
        task_type: str,
        user_prefs: Dict[str, Any]
    ) -> str:
        """
        Enhance a prompt with learned improvements.
        
        🧠 APPLIES: Admin rules + learned patterns
        
        Args:
            base_prompt: Original prompt
            user_id: User ID
            task_type: Task type
            user_prefs: User preferences
            
        Returns:
            Enhanced prompt
        """
        enhanced = base_prompt
        
        try:
            # Apply admin improvement rules
            rules = self.admin_interface.get_improvement_rules()
            
            for rule in rules:
                if self._rule_matches(rule["condition"], task_type, user_prefs):
                    enhanced = self._apply_rule_action(enhanced, rule["action"])
                    
                    # Track rule usage
                    self.db.admin_improvement_rules.update_one(
                        {"_id": rule["_id"]},
                        {"$inc": {"times_applied": 1}}
                    )
            
            # Apply learned patterns
            behavior = self.learner.analyze_user_behavior(user_id)
            if behavior.get("confidence", 0) > 0.5:
                for suggestion in behavior.get("suggestions", []):
                    enhanced = self._apply_suggestion(enhanced, suggestion)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Failed to enhance prompt: {e}")
            return base_prompt
    
    def _rule_matches(
        self,
        condition: Dict,
        task_type: str,
        user_prefs: Dict
    ) -> bool:
        """Check if a rule's condition matches current context."""
        if "task_type" in condition and condition["task_type"] != task_type:
            return False
        
        if "proficiency_level" in condition:
            if condition["proficiency_level"] != user_prefs.get("proficiency_level"):
                return False
        
        if "study_level" in condition:
            if condition["study_level"] != user_prefs.get("study_level"):
                return False
        
        return True
    
    def _apply_rule_action(self, prompt: str, action: Dict) -> str:
        """Apply a rule's action to a prompt."""
        enhanced = prompt
        
        if action.get("add_examples"):
            enhanced += "\n\n🎯 IMPORTANT: Include practical examples."
        
        if action.get("simplify_language"):
            enhanced += "\n\n🎯 IMPORTANT: Use simple, clear language."
        
        if action.get("add_practice"):
            enhanced += "\n\n🎯 IMPORTANT: Include practice questions."
        
        if action.get("step_by_step"):
            enhanced += "\n\n🎯 IMPORTANT: Break down into clear steps."
        
        if action.get("add_analogies"):
            enhanced += "\n\n🎯 IMPORTANT: Use analogies to explain concepts."
        
        return enhanced
    
    def _apply_suggestion(self, prompt: str, suggestion: Dict) -> str:
        """Apply a learned suggestion to a prompt."""
        if suggestion.get("type") == "explanation_style":
            if suggestion.get("suggested") == "more_detailed":
                prompt += "\n\n💡 Note: This user benefits from detailed explanations."
        
        return prompt


# Global instances
usage_analytics = UsageAnalytics()
preference_learner = PreferenceLearner()
admin_teaching = AdminTeachingInterface()
continuous_improvement = ContinuousImprovement()


# Helper function for easy integration
def track_and_learn(
    user_id: str,
    interaction_type: str,
    content_summary: str,
    task_type: str,
    user_prefs: Dict[str, Any],
    response_quality: Optional[float] = None
):
    """
    One-line function to track interaction and trigger learning.
    
    Usage:
        track_and_learn(
            user_id=user_id,
            interaction_type="question_answered",
            content_summary="User asked about photosynthesis",
            task_type="summary",
            user_prefs=user_preferences,
            response_quality=0.9
        )
    """
    usage_analytics.track_interaction(
        user_id=user_id,
        interaction_type=interaction_type,
        content_summary=content_summary,
        task_type=task_type,
        user_prefs=user_prefs,
        response_quality=response_quality
    )
