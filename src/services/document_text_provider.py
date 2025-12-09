from typing import Optional
from pymongo.database import Database

from src.infrastructure.repositories import MongoDocumentRepository
from src.utils.smart_parser import load_smart_repository
from src.domain.errors import DocumentNotFoundError
from src.domain.models.db_models import Document
from sb_utils.logger_utils import logger


def get_document_text(db_conn: Database, document_id: str) -> str:
    """
    Hybrid text retrieval:
    1) Try smart repository (RAG index)
    2) Fallback to document.content_text from Mongo

    Raises:
        DocumentNotFoundError if the document does not exist.
    """
    doc_repo = MongoDocumentRepository(db_conn)

    # --- Fetch document metadata ---
    document: Optional[Document] = doc_repo.get_by_id(document_id)
    if not document:
        # חשוב: אותה שגיאה שה-worker כבר יודע לטפל בה
        raise DocumentNotFoundError(f"Document {document_id} not found")

    # --- Try smart repository first ---
    try:
        smart_text: Optional[str] = load_smart_repository(document_id)
        if smart_text:
            logger.debug(
                "Loaded text from smart repository",
                extra={"document_id": document_id},
            )
            return smart_text

    except Exception as e:
        logger.warning(
            f"Smart repository not available for {document_id}: {e}",
            extra={"document_id": document_id},
        )

    # --- Fallback to content_text ---
    logger.debug(
        "Falling back to content_text for document",
        extra={"document_id": document_id},
    )
    return document.content_text or ""
