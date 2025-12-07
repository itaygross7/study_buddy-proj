import uuid
import os
import tempfile
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.domain.models.db_models import Document, Task, DocumentStatus
from src.services.file_service import get_file_service
from sb_utils.logger_utils import logger

upload_bp = Blueprint('upload_bp', __name__)

@upload_bp.route("/files", methods=["POST"])
@login_required
def upload_files_route():
    """
    Handles file uploads for a course.

    - Supports multiple files from input name="files"
    - Also supports a single file from name="file" as a fallback
    - For each file:
        * Save to GridFS
        * Create Document in Mongo (including file_size)
        * Create 'file_processing' Task
        * Publish task to RabbitMQ
    """
    user_id = current_user.id
    course_id = request.form.get("course_id", "default")

    # Try multi-file input: name="files"
    files = request.files.getlist("files")
    if not files:
        # Fallback: single file input: name="file"
        single_file = request.files.get("file")
        if single_file:
            files = [single_file]

    if not files:
        return jsonify({"error": "לא התקבלו קבצים להעלאה"}), 400

    file_service = get_file_service()
    doc_repo = MongoDocumentRepository(db)
    task_repo = MongoTaskRepository(db)

    created_docs: list[str] = []
    task_ids: list[str] = []

    try:
        for f in files:
            if not f or not f.filename:
                continue

            filename = secure_filename(f.filename)

            # Best-effort file size in bytes
            # (Most browsers send content_length; if not, we fall back to 0)
            file_size = getattr(f, "content_length", None)
            if file_size is None:
                try:
                    pos = f.stream.tell()
                    f.stream.seek(0, os.SEEK_END)
                    file_size = f.stream.tell()
                    f.stream.seek(pos, os.SEEK_SET)
                except Exception:
                    file_size = 0

            # Save file to GridFS
            gridfs_id = file_service.save_file(f, user_id, course_id)

            # Create Document record (now with file_size)
            document = Document(
                _id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename=filename,
                content_text="[File uploaded, pending processing...]",
                status=DocumentStatus.UPLOADED,
                gridfs_id=str(gridfs_id),
                file_size=file_size,
            )
            doc_repo.create(document)

            # Create Task for processing this document
            task = task_repo.create(
                user_id=user_id,
                document_id=document.id,
                task_type="file_processing",
            )

            # Publish processing task
            publish_task(
                queue_name="file_processing",
                task_body={
                    "task_id": task.id,
                    "document_id": document.id,
                },
            )

            created_docs.append(document.id)
            task_ids.append(str(task.id))

            logger.info(
                "File queued for processing",
                extra={
                    "filename": filename,
                    "user_id": user_id,
                    "course_id": course_id,
                    "task_id": str(task.id),
                    "component": "upload_files_route",
                },
            )

        if not created_docs:
            return jsonify({"error": "לא נמצאו קבצים תקינים להעלאה"}), 400

        return jsonify(
            {
                "status": "processing_file",
                "files_uploaded": len(created_docs),
                "task_ids": task_ids,
            }
        ), 202

    except Exception as e:
        logger.error(
            f"File upload failed for user {user_id}: {e}",
            exc_info=True,
            extra={"component": "upload_files_route"},
        )
        return jsonify({"error": "אירעה שגיאה פנימית. נסה שוב מאוחר יותר."}), 500
