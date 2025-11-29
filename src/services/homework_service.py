from .ai_client import ai_client
from sb_utils.logger_utils import logger

def solve_homework_problem(problem_statement: str) -> str:
    """
    Uses the AI client to generate a step-by-step solution for a problem.
    """
    logger.info(f"Generating solution for problem: {problem_statement[:50]}...")
    
    prompt = """
    You are a helpful teaching assistant. Explain the solution to the following problem in a clear, step-by-step manner.
    Break down the problem, explain the concepts involved, and then show the work.
    """
    
    solution_text = ai_client.generate_text(prompt=prompt, context=problem_statement)
    
    # For homework helper, the result is the text itself, not a DB entry.
    # We can consider saving it later if history is needed.
    
    logger.info(f"Generated solution for problem: {problem_statement[:50]}...")
    return solution_text
