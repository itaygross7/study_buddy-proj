from flask import Blueprint, jsonify, render_template
from src.services.task_service import get_task
from sb_utils.logger_utils import logger

task_bp = Blueprint('task_bp', __name__)

@task_bp.route('/<string:task_id>', methods=['GET'])
def get_task_status_route(task_id: str):
    """
    API endpoint to poll for task status and return an HTML partial.
    """
    logger.debug(f"Polling status for task_id: {task_id}")
    task = get_task(task_id)
    
    if not task:
        logger.warning(f"Task not found for task_id: {task_id}")
        return jsonify({"error": "Task not found"}), 404

    # This template is designed to be swapped into the UI by HTMX
    return render_template('task_status.html', task=task)
