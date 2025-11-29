from typing import IO
import logging
from sb_utils.file_utils import save_stream_to_temp, clean_temp_path, UploadedFile
from sb_utils.validation import validate_upload

logger = logging.getLogger(__name__)

class FileService:
    """
    Handles user files: validation, safe temp storage, lightweight extraction.
    Extraction itself can be implemented using optional libs; here we keep API simple.
    """

    def validate_and_store(self, stream: IO[bytes], filename: str) -> UploadedFile:
        uf = save_stream_to_temp(stream, filename)
        # do not log contents or names that could be sensitive (only size/mime)
        logger.debug("Stored temp file (size=%d, mime=%s)", uf.size, uf.content_type)
        err = validate_upload(uf.content_type, uf.size)
        if err:
            clean_temp_path(uf.temp_path)
            raise ValueError(err)
        return uf

    def extract_text(self, uploaded: UploadedFile) -> str:
        """
        Lightweight extraction: for TXT, read; for others return placeholder instruction.
        Real extraction should be implemented via dedicated extractors (pdfminer, docx2txt...).
        """
        try:
            if uploaded.content_type == "text/plain":
                with open(uploaded.temp_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            # keep fallback small and explicit
            return f"[קובץ נתמך: {uploaded.filename} — טקסט לא הופק אוטומטית]"
        finally:
            # caller decides when to clean
            pass

    @staticmethod
    def cleanup(uploaded: UploadedFile) -> None:
        """
        Public helper so routes/tests do not touch filesystem utils directly.
        """
        clean_temp_path(uploaded.temp_path)
