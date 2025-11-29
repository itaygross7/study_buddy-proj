import logging
import logging.config
from ..config.settings import settings

def setup_logger():
    """
    Sets up the application logger.
    """
    logging.config.fileConfig('src/config/logging.conf', disable_existing_loggers=False)
    logger = logging.getLogger(__name__)
    logger.setLevel(settings.LOG_LEVEL.upper())
    return logger

logger = setup_logger()
