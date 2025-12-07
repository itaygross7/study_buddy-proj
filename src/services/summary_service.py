from pymongo.database import Database

from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context


def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db


def _get_course_smart_context(course_id: str, query: str, db_conn: Database) -> str | None:
    """
    Build a 'smart context' for an ENTIRE course by aggregating
    the smart contexts of all its documents.

    We keep the existing document-level sniper retrieval:
    - For each document in the course, call get_smart_context(...)
    - Concatenate only relevant chunks.
    """
    db = db_conn

    # Assumes you have a 'documents' collection with course_id field.
    # If your collection is named differently, just change this one line.
    docs_cursor = db.documents.find(
        {"course_id": course_id},
        {"_id": 1},
    )

    all_chunks: list[str] = []
    for doc in docs_cursor:
        doc_id = str(doc["_id"])
        ctx = get_smart_context(doc_id, query=query)
        if ctx:
            all_chunks.append(ctx)

    if not all_chunks:
        return None

    # Join contexts with spacing so the model can see transitions.
    return "\n\n---\n\n".join(all_chunks)


def generate_summary(course_id: str, query: str, db_conn: Database = None) -> str:
    """
    Generate a course-level summary using ONLY smart context from
    all documents in the course.

    This makes the tool:
    - Course-wide (not per single document).
    - Interactive (query can change focus each time).
    """
    db = _get_db(db_conn)
    logger.info(f"🔒 [STRICT] Generating course summary for course_id: {course_id}")

    context = _get_course_smart_context(course_id=course_id, query=query, db_conn=db)

    if context is None:
        logger.error(
            f"Could not generate course summary for course {course_id}: "
            f"No smart context found and fallback is disabled."
        )
        raise ValueError("Could not find relevant context in the course to generate a summary.")

    prompt = (
        "Summarize the following course material into a few key bullet points, "
        "focusing on the student's query. Then, provide three follow-up questions "
        "a student could use to test their understanding."
    )

    summary_text = ai_client.generate_text(
        prompt=prompt,
        context=context,
        task_type="summary",
    )

    result_id = f"summary_course_{course_id}"
    db.summaries.insert_one({
        "_id": result_id,
        "course_id": course_id,
        "summary_text": summary_text,
        "query": query,
    })

    logger.info(f"Generated and saved course summary for course {course_id}")
    return result_id
