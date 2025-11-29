import io
import pytesseract
from PIL import Image
from sb_utils.logger_utils import logger

def extract_text_from_image(file_stream: io.BytesIO) -> str:
    """
    Extracts text from an image file stream using Tesseract OCR.
    """
    try:
        image = Image.open(file_stream)
        text = pytesseract.image_to_string(image)
        
        logger.info("Successfully extracted text from image using OCR.")
        if not text.strip():
            logger.warning("OCR process completed but returned no text.")
            
        return text
    except Exception as e:
        logger.error(f"Could not process image file with Tesseract: {e}", exc_info=True)
        raise ValueError("Invalid or unsupported image file.")
