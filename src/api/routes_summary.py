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
    Trigger an AI summary task for an entire course.

    Expected form fields:
    - course_id: required
    - query: optional (defaults to 'general summary').
    """
    user_id = current_user.id
    course_id = request.form.get('course_id')
    query = request.form.get('query', 'general summary')

    if not course_id:
        
        # ✅ HTMX expects an HTML partial so it won't render JSON in the page
        if request.headers.get("HX-Request") == "true":
            task = task_repo.get_by_id(task.id)
            if task is None:
                return jsonify({"error": "Task not found"}), 404
            return render_template("task_status.html", task=task), 202

return jsonify({"error": "course_id is required"}), 400

    try:
        task_repo = MongoTaskRepository(db)
        task = task_repo.create(
            user_id=user_id,
            course_id=course_id,
            task_type='summary'
        )

        publish_task(
            queue_name='summarize',
            task_body={
                "task_id": task.id,
                "course_id": course_id,
                "query": query,
            },
        )

        return jsonify({
            "status": "processing_summary",
            "polling_url": url_for('task_bp.get_task_status_route', task_id=task.id),
        }), 202

    except Exception as e:
        logger.error(f"Error in trigger_summary for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500
