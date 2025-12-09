"""
Service for handling the AI Tutor chat functionality.
"""

from pymongo.database import Database

from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from src.infrastructure.repositories import MongoDocumentRepository
from src.domain.models.db_models import DocumentStatus
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context  # centralized utility


def _get_db(db_conn: Database | None = None) -> Database:
    return db_conn if db_conn is not None else flask_db


def answer_tutor_question(
    user_id: str,
    course_id: str,
    question: str,
    db_conn: Database | None = None,
) -> str:
    """
    Answers a user's question using documents from a specific course as context.
    Uses "Sniper Retrieval" (smart_context per document) with fallback.

    Flow:
    1. Get READY documents for this course & user.
    2. For each doc: try smart context with the question.
    3. Aggregate chunks; if none -> fallback to full content_text.
    """
    db = _get_db(db_conn)
    doc_repo = MongoDocumentRepository(db)

    logger.info(
        f"Tutor question received from user {user_id} for course {course_id}: '{question[:30]}...'"
    )

    # 1. Find all documents associated with the course (READY only)
    course_documents = [
        doc
        for doc in doc_repo.find_by_course(course_id, user_id)
        if getattr(doc, "status", DocumentStatus.READY) == DocumentStatus.READY
    ]

    # 2. Smart retrieval per document
    smart_contexts: list[str] = []
    for doc in course_documents:
        context_chunk = get_smart_context(doc.id, query=question)
        if context_chunk:
            smart_contexts.append(f"קטע מתוך '{doc.filename}':\n{context_chunk}")

    # 3. Aggregate or fallback
    if smart_contexts:
        logger.info(
            f"Found {len(smart_contexts)} relevant smart chunks for tutor question."
        )
        final_context = "\n--- \n".join(smart_contexts)
    else:
        logger.warning(
            f"No smart context found for tutor question. "
            f"Falling back to full document text for course {course_id}."
        )
        full_texts = [
            (doc.content_text or "")
            for doc in course_documents
            if (doc.content_text or "").strip()
        ]
        final_context = "\n--- \n".join(full_texts)

    if not final_context.strip():
        return (
            "מצטער, לא מצאתי חומר לימוד רלוונטי בקורס הזה כדי לענות על השאלה. "
            "אולי כדאי להעלות קודם כמה קבצים?"
        )

    prompt = f"""
You are Avner, a friendly and expert teaching assistant.
Your goal is to answer the user's question based *only* on the provided context
from their study materials.

If the answer is not in the context, you MUST reply in Hebrew:
"מצטער, אבל התשובה לשאלה הזו לא מופיעה בחומר הלימוד שהעלית. אולי תנסה לנסח את השאלה אחרת?"

User's question: "{question}"
"""

    answer = ai_client.generate_text(
        prompt=prompt,
        context=final_context,
        task_type="tutor",
    )

    return answer
