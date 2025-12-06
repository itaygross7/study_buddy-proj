"""Service for Avner chat - handles AI-powered Q&A with course context."""
from pymongo.database import Database
from src.infrastructure.database import db as flask_db
from src.services.ai_client import AIClient
from sb_utils.logger_utils import logger


def _get_db(db_conn: Database = None) -> Database:
    """Returns the provided db_conn or the default Flask db proxy."""
    return db_conn or flask_db


# Avner's personality prompt
AVNER_SYSTEM_PROMPT = """
אתה אבנר 🦫 - קפיברה חכמה, מצחיקה וסרקסטית קלות (כמו צ'נדלר מהסדרה Friends) שעוזרת לסטודנטים ללמוד.

הסגנון שלך:
- דבר בעברית פשוטה וברורה (אלא אם הקורס באנגלית)
- היה קצר - 2-4 משפטים מקסימום
- השתמש באימוג'י אחד או שניים
- היה חם, ידידותי ומעודד
- הוסף קצת הומור וסרקזם עדין (בסגנון: "Could this BE any easier?")
- תן תשובות מעשיות ושימושיות
- ענה רק על בסיס החומר שניתן לך
- אם המשתמש עושה טוב - עודד אותו! ("יופי! ממש טוב!")
- אם יש משהו קשה - תמוך ("זה קצת מסובך, אבל אני כאן לעזור")
- לפעמים הוסף הערה מצחיקה ("עוד שאלה כזאת ואני צריך קפה... אבל בואו נמשיך!")

אם אין לך מספיק מידע לענות - אמור את זה בכנות אבל בחביבות.
"""

BABY_MODE_MODIFIER = """
אתה במצב "תינוק" 👶🦫 - תן תשובות פשוטות מאוד, קצרות, וחמודות.
השתמש בשפה פשוטה במיוחד, הרבה אימוג'י, והיה סופר-חמוד ומעודד!
"""


def answer_question(
    question: str,
    context: str = "",
    language: str = "he",
    baby_mode: bool = False,
    user_id: str = "",
    db_conn: Database = None
) -> str:
    """
    Answer a question using Avner's personality with optional course context.
    
    This uses the Triple Hybrid AI client which automatically selects
    the best model based on the task.
    
    Args:
        question: The user's question
        context: Optional course context/documents
        language: Language code (he/en)
        baby_mode: Whether to use simplified baby mode
        user_id: User ID for tracking
        db_conn: Optional database connection
        
    Returns:
        The answer from Avner
    """
    db = _get_db(db_conn)
    
    try:
        # Build the system prompt
        system_prompt = AVNER_SYSTEM_PROMPT
        if baby_mode:
            system_prompt += "\n\n" + BABY_MODE_MODIFIER
        
        # Build the user prompt with context
        if context:
            user_prompt = f"""השאלה שלי: {question}

חומר הקורס (ענה רק על בסיס זה):
{context[:4000]}  
"""
        else:
            user_prompt = f"""השאלה שלי: {question}

(אין חומר קורס ספציפי - ענה באופן כללי)
"""
        
        # Use AI client - it will automatically select the best model
        ai_client = AIClient()
        
        # Chat-style short answers are good for gpt-4o-mini
        # The TripleHybridClient will route this appropriately
        answer = ai_client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=500,  # Short answers
            temperature=0.8   # More creative for chat
        )
        
        logger.info(f"Avner answered question for user {user_id}", extra={
            "user_id": user_id,
            "question_length": len(question),
            "has_context": bool(context),
            "baby_mode": baby_mode
        })
        
        return answer.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate Avner response: {e}", exc_info=True)
        return "🦫 אופס! משהו לא עבד כמו שצריך. נסה שוב בעוד רגע."


def get_course_context(course_id: str, user_id: str, db_conn: Database = None) -> tuple[str, str]:
    """
    Get context from a course's documents.
    
    Returns:
        Tuple of (context_text, language)
    """
    db = _get_db(db_conn)
    
    try:
        # Get course
        course = db.courses.find_one({"_id": course_id, "user_id": user_id})
        if not course:
            return "", "he"
        
        language = course.get("language", "he")
        
        # Get course documents
        documents = list(db.documents.find(
            {"user_id": user_id, "course_id": course_id}
        ).limit(5))  # Limit to 5 most recent docs to avoid huge context
        
        if not documents:
            return "", language
        
        # Combine document content
        context_parts = []
        for doc in documents:
            content = doc.get("content_text", "")
            if content and content != "[Processing...]":
                context_parts.append(f"=== {doc.get('filename', 'Document')} ===\n{content[:2000]}")
        
        context = "\n\n".join(context_parts)
        return context, language
        
    except Exception as e:
        logger.error(f"Failed to get course context: {e}", exc_info=True)
        return "", "he"


def get_user_general_context(user_id: str, db_conn: Database = None) -> str:
    """
    Get user's general academic context from their profile.
    
    Returns:
        User's general context or empty string
    """
    db = _get_db(db_conn)
    
    try:
        user = db.users.find_one({"_id": user_id})
        if user and user.get("general_context"):
            return f"מידע כללי על המשתמש: {user['general_context']}"
        return ""
    except Exception as e:
        logger.error(f"Failed to get user context: {e}", exc_info=True)
        return ""
