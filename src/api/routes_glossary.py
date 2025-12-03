from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from src.services import glossary_service
from src.infrastructure.database import db
from sb_utils.logger_utils import logger

glossary_bp = Blueprint('glossary', __name__)


@glossary_bp.route('/course/<course_id>', methods=['GET'])
@login_required
def get_course_glossary(course_id):
    """
    Get all glossary terms for a specific course.
    """
    try:
        terms = glossary_service.get_course_glossary(course_id, current_user.id, db)
        return jsonify({
            "success": True,
            "terms": terms,
            "count": len(terms)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching glossary: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@glossary_bp.route('/search', methods=['POST'])
@login_required
def search_glossary():
    """
    Search for terms in the glossary.
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        course_id = data.get('course_id', '')
        
        if not query or not course_id:
            return jsonify({"success": False, "error": "Missing query or course_id"}), 400
        
        terms = glossary_service.search_terms(query, course_id, current_user.id, db)
        return jsonify({
            "success": True,
            "terms": terms,
            "count": len(terms)
        }), 200
    except Exception as e:
        logger.error(f"Error searching glossary: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
