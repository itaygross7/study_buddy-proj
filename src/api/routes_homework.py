import json
from flask import Blueprint, request, jsonify, url_for
from pydantic import ValidationError

from src.domain.models.api_models import HomeworkRequest, TaskResponse
from src.services.task_service import create_task
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

homework_bp = Blueprint('homework_bp', __name__)

@homework_bp.route('/', methods=['POST'])
def trigger_homework_helper():
    """Triggers the homework helper task."""
    try:
        req_data = HomeworkRequest(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    task_id = create_task()
    
    message_body = json.dumps({
        "task_id": task_id,
        "queue_name": "homework",
        "problem_statement": req_data.problem_statement
    })
    
    publish_task(queue_name='homework', body=message_body)
    logger.info(f"Published homework task {task_id}")

    response = TaskResponse(
        task_id=task_id,
        status="PENDING",
        polling_url=url_for('task_bp.get_task_status_route', task_id=task_id, _external=True)
    )
    
    return jsonify(response.to_dict()), 202
