import uuid
import os
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from src.infrastructure.database import db
from src.infrastructure.repositories import MongoDocumentRepository, MongoTaskRepository
from src.infrastructure.rabbitmq import publish_task
from src.services.file_service import get_file_service
from sb_utils.logger_utils import logger
from src.domain.models.db_models import Document, DocumentStatus

upload_bp = Blueprint("upload_bp", __name__)


@upload_bp.route("/files", methods=["POST"])
@login_required
def upload_files_route():
    """
    Upload one or more files, save to GridFS, create Document + Task.

    Form fields:
      - course_id (required)
      - files (can be multiple)  OR single "file"
    """
    user_id = current_user.id
    course_id = request.form.get("course_id")

    if not course_id:
        return jsonify({"error": "course_id is required"}), 400

    # Collect files (multi or single) and filter out empties
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        single_file = request.files.get("file")
        if single_file and single_file.filename:
            files = [single_file]

    if not files:
        return jsonify({"error": "לא התקבלו קבצים"}), 400

    file_service = get_file_service()
    doc_repo = MongoDocumentRepository(db)
    task_repo = MongoTaskRepository(db)

    created_docs: list[str] = []
    tasks_created: list[str] = []

    logger.info(
        "User %s uploading %d file(s) to course %s",
        user_id,
        len(files),
        course_id,
    )

    try:
        for f in files:
            filename = secure_filename(f.filename)

            # --- FILE SIZE (best-effort) ---
            try:
                pos = f.stream.tell()
                f.stream.seek(0, os.SEEK_END)
                file_size = f.stream.tell()
                f.stream.seek(pos, os.SEEK_SET)
            except Exception:
                file_size = 0

            # --- SAVE TO GRIDFS ---
            gridfs_id = file_service.save_file(f, user_id, course_id)
            logger.info(
                "Saved file '%s' to GridFS with ID: %s",
                filename,
                gridfs_id,
            )

            # --- CREATE DOCUMENT MODEL (gridfs_id as STRING) ---
            document = Document(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                filename=filename,
                original_filename=filename,
                content_text="[Processing file…]",
                content_type="file",
                file_size=file_size,
                status=DocumentStatus.UPLOADED,
                gridfs_id=str(gridfs_id),
            )

            # --- SAVE DOCUMENT ---
            doc_repo.create(document)
            created_docs.append(document.id)

            # --- CREATE TASK VIA REPOSITORY ---
            task = task_repo.create(
                user_id=user_id,
                document_id=document.id,
                task_type="file_processing",
            )
            tasks_created.append(task.id)

            # --- SEND TO QUEUE ---
            publish_task(
                queue_name="file_processing",
                task_body={
                    "task_id": task.id,
                    "document_id": document.id,
                },
            )

        return jsonify(
            {
                "status": "processing",
                "files_uploaded": len(created_docs),
                "documents": created_docs,
                "task_ids": tasks_created,
            }
        ), 202

    except Exception as e:
        logger.error(
            "Upload failed for user %s: %s",
            user_id,
            e,
            exc_info=True,
        )
        return jsonify({"error": "שגיאה פנימית בשרת"}), 500
