import magic
from werkzeug.datastructures import FileStorage
from src.utils.pdf_utils import extract_text_from_pdf
from src.utils.html_to_text import convert_html_to_text
from sb_utils.logger_utils import logger

def extract_text_from_file(file: FileStorage) -> str:
    """
    Detects file type and extracts text content from an uploaded file.
    Supports plain text, HTML, and PDF.
    """
    try:
        # Read a small chunk to identify the file type
        file_content_chunk = file.read(2048)
        file.seek(0)  # Reset file pointer to the beginning
        
        mime_type = magic.from_buffer(file_content_chunk, mime=True)
        logger.info(f"Detected MIME type '{mime_type}' for file '{file.filename}'.")

        if mime_type == 'application/pdf':
            return extract_text_from_pdf(file)
        
        elif mime_type == 'text/html':
            html_content = file.read().decode('utf-8')
            return convert_html_to_text(html_content)
            
        elif mime_type.startswith('text/'):
            return file.read().decode('utf-8')
            
        else:
            logger.warning(f"Unsupported file type '{mime_type}' for file '{file.filename}'.")
            raise ValueError(f"Unsupported file type: {mime_type}")

    except Exception as e:
        logger.error(f"Failed to read or process file '{file.filename}': {e}", exc_info=True)
        raise
