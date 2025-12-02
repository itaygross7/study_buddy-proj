import logging
import sys
from pythonjsonlogger import jsonlogger

# This function can be called from the app factory to get a configured logger


def get_logger(name: str, log_level: str = "INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = False

    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(module)s %(funcName)s %(message)s'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# Default logger instance
logger = get_logger("studybuddyai")
