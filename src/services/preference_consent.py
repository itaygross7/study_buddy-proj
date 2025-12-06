"""
User Preference Consent & Collection System

PURPOSE: Politely ask users about preferences before storing them.
PRINCIPLE: User-friendly, transparent, optional, and respectful.

🎯 DESIGN PHILOSOPHY:
- Polite and friendly
- Light and relaxed tone
- Clear explanation of benefits
- Always optional
- Easy to skip or update
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from pymongo.database import Database

from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger


@dataclass
class ConsentStatus:
    """Track what user has consented to."""
    user_id: str
    preferences_collection_allowed: bool = False
    feedback_collection_allowed: bool = False
    learning_analytics_allowed: bool = False
    consent_date: str = ""
    last_asked: str = ""
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "preferences_collection_allowed": self.preferences_collection_allowed,
            "feedback_collection_allowed": self.feedback_collection_allowed,
            "learning_analytics_allowed": self.learning_analytics_allowed,
            "consent_date": self.consent_date,
            "last_asked": self.last_asked
        }


class PreferenceConsentManager:
    """
    Manages user consent for preference collection.
    
    DESIGN: Polite, transparent, optional.
    """
    
    def __init__(self, db_conn: Database = None):
        self.db = db_conn if db_conn is not None else flask_db
    
    def get_consent_status(self, user_id: str) -> ConsentStatus:
        """Get user's consent status."""
        try:
            doc = self.db.user_consent.find_one({"user_id": user_id})
            if doc:
                return ConsentStatus(
                    user_id=user_id,
                    preferences_collection_allowed=doc.get('preferences_collection_allowed', False),
                    feedback_collection_allowed=doc.get('feedback_collection_allowed', False),
                    learning_analytics_allowed=doc.get('learning_analytics_allowed', False),
                    consent_date=doc.get('consent_date', ''),
                    last_asked=doc.get('last_asked', '')
                )
            return ConsentStatus(user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to load consent status: {e}")
            return ConsentStatus(user_id=user_id)
    
    def save_consent(self, consent: ConsentStatus):
        """Save user consent."""
        try:
            from datetime import datetime, timezone
            consent.consent_date = datetime.now(timezone.utc).isoformat()
            
            self.db.user_consent.update_one(
                {"user_id": consent.user_id},
                {"$set": consent.to_dict()},
                upsert=True
            )
            logger.info(f"✓ Saved consent for user {consent.user_id}")
        except Exception as e:
            logger.error(f"Failed to save consent: {e}")
    
    def should_ask_for_consent(self, user_id: str) -> bool:
        """
        Check if we should ask user for consent.
        
        Ask if:
        - Never asked before
        - Asked but they said "maybe later" (after 7 days)
        - They haven't given any consent
        """
        consent = self.get_consent_status(user_id)
        
        # Never asked
        if not consent.last_asked:
            return True
        
        # They already gave consent
        if consent.preferences_collection_allowed:
            return False
        
        # Check if 7 days passed since last ask
        try:
            from datetime import datetime, timezone, timedelta
            last_asked = datetime.fromisoformat(consent.last_asked)
            days_since = (datetime.now(timezone.utc) - last_asked).days
            
            # Ask again after 7 days
            return days_since >= 7
        except:
            return False
    
    def mark_asked(self, user_id: str):
        """Mark that we asked the user (even if they skipped)."""
        try:
            from datetime import datetime, timezone
            self.db.user_consent.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "last_asked": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to mark asked: {e}")


def get_consent_prompt_hebrew() -> Dict[str, str]:
    """
    Get friendly Hebrew consent prompt.
    
    TONE: Polite, friendly, clear benefits, easy to skip.
    """
    return {
        "title": "📚 רוצה חוויה אישית יותר?",
        
        "message": """
היי! 👋

אנחנו יכולים לעזור לך ללמוד טוב יותר אם נכיר אותך קצת.

**למה זה טוב בשבילך?**
✨ תשובות מותאמות לרמה שלך
✨ הסברים בסגנון שמתאים לך
✨ דוגמאות שבאמת עוזרות לך
✨ תוכן שמתאים לקצב הלימוד שלך

**מה נשמור?**
📝 רמת הידע שלך (מתחיל/בינוני/מתקדם)
📝 סגנון הלמידה שלך (מפורט/תמציתי/צעד אחר צעד)
📝 השפה שלך והעדפות תצוגה
📝 נושאים שקשים/קלים לך (אם תרצה לשתף)

**חשוב לדעת:**
🔒 המידע נשאר רק אצלך
🔒 אף אחד אחר לא רואה את זה
🔒 אפשר לשנות או למחוק בכל זמן
🔒 זה לגמרי אופציונלי - אין חובה

**אז מה את/ה אומר/ת?**
        """,
        
        "options": {
            "yes": "כן, בוא נתאים את החוויה! 🎯",
            "later": "אולי אחר כך",
            "no": "לא תודה, אני מעדיף/ה כך"
        },
        
        "yes_response": """
מעולה! 🎉

עכשיו נשאל אותך כמה שאלות קצרות (2-3 דקות).
זה יעזור לנו להתאים את התוכן בדיוק בשבילך.

מוכן/ה להתחיל?
        """,
        
        "later_response": """
בסדר גמור! 😊

אפשר תמיד לחזור לזה אחר כך מההגדרות.
בינתיים תקבל/י חוויה רגילה.

בהצלחה בלימודים! 📚
        """,
        
        "no_response": """
אין בעיה בכלל! 👍

תמשיך/י ללמוד בצורה הרגילה.
אם תרצה/י לשנות את זה אחר כך, זה תמיד אפשרי בהגדרות.

בהצלחה! 🎓
        """
    }


def get_consent_prompt_english() -> Dict[str, str]:
    """
    Get friendly English consent prompt.
    
    TONE: Polite, friendly, clear benefits, easy to skip.
    """
    return {
        "title": "📚 Want a More Personal Experience?",
        
        "message": """
Hey there! 👋

We can help you learn better if we get to know you a bit.

**Why is this good for you?**
✨ Answers matched to your level
✨ Explanations in your preferred style
✨ Examples that actually help you
✨ Content that fits your learning pace

**What will we remember?**
📝 Your knowledge level (beginner/intermediate/advanced)
📝 Your learning style (detailed/concise/step-by-step)
📝 Your language and display preferences
📝 Topics you find easy/hard (if you want to share)

**Important to know:**
🔒 Your info stays with you only
🔒 Nobody else sees it
🔒 You can change or delete anytime
🔒 Completely optional - no pressure

**So, what do you say?**
        """,
        
        "options": {
            "yes": "Yes, let's personalize! 🎯",
            "later": "Maybe later",
            "no": "No thanks, I'm good"
        },
        
        "yes_response": """
Awesome! 🎉

We'll ask you a few quick questions (2-3 minutes).
This helps us tailor everything just for you.

Ready to start?
        """,
        
        "later_response": """
No problem! 😊

You can always come back to this from Settings.
For now, you'll get the standard experience.

Happy studying! 📚
        """,
        
        "no_response": """
No worries at all! 👍

Continue with the standard experience.
If you ever change your mind, it's always available in Settings.

Good luck! 🎓
        """
    }


def get_quick_questions_hebrew() -> List[Dict]:
    """
    Get quick preference questions in Hebrew.
    
    DESIGN: Short, simple, optional, with defaults.
    """
    return [
        {
            "id": "study_level",
            "question": "באיזה שלב לימודים את/ה?",
            "type": "choice",
            "options": [
                {"value": "elementary", "label": "יסודי", "emoji": "🎒"},
                {"value": "middle_school", "label": "חטיבה", "emoji": "📚"},
                {"value": "high_school", "label": "תיכון", "emoji": "🎓"},
                {"value": "university", "label": "אקדמיה", "emoji": "🏛️"},
                {"value": "professional", "label": "מקצועי", "emoji": "💼"}
            ],
            "default": "high_school",
            "can_skip": True
        },
        {
            "id": "proficiency_level",
            "question": "איך תתאר/י את רמת הידע שלך בנושאים שאת/ה לומד/ת?",
            "type": "choice",
            "options": [
                {"value": "beginner", "label": "מתחיל/ה - צריך/ה הרבה הסבר", "emoji": "🌱"},
                {"value": "intermediate", "label": "בינוני - מבין/ה בסיס", "emoji": "🌿"},
                {"value": "advanced", "label": "מתקדם/ת - מבין/ה טוב", "emoji": "🌳"},
                {"value": "expert", "label": "מומחה - יודע/ת לעומק", "emoji": "🏆"}
            ],
            "default": "intermediate",
            "can_skip": True
        },
        {
            "id": "explanation_style",
            "question": "איך את/ה אוהב/ת שמסבירים לך?",
            "type": "choice",
            "options": [
                {"value": "concise", "label": "תמציתי וישיר", "emoji": "⚡"},
                {"value": "detailed", "label": "מפורט עם הרבה פרטים", "emoji": "📖"},
                {"value": "step_by_step", "label": "צעד אחר צעד", "emoji": "👣"},
                {"value": "visual", "label": "עם דיאגרמות וחזותי", "emoji": "🎨"}
            ],
            "default": "detailed",
            "can_skip": True
        },
        {
            "id": "learning_preferences",
            "question": "מה עוזר לך ללמוד? (אפשר לבחור כמה)",
            "type": "multiple",
            "options": [
                {"value": "examples", "label": "דוגמאות", "emoji": "💡"},
                {"value": "analogies", "label": "השוואות ואנלוגיות", "emoji": "🔄"},
                {"value": "real_world", "label": "דוגמאות מהחיים", "emoji": "🌍"},
                {"value": "practice", "label": "שאלות תרגול", "emoji": "✍️"},
                {"value": "summaries", "label": "סיכומים", "emoji": "📝"}
            ],
            "default": ["examples", "practice"],
            "can_skip": True
        },
        {
            "id": "learning_pace",
            "question": "באיזה קצב את/ה לומד/ת?",
            "type": "choice",
            "options": [
                {"value": "slow", "label": "לאט - צריך/ה זמן להבין", "emoji": "🐢"},
                {"value": "moderate", "label": "בינוני - קצב נוח", "emoji": "🚶"},
                {"value": "fast", "label": "מהיר - תופס/ת מהר", "emoji": "🏃"}
            ],
            "default": "moderate",
            "can_skip": True
        }
    ]


def get_quick_questions_english() -> List[Dict]:
    """
    Get quick preference questions in English.
    
    DESIGN: Short, simple, optional, with defaults.
    """
    return [
        {
            "id": "study_level",
            "question": "What's your current education level?",
            "type": "choice",
            "options": [
                {"value": "elementary", "label": "Elementary School", "emoji": "🎒"},
                {"value": "middle_school", "label": "Middle School", "emoji": "📚"},
                {"value": "high_school", "label": "High School", "emoji": "🎓"},
                {"value": "university", "label": "University", "emoji": "🏛️"},
                {"value": "professional", "label": "Professional", "emoji": "💼"}
            ],
            "default": "high_school",
            "can_skip": True
        },
        {
            "id": "proficiency_level",
            "question": "How would you describe your knowledge level?",
            "type": "choice",
            "options": [
                {"value": "beginner", "label": "Beginner - Need detailed explanations", "emoji": "🌱"},
                {"value": "intermediate", "label": "Intermediate - Understand basics", "emoji": "🌿"},
                {"value": "advanced", "label": "Advanced - Solid understanding", "emoji": "🌳"},
                {"value": "expert", "label": "Expert - Deep knowledge", "emoji": "🏆"}
            ],
            "default": "intermediate",
            "can_skip": True
        },
        {
            "id": "explanation_style",
            "question": "How do you prefer explanations?",
            "type": "choice",
            "options": [
                {"value": "concise", "label": "Concise and direct", "emoji": "⚡"},
                {"value": "detailed", "label": "Detailed with lots of info", "emoji": "📖"},
                {"value": "step_by_step", "label": "Step by step", "emoji": "👣"},
                {"value": "visual", "label": "Visual with diagrams", "emoji": "🎨"}
            ],
            "default": "detailed",
            "can_skip": True
        },
        {
            "id": "learning_preferences",
            "question": "What helps you learn? (Select multiple)",
            "type": "multiple",
            "options": [
                {"value": "examples", "label": "Examples", "emoji": "💡"},
                {"value": "analogies", "label": "Analogies", "emoji": "🔄"},
                {"value": "real_world", "label": "Real-world examples", "emoji": "🌍"},
                {"value": "practice", "label": "Practice questions", "emoji": "✍️"},
                {"value": "summaries", "label": "Summaries", "emoji": "📝"}
            ],
            "default": ["examples", "practice"],
            "can_skip": True
        },
        {
            "id": "learning_pace",
            "question": "What's your learning pace?",
            "type": "choice",
            "options": [
                {"value": "slow", "label": "Slow - Need time to understand", "emoji": "🐢"},
                {"value": "moderate", "label": "Moderate - Comfortable pace", "emoji": "🚶"},
                {"value": "fast", "label": "Fast - Quick learner", "emoji": "🏃"}
            ],
            "default": "moderate",
            "can_skip": True
        }
    ]


def process_preference_responses(responses: Dict, user_id: str, db_conn: Database = None) -> Dict:
    """
    Process user's preference responses and create preferences object.
    
    Args:
        responses: User's answers to preference questions
        user_id: User ID
        db_conn: Database connection
        
    Returns:
        Dict with preferences ready to save
    """
    db = db_conn if db_conn is not None else flask_db
    
    # Build preferences from responses
    preferences = {
        "user_id": user_id,
        "language": responses.get("language", "he"),
        "study_level": responses.get("study_level", "high_school"),
        "proficiency_level": responses.get("proficiency_level", "intermediate"),
        "explanation_style": responses.get("explanation_style", "detailed"),
        "learning_pace": responses.get("learning_pace", "moderate"),
    }
    
    # Process multiple choice learning preferences
    learning_prefs = responses.get("learning_preferences", [])
    preferences["use_examples"] = "examples" in learning_prefs
    preferences["use_analogies"] = "analogies" in learning_prefs
    preferences["use_real_world_examples"] = "real_world" in learning_prefs
    preferences["prefers_practice"] = "practice" in learning_prefs
    preferences["prefers_summary"] = "summaries" in learning_prefs
    
    # Set defaults for other fields
    preferences["preferred_formats"] = ["bullet_points"]
    preferences["study_time_preference"] = "medium"
    preferences["subject_knowledge"] = {}
    preferences["previous_feedback"] = []
    preferences["difficult_topics"] = []
    preferences["strong_topics"] = []
    preferences["baby_mode"] = False
    preferences["visual_learner"] = responses.get("explanation_style") == "visual"
    preferences["needs_more_detail"] = responses.get("explanation_style") == "detailed"
    
    try:
        # Save to database
        db.user_preferences.update_one(
            {"user_id": user_id},
            {"$set": preferences},
            upsert=True
        )
        logger.info(f"✓ Saved preferences for user {user_id}")
        
        return {"success": True, "message": "העדפות נשמרו בהצלחה! ✨"}
    except Exception as e:
        logger.error(f"Failed to save preferences: {e}")
        return {"success": False, "error": str(e)}


# Global consent manager
consent_manager = PreferenceConsentManager()
