import io
from PyPDF2 import PdfReader, errors
from sb_utils.logger_utils import logger


def extract_text_from_pdf(file_stream: io.BytesIO) -> str:
    """
    Extracts text from a PDF file stream using PyPDF2.
    """
    try:
        pdf_reader = PdfReader(file_stream)
        text = "".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
        if not text:
            logger.warning("PyPDF2 extracted no text. The PDF might be image-based or scanned.")
        return text
    except errors.PdfReadError as e:
        logger.error(f"Could not read PDF file. It may be encrypted or corrupted: {e}")
        raise ValueError("Invalid or corrupted PDF file.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during PDF text extraction: {e}", exc_info=True)
        raise
