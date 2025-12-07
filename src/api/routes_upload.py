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

@upload_bp.route('/files', methods=['POST'])
@login_required
def upload_files_route():
    """
    (RESTORED) Handles file uploads for a specific course and creates a background
    task for processing. This is the endpoint the course page form posts to.
    """
    user_id = current_user.id
    course_id = request.form.get('course_id')
    if not course_id:
        return jsonify({"error": "Course ID is required"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    try:
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        doc_repo = MongoDocumentRepository(db)
        task_repo = MongoTaskRepository(db)

        document = Document(
            _id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            content_text="[File uploaded, pending processing...]"
        )
        doc_repo.create(document)

        task = task_repo.create(user_id=user_id, document_id=document.id, task_type='file_processing')

        publish_task(
            queue_name='file_processing',
            task_body={
                "task_id": task.id,
                "document_id": document.id,
                "temp_path": temp_path,
                "filename": filename
            }
        )
        
        logger.info(f"File '{filename}' for course '{course_id}' queued for processing. Task ID: {task.id}")
        
        # Return a success message that HTMX can display.
        # The reactive list on the page will be updated via its own polling or event trigger.
        return f"<p class='text-green-500'>הקובץ '{filename}' הועלה בהצלחה ומעובד ברקע.</p>", 202

    except Exception as e:
        logger.error(f"File upload failed for user {user_id}, course {course_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during file upload."}), 500
