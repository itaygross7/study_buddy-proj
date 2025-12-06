"""Routes for the Ask Avner helper feature - Live Chat with Avner."""
from flask import Blueprint, request, jsonify, url_for
from flask_login import current_user

from src.infrastructure.database import db
from src.infrastructure.rabbitmq import publish_task
from src.services import auth_service, avner_service
from src.services.task_service import create_task
from src.api.routes_admin import get_system_config
from sb_utils.logger_utils import logger

avner_bp = Blueprint('avner', __name__)

# ============ LOCAL ANSWERS (No AI needed) ============
# These answers are returned without using AI prompts

APP_HELP_RESPONSES = {
    # App features
    "summary": "📝 **מסכם** - העלה טקסט או קובץ ואבנר יסכם לך את הנקודות העיקריות בצורה ברורה.",
    "flashcards": "🃏 **כרטיסיות** - אבנר יצור לך כרטיסיות שאלה-תשובה מהחומר שלך לתרגול.",
    "assess": "✅ **בחן אותי** - קבל שאלות בחירה מרובה מהחומר לבדוק את עצמך.",
    "homework": "📚 **עזרה בשיעורים** - אבנר יעזור לך להבין בעיות ולפתור תרגילים.",

    # Library
    "library": ("📚 **הספרייה** - כאן אתה יוצר קורסים ומעלה חומרים. "
                "כל קורס מופרד - אבנר עונה רק מהחומר של הקורס הספציפי."),
    "course": ("📖 **קורס** - צור קורס לכל נושא (למשל: מבוא לפסיכולוגיה). "
               "העלה אליו חומרים והשתמש בכלים."),
    "upload": ("📤 **העלאת חומר** - אפשר להעלות PDF, Word, PowerPoint או "
               "להדביק טקסט. החומר נשמר רק בקורס שלך."),

    # Account
    "profile": "👤 **פרופיל** - בפרופיל אפשר לעדכן פרטים אישיים ולהוסיף מידע כללי שאבנר ישתמש בו.",
    "language": "🌐 **שפה** - לכל קורס אפשר לבחור שפה (עברית/אנגלית). אבנר יענה בשפה שבחרת.",

    # How to use
    "start": ("🚀 **איך להתחיל?**\n1. צור קורס חדש בספרייה\n"
              "2. העלה חומרי לימוד\n3. השתמש בכלים: סיכום, כרטיסיות, בחינות\n"
              "4. שאל אותי שאלות על החומר!"),
    "help": ("🦫 **אני אבנר!** אני יכול לעזור לך עם:\n"
             "• שאלות על האפליקציה\n• שאלות על החומר שהעלית\n"
             "• טיפים ללמידה\n\nפשוט שאל!"),
}

# Keywords to detect app-related questions
APP_KEYWORDS = {
    "summary": ["סיכום", "לסכם", "מסכם", "summarize", "summary"],
    "flashcards": ["כרטיסיות", "כרטיסיה", "flashcard", "cards"],
    "assess": ["בחינה", "מבחן", "שאלות", "בחן", "quiz", "test", "assess"],
    "homework": ["שיעורים", "תרגיל", "homework", "exercise"],
    "library": ["ספרייה", "library", "ספריה"],
    "course": ["קורס", "course", "נושא"],
    "upload": ["העלאה", "להעלות", "upload", "קובץ", "file"],
    "profile": ["פרופיל", "profile", "חשבון", "account"],
    "language": ["שפה", "language", "עברית", "אנגלית", "hebrew", "english"],
    "start": ["להתחיל", "איך מתחילים", "how to start", "getting started", "התחלה"],
    "help": ["עזרה", "help", "מה אתה", "מי אתה", "what can you"],
}

# Keywords that indicate a learning/course question (needs AI)
LEARNING_KEYWORDS = ["הסבר", "למה", "מה זה", "איך", "explain", "why", "what is", "how does",
                     "מהו", "מהי", "מהם", "מדוע", "כיצד", "תסביר", "ספר לי על"]

# Keywords that are off-topic
OFFTOPIC_KEYWORDS = ["מזג אוויר", "weather", "ספורט", "sport", "פוליטיקה", "politics",
                     "בדיחה", "joke", "משחק", "game", "סרט", "movie", "שיר", "song",
                     "אוכל", "food", "מתכון", "recipe"]


def detect_question_type(question: str) -> tuple:
    """
    Detect the type of question.
    Returns: (type, key) where type is 'app', 'learning', 'offtopic', or 'unknown'
    """
    question_lower = question.lower()

    # Check for off-topic first
    for keyword in OFFTOPIC_KEYWORDS:
        if keyword in question_lower:
            return ('offtopic', None)

    # Check for app-related questions
    for key, keywords in APP_KEYWORDS.items():
        for keyword in keywords:
            if keyword in question_lower:
                return ('app', key)

    # Check for learning questions (needs AI)
    for keyword in LEARNING_KEYWORDS:
        if keyword in question_lower:
            return ('learning', None)

    # Default to learning if unclear (but short questions might be greetings)
    if len(question) < 15:
        return ('greeting', None)

    return ('learning', None)


def get_local_response(question_type: str, key: str, question: str) -> str:
    """Get a response without using AI."""

    if question_type == 'app' and key in APP_HELP_RESPONSES:
        return APP_HELP_RESPONSES[key]

    if question_type == 'greeting':
        greetings = ["היי", "שלום", "הי", "hello", "hi", "hey"]
        if any(g in question.lower() for g in greetings):
            return "שלום! 🦫 אני אבנר, ואני כאן לעזור לך ללמוד. מה תרצה לדעת?"
        return "היי! איך אפשר לעזור? 🦫"

    if question_type == 'offtopic':
        return ("🦫 אני מתמחה בעזרה בלימודים ובשימוש באפליקציה. "
                "אם יש לך שאלה על החומר שהעלית או על איך להשתמש "
                "ב-StudyBuddy - אשמח לעזור!")

    return None  # Needs AI


# Avner's personality prompt for AI questions
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


@avner_bp.route('/ask', methods=['POST'])
def ask_avner():
    """
    Ask Avner a question.
    - App questions: answered locally (no AI)
    - Learning questions: require login + use AI with course context
    - Off-topic: politely declined (no AI)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "חסר תוכן לשאלה"}), 400

        question = data.get('question', '').strip()
        course_id = data.get('course_id', '')  # Optional: specific course context
        baby_mode = data.get('baby_mode', False)  # Baby Capy mode toggle

        if not question:
            return jsonify({"error": "לא הוזנה שאלה"}), 400

        if len(question) > 1000:
            return jsonify({"error": "השאלה ארוכה מדי (מקסימום 1000 תווים)"}), 400

        # Detect question type
        q_type, q_key = detect_question_type(question)

        # Try to get local response (no AI needed)
        local_response = get_local_response(q_type, q_key, question)
        if local_response:
            return jsonify({
                "answer": local_response,
                "used_ai": False,
                "prompts_used": 0
            })

        # Learning questions require login
        if not current_user.is_authenticated:
            return jsonify({
                "answer": ("🦫 כדי לענות על שאלות לימודיות, צריך להתחבר קודם."
                           "\n\nאם יש לך שאלה על האפליקציה - אשמח לעזור!"),
                "used_ai": False,
                "requires_login": True
            })

        # Check prompt limits (admin users have no limit)
        config = get_system_config()
        user = auth_service.get_user_by_id(db, current_user.id)

        from src.domain.models.db_models import UserRole
        if user and user.role != UserRole.ADMIN and user.prompt_count >= config.max_prompts_per_day:
            return jsonify({
                "error": f"הגעת למגבלת {config.max_prompts_per_day} שאלות ליום. נסה שוב מחר! 🦫",
                "limit_reached": True
            }), 429

        # Get course context and language
        context = ""
        language = "he"

        if course_id:
            context, language = avner_service.get_course_context(
                course_id, current_user.id, db
            )
        
        # Get user's general context
        user_context = avner_service.get_user_general_context(current_user.id, db)
        if user_context:
            context = f"{user_context}\n\n{context}" if context else user_context

        # Create a task for async processing
        task_id = create_task(db)
        
        # Publish to RabbitMQ for worker processing
        try:
            publish_task(
                queue_name='avner_chat',
                task_body={
                    "task_id": task_id,
                    "question": question,
                    "context": context,
                    "language": language,
                    "baby_mode": baby_mode,
                    "user_id": current_user.id
                }
            )
            
            # Increment prompt count immediately (optimistic)
            auth_service.increment_prompt_count(db, current_user.id)
            
            logger.info(f"Avner chat task created for user {current_user.id}")
            
            # Return task ID for polling
            return jsonify({
                "message": "Avner is thinking...",
                "status": "processing",
                "task_id": task_id,
                "polling_url": url_for('task_bp.get_task_status_route', task_id=task_id),
                "prompts_used": user.prompt_count + 1 if user else 1,
                "prompts_limit": config.max_prompts_per_day
            }), 202
            
        except Exception as queue_error:
            logger.error(f"Failed to queue Avner task: {queue_error}", exc_info=True)
            return jsonify({
                "error": "לא הצלחתי להעביר את השאלה למערכת. נסה שוב 🦫"
            }), 500

    except Exception as e:
        logger.error(f"Ask Avner error: {e}", exc_info=True)
        return jsonify({
            "error": "אופס! משהו השתבש. נסה שוב 🦫"
        }), 500


@avner_bp.route('/tips', methods=['GET'])
def get_study_tips():
    """Get random study tips from Avner (no auth required, no AI)."""
    tips = [
        "💡 קח הפסקה כל 25 דקות - המוח צריך מנוחה!",
        "📚 נסה להסביר את החומר בקול - ככה תבין אם הבנת",
        "🎯 התחל מהקשה כשאתה רענן",
        "✨ כרטיסיות זיכרון עוזרות לזכור!",
        "🦫 שתה מים - המוח צריך הידרציה",
        "📝 כתוב במילים שלך - זה עוזר להבין",
        "🌟 חגוג כל הצלחה קטנה!",
        "🧠 שינה טובה = למידה טובה יותר",
        "🎧 מוזיקה בלי מילים יכולה לעזור להתרכז",
        "📖 קרא את הכותרות והסיכום קודם"
    ]

    import random
    return jsonify({"tip": random.choice(tips)})


@avner_bp.route('/app-help', methods=['GET'])
def get_app_help():
    """Get all app help topics (no auth required)."""
    return jsonify({
        "topics": list(APP_HELP_RESPONSES.keys()),
        "responses": APP_HELP_RESPONSES
    })
