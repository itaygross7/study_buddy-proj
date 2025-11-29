import io
from docx import Document
from sb_utils.logger_utils import logger

def extract_text_from_docx(file_stream: io.BytesIO) -> str:
    """
    Extracts text from a .docx file stream.
    """
    try:
        document = Document(file_stream)
        full_text = [para.text for para in document.paragraphs]
        logger.info("Successfully extracted text from DOCX file.")
        return '\\n'.join(full_text)
    except Exception as e:
        logger.error(f"Could not read DOCX file: {e}", exc_info=True)
        raise ValueError("Invalid or corrupted DOCX file.")
