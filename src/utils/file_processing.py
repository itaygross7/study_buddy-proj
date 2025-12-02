import magic
from werkzeug.datastructures import FileStorage
from .pdf_utils import extract_text_from_pdf
from .html_to_text import convert_html_to_text
from .docx_utils import extract_text_from_docx
from .pptx_utils import extract_text_from_pptx
from .image_utils import extract_text_from_image
from sb_utils.logger_utils import logger


def process_uploaded_file(file: FileStorage) -> str:
    """
    Detects file type and extracts text content from an uploaded file.
    Supports images (PNG, JPEG), PDF, DOCX, PPTX, HTML, and plain text.
    """
    try:
        file_content_chunk = file.read(2048)
        file.seek(0)

        mime_type = magic.from_buffer(file_content_chunk, mime=True)
        logger.info(f"Processing file '{file.filename}' with detected MIME type '{mime_type}'.")

        if mime_type.startswith('image/'):
            return extract_text_from_image(file)

        elif mime_type == 'application/pdf':
            return extract_text_from_pdf(file)

        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return extract_text_from_docx(file)

        elif mime_type == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
            return extract_text_from_pptx(file)

        elif mime_type == 'text/html':
            html_content = file.read().decode('utf-8', errors='ignore')
            return convert_html_to_text(html_content)

        elif mime_type.startswith('text/'):
            return file.read().decode('utf-8', errors='ignore')

        else:
            logger.warning(f"Unsupported file type '{mime_type}' for file '{file.filename}'.")
            raise ValueError(f"Unsupported file type: {mime_type}")

    except Exception as e:
        logger.error(f"Error processing file '{file.filename}': {e}", exc_info=True)
        raise ValueError("Failed to read or process the uploaded file.")
