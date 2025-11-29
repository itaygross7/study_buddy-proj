import logging
from python_json_logger import jsonlogger
from .config import settings

def setup_logging():
    """
    Configures structured JSON logging for the application.
    """
    logger = logging.getLogger("studybuddy")
    logger.setLevel(settings.LOG_LEVEL)
    
    # Prevent logs from being propagated to the root logger
    logger.propagate = False

    # Use a JSON formatter
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )

    # Log to console
    logHandler = logging.StreamHandler()
    logHandler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(logHandler)
        
    return logger
