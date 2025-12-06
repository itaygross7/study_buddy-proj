import json
from flask import Blueprint, request, jsonify, url_for
from pydantic import ValidationError

from src.domain.models.api_models import AssessRequest, TaskResponse
from src.services.task_service import create_task
from src.infrastructure.rabbitmq import publish_task
from sb_utils.logger_utils import logger

assess_bp = Blueprint('assess_bp', __name__)


@assess_bp.route('/', methods=['POST'])
def trigger_assessment():
    """Triggers the assessment generation task."""
    try:
        req_data = AssessRequest(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logger.error(f"Failed to parse assessment request: {e}", exc_info=True)
        return jsonify({"error": "Invalid request format"}), 400

    try:
        task_id = create_task()

        message_body = json.dumps({
            "task_id": task_id,
            "queue_name": "assess",
            "document_id": req_data.document_id,
            "num_questions": req_data.num_questions,
            "question_type": req_data.question_type
        })

        publish_task(queue_name='assess', body=message_body)
        logger.info(f"Published assessment task {task_id} for document {req_data.document_id}")

        response = TaskResponse(
            task_id=task_id,
            status="PENDING",
            polling_url=url_for('task_bp.get_task_status_route', task_id=task_id, _external=True)
        )

        return jsonify(response.to_dict()), 202
    except Exception as e:
        logger.error(f"Failed to create assessment task: {e}", exc_info=True)
        return jsonify({"error": "Failed to create task"}), 500
