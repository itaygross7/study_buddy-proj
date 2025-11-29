from ..utils.queue_utils import celery_app

@celery_app.task
def generate_flashcards_task(text: str):
    """
    Celery task to generate flashcards.
    """
    # TODO: Implement actual flashcard generation logic with LLM
    print(f"Worker generating flashcards from text: {text[:50]}...")
    return [{"question": "What is the capital of France?", "answer": "Paris"}]
