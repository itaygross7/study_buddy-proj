import uuid
import os
import tempfile
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.domain.models.db_models import Document, Task
from sb_utils.logger_utils import logger

summary_bp = Blueprint('summary_bp', __name__)

@summary_bp.route('/trigger', methods=['POST'])
@login_required
def trigger_summary():
    """
    (CORRECTED) Creates a single 'summary' task for text, file, or existing doc.
    """
    user_id = current_user.id
    course_id = request.form.get('course_id', 'default')
    text_input = request.form.get('text', '').strip()
    file = request.files.get('file')
    document_id = request.form.get('document_id')

    task_repo = MongoTaskRepository(db)
    doc_repo = MongoDocumentRepository(db)
    task_body = {}

    try:
        if document_id:
            doc = doc_repo.get_by_id(document_id)
            if not doc or doc.user_id != user_id: return jsonify({"error": "Document not found"}), 404
            task_body['document_id'] = document_id

        elif text_input:
            document = Document(_id=str(uuid.uuid4()), user_id=user_id, course_id=course_id, filename="הדבקת טקסט.txt", content_text=text_input)
            doc_repo.create(document)
            task_body['document_id'] = document.id

        elif file and file.filename:
            filename = secure_filename(file.filename)
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, filename)
            file.save(temp_path)

            document = Document(_id=str(uuid.uuid4()), user_id=user_id, course_id=course_id, filename=filename, content_text="[File content to be processed by worker...]")
            doc_repo.create(document)
            task_body['document_id'] = document.id
            task_body['temp_path'] = temp_path
            task_body['filename'] = filename
        
        else:
            return jsonify({"error": "No input provided"}), 400

        task = task_repo.create(user_id=user_id, document_id=task_body['document_id'], task_type='summary')
        task_body['task_id'] = task.id
        task_body['user_id'] = user_id
        task_body['course_id'] = course_id
        
        publish_task(queue_name='summarize', task_body=task_body)

        return jsonify({
            "status": "processing",
            "polling_url": url_for('task_bp.get_task_status_route', task_id=task.id)
        }), 202

    except Exception as e:
        logger.error(f"Error in trigger_summary for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500
