def create_safety_guard_prompt(prompt: str, context: str) -> str:
    """
    Wraps a user prompt with safety instructions and context grounding.
    This helps prevent hallucinations and ensures the AI stays on topic.
    """
    safety_instructions = """
    IMPORTANT: You are an educational assistant. Your response MUST be directly related to the provided text and the user's question.
    - Do NOT invent facts, sources, or figures.
    - If the answer is not in the text, state that clearly.
    - Do not provide opinions or engage in conversation outside the educational scope.
    - Format your response clearly as requested.
    """
    
    full_prompt = f"""
    {safety_instructions}

    --- TEXT FOR CONTEXT ---
    {context}
    --- END OF TEXT ---

    Based *only* on the text provided above, please perform the following task:
    Task: {prompt}
    """
    return full_prompt
