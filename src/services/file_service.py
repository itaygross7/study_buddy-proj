import gridfs
from bson import ObjectId
from werkzeug.datastructures import FileStorage
from src.infrastructure.database import db
from sb_utils.logger_utils import logger

class FileService:
    """A dedicated service for interacting with GridFS."""

    def __init__(self):
        self.fs = gridfs.GridFS(db)

    def save_file(self, file_stream: FileStorage, user_id: str, course_id: str) -> ObjectId:
        """
        Streams a file directly to GridFS and returns the new file's ObjectId.
        This is a safe, synchronous operation.
        """
        try:
            file_id = self.fs.put(
                file_stream,
                filename=file_stream.filename,
                contentType=file_stream.content_type,
                metadata={
                    "owner_id": user_id,
                    "course_id": course_id
                }
            )
            logger.info(f"Successfully saved file '{file_stream.filename}' to GridFS with ID: {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Failed to save file to GridFS: {e}", exc_info=True)
            raise

    def get_file_stream(self, gridfs_id: str):
        """
        Retrieves a file stream from GridFS by its ID.
        """
        try:
            gridfs_file = self.fs.get(ObjectId(gridfs_id))
            return gridfs_file
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

file_service = FileService()
