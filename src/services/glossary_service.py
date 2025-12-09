import json
from pymongo.database import Database

from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from sb_utils.logger_utils import logger
from src.utils.smart_parser import get_smart_context


def _get_db(db_conn: Database | None = None) -> Database:
    return db_conn if db_conn is not None else flask_db


def extract_terms_from_content(
    document_id: str,
    query: str,
    course_id: str,
    user_id: str,
    filename: str,
    db_conn: Database | None = None,
):
    """
    Extracts glossary terms using smart context retrieval with fallback.

    1. Try smart_context(document_id, query)
    2. If None -> fallback to full content_text from Mongo
    """
    db = _get_db(db_conn)
    logger.info(f"Extracting glossary terms for document_id: {document_id}")

    # --- SNIPER RETRIEVAL ---
    context = get_smart_context(document_id, query=query)
    if context is None:
        doc = db.documents.find_one({"_id": document_id}, {"content_text": 1})
        context = (doc or {}).get("content_text") or ""

    if not context.strip():
        logger.error(
            f"Could not extract terms for doc {document_id}: "
            f"No smart or fallback context found."
        )
        return
    # --- END ---

    prompt = """
    Based on the provided text, identify and extract key terms and their definitions.
    Return the output as a valid JSON array of objects, like this:
    [
      {"term": "Photosynthesis", "definition": "The process by which green plants use sunlight to synthesize foods."},
      {"term": "Gravity", "definition": "The force that attracts a body toward the center of the earth."}
    ]
    Only extract terms explicitly defined in the text. Do not include any other text in your response.
    """

    try:
        json_string = ai_client.generate_text(
            prompt=prompt, context=context, task_type="glossary", require_json=True
        )
        terms_data = json.loads(json_string)

        if not terms_data:
            logger.info(f"No glossary terms found by AI for document {document_id}")
            return

        from pymongo import UpdateOne

        operations = [
            UpdateOne(
                {"term": item["term"], "course_id": course_id, "user_id": user_id},
                {
                    "$set": {
                        "definition": item["definition"],
                        "source_file": filename,
                    }
                },
                upsert=True,
            )
            for item in terms_data
            if "term" in item and "definition" in item
        ]

        if operations:
            db.glossary.bulk_write(operations)
            logger.info(
                f"Successfully saved or updated {len(operations)} glossary "
                f"terms for document {document_id}"
            )

    except (json.JSONDecodeError, TypeError) as e:
        logger.error(
            f"Failed to parse AI response for glossary terms: {e}", exc_info=True
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during glossary extraction: {e}",
            exc_info=True,
        )
