import json
import uuid
from pymongo.database import Database
from typing import Dict, List
from datetime import datetime, timezone
from .ai_client import ai_client
from src.infrastructure.database import db as flask_db
from src.domain.models.db_models import TutorSession
from sb_utils.logger_utils import logger


def _utc_now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _get_db(db_conn: Database = None) -> Database:
    return db_conn or flask_db


def create_tutor_session(user_id: str, topic: str, course_id: str = "", 
                        db_conn: Database = None) -> str:
    """
    Creates a new interactive tutor session for a given topic.
    Generates a 5-step syllabus using AI.
    
    Args:
        user_id: ID of the user
        topic: The topic the user wants to learn
        course_id: Optional course ID for context
        db_conn: Optional database connection
        
    Returns:
        Session ID
    """
    db = _get_db(db_conn)
    logger.info(f"Creating tutor session for user {user_id} on topic: {topic}")
    
    # Generate syllabus using GPT-4o for better planning
    prompt = f"""
    Create a 5-step learning syllabus for teaching the topic: "{topic}"
    
    Each step should be:
    - A clear, specific concept or skill
    - Buildable on previous steps
    - Achievable in one focused lesson
    
    Return a JSON array of exactly 5 strings (the step titles).
    Example: ["Introduction to basic concepts", "Core principles", "Practical applications", "Advanced techniques", "Summary and practice"]
    
    Return ONLY valid JSON, no other text.
    """
    
    try:
        json_string = ai_client.generate_text(
            prompt=prompt,
            context="",
            task_type="complex_reasoning"
        )
        
        # Try to parse as JSON
        try:
            syllabus = json.loads(json_string)
        except json.JSONDecodeError:
            # Fallback to simple split if not JSON
            syllabus = [
                f"Introduction to {topic}",
                "Core Concepts",
                "Practical Applications",
                "Advanced Topics",
                "Review and Practice"
            ]
        
        session_id = f"tutor_{uuid.uuid4().hex[:12]}"
        session = TutorSession(
            _id=session_id,
            user_id=user_id,
            course_id=course_id,
            topic=topic,
            syllabus=syllabus,
            current_step=0,
            chat_history=[],
            completed_steps=[]
        )
        
        db.tutor_sessions.insert_one(session.to_dict())
        logger.info(f"Created tutor session {session_id}")
        return session_id
        
    except Exception as e:
        logger.error(f"Error creating tutor session: {e}", exc_info=True)
        raise


def get_session(session_id: str, user_id: str, db_conn: Database = None) -> Dict:
    """
    Retrieves a tutor session.
    
    Args:
        session_id: ID of the session
        user_id: ID of the user (for permission check)
        db_conn: Optional database connection
        
    Returns:
        Session dictionary
    """
    db = _get_db(db_conn)
    session = db.tutor_sessions.find_one({"_id": session_id, "user_id": user_id})
    return session


def teach_step(session_id: str, user_id: str, db_conn: Database = None) -> Dict:
    """
    Teaches the current step in the tutor session.
    Generates teaching content and a drill question.
    
    Args:
        session_id: ID of the session
        user_id: ID of the user
        db_conn: Optional database connection
        
    Returns:
        Dictionary with teaching content and question
    """
    db = _get_db(db_conn)
    session = db.tutor_sessions.find_one({"_id": session_id, "user_id": user_id})
    
    if not session:
        raise ValueError("Session not found")
    
    current_step = session.get("current_step", 0)
    syllabus = session.get("syllabus", [])
    
    if current_step >= len(syllabus):
        return {"completed": True, "message": "🎉 You've completed all steps!"}
    
    step_title = syllabus[current_step]
    topic = session.get("topic", "")
    
    prompt = f"""
    You are teaching step {current_step + 1} of {len(syllabus)} on the topic "{topic}".
    This step is: "{step_title}"
    
    Provide:
    1. A clear, engaging explanation of this concept (2-3 paragraphs)
    2. An example to illustrate the concept
    3. One drill question to test understanding
    
    Format your response as JSON:
    {{
      "explanation": "...",
      "example": "...",
      "question": "..."
    }}
    """
    
    try:
        json_string = ai_client.generate_text(
            prompt=prompt,
            context="",
            task_type="standard",
            require_json=True
        )
        
        content = json.loads(json_string)
        
        # Add to chat history
        chat_entry = {
            "role": "tutor",
            "step": current_step,
            "content": content
        }
        
        db.tutor_sessions.update_one(
            {"_id": session_id},
            {
                "$push": {"chat_history": chat_entry},
                "$set": {"updated_at": _utc_now()}
            }
        )
        
        return {
            "step": current_step + 1,
            "total_steps": len(syllabus),
            "title": step_title,
            **content
        }
        
    except Exception as e:
        logger.error(f"Error teaching step: {e}", exc_info=True)
        raise


def submit_answer(session_id: str, user_id: str, answer: str, db_conn: Database = None) -> Dict:
    """
    Evaluates user's answer to the drill question.
    Moves to next step if correct, provides feedback if wrong.
    
    Args:
        session_id: ID of the session
        user_id: ID of the user
        answer: User's answer
        db_conn: Optional database connection
        
    Returns:
        Dictionary with evaluation result
    """
    db = _get_db(db_conn)
    session = db.tutor_sessions.find_one({"_id": session_id, "user_id": user_id})
    
    if not session:
        raise ValueError("Session not found")
    
    current_step = session.get("current_step", 0)
    chat_history = session.get("chat_history", [])
    
    # Get the last question
    last_entry = chat_history[-1] if chat_history else None
    if not last_entry or last_entry.get("role") != "tutor":
        return {"error": "No active question"}
    
    question = last_entry.get("content", {}).get("question", "")
    
    prompt = f"""
    A student answered the following question:
    Question: {question}
    Student's answer: {answer}
    
    Evaluate if the answer is correct. Return JSON:
    {{
      "correct": true/false,
      "feedback": "Encouraging feedback explaining why the answer is correct or incorrect"
    }}
    """
    
    try:
        json_string = ai_client.generate_text(
            prompt=prompt,
            context="",
            task_type="standard",
            require_json=True
        )
        
        evaluation = json.loads(json_string)
        is_correct = evaluation.get("correct", False)
        
        # Add answer to chat history
        answer_entry = {
            "role": "student",
            "step": current_step,
            "answer": answer,
            "evaluation": evaluation
        }
        
        update_data = {
            "$push": {"chat_history": answer_entry},
            "$set": {"updated_at": _utc_now()}
        }
        
        # If correct, advance to next step
        if is_correct:
            update_data["$set"]["current_step"] = current_step + 1
            update_data["$addToSet"] = {"completed_steps": current_step}  # Use $addToSet to avoid duplicates
        
        db.tutor_sessions.update_one({"_id": session_id}, update_data)
        
        return {
            "correct": is_correct,
            "feedback": evaluation.get("feedback", ""),
            "next_step": current_step + 1 if is_correct else current_step
        }
        
    except Exception as e:
        logger.error(f"Error evaluating answer: {e}", exc_info=True)
        raise


def list_user_sessions(user_id: str, db_conn: Database = None) -> List[Dict]:
    """
    Lists all tutor sessions for a user.
    
    Args:
        user_id: ID of the user
        db_conn: Optional database connection
        
    Returns:
        List of session dictionaries
    """
    db = _get_db(db_conn)
    sessions = list(db.tutor_sessions.find({"user_id": user_id}).sort("created_at", -1))
    return sessions
