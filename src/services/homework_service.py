from .ai_client import ai_client
from sb_utils.logger_utils import logger


def solve_homework_problem(problem_statement: str, context_text: str | None = None) -> str:
    """
    Uses the AI client to generate a step-by-step solution for a problem.

    Now correctly:
    - Gets the student's problem.
    - Optionally uses relevant course material / uploaded content (context_text).
    - Sends BOTH to the AI so answers are grounded in the right material.
    """
    # Log only a small prefix to avoid leaking full question in logs.
    logger.info(f"Generating solution for problem: {problem_statement[:50]}...")

    prompt = (
        "You are a helpful teaching assistant. Explain the solution to the "
        "following problem in a clear, step-by-step manner. Break down the "
        "problem, explain the concepts involved, and then show the work.\n\n"
        "Use ONLY the course material provided. If the answer is not clearly "
        "supported by the material, say that explicitly and suggest what the "
        "student should review."
    )

    if context_text:
        combined_context = (
            "=== STUDENT PROBLEM ===\n"
            f"{problem_statement}\n\n"
            "=== RELEVANT COURSE MATERIAL / UPLOADED CONTENT ===\n"
            f"{context_text}\n"
        )
    else:
        # Fallback: no extra material, use only the problem.
        combined_context = problem_statement

    solution_text = ai_client.generate_text(
        prompt=prompt,
        context=combined_context,
        task_type="homework",  # Routes to Gemini / homework profile as you set up
    )

    logger.info(f"Generated solution for problem: {problem_statement[:50]}...")
    return solution_text
