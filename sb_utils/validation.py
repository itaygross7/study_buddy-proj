from typing import Optional
from .file_utils import allowed_mimetype, MAX_FILE_SIZE_BYTES
import logging

logger = logging.getLogger(__name__)

# user-facing messages (use enums / constants)
HEBREW_ERRORS = {
    "no_input": "לא הוזן טקסט או קובץ. אנא העתק טקסט או העלה קובץ.",
    "bad_type": "סוג הקובץ אינו נתמך. אנא העלה PDF, DOCX, TXT או תמונה (PNG/JPEG).",
    "too_large": "הקובץ גדול מדי. אנא השתמש בקבצים עד 10MB.",
    "server_error": "אירעה שגיאה בשרת. נסה שוב מאוחר יותר.",
}

def validate_upload(mime: Optional[str], size: int) -> Optional[str]:
    """
    Validate upload size and MIME type.
    Returns a Hebrew error message if invalid, otherwise None.
    """
    if size <= 0:
        logger.debug("Validation failed: empty upload (size=%d)", size)
        return HEBREW_ERRORS["no_input"]
    if size > MAX_FILE_SIZE_BYTES:
        logger.debug("Validation failed: too large (size=%d)", size)
        return HEBREW_ERRORS["too_large"]
    if not allowed_mimetype(mime):
        logger.debug("Validation failed: bad MIME type (%s)", mime)
        return HEBREW_ERRORS["bad_type"]
    return None
