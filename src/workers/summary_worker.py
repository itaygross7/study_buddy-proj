from ..utils.queue_utils import celery_app

@celery_app.task
def summarize_text_task(text: str):
    """
    Celery task to summarize text.
    """
    # TODO: Implement actual summarization logic with LLM
    print(f"Worker summarizing text: {text[:50]}...")
    return f"Summary of: {text[:50]}..."
