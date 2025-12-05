import gridfs
from datetime import datetime
from werkzeug.datastructures import FileStorage
from typing import List
from bson import ObjectId

from src.infrastructure.database import db
# from src.infrastructure.messaging import publish_file_processing_job

class FileService:
    def __init__(self):
        self.fs = gridfs.GridFS(db)

    def upload_files_to_gridfs(self, files: List[FileStorage], user_id: str) -> List[str]:
        """
        Streams a list of files directly to GridFS without loading them into memory.
        """
        file_ids = []
        for file_stream in files:
            if file_stream and file_stream.filename:
                file_id = self.fs.put(
                    file_stream,
                    filename=file_stream.filename,
                    contentType=file_stream.content_type,
                    metadata={
                        "owner_id": user_id,
                        "upload_date": datetime.utcnow()
                    }
                )
                # publish_file_processing_job({"file_id": str(file_id), "user_id": user_id})
                print(f"Published job for file_id: {file_id}")
                file_ids.append(str(file_id))
        return file_ids

    def delete_file(self, file_id: str, user_id: str):
        """
        Deletes a file from GridFS, ensuring the user has ownership.
        """
        file_doc = self.fs.find_one({"_id": ObjectId(file_id), "metadata.owner_id": user_id})
        if not file_doc:
            raise PermissionError("File not found or user does not have permission to delete.")
        
        self.fs.delete(ObjectId(file_id))
        print(f"Deleted file {file_id} for user {user_id}")

file_service = FileService()
