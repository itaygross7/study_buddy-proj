"""
🔒 SAFETY CLASSIFICATION: DOCUMENT-ONLY (CLASS A - STRICT)
==========================================================
This service processes user documents and generates summaries.
"""
from pymongo.database import Database
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context # Import the centralized utility

def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db

def generate_summary(document_id: str, document_content: str, db_conn: Database = None) -> str:
    """
    Uses the AI client to generate a summary for the given document.
    It first attempts to use the "Smart Repository" for context, falling back to the full document.
    """
    db = _get_db(db_conn)
    logger.info(f"🔒 [STRICT] Generating summary for document_id: {document_id}")

    # --- ADDITIVE INJECTION POINT (Retrieval) ---
    context = get_smart_context(document_id, query="general summary")

    if context is None:
        # FALLBACK: If smart retrieval fails, use the original full-document logic.
        logger.info(f"Falling back to full document context for doc {document_id}.")
        context = document_content
    # --- END OF INJECTION ---

    prompt = ("Summarize the following text into a few key bullet points. "
              "Then, provide three follow-up questions a student could use "
              "to test their understanding.")

    summary_text = ai_client.generate_text(
        prompt=prompt, 
        context=context,
        task_type="summary"
    )

    result_id = f"summary_{document_id}"
    db.summaries.insert_one({
        "_id": result_id,
        "document_id": document_id,
        "summary_text": summary_text
    })

    logger.info(f"Generated and saved summary for document {document_id}")
    return result_id
