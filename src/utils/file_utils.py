import magic
from bs4 import BeautifulSoup
from werkzeug.datastructures import FileStorage
from .pdf_utils import extract_text_from_pdf
from ..infrastructure.logging_config import setup_logging

logger = setup_logging()

def extract_text_from_file(file: FileStorage) -> str:
    """
    Detects file type and extracts text content.
    Supports plain text, HTML, and PDF.
    """
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)

    logger.info(f"Detected MIME type: {mime_type} for file {file.filename}")

    if mime_type == 'application/pdf':
        return extract_text_from_pdf(file)
    elif mime_type == 'text/html':
        soup = BeautifulSoup(file.read(), 'html.parser')
        return soup.get_text()
    elif mime_type.startswith('text/'):
        return file.read().decode('utf-8')
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")
