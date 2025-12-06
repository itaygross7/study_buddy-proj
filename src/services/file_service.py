import gridfs
from bson import ObjectId
from werkzeug.datastructures import FileStorage
from flask import g
from src.infrastructure.database import db
from sb_utils.logger_utils import logger

class FileService:
    """A dedicated service for interacting with GridFS."""

    def __init__(self, database):
        # This now requires a real database instance, not a proxy.
        if not hasattr(database, 'collection'):
             raise TypeError(f"database must be a real pymongo.database.Database instance, not {type(database)}")
        self.fs = gridfs.GridFS(database)

    def save_file(self, file_stream: FileStorage, user_id: str, course_id: str) -> ObjectId:
        """Streams a file directly to GridFS and returns the new file's ObjectId."""
        try:
            file_id = self.fs.put(
                file_stream,
                filename=file_stream.filename,
                contentType=file_stream.content_type,
                metadata={"owner_id": user_id, "course_id": course_id}
            )
            logger.info(f"Successfully saved file '{file_stream.filename}' to GridFS with ID: {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Failed to save file to GridFS: {e}", exc_info=True)
            raise

    def get_file_stream(self, gridfs_id: str):
        """Retrieves a file stream from GridFS by its ID."""
        try:
            return self.fs.get(ObjectId(gridfs_id))
        except gridfs.errors.NoFile:
            logger.error(f"No file found in GridFS with ID: {gridfs_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve file from GridFS with ID {gridfs_id}: {e}", exc_info=True)
            raise
            
    def delete_file(self, gridfs_id: str):
        """Deletes a file from GridFS."""
        try:
            self.fs.delete(ObjectId(gridfs_id))
            logger.info(f"Deleted file from GridFS with ID: {gridfs_id}")
        except Exception as e:
            logger.error(f"Failed to delete file from GridFS with ID {gridfs_id}: {e}", exc_info=True)
            raise

def get_file_service() -> FileService:
    """
    Factory function to get a FileService instance.
    It uses the Flask 'g' object to ensure a single instance per request.
    This is the ONLY safe way to use it within the Flask app.
    """
    if 'file_service' not in g:
        # The 'db' proxy resolves to the real database object here
        # because this function is only ever called within a request context.
        g.file_service = FileService(db)
    return g.file_service
