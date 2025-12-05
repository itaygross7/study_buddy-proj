import uuid
import os
import tempfile
from flask import Blueprint, request, jsonify
from flask_login import current_user

from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.domain.models.db_models import Document, Task, TaskStatus
from src.utils.file_processing import process_uploaded_file
from src.domain.errors import InvalidFileTypeError
from sb_utils.logger_utils import logger
from src.services.task_service import TaskService

upload_bp = Blueprint('upload_bp', __name__)

# Allowed file extensions and MIME types for quick validation
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'pptx', 'txt', 'html', 'png', 'jpg', 'jpeg', 'gif'
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def allowed_file(filename):
    """Quick check for allowed file extensions."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route('/', methods=['POST'])
def upload_file_route():
    """
    Handles file uploads OR text input with INSTANT response.
    File processing happens in the background for lightning-fast uploads.
    """
    # Determine user_id: prioritize authenticated user, then form value, then default
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = request.form.get('user_id', '') or 'anonymous'

    # Get course_id from form or use default
    course_id = request.form.get('course_id', '') or 'default'
    
    # Check if text was provided directly
    text_input = request.form.get('text', '').strip()
    
    if text_input:
        # Handle direct text input - this is fast, process immediately
        try:
            doc_repo = MongoDocumentRepository(db)
            document = Document(
                _id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename="text_input.txt",
                content_text=text_input
            )
            doc_repo.create(document)
            
            logger.info(f"Text content uploaded by user {user_id} to course {course_id}")
            return jsonify({"document_id": document.id, "filename": "text_input.txt", "status": "completed"}), 201
            
        except Exception as e:
            logger.error(f"Error processing text input: {e}", exc_info=True)
            return jsonify({"error": "An internal error occurred while processing the text."}), 500
    
    # Handle file upload - LIGHTNING FAST MODE
    if 'file' not in request.files:
        return jsonify({"error": "No file or text provided"}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    
    # Quick validation - fail fast
    if not allowed_file(filename):
        return jsonify({"error": f"File type not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 415
    
    # Check file size using Content-Length header first, then seek as fallback
    file_size = 0
    if request.content_length:
        file_size = request.content_length
    else:
        # Fallback: use seek for size detection
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": "File too large. Maximum size is 50MB."}), 413
    
    if file_size == 0:
        return jsonify({"error": "File is empty"}), 400
    
    try:
        # Save file to temporary location immediately
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        # Create document record immediately with placeholder content
        doc_repo = MongoDocumentRepository(db)
        document_id = str(uuid.uuid4())
        document = Document(
            _id=document_id,
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            content_text="[Processing... This file is being processed in the background]"
        )
        doc_repo.create(document)
        
        # Create background task to process the file
        task_repo = MongoTaskRepository(db)
        task_id = str(uuid.uuid4())
        task = Task(
            _id=task_id,
            user_id=user_id,
            document_id=document_id,
            task_type='file_upload',
            status=TaskStatus.QUEUED
        )
        task_repo.create(task)
        
        # Queue the file processing job
        task_service = TaskService(db)
        task_service.enqueue_task({
            'task_id': task_id,
            'document_id': document_id,
            'temp_path': temp_path,
            'filename': filename,
            'user_id': user_id,
            'course_id': course_id,
            'queue_name': 'file_processing'
        })
        
        logger.info(f"File '{filename}' queued for processing by user {user_id} to course {course_id}")
        
        # Return immediately - lightning fast!
        return jsonify({
            "document_id": document_id,
            "filename": filename,
            "status": "processing",
            "task_id": task_id,
            "message": "File uploaded successfully! Processing in background..."
        }), 201

    except Exception as e:
        logger.error(f"Internal server error during upload of '{filename}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while uploading the file."}), 500


@upload_bp.route('/status/<document_id>', methods=['GET'])
def check_upload_status(document_id):
    """
    Check the processing status of an uploaded file.
    """
    try:
        doc_repo = MongoDocumentRepository(db)
        document = doc_repo.get_by_id(document_id)
        
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        # Check if document is still being processed
        is_processing = document.content_text.startswith("[Processing...")
        
        return jsonify({
            "document_id": document_id,
            "filename": document.filename,
            "status": "processing" if is_processing else "completed",
            "ready": not is_processing
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking upload status: {e}", exc_info=True)
        return jsonify({"error": "Failed to check status"}), 500
