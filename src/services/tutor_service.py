"""
Service for handling the AI Tutor chat functionality.
"""
from pymongo.database import Database
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from src.infrastructure.repositories import MongoDocumentRepository
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context # Import the centralized utility

def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db

def answer_tutor_question(user_id: str, course_id: str, question: str, db_conn: Database = None) -> str:
    """
    Answers a user's question using documents from a specific course as context.
    This now uses the high-performance "Sniper Retrieval" method.
    """
    db = _get_db(db_conn)
    doc_repo = MongoDocumentRepository(db)
    
    logger.info(f"Tutor question received from user {user_id} for course {course_id}: '{question[:30]}...'")

    # --- ADDITIVE INJECTION POINT (Retrieval) ---
    
    # 1. Find all documents associated with the course.
    course_documents = doc_repo.find_by_course(course_id, user_id)
    
    # 2. Perform "Sniper Retrieval" on each document.
    smart_contexts = []
    for doc in course_documents:
        context_chunk = get_smart_context(doc.id, query=question)
        if context_chunk:
            smart_contexts.append(f"קטע מתוך '{doc.filename}':\\n{context_chunk}")

    # 3. Aggregate the results or fall back.
    final_context = ""
    if smart_contexts:
        logger.info(f"Found {len(smart_contexts)} relevant smart chunks for tutor question.")
        final_context = "\\n--- \\n".join(smart_contexts)
    else:
        # FALLBACK: If no smart chunks are found, revert to the original, robust logic.
        logger.warning(f"No smart context found for tutor question. Falling back to full document text for course {course_id}.")
        full_texts = [doc.content_text for doc in course_documents]
        final_context = "\\n--- \\n".join(full_texts)

    if not final_context:
        return "מצטער, לא מצאתי חומר לימוד רלוונטי בקורס הזה כדי לענות על השאלה. אולי כדאי להעלות קודם כמה קבצים?"
    # --- END OF INJECTION ---

    prompt = f"""
    You are Avner, a friendly and expert teaching assistant.
    Your goal is to answer the user's question based *only* on the provided context from their study materials.
    If the answer is not in the context, you MUST reply with: 'מצטער, אבל התשובה לשאלה הזו לא מופיעה בחומר הלימוד שהעלית. אולי תנסה לנסח את השאלה אחרת?'
    
    User's question: "{question}"
    """

    answer = ai_client.generate_text(
        prompt=prompt,
        context=final_context,
        task_type="tutor"
    )
    
    return answer
