#!/usr/bin/env python3
"""
StudyBuddyAI Interactive Demo
============================

This script runs an interactive demo of StudyBuddyAI without requiring:
- MongoDB
- RabbitMQ
- External AI API keys (uses mock AI responses)
- Docker or any external services

Run with: python demo.py

Then visit http://localhost:5000 in your browser.
A demo user is auto-logged in for you!
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from collections import defaultdict

# Set up demo environment before importing app modules
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('SECRET_KEY', 'demo-secret-key-for-testing-only')
os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/demo')
os.environ.setdefault('GEMINI_API_KEY', 'demo-key')
os.environ.setdefault('ADMIN_EMAIL', 'demo@studybuddy.local')


class MockCollection:
    """Mock MongoDB collection with in-memory storage."""
    
    def __init__(self, name):
        self.name = name
        self._data = {}
    
    def find_one(self, query=None):
        if query is None:
            return list(self._data.values())[0] if self._data else None
        
        for doc in self._data.values():
            if self._matches(doc, query):
                return doc
        return None
    
    def find(self, query=None):
        results = []
        for doc in self._data.values():
            if query is None or self._matches(doc, query):
                results.append(doc)
        return MockCursor(results)
    
    def insert_one(self, document):
        doc_id = document.get('_id', str(uuid.uuid4()))
        document['_id'] = doc_id
        self._data[doc_id] = document.copy()
        return MagicMock(inserted_id=doc_id)
    
    def update_one(self, query, update, upsert=False):
        for doc_id, doc in self._data.items():
            if self._matches(doc, query):
                if '$set' in update:
                    doc.update(update['$set'])
                if '$inc' in update:
                    for key, val in update['$inc'].items():
                        doc[key] = doc.get(key, 0) + val
                return MagicMock(modified_count=1, upserted_id=None)
        
        if upsert:
            new_doc = query.copy()
            if '$set' in update:
                new_doc.update(update['$set'])
            doc_id = new_doc.get('_id', str(uuid.uuid4()))
            new_doc['_id'] = doc_id
            self._data[doc_id] = new_doc
            return MagicMock(modified_count=0, upserted_id=doc_id)
        
        return MagicMock(modified_count=0, upserted_id=None)
    
    def find_one_and_update(self, query, update, return_document=False):
        for doc_id, doc in self._data.items():
            if self._matches(doc, query):
                if '$set' in update:
                    doc.update(update['$set'])
                if '$inc' in update:
                    for key, val in update['$inc'].items():
                        doc[key] = doc.get(key, 0) + val
                return doc
        return None
    
    def delete_one(self, query):
        for doc_id, doc in list(self._data.items()):
            if self._matches(doc, query):
                del self._data[doc_id]
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)
    
    def delete_many(self, query):
        deleted = 0
        for doc_id, doc in list(self._data.items()):
            if self._matches(doc, query):
                del self._data[doc_id]
                deleted += 1
        return MagicMock(deleted_count=deleted)
    
    def count_documents(self, query=None):
        if query is None:
            return len(self._data)
        return sum(1 for doc in self._data.values() if self._matches(doc, query))
    
    def _matches(self, doc, query):
        """Simple query matching (supports basic equality and $ne, $gt, $gte operators)."""
        for key, value in query.items():
            if key == '$or':
                if not any(self._matches(doc, cond) for cond in value):
                    return False
                continue
            
            doc_value = doc.get(key)
            
            if isinstance(value, dict):
                for op, op_val in value.items():
                    if op == '$ne' and doc_value == op_val:
                        return False
                    if op == '$gt' and not (doc_value is not None and doc_value > op_val):
                        return False
                    if op == '$gte' and not (doc_value is not None and doc_value >= op_val):
                        return False
            elif doc_value != value:
                return False
        return True


class MockCursor:
    """Mock MongoDB cursor."""
    
    def __init__(self, results):
        self._results = results
        self._skip = 0
        self._limit = None
        self._sort_key = None
        self._sort_dir = 1
    
    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            key, direction = key_or_list[0]
        else:
            key = key_or_list
        self._sort_key = key
        self._sort_dir = direction
        return self
    
    def skip(self, count):
        self._skip = count
        return self
    
    def limit(self, count):
        self._limit = count
        return self
    
    def __iter__(self):
        results = self._results.copy()
        if self._sort_key:
            results.sort(key=lambda x: x.get(self._sort_key, ''), reverse=(self._sort_dir == -1))
        results = results[self._skip:]
        if self._limit:
            results = results[:self._limit]
        return iter(results)
    
    def __len__(self):
        return len(list(self))


class MockDatabase:
    """Mock MongoDB database with in-memory collections."""
    
    def __init__(self):
        self._collections = defaultdict(lambda: None)
    
    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        if self._collections[name] is None:
            self._collections[name] = MockCollection(name)
        return self._collections[name]
    
    def list_collection_names(self):
        return [name for name, col in self._collections.items() if col and col._data]
    
    def command(self, cmd):
        """Mock database commands."""
        if cmd == "dbStats":
            return {
                "dataSize": 1024 * 1024,  # 1MB
                "storageSize": 2 * 1024 * 1024,  # 2MB
                "collections": len(self.list_collection_names()),
                "objects": sum(len(col._data) for col in self._collections.values() if col)
            }
        return {}


# Create global mock database
mock_db = MockDatabase()


def create_demo_data():
    """Create demo user and sample data."""
    from src.services.auth_service import hash_password
    from src.domain.models.db_models import UserRole
    
    # Create demo user (pre-verified, no email verification needed)
    demo_user = {
        "_id": "demo-user-001",
        "email": "demo@studybuddy.local",
        "password_hash": hash_password("demo123"),
        "name": "Demo User",
        "role": UserRole.ADMIN.value,
        "is_verified": True,
        "verification_token": None,
        "created_at": datetime.now(timezone.utc),
        "last_login": datetime.now(timezone.utc),
        "prompt_count": 0,
        "prompt_count_date": None,
        "is_active": True
    }
    mock_db.users.insert_one(demo_user)
    
    # Create demo user profile
    demo_profile = {
        "_id": "demo-user-001",
        "full_name": "Demo User",
        "phone": "",
        "institution": "Demo University",
        "degree": "Computer Science",
        "year_of_study": "2nd Year",
        "general_context": "I prefer examples and visual explanations",
        "preferred_language": "he",
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db.user_profiles.insert_one(demo_profile)
    
    # Create a sample course
    sample_course = {
        "_id": "course-001",
        "user_id": "demo-user-001",
        "name": "Introduction to AI",
        "description": "Learn the basics of Artificial Intelligence",
        "language": "he",
        "icon": "🤖",
        "color": "#42A5F5",
        "document_count": 1,
        "summary_count": 0,
        "flashcard_count": 0,
        "assessment_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db.courses.insert_one(sample_course)
    
    # Create a sample document
    sample_document = {
        "_id": "doc-001",
        "user_id": "demo-user-001",
        "course_id": "course-001",
        "filename": "ai_basics.txt",
        "original_filename": "AI Basics Notes.txt",
        "content_text": """
בינה מלאכותית (AI) היא תחום במדעי המחשב שעוסק ביצירת מערכות חכמות.

נושאים עיקריים:
1. למידת מכונה (Machine Learning) - מאפשרת למחשבים ללמוד מנתונים
2. רשתות נוירונים - מודלים מתמטיים המחקים את המוח האנושי
3. עיבוד שפה טבעית (NLP) - מאפשר למחשבים להבין טקסט ודיבור
4. ראייה ממוחשבת - ניתוח תמונות ווידאו

יישומים של AI:
- עוזרים וירטואליים (Siri, Alexa)
- רכבים אוטונומיים
- אבחון רפואי
- המלצות אישיות (Netflix, Spotify)
- תרגום אוטומטי

אתגרים:
- הטיות באלגוריתמים
- פרטיות נתונים
- אבטחת מערכות AI
- אתיקה בשימוש ב-AI
        """.strip(),
        "content_type": "text",
        "file_size": 1024,
        "created_at": datetime.now(timezone.utc)
    }
    mock_db.documents.insert_one(sample_document)
    
    # Create system config
    system_config = {
        "_id": "system_config",
        "max_prompts_per_day": 50,
        "max_file_size_mb": 10,
        "max_courses_per_user": 20,
        "default_flashcards_count": 10,
        "default_questions_count": 5,
        "enabled_modules": ["summary", "flashcards", "assess", "homework"],
        "maintenance_mode": False,
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db.system_config.insert_one(system_config)
    
    print("✅ Demo data created successfully!")
    print(f"   - Demo user: demo@studybuddy.local / demo123")
    print(f"   - Sample course: Introduction to AI")


def mock_ai_response(prompt_type, content=""):
    """Generate mock AI responses for demo purposes."""
    if prompt_type == "summary":
        return """
## סיכום: מבוא לבינה מלאכותית 🤖

### נקודות עיקריות:

**1. מהי בינה מלאכותית?**
- תחום במדעי המחשב ליצירת מערכות חכמות
- מאפשרת למחשבים לבצע משימות הדורשות אינטליגנציה

**2. טכנולוגיות מרכזיות:**
- למידת מכונה (ML)
- רשתות נוירונים
- עיבוד שפה טבעית
- ראייה ממוחשבת

**3. יישומים נפוצים:**
- עוזרים וירטואליים
- רכבים אוטונומיים
- אבחון רפואי

**4. אתגרים:**
- הטיות, פרטיות, אבטחה, אתיקה
        """.strip()
    
    elif prompt_type == "flashcards":
        return [
            {"question": "מהי בינה מלאכותית?", "answer": "תחום במדעי המחשב שעוסק ביצירת מערכות חכמות"},
            {"question": "מהי למידת מכונה?", "answer": "טכנולוגיה שמאפשרת למחשבים ללמוד מנתונים"},
            {"question": "מה תפקיד רשתות נוירונים?", "answer": "מודלים מתמטיים המחקים את המוח האנושי"},
            {"question": "מהו NLP?", "answer": "עיבוד שפה טבעית - מאפשר למחשבים להבין טקסט ודיבור"},
            {"question": "תן דוגמה לעוזר וירטואלי", "answer": "Siri, Alexa, Google Assistant"}
        ]
    
    elif prompt_type == "assess":
        return [
            {
                "question": "מהו התחום המאפשר למחשבים ללמוד מנתונים?",
                "options": ["ראייה ממוחשבת", "למידת מכונה", "עיבוד גרפי", "אבטחת מידע"],
                "correct_answer": "למידת מכונה"
            },
            {
                "question": "איזה יישום אינו קשור ישירות ל-AI?",
                "options": ["רכבים אוטונומיים", "תרגום אוטומטי", "מחשבון פשוט", "אבחון רפואי"],
                "correct_answer": "מחשבון פשוט"
            },
            {
                "question": "מהו אחד האתגרים העיקריים של AI?",
                "options": ["מהירות חישוב", "הטיות באלגוריתמים", "עלות חומרה", "צריכת חשמל"],
                "correct_answer": "הטיות באלגוריתמים"
            }
        ]
    
    elif prompt_type == "homework":
        return """
## עזרה בשיעורי בית: בינה מלאכותית 📚

### הסבר צעד אחר צעד:

**שלב 1: הבנת השאלה**
לפני שמתחילים, חשוב להבין מה השאלה מבקשת.

**שלב 2: איסוף מידע רלוונטי**
בינה מלאכותית היא תחום רחב הכולל מספר טכנולוגיות:
- למידת מכונה
- רשתות נוירונים
- עיבוד שפה טבעית

**שלב 3: יישום**
כדי ליישם את הידע, חשבו על דוגמאות מהחיים:
- איך Siri מבינה את מה שאתם אומרים?
- איך Netflix יודע מה להמליץ?

**טיפים נוספים:**
- חזרו על ההגדרות
- נסו להסביר לעצמכם במילים שלכם
- חפשו דוגמאות נוספות
        """.strip()
    
    elif prompt_type == "chat":
        return """
שלום! 🦫 אני אבנר, עוזר הלמידה שלך!

אשמח לעזור לך עם כל שאלה על החומר או על האפליקציה.

**כמה דברים שאני יכול לעזור בהם:**
- להסביר מושגים מהחומר שלך
- לתת טיפים ללמידה
- לענות על שאלות על השימוש באפליקציה

מה תרצה לדעת? 😊
        """.strip()
    
    return "Demo response"


def patch_database():
    """Patch the database module to use mock database."""
    # Create a mock get_db function that returns our mock database
    def mock_get_db():
        return mock_db
    
    # Patch the database module
    import src.infrastructure.database as db_module
    db_module.get_db = mock_get_db
    db_module.db = mock_db


def patch_email_service():
    """Patch email service to just log instead of sending emails."""
    import src.services.email_service as email_module
    
    def mock_send_email(*args, **kwargs):
        print(f"📧 [Demo] Email would be sent: {args}")
        return True
    
    email_module.send_email = mock_send_email
    email_module.send_verification_email = mock_send_email
    email_module.send_new_user_notification = mock_send_email
    email_module.send_error_notification = mock_send_email


def create_demo_app():
    """Create Flask app configured for demo mode."""
    # Apply patches before importing app
    patch_database()
    patch_email_service()
    
    # Now import and create the app
    from app import create_app
    
    app = create_app()
    app.config['TESTING'] = False
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for easier testing
    
    # Create demo data
    with app.app_context():
        create_demo_data()
    
    return app


def auto_login_demo_user(app):
    """Configure app to auto-login demo user."""
    from flask_login import login_user
    from src.services import auth_service
    from src.api.routes_auth import FlaskUser
    
    @app.before_request
    def check_auto_login():
        from flask_login import current_user
        from flask import request
        
        # Skip for static files
        if request.path.startswith('/static') or request.path.startswith('/avner'):
            return
        
        # Auto-login demo user if not authenticated
        if not current_user.is_authenticated:
            from src.domain.models.db_models import User
            user_data = mock_db.users.find_one({"email": "demo@studybuddy.local"})
            if user_data:
                user = User(**user_data)
                login_user(FlaskUser(user))


def print_banner():
    """Print welcome banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🦫 StudyBuddyAI - Interactive Demo                         ║
║                                                               ║
║   Welcome! This demo runs entirely locally without            ║
║   requiring MongoDB, RabbitMQ, or AI API keys.               ║
║                                                               ║
║   ✨ Features available:                                      ║
║   - Browse the UI and all pages                              ║
║   - Create courses and upload documents                      ║
║   - Test all learning tools (with mock AI responses)         ║
║   - Admin dashboard access                                   ║
║                                                               ║
║   📝 Demo User (auto-logged in):                             ║
║      Email: demo@studybuddy.local                            ║
║      Password: demo123                                       ║
║                                                               ║
║   🌐 Open your browser to: http://localhost:5000             ║
║                                                               ║
║   Press Ctrl+C to stop the demo server                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Run the demo server."""
    print_banner()
    
    try:
        app = create_demo_app()
        auto_login_demo_user(app)
        
        print("\n🚀 Starting demo server...")
        print("   URL: http://localhost:5000\n")
        
        # Run the development server
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,  # Disable debug to avoid reloader issues with patches
            use_reloader=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Demo server stopped. Thanks for trying StudyBuddyAI!")
    except Exception as e:
        print(f"\n❌ Error starting demo: {e}")
        raise


if __name__ == '__main__':
    main()
