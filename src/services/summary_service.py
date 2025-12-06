"""
🔒 SAFETY CLASSIFICATION: DOCUMENT-ONLY (CLASS A - STRICT)
==========================================================
This service processes user documents and generates summaries.
"""
import os
import pickle
from typing import List, Dict, Optional
from pymongo.database import Database
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger
from src.utils.smart_parser import SMART_REPO_CACHE_DIR

def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db

def _get_smart_context(document_id: str, query: str) -> Optional[str]:
    """
    "Sniper Retrieval" - Tries to find the most relevant chunk from the pickled repository.
    This is a simple heuristic based on the query appearing in the content.
    """
    try:
        repo_path = os.path.join(SMART_REPO_CACHE_DIR, document_id)
        pickle_path = os.path.join(repo_path, "chunks.pkl")

        if not os.path.exists(pickle_path):
            return None

        with open(pickle_path, "rb") as f:
            chunks: List[Dict[str, str]] = pickle.load(f)
        
        # Simple retrieval: find the first chunk that contains the query words.
        # A real RAG system would use vector embeddings for semantic search.
        query_words = set(query.lower().split())
        for chunk in chunks:
            if any(word in chunk["content"].lower() for word in query_words):
                logger.info(f"Smart retrieval successful for doc {document_id}. Using chunk '{chunk['heading']}'.")
                return f"Context from section '{chunk['heading']}':\\n{chunk['content']}"
        
        logger.warning(f"Smart repository for doc {document_id} exists, but no relevant chunks found for query.")
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve from smart repository for doc {document_id}: {e}", exc_info=True)
        return None

def generate_summary(document_id: str, document_content: str, db_conn: Database = None) -> str:
    """
    Uses the AI client to generate a summary for the given document.
    It first attempts to use the "Smart Repository" for context, falling back to the full document.
    """
    db = _get_db(db_conn)
    logger.info(f"🔒 [STRICT] Generating summary for document_id: {document_id}")

    # --- ADDITIVE INJECTION POINT (Retrieval) ---
    # For a generic summary, the query is simple. For a Q&A, the query would be the user's question.
    user_query = "general summary" 
    context = _get_smart_context(document_id, user_query)

    if context is None:
        # FALLBACK: If smart retrieval fails or returns nothing, use the original logic.
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
