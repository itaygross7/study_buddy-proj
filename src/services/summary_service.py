"""
🔒 SAFETY CLASSIFICATION: DOCUMENT-ONLY (CLASS A - STRICT)
==========================================================
This service processes user documents and generates summaries.

SECURITY REQUIREMENTS:
- ✅ Uses ONLY user document content
- ✅ NO external knowledge allowed
- ✅ Strict constraints enforced
- ✅ User isolation maintained

CONSTRAINT LEVEL: STRICT
- All responses must come from provided document
- If information not in document, must say so
- Zero hallucinations policy
"""

from pymongo.database import Database
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger


def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db


def generate_summary(document_id: str, document_content: str, db_conn: Database = None) -> str:
    """
    Uses the AI client to generate a summary for the given document.
    
    🔒 SECURITY: Uses STRICT document-only constraint.
    All content must come from document_content parameter.
    
    Saves the result to the database.
    """
    db = _get_db(db_conn)
    logger.info(f"🔒 [STRICT] Generating summary for document_id: {document_id}")

    prompt = ("Summarize the following text into a few key bullet points. "
              "Then, provide three follow-up questions a student could use "
              "to test their understanding.")

    summary_text = ai_client.generate_text(
        prompt=prompt, 
        context=document_content,
        task_type="summary"  # Routes to Gemini with STRICT constraint
    )

    # For this scaffold, we'll store the raw summary text in a new collection
    result_id = f"summary_{document_id}"
    db.summaries.insert_one({
        "_id": result_id,
        "document_id": document_id,
        "summary_text": summary_text
    })

    logger.info(f"Generated and saved summary for document {document_id}")
    return result_id
