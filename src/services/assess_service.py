import json
from pymongo.database import Database
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from src.domain.models.db_models import Assessment, AssessmentQuestion
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context

def _get_db(db_conn: Database = None) -> Database:
    return db_conn or flask_db

def generate_assessment(document_id: str, query: str, num_questions: int, question_type: str, db_conn: Database = None) -> str:
    """
    Generates an assessment using smart context retrieval.
    """
    db = _get_db(db_conn)
    logger.info(f"Generating {num_questions} '{question_type}' questions for document_id: {document_id}")

    # --- SNIPER RETRIEVAL ---
    context = get_smart_context(document_id, query=query)
    if context is None:
        logger.error(f"Could not generate assessment for doc {document_id}: No smart context found.")
        raise ValueError("Could not find relevant context in the document to generate an assessment.")
    # --- END ---

    prompt = f"""
    Based on the provided text, generate exactly {num_questions} quiz questions of type '{question_type}'.
    For 'mcq' (multiple choice), each question must have 'options' (a list of 4 strings) and a 'correct_answer'.
    Return the output as a valid JSON array of objects, like this:
    [
      {{"question": "What is the capital of France?", "options": ["Berlin", "Paris", "London", "Madrid"], "correct_answer": "Paris"}},
      ...
    ]
    Do not include any other text or explanation in your response.
    """

    json_string = ai_client.generate_text(prompt=prompt, context=context, task_type="assessment", require_json=True)

    try:
        questions_data = json.loads(json_string)
        questions = [AssessmentQuestion(**item) for item in questions_data]

        assessment = Assessment(
            _id=f"assessment_{document_id}",
            document_id=document_id,
            questions=questions,
            course_id=db.documents.find_one({"_id": document_id}).get("course_id")
        )
        db.assessments.insert_one(assessment.dict(by_alias=True))

        logger.info(f"Successfully created and saved assessment for document {document_id}")
        return assessment.id

    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse AI response for assessment: {e}", exc_info=True)
        raise ValueError("AI returned an invalid JSON format.") from e
