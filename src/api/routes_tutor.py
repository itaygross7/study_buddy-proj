from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from src.services import tutor_service
from src.infrastructure.database import db
from sb_utils.logger_utils import logger

tutor_bp = Blueprint('tutor', __name__)


@tutor_bp.route('/create', methods=['POST'])
@login_required
def create_session():
    """
    Create a new tutor session for a topic.
    """
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        course_id = data.get('course_id', '')
        
        if not topic:
            return jsonify({"success": False, "error": "Topic is required"}), 400
        
        session_id = tutor_service.create_tutor_session(
            current_user.id, topic, course_id, db
        )
        
        session = tutor_service.get_session(session_id, current_user.id, db)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "session": session
        }), 201
    except Exception as e:
        logger.error(f"Error creating tutor session: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@tutor_bp.route('/<session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """
    Get a tutor session by ID.
    """
    try:
        session = tutor_service.get_session(session_id, current_user.id, db)
        if not session:
            return jsonify({"success": False, "error": "Session not found"}), 404
        
        return jsonify({
            "success": True,
            "session": session
        }), 200
    except Exception as e:
        logger.error(f"Error fetching session: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@tutor_bp.route('/<session_id>/teach', methods=['POST'])
@login_required
def teach_current_step(session_id):
    """
    Get teaching content for the current step.
    """
    try:
        content = tutor_service.teach_step(session_id, current_user.id, db)
        return jsonify({
            "success": True,
            "content": content
        }), 200
    except Exception as e:
        logger.error(f"Error teaching step: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@tutor_bp.route('/<session_id>/answer', methods=['POST'])
@login_required
def submit_answer(session_id):
    """
    Submit an answer to the drill question.
    """
    try:
        data = request.get_json()
        answer = data.get('answer', '')
        
        if not answer:
            return jsonify({"success": False, "error": "Answer is required"}), 400
        
        result = tutor_service.submit_answer(session_id, current_user.id, answer, db)
        return jsonify({
            "success": True,
            "result": result
        }), 200
    except Exception as e:
        logger.error(f"Error submitting answer: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@tutor_bp.route('/sessions', methods=['GET'])
@login_required
def list_sessions():
    """
    List all tutor sessions for the current user.
    """
    try:
        sessions = tutor_service.list_user_sessions(current_user.id, db)
        return jsonify({
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }), 200
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
