import json
from pymongo.database import Database
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from src.domain.models.db_models import FlashcardSet, Flashcard
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context # Import the centralized utility

def _get_db(db_conn: Database = None) -> Database:
    return db_conn or flask_db

def generate_flashcards(document_id: str, document_content: str, num_cards: int, db_conn: Database = None) -> str:
    """
    Uses the AI client to generate flashcards.
    Attempts to use the Smart Repository for context.
    """
    db = _get_db(db_conn)
    logger.info(f"Generating {num_cards} flashcards for document_id: {document_id}")

    # --- ADDITIVE INJECTION POINT (Retrieval) ---
    context = get_smart_context(document_id, query="generate flashcards")

    if context is None:
        # FALLBACK: If smart retrieval fails, use the original full-document logic.
        logger.info(f"Falling back to full document context for flashcards on doc {document_id}.")
        context = document_content
    # --- END OF INJECTION ---
    
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
    
    json_string = ai_client.generate_text(prompt=prompt, context=context, task_type="flashcards")
    
    try:
        cards_data = json.loads(json_string)
        cards = [Flashcard(**item) for item in cards_data]
        
        flashcard_set = FlashcardSet(
            _id=f"flashcards_{document_id}",
            document_id=document_id,
            cards=cards
        )
        db.flashcards.insert_one(flashcard_set.dict(by_alias=True))
        
        logger.info(f"Successfully created and saved flashcard set for document {document_id}")
        return flashcard_set.id
        
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse AI response for flashcards: {e}", exc_info=True)
        raise ValueError("AI returned an invalid JSON format.") from e
