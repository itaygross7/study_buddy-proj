import uuid
import os
import tempfile
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.domain.models.db_models import Document, Task, TaskStatus
from sb_utils.logger_utils import logger

upload_bp = Blueprint('upload_bp', __name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@upload_bp.route('/', methods=['POST'])
@login_required
def upload_route():
    """
    Handles both direct text input and file uploads.
    - For text, it's processed synchronously.
    - For files, it's processed asynchronously.
    """
    user_id = current_user.id
    course_id = request.form.get('course_id', 'default')
    text_input = request.form.get('text', '').strip()

    # --- Handle Direct Text Input ---
    if text_input:
        try:
            doc_repo = MongoDocumentRepository(db)
            document = Document(
                _id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename="הדבקת טקסט.txt",
                content_text=text_input
            )
            doc_repo.create(document)
            logger.info(f"Text content uploaded by user {user_id}")
            return jsonify({
                "document_id": document.id, 
                "filename": document.filename, 
                "status": "completed"
            }), 201
        except Exception as e:
            logger.error(f"Error processing text input for user {user_id}: {e}", exc_info=True)
            return jsonify({"error": "An internal error occurred"}), 500

    # --- Handle File Upload (Async) ---
    if 'file' not in request.files:
        return jsonify({"error": "No file or text provided"}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if file.content_length > MAX_FILE_SIZE:
        return jsonify({"error": "File too large"}), 413

    try:
        # Save file to a temporary location for the worker
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        # Create DB records for the document and the task
        doc_repo = MongoDocumentRepository(db)
        task_repo = MongoTaskRepository(db)
        
        document = Document(
            _id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            content_text="[Processing...]"
        )
        doc_repo.create(document)

        task = task_repo.create(user_id=user_id, document_id=document.id, task_type='file_processing')

        # Publish the job to RabbitMQ
        publish_task(
            queue_name='file_processing',
            task_body={
                "task_id": task.id,
                "document_id": document.id,
                "temp_path": temp_path,
                "filename": filename
            }
        )
        
        # Return a response that HTMX can use to start polling
        return jsonify({
            "message": "File upload started.",
            "status": "processing",
            "polling_url": url_for('task_bp.get_task_status_route', task_id=task.id)
        }), 202
    except Exception as e:
        logger.error(f"File upload failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "File upload failed"}), 500
