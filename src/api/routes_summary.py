from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

summary_bp = Blueprint('summary_bp', __name__)

@summary_bp.route('/trigger', methods=['POST'])
@login_required
def trigger_summary():
    """
    (CORRECTED) This route ONLY triggers the 'summary' AI task.
    It assumes the document has already been processed.
    """
    user_id = current_user.id
    document_id = request.form.get('document_id')
    query = request.form.get('query', 'general summary') # For follow-up questions

    if not document_id:
        return jsonify({"error": "document_id is required"}), 400

    try:
        task_repo = MongoTaskRepository(db)
        task = task_repo.create(user_id=user_id, document_id=document_id, task_type='summary')
        
        publish_task(
            queue_name='summarize',
            task_body={
                "task_id": task.id,
                "document_id": document_id,
                "query": query
            }
        )

        return jsonify({
            "status": "processing_summary",
            "polling_url": url_for('task_bp.get_task_status_route', task_id=task.id)
        }), 202

    except Exception as e:
        logger.error(f"Error in trigger_summary for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500
