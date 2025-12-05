import uuid
import os
import tempfile
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.domain.models.db_models import Document, Task, TaskStatus
from sb_utils.logger_utils import logger
from src.services.file_service import file_service

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


@upload_bp.route('/files', methods=['POST'])
@login_required
def upload_files_route():
    """
    Handles multiple file uploads using GridFS streaming.
    Files are streamed directly to GridFS without loading into memory.
    Metadata is stored separately for fast querying.
    RabbitMQ is used for async processing handoff.
    """
    user_id = current_user.id
    course_id = request.form.get('course_id', 'default')
    
    # Get list of files from the request
    files = request.files.getlist('files')
    
    if not files or len(files) == 0:
        return jsonify({"error": "No files provided"}), 400
    
    try:
        uploaded_files = []
        
        for file in files:
            if not file or not file.filename:
                continue
                
            # Validate file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({"error": f"File {file.filename} is too large (max 50MB)"}), 413
            
            # Stream file directly to GridFS
            file_id = file_service.fs.put(
                file,
                filename=file.filename,
                contentType=file.content_type,
                metadata={
                    "owner_id": user_id,
                    "upload_date": datetime.utcnow()
                }
            )
            
            # Store metadata in a separate collection for fast querying
            user_files_collection = db['user_files']
            file_metadata = {
                "_id": str(file_id),
                "user_id": user_id,
                "course_id": course_id,
                "filename": file.filename,
                "size": file_size,
                "content_type": file.content_type,
                "upload_date": datetime.utcnow(),
                "status": "processing"
            }
            user_files_collection.insert_one(file_metadata)
            
            # Publish async task to RabbitMQ immediately (non-blocking)
            publish_task(
                queue_name='file_processing',
                task_body={
                    "file_id": str(file_id),
                    "user_id": user_id,
                    "filename": file.filename
                }
            )
            
            uploaded_files.append({
                "file_id": str(file_id),
                "filename": file.filename,
                "size": file_size
            })
            
            logger.info(f"File {file.filename} uploaded to GridFS by user {user_id}, file_id: {file_id}")
        
        return jsonify({
            "message": f"{len(uploaded_files)} file(s) uploaded successfully",
            "files": uploaded_files,
            "status": "processing"
        }), 202
        
    except Exception as e:
        logger.error(f"Multi-file upload failed for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "File upload failed"}), 500


@upload_bp.route('/files/<file_id>', methods=['DELETE'])
@login_required
def delete_file_route(file_id):
    """
    Deletes a file from GridFS and removes its metadata.
    Ensures user has ownership before deletion.
    """
    user_id = current_user.id
    
    try:
        # Delete from GridFS
        file_service.delete_file(file_id, user_id)
        
        # Delete metadata
        user_files_collection = db['user_files']
        result = user_files_collection.delete_one({"_id": file_id, "user_id": user_id})
        
        if result.deleted_count == 0:
            return jsonify({"error": "File not found or permission denied"}), 404
        
        logger.info(f"File {file_id} deleted by user {user_id}")
        return jsonify({"message": "File deleted successfully"}), 200
        
    except PermissionError as e:
        logger.warning(f"Permission denied for file deletion: {e}")
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.error(f"File deletion failed: {e}", exc_info=True)
        return jsonify({"error": "File deletion failed"}), 500


@upload_bp.route('/files', methods=['GET'])
@login_required
def list_files_route():
    """
    Lists all files uploaded by the current user.
    Returns metadata from the user_files collection for fast querying.
    """
    user_id = current_user.id
    
    try:
        from flask import render_template_string
        
        user_files_collection = db['user_files']
        files = list(user_files_collection.find(
            {"user_id": user_id},
            {"_id": 1, "filename": 1, "size": 1, "upload_date": 1, "status": 1}
        ).sort("upload_date", -1))
        
        # Convert ObjectId to string and format dates
        for file in files:
            file['file_id'] = str(file.pop('_id'))
            if 'upload_date' in file:
                file['upload_date'] = file['upload_date'].isoformat()
        
        # Return HTML for HTMX
        template = """
{% if files %}
<div class="overflow-x-auto">
    <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
            <tr>
                <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">שם קובץ</th>
                <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">גודל</th>
                <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">תאריך</th>
                <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">סטטוס</th>
                <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">פעולות</th>
            </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
            {% for file in files %}
            <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">{{ file.filename }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                    {% if file.size %}
                        {% if file.size < 1024 %}
                            {{ file.size }} B
                        {% elif file.size < 1048576 %}
                            {{ "%.2f"|format(file.size / 1024) }} KB
                        {% else %}
                            {{ "%.2f"|format(file.size / 1048576) }} MB
                        {% endif %}
                    {% else %}
                        -
                    {% endif %}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                    {% if file.upload_date %}
                        {{ file.upload_date[:10] }}
                    {% else %}
                        -
                    {% endif %}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-right">
                    {% if file.status == 'processing' %}
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                            מעבד
                        </span>
                    {% elif file.status == 'completed' %}
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            הושלם
                        </span>
                    {% else %}
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                            {{ file.status }}
                        </span>
                    {% endif %}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-right">
                    <button 
                        hx-delete="{{ url_for('upload_bp.delete_file_route', file_id=file.file_id) }}"
                        hx-confirm="האם אתה בטוח שברצונך למחוק את הקובץ?"
                        hx-target="closest tr"
                        hx-swap="outerHTML"
                        class="text-red-600 hover:text-red-900">
                        מחק
                    </button>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% else %}
<p class="text-center text-gray-500">לא נמצאו קבצים</p>
{% endif %}
        """
        
        return render_template_string(template, files=files)
        
    except Exception as e:
        logger.error(f"Failed to list files for user {user_id}: {e}", exc_info=True)
        return "<p class='text-center text-red-500'>שגיאה בטעינת הקבצים</p>", 500
