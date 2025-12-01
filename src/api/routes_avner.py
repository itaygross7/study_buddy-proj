"""Routes for the Ask Avner helper feature - Live Chat with Avner."""
import json
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from src.services.ai_client import AIClient
from src.infrastructure.database import db
from src.infrastructure.config import settings
from src.services import auth_service
from src.api.routes_admin import get_system_config
from sb_utils.logger_utils import logger

avner_bp = Blueprint('avner', __name__)

# Avner's personality prompt - Simple, clear Hebrew responses
AVNER_SYSTEM_PROMPT = """
אתה אבנר 🦫 - קפיברה חמודה שעוזרת לסטודנטים ללמוד.

הסגנון שלך:
- דבר בעברית פשוטה וברורה
- היה קצר - 2-4 משפטים מקסימום
- השתמש באימוג'י אחד או שניים
- היה חם, ידידותי ומעודד
- תן תשובות מעשיות ושימושיות

מה אתה יודע לעשות:
1. להסביר איך להשתמש באפליקציה:
   - מסכם: מעלים טקסט/קובץ → מקבלים סיכום מסודר
   - כרטיסיות: יוצרים כרטיסיות שאלה-תשובה מהחומר
   - בחן אותי: מייצרים שאלות בחירה לתרגול
   - עוזר שיעורים: מקבלים עזרה בפתרון בעיות

2. לתת טיפים ללמידה (הפסקות, שינה, ארגון זמן)

3. לענות על שאלות כלליות על החומר שהמשתמש העלה

4. לעודד ולתת מוטיבציה

אם שואלים משהו לא קשור - הפנה בעדינות ללמידה.
תמיד סיים בנימה חיובית!
"""


@avner_bp.route('/ask', methods=['POST'])
@login_required
def ask_avner():
    """Ask Avner a question - Live chat functionality."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "חסר תוכן לשאלה"}), 400
        
        question = data.get('question', '').strip()
        context = data.get('context', '')  # Optional context from uploaded material
        
        if not question:
            return jsonify({"error": "לא הוזנה שאלה"}), 400
        
        if len(question) > 1000:
            return jsonify({"error": "השאלה ארוכה מדי (מקסימום 1000 תווים)"}), 400
        
        # Check prompt limits
        config = get_system_config()
        user = auth_service.get_user_by_id(db, current_user.id)
        
        if user and user.prompt_count >= config.max_prompts_per_day:
            return jsonify({
                "error": f"הגעת למגבלת {config.max_prompts_per_day} שאלות ליום. נסה שוב מחר! 🦫",
                "limit_reached": True
            }), 429
        
        # Build the prompt
        prompt = f"{AVNER_SYSTEM_PROMPT}\n\n"
        if context:
            prompt += f"הקשר מחומר הלימוד של המשתמש:\n{context[:2000]}\n\n"
        prompt += f"שאלת המשתמש: {question}\n\nתשובת אבנר (קצרה וברורה):"
        
        # Generate response
        ai_client = AIClient()
        response = ai_client.generate_text(prompt, "")
        
        # Increment prompt count
        auth_service.increment_prompt_count(db, current_user.id)
        
        logger.info(f"Avner answered question for user {current_user.id}")
        
        return jsonify({
            "answer": response,
            "prompts_used": user.prompt_count + 1 if user else 1,
            "prompts_limit": config.max_prompts_per_day
        })
        
    except Exception as e:
        logger.error(f"Ask Avner error: {e}", exc_info=True)
        return jsonify({
            "error": "אופס! משהו השתבש. נסה שוב 🦫"
        }), 500


@avner_bp.route('/tips', methods=['GET'])
def get_study_tips():
    """Get random study tips from Avner (no auth required)."""
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
