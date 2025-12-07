from pymongo.database import Database
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context

def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db

def generate_summary(document_id: str, query: str, db_conn: Database = None) -> str:
    """
    (CORRECTED) Generates a summary using only the smart context for the given document.
    """
    db = _get_db(db_conn)
    logger.info(f"🔒 [STRICT] Generating summary for document_id: {document_id}")

    # --- THIS IS THE CORRECT "SNIPER RETRIEVAL" LOGIC ---
    context = get_smart_context(document_id, query=query)

    if context is None:
        # If no specific chunks are found, we cannot proceed.
        # The full text is no longer stored in the document record.
        logger.error(f"Could not generate summary for doc {document_id}: No smart context found and fallback is disabled.")
        raise ValueError("Could not find relevant context in the document to generate a summary.")
    # --- END OF CORRECT LOGIC ---

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
