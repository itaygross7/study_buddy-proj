import json
from pymongo.database import Database

from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from src.domain.models.db_models import FlashcardSet, Flashcard
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context


def _get_db(db_conn: Database | None = None) -> Database:
    return db_conn or flask_db


def generate_flashcards(
    document_id: str,
    query: str,
    num_cards: int,
    db_conn: Database | None = None,
) -> str:
    """
    Generates flashcards using smart context retrieval with fallback.

    1. Try smart_context(document_id, query)
    2. If None -> fallback to full content_text from Mongo
    """
    db = _get_db(db_conn)
    logger.info(f"Generating {num_cards} flashcards for document_id: {document_id}")

    context = get_smart_context(document_id, query=query)
    if context is None:
        doc = db.documents.find_one({"_id": document_id}, {"content_text": 1})
        context = (doc or {}).get("content_text") or ""

    if not context.strip():
        logger.error(
            f"Could not generate flashcards for doc {document_id}: "
            f"No smart or fallback context found."
        )
        raise ValueError(
            "Could not find relevant context in the document to generate flashcards."
        )

    prompt = f"""
    Based on the provided text, generate exactly {num_cards} flashcards.
    Each flashcard should have a 'question' and an 'answer'.
    Return the output as a valid JSON array of objects, like this:
    [
      {{"question": "What is the main topic?", "answer": "The main topic is..."}},
      {{"question": "...", "answer": "..."}}
    ]
    Do not include any other text or explanation in your response.
    """

    json_string = ai_client.generate_text(
        prompt=prompt, context=context, task_type="flashcards", require_json=True
    )

    try:
        cards_data = json.loads(json_string)
        cards = [Flashcard(**item) for item in cards_data]

        doc = db.documents.find_one({"_id": document_id}, {"course_id": 1})
        course_id = doc.get("course_id") if doc else None

        flashcard_set = FlashcardSet(
            _id=f"flashcards_{document_id}",
            document_id=document_id,
            cards=cards,
            course_id=course_id,
        )
        db.flashcard_sets.insert_one(flashcard_set.model_dump(by_alias=True))

        logger.info(
            f"Successfully created and saved flashcard set for document {document_id}"
        )
        return flashcard_set.id

    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse AI response for flashcards: {e}", exc_info=True)
        raise ValueError("AI returned an invalid JSON format.") from e
