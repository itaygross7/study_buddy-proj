"""
Adapter layer between old worker.py and the NEW BACKEND CORE.
Each handler receives:
    - data: dict from RabbitMQ
    - db_conn: Mongo database connection

Each handler MUST:
    - perform logic using new backend core
    - return result_id (string)

Task status updates & retries are handled in worker.py.
"""

from typing import Dict, Any
from pymongo.database import Database

from new_backend.core.file_processor import FileProcessor
from new_backend.core.summary_engine import SummaryEngine
from new_backend.core.flashcard_engine import FlashcardEngine
from new_backend.core.assessment_engine import AssessmentEngine
from new_backend.core.homework_solver import HomeworkSolver
from new_backend.core.chat_engine import ProtectedChatEngine


# --------------------------------------------------
# FILE PROCESSING
# --------------------------------------------------

def handle_file_processing_task(data: Dict[str, Any], db_conn: Database) -> str:
    document_id = data["document_id"]

    processor = FileProcessor(db_conn)
    result_document_id = processor.process(document_id=document_id)

    return result_document_id



# --------------------------------------------------
# SUMMARIZE
# --------------------------------------------------

def handle_summarize_task(data: Dict[str, Any], db_conn: Database) -> str:
    engine = SummaryEngine(db_conn)
    return engine.run(
        document_id=data["document_id"],
        query=data.get("query", "")
    )



# --------------------------------------------------
# FLASHCARDS
# --------------------------------------------------

def handle_flashcards_task(data: Dict[str, Any], db_conn: Database) -> str:
    engine = FlashcardEngine(db_conn)
    return engine.run(
        document_id=data["document_id"],
        query=data.get("query", ""),
        num_cards=data.get("num_cards", 10)
    )



# --------------------------------------------------
# ASSESS ME
# --------------------------------------------------

def handle_assess_task(data: Dict[str, Any], db_conn: Database) -> str:
    engine = AssessmentEngine(db_conn)
    return engine.run(
        document_id=data["document_id"],
        query=data.get("query", ""),
        num_questions=data.get("num_questions", 5),
        question_type=data.get("question_type", "mixed")
    )



# --------------------------------------------------
# HOMEWORK SOLVER
# --------------------------------------------------

def handle_homework_task(data: Dict[str, Any], db_conn: Database) -> str:
    solver = HomeworkSolver()
    return solver.solve(data["problem_statement"])



# --------------------------------------------------
# AVNER PROTECTED CHAT
# --------------------------------------------------

def handle_avner_chat_task(data: Dict[str, Any], db_conn: Database) -> str:
    """
    Your protected STUDYBUDDY-only chat layer.
    Rules:
    - Only answers app-related questions
    - Rejects anything out of scope
    - Uses Avner tone + study-friendly persona
    - Uses Gemini/OpenAI depending on user preference
    - Logs everything securely
    """
    engine = ProtectedChatEngine(db_conn)
    return engine.reply(
        conversation_id=data["conversation_id"],
        user_message=data["message"]
    )