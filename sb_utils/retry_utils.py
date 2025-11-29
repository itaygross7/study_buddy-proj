from tenacity import retry, stop_after_attempt, wait_exponential
from .logger_utils import logger

def on_retry_callback(retry_state):
    """Callback function to log retry attempts."""
    logger.warning(
        f"Retrying function {retry_state.fn.__name__}, "
        f"attempt {retry_state.attempt_number} after {retry_state.seconds_since_start:.2f}s..."
    )

# A general-purpose retry decorator
retry_decorator = retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    before_sleep=on_retry_callback
)
