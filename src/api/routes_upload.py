# src/api/routes_upload.py
import os
import uuid
import tempfile

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.domain.models.db_models import Document, Task, DocumentStatus
from src.services.file_service import get_file_service
from sb_utils.logger_utils import logger

upload_bp = Blueprint("upload_bp", __name__)


def _collect_files():
    """
    Supports:
    - multiple files from <input name="files" multiple>
    - single file from <input name="file">
    Returns list[FileStorage]
    """
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        f = request.files.get("file")
        if f and f.filename:
            files = [f]
    return files


@upload_bp.route("/files", methods=["POST"])
@login_required
def upload_files_route():
    """
    Handles file uploads for a course.

    For each file:
      - save to GridFS
      - create Document in Mongo (status=PENDING)
      - create 'file_processing' Task
      - publish task to RabbitMQ
    """
    user_id = current_user.id
    course_id = (request.form.get("course_id") or "default").strip() or "default"

<<<<<<< HEAD
    if not course_id:
        return jsonify({"error": "course_id is required"}), 400

    # Collect files (multi or single) and filter out empties
    files = [f for f in request.files.getlist("files") if f and f.filename]
=======
    files = _collect_files()
>>>>>>> 77e9dff1cb0f98453d85d9209d4c51ad152fd220
    if not files:
        return jsonify({"error": "No files provided"}), 400

    document_repo = MongoDocumentRepository(db)
    task_repo = MongoTaskRepository(db)
    file_service = get_file_service(db)

    created_docs: list[dict] = []
    created_tasks: list[dict] = []

    for file_storage in files:
        original_name = file_storage.filename or "upload"
        safe_name = secure_filename(original_name) or "upload"
        ext = os.path.splitext(safe_name)[1].lower()

        # Optional: basic allowlist (adjust as needed)
        # allowed = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx"}
        # if ext and ext not in allowed:
        #     return jsonify({"error": f"File type not allowed: {ext}"}), 400

        tmp_path = None
        try:
            # Save to temp (FileStorage.stream -> disk) for consistent FS/GridFS handling
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp_path = tmp.name
                file_storage.save(tmp_path)

            file_size = os.path.getsize(tmp_path)

            # Save binary into GridFS (your file service should return gridfs_id)
            gridfs_id = file_service.save_file(
                file_path=tmp_path,
                filename=safe_name,
                content_type=file_storage.mimetype,
                metadata={
                    "user_id": user_id,
                    "course_id": course_id,
                    "original_name": original_name,
                },
            )

            # IMPORTANT:
            # Some setups return ObjectId. Your Pydantic model expects str.
            # Always stringify here to avoid the exact error you had earlier.
            gridfs_id_str = str(gridfs_id)

            # Create Document
            doc = Document(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename=safe_name,
                original_filename=original_name,
                content_type=file_storage.mimetype or "application/octet-stream",
                file_size=file_size,
                gridfs_id=gridfs_id_str,
                status=DocumentStatus.PENDING,
            )
            document_repo.create(doc)

            # Create Task
            task = Task(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                task_type="file_processing",
                status="PENDING",
                document_id=doc.id,
            )
            task_repo.create(task)

            # Publish
            publish_task(
                queue_name="file_processing",
                task_body={
                    "task_id": task.id,
                    "user_id": user_id,
                    "course_id": course_id,
                    "document_id": doc.id,
                    "gridfs_id": gridfs_id_str,
                    "filename": safe_name,
                    "content_type": doc.content_type,
                    "file_size": file_size,
                },
            )

            created_docs.append({"document_id": doc.id, "filename": safe_name})
            created_tasks.append({"task_id": task.id, "document_id": doc.id})

            logger.info(f"Uploaded file: {safe_name} doc={doc.id} task={task.id}")

        except Exception as e:
            logger.error(f"Upload failed for file {original_name}: {e}", exc_info=True)
            return jsonify({"error": f"Upload failed for {original_name}"}), 500

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    logger.warning(f"Failed to remove temp file: {tmp_path}")

    return jsonify({"documents": created_docs, "tasks": created_tasks}), 201
