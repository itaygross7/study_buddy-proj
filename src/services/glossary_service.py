import json
import uuid
from pymongo.database import Database
from typing import List, Dict
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from src.domain.models.db_models import CourseTerm
from sb_utils.logger_utils import logger


def _get_db(db_conn: Database = None) -> Database:
    return db_conn if db_conn is not None else flask_db


def extract_terms_from_content(document_id: str, document_content: str, 
                               course_id: str, user_id: str, 
                               filename: str = "", db_conn: Database = None) -> List[str]:
    """
    Extracts key terms and definitions from document content using AI.
    Saves terms to the glossary collection.
    
    Args:
        document_id: ID of the source document
        document_content: The text content to extract terms from
        course_id: ID of the course this document belongs to
        user_id: ID of the user who owns this content
        filename: Original filename for reference
        db_conn: Optional database connection
        
    Returns:
        List of term IDs that were created
    """
    db = _get_db(db_conn)
    logger.info(f"Extracting glossary terms from document {document_id}")
    
    prompt = """
    Extract key terms, concepts, and definitions from the provided text.
    Return a JSON array of objects, where each object has:
    - "term": the key term or concept name
    - "definition": a clear, concise definition or explanation
    
    Focus on important academic concepts, technical terms, and vocabulary.
    Return at least 5 terms, but no more than 20.
    
    Example format:
    [
      {"term": "Photosynthesis", "definition": "The process by which plants convert light energy into chemical energy"},
      {"term": "Chlorophyll", "definition": "The green pigment in plants that captures light energy"}
    ]
    
    Return ONLY valid JSON, no other text.
    """
    
    try:
        # Use OpenAI for JSON extraction (require_json enforces routing)
        json_string = ai_client.generate_text(
            prompt=prompt, 
            context=document_content,
            task_type="glossary",  # Task type for logging
            require_json=True  # This ensures routing to OpenAI
        )
        
        terms_data = json.loads(json_string)
        term_ids = []
        
        for term_data in terms_data:
            term_id = f"term_{uuid.uuid4().hex[:12]}"
            course_term = CourseTerm(
                _id=term_id,
                term=term_data.get("term", ""),
                definition=term_data.get("definition", ""),
                source_file=filename,
                course_id=course_id,
                user_id=user_id
            )
            
            # Insert into database
            db.glossary.insert_one(course_term.to_dict())
            term_ids.append(term_id)
            logger.debug(f"Created glossary term: {course_term.term}")
        
        logger.info(f"Successfully extracted {len(term_ids)} terms from document {document_id}")
        return term_ids
        
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse AI response for glossary extraction: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error extracting glossary terms: {e}", exc_info=True)
        return []


def get_course_glossary(course_id: str, user_id: str, db_conn: Database = None) -> List[Dict]:
    """
    Retrieves all glossary terms for a specific course.
    
    Args:
        course_id: ID of the course
        user_id: ID of the user (for permission check)
        db_conn: Optional database connection
        
    Returns:
        List of term dictionaries
    """
    db = _get_db(db_conn)
    
    terms = list(db.glossary.find({
        "course_id": course_id,
        "user_id": user_id
    }).sort("term", 1))
    
    return terms


def search_terms(query: str, course_id: str, user_id: str, db_conn: Database = None) -> List[Dict]:
    """
    Search for terms in the glossary.
    
    Args:
        query: Search query string
        course_id: ID of the course to search in
        user_id: ID of the user
        db_conn: Optional database connection
        
    Returns:
        List of matching term dictionaries
    """
    db = _get_db(db_conn)
    
    # Case-insensitive search in term and definition
    terms = list(db.glossary.find({
        "course_id": course_id,
        "user_id": user_id,
        "$or": [
            {"term": {"$regex": query, "$options": "i"}},
            {"definition": {"$regex": query, "$options": "i"}}
        ]
    }).sort("term", 1))
    
    return terms
