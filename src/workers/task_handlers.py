"""
Worker task handlers - adapter between worker.py and backend services.

This file is the thin layer between the queue messages (worker.py)
and the domain/services in src.*.

All heavy logic lives in services. This module provides the worker interface.
"""

from typing import Any, Dict

from pymongo.database import Database

from src.infrastructure.repositories import MongoDocumentRepository
from src.services import (
    summary_service,
    flashcards_service,
    assess_service,
    homework_service,
    avner_service,
)
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
    - Store processed text on the document
    - Delete original file
    - Return document_id
    """
    document_id = data["document_id"]

    doc_repo = MongoDocumentRepository(db_conn)
    file_service = FileService(db_conn)

    # --- Load document ---
    doc = doc_repo.get_by_id(document_id)
    if not doc or not getattr(doc, "gridfs_id", None):
        raise DocumentNotFoundError(
            f"Document or GridFS file not found for document {document_id}"
        )

    logger.info(
        "Worker is processing file from GridFS",
        extra={"document_id": document_id, "gridfs_id": str(doc.gridfs_id)},
    )

    # --- Get file stream from GridFS ---
    file_stream = file_service.get_file_stream(doc.gridfs_id)
    if not file_stream:
        raise FileNotFoundError(f"File with GridFS ID {doc.gridfs_id} not found.")

    # --- Process uploaded file into text ---
    text_content = process_uploaded_file(file_stream)

    # --- Best-effort smart repository creation (RAG index) ---
    try:
        # NOTE: current implementation of create_smart_repository uses global DB.
        # If you later change it to accept db_conn, update the call here.
        create_smart_repository(document_id, text_content)
    except Exception as e:
        logger.warning(
            "Smart repository creation failed",
            extra={"document_id": document_id, "error": str(e)},
        )

    # --- Mark document as READY and save processed text ---
    doc.status = DocumentStatus.READY
    doc.content_text = text_content
    doc_repo.update(doc)  # repo should call to_dict() inside

    # --- Delete original binary file from GridFS ---
    file_service.delete_file(doc.gridfs_id)
    logger.info(
        "Original GridFS file deleted after successful processing.",
        extra={"document_id": document_id, "gridfs_id": str(doc.gridfs_id)},
    )

    return document_id


# --------------------------------------------------
# SUMMARIZE (COURSE-LEVEL)
# --------------------------------------------------
def handle_summarize_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Generates a summary for a COURSE (not a single document).

    Expected data:
        {
            "task_id": "...",
            "course_id": "...",
            "query": "optional focus string"
        }

    Returns:
        result_id of the summary record (e.g. 'summary_<uuid>')
    """
    course_id = data["course_id"]
    query = data.get("query", "") or ""

    logger.info(
        "Running summarize task",
        extra={"course_id": course_id, "query": query[:100]},
    )

    # New base: summary is course-based
    result_id = summary_service.generate_summary(
        course_id=course_id,
        query=query,
        db_conn=db_conn,
    )
    return result_id


# --------------------------------------------------
# FLASHCARDS (DOCUMENT-LEVEL)
# --------------------------------------------------
def handle_flashcards_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Generates flashcards for a single document.

    Expected data:
        {
            "task_id": "...",
            "document_id": "...",
            "num_cards": int,
            "query": "optional focus string"
        }
    """
    document_id = data["document_id"]
    num_cards = data["num_cards"]
    query = data.get("query", "") or ""

    logger.info(
        "Running flashcards task",
        extra={
            "document_id": document_id,
            "num_cards": num_cards,
            "query": query[:100],
        },
    )

    result_id = flashcards_service.generate_flashcards(
        document_id=document_id,
        query=query,
        num_cards=num_cards,
        db_conn=db_conn,
    )
    return result_id


# --------------------------------------------------
# ASSESS ME (DOCUMENT-LEVEL)
# --------------------------------------------------
def handle_assess_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Generates assessment questions for a document.

    Expected data:
        {
            "task_id": "...",
            "document_id": "...",
            "num_questions": int,
            "question_type": "mcq|open|mixed",
            "query": "optional focus string"
        }
    """
    document_id = data["document_id"]
    num_questions = data["num_questions"]
    question_type = data["question_type"]
    query = data.get("query", "") or ""

    logger.info(
        "Running assess task",
        extra={
            "document_id": document_id,
            "num_questions": num_questions,
            "question_type": question_type,
            "query": query[:100],
        },
    )

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
    Solves a homework problem.

    Expected data:
        {
            "task_id": "...",
            "problem_statement": "...",
            "course_id": "optional",
            "context": "optional extra context text"
        }

    Returns:
        result_id of the homework solution (e.g. 'homework_<uuid>')
    """
    problem_statement = data["problem_statement"]
    course_id = data.get("course_id")
    context_text = data.get("context")

    logger.info(
        "Running homework task",
        extra={
            "course_id": course_id,
            "problem_len": len(problem_statement),
            "has_context": bool(context_text),
        },
    )

    # New base: pass db_conn + optional course context down to the service
    result_id = homework_service.solve_homework_problem(
        problem_statement=problem_statement,
        course_id=course_id,
        context=context_text,
        db_conn=db_conn,
    )
    return result_id


# --------------------------------------------------
# AVNER PROTECTED CHAT
# --------------------------------------------------
def handle_avner_chat_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Protected Avner chat handler.

    Expected data from queue (see routes_avner.ask_avner):
        {
            "task_id": "...",
            "question": "...",
            "context": "course + user context (may be empty)",
            "language": "he|en",
            "baby_mode": bool,
            "user_id": "<user_id>"
        }

    This function delegates to avner_service so all the logic (safety,
    RAG, style, etc.) lives in one place.

    Returns:
        result_id of the Avner answer record (used later by /results/<id>)
    """
    task_id = data["task_id"]
    question = data["question"]
    context = data.get("context", "") or ""
    language = data.get("language", "he")
    baby_mode = bool(data.get("baby_mode", False))
    user_id = data.get("user_id")

    logger.info(
        "Running Avner chat task",
        extra={
            "task_id": task_id,
            "user_id": user_id,
            "language": language,
            "baby_mode": baby_mode,
            "context_len": len(context),
        },
    )

    # The service should:
    #  - run the actual AI call
    #  - store the answer in db.avner_results (or similar)
    #  - return result_id (e.g. same as task_id or 'avner_<uuid>')
    result_id = avner_service.handle_avner_chat_worker(
        task_id=task_id,
        user_id=user_id,
        question=question,
        context=context,
        language=language,
        baby_mode=baby_mode,
        db_conn=db_conn,
    )

    return result_id

