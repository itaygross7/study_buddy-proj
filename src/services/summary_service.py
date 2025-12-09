from typing import Any, Dict, Optional
from pymongo.database import Database

from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context
from src.domain.models.db_models import DocumentStatus


def _get_db(db_conn: Database | None = None) -> Database:
    return db_conn if db_conn is not None else flask_db


def _get_course_smart_context(course_id: str, query: str, db: Database) -> Optional[str]:
    """
    Build a 'smart context' for an ENTIRE course by aggregating
    the smart contexts of all its READY documents.

    Priority:
    1. Smart context per document (RAG)
    2. Fallback: content_text from Mongo (READY docs only)
    """
    # רק מסמכים READY
    docs_cursor = db.documents.find(
        {"course_id": course_id, "status": DocumentStatus.READY.value},
        {"_id": 1, "content_text": 1},
    )

    all_chunks: list[str] = []

    for doc in docs_cursor:
        doc_id = str(doc["_id"])
        # 1) ניסיון להביא smart context
        ctx = get_smart_context(doc_id, query=query)
        if ctx:
            all_chunks.append(ctx)
            continue

        # 2) fallback ל-content_text
        fallback_text = (doc.get("content_text") or "").strip()
        if fallback_text:
            all_chunks.append(fallback_text)

    if not all_chunks:
        return None

    return "\n\n---\n\n".join(all_chunks)


def _get_document_context(document_id: str, query: str, db: Database) -> Optional[Dict[str, Any]]:
    """
    Single-document context with the same hybrid logic:
    1. Smart context
    2. Fallback to content_text
    """
    doc = db.documents.find_one({"_id": document_id})
    if not doc:
        return None

    # 1) Smart context
    ctx = get_smart_context(document_id, query=query)
    if not ctx:
        # 2) Fallback to content_text (READY בלבד אם יש סטטוס)
        if doc.get("status") and doc["status"] != DocumentStatus.READY.value:
            logger.warning(f"Document {document_id} is not READY; status={doc['status']}")
        ctx = (doc.get("content_text") or "").strip()

    if not ctx:
        return None

    return {
        "context": ctx,
        "course_id": doc.get("course_id"),
    }


def generate_summary(
    course_id: str | None = None,
    query: str = "",
    db_conn: Database | None = None,
    document_id: str | None = None,
) -> str:
    """
    Unified summary generator.

    Supports BOTH:
    - Course-wide summary   -> use course_id (preferred)
    - Single-document summary (for backward compatibility with worker) -> use document_id

    NOTE:
    - worker_tasks.handle_summarize_task יכול עדיין לקרוא עם document_id=document_id
    - ה-UI החדש יכול לקרוא עם course_id=course_id
    """
    db = _get_db(db_conn)

    if not course_id and not document_id:
        raise ValueError("generate_summary requires either course_id or document_id")

    logger.info(
        "🔒 Generating summary",
        extra={"course_id": course_id, "document_id": document_id},
    )

    # ------------------------
    # MODE 1: Course-wide
    # ------------------------
    if course_id is not None:
        context = _get_course_smart_context(course_id=course_id, query=query, db=db)

        if context is None:
            logger.error(
                f"Could not generate course summary for course {course_id}: "
                f"No smart or fallback context found."
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
        db.summaries.insert_one(
            {
                "_id": result_id,
                "scope": "course",
                "course_id": course_id,
                "document_id": None,
                "summary_text": summary_text,
                "query": query,
            }
        )

        logger.info(f"Generated and saved course summary for course {course_id}")
        return result_id

    # ------------------------
    # MODE 2: Single document
    # ------------------------
    ctx_info = _get_document_context(document_id=document_id, query=query, db=db)
    if ctx_info is None:
        logger.error(
            f"Could not generate summary for document {document_id}: "
            f"No smart or fallback context found."
        )
        raise ValueError("Could not find relevant context in the document to generate a summary.")

    context = ctx_info["context"]
    course_id_from_doc = ctx_info["course_id"]

    prompt = (
        "Summarize the following material into clear bullet points, focusing "
        "on the student's query. Then provide 2–3 follow-up questions a student "
        "could use to test themselves."
    )

    summary_text = ai_client.generate_text(
        prompt=prompt,
        context=context,
        task_type="summary",
    )

    result_id = f"summary_doc_{document_id}"
    db.summaries.insert_one(
        {
            "_id": result_id,
            "scope": "document",
            "course_id": course_id_from_doc,
            "document_id": document_id,
            "summary_text": summary_text,
            "query": query,
        }
    )

    logger.info(f"Generated and saved document summary for document {document_id}")
    return result_id
