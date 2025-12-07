"""
Adapter between worker.py and backend logic.

Right now this file delegates to the existing src.* services,
so you can move logic gradually into /new_backend/ without touching the worker again.
"""

from typing import Any, Dict

from pymongo.database import Database

from src.infrastructure.repositories import MongoDocumentRepository
from src.services import summary_service, flashcards_service, assess_service, homework_service
from src.services.file_service import FileService
from src.domain.models.db_models import DocumentStatus
from src.domain.errors import DocumentNotFoundError
from src.utils.file_processing import process_uploaded_file
from src.utils.smart_parser import create_smart_repository
from sb_utils.logger_utils import logger


# --------------------------------------------------
# FILE PROCESSING
# --------------------------------------------------
def handle_file_processing_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    - Load document + file from GridFS
    - Process file into text
    - Create smart repository (RAG index)
    - Mark document READY
    - Delete original file
    - Return document_id
    """
    document_id = data["document_id"]

    doc_repo = MongoDocumentRepository(db_conn)
    file_service = FileService(db_conn)

    doc = doc_repo.get_by_id(document_id)
    if not doc or not getattr(doc, "gridfs_id", None):
        raise DocumentNotFoundError(
            f"Document or GridFS file not found for document {document_id}"
        )

    logger.info(
        f"Worker is processing file from GridFS for doc {doc.id}",
        extra={"document_id": document_id},
    )

    file_stream = file_service.get_file_stream(doc.gridfs_id)
    if not file_stream:
        raise FileNotFoundError(f"File with GridFS ID {doc.gridfs_id} not found.")

    # Process uploaded file into text
    text_content = process_uploaded_file(file_stream)

    # Best-effort smart repository creation
    try:
        create_smart_repository(document_id, text_content)
    except Exception as e:
        logger.warning(
            f"Smart repository creation failed for doc {document_id}: {e}",
            extra={"document_id": document_id},
        )

    # Mark document as ready and clear placeholder text
    doc.status = DocumentStatus.READY
    doc.content_text = ""
    doc_repo.update(doc)

    # Delete original file from GridFS
    file_service.delete_file(doc.gridfs_id)
    logger.info(
        f"Original GridFS file {doc.gridfs_id} deleted after successful processing.",
        extra={"document_id": document_id},
    )

    return document_id


# --------------------------------------------------
# SUMMARIZE
# --------------------------------------------------
def handle_summarize_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Generates a summary based on an already-processed document.
    Returns result_id of the summary record.
    """
    document_id = data["document_id"]
    query = data.get("query", "")

    result_id = summary_service.generate_summary(
        document_id=document_id,
        query=query,
        db_conn=db_conn,
    )
    return result_id


# --------------------------------------------------
# FLASHCARDS
# --------------------------------------------------
def handle_flashcards_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Generates flashcards for a document.
    """
    document_id = data["document_id"]
    query = data.get("query", "")
    num_cards = data["num_cards"]

    result_id = flashcards_service.generate_flashcards(
        document_id=document_id,
        query=query,
        num_cards=num_cards,
        db_conn=db_conn,
    )
    return result_id


# --------------------------------------------------
# ASSESS ME
# --------------------------------------------------
def handle_assess_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Generates assessment questions for a document.
    """
    document_id = data["document_id"]
    query = data.get("query", "")
    num_questions = data["num_questions"]
    question_type = data["question_type"]

    result_id = assess_service.generate_assessment(
        document_id=document_id,
        query=query,
        num_questions=num_questions,
        question_type=question_type,
        db_conn=db_conn,
    )
    return result_id


# --------------------------------------------------
# HOMEWORK HELPER
# --------------------------------------------------
def handle_homework_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Solves a homework problem. No document required.
    """
    problem_statement = data["problem_statement"]
    result_id = homework_service.solve_homework_problem(problem_statement)
    return result_id


# --------------------------------------------------
# AVNER PROTECTED CHAT (stub for now)
# --------------------------------------------------
def handle_avner_chat_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Protected chat endpoint (Avner).

    For now this is a stub – you can later wire it to your new backend core
    that enforces:
      - Only StudyBuddy/app-related questions
      - Domain-limited RAG
      - Safety / refusal on out-of-scope topics
    """
    # TODO: implement real logic using your new utils / core
    logger.warning("avner_chat handler is not implemented yet.")
    raise NotImplementedError("avner_chat handler not implemented yet")