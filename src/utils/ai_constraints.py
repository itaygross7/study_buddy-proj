"""
AI Constraint System - CRITICAL SECURITY MODULE

REQUIREMENT: All AI responses must come ONLY from user-uploaded documents.
NO external knowledge, NO hallucinations, NO outside material.

This module provides strict constraint prompts and validation to ensure
AI models only use document content.
"""

from typing import Literal


ConstraintLevel = Literal["strict", "moderate", "relaxed"]


# STRICT CONSTRAINT: For document-based tasks (summary, flashcards, assessment, etc.)
STRICT_DOCUMENT_CONSTRAINT = """
🔒 CRITICAL CONSTRAINT - READ CAREFULLY:

You are answering based on PROVIDED DOCUMENTS ONLY.

RULES (MUST FOLLOW):
1. ✓ Use ONLY information from the provided document/context
2. ✗ DO NOT use external knowledge, even if you know the topic
3. ✗ DO NOT add information that's not in the document
4. ✗ DO NOT make assumptions or inferences beyond the text
5. ✓ If the answer is NOT in the document, say: "המידע אינו מופיע במסמך" (Information not in document)
6. ✓ Quote or reference the document when answering
7. ✗ DO NOT use phrases like "I know" or "generally" - stick to the document

WHY THIS MATTERS:
- Users trust you to work with THEIR documents only
- Adding outside info = hallucination = wrong answers
- This is a learning tool - accuracy is CRITICAL

If you're unsure if something is in the document, DON'T include it.
When in doubt, err on the side of "not in document."
"""


# MODERATE CONSTRAINT: For homework help (uses document + general teaching)
MODERATE_DOCUMENT_CONSTRAINT = """
📚 CONSTRAINT - Document-First Teaching:

You are helping with homework based on PROVIDED CONTEXT.

RULES:
1. ✓ PRIMARY: Use information from the provided context/document
2. ✓ SECONDARY: If context insufficient, you may use general educational knowledge
3. ✓ ALWAYS indicate when you're going beyond the provided material
4. ✓ Prioritize document content over external knowledge
5. ✓ If document has the answer, use it exclusively

PHRASES TO USE:
- "לפי המסמך..." (According to the document...)
- "המסמך מזכיר..." (The document mentions...)
- "נוסף על המידע במסמך..." (Beyond the document info...)
- "באופן כללי..." (Generally...) - only when supplementing
"""


# RELAXED CONSTRAINT: For chat/conversational (general questions OK)
RELAXED_DOCUMENT_CONSTRAINT = """
💬 CONSTRAINT - Context-Aware Chat:

You are a helpful study assistant.

RULES:
1. ✓ If user provides context/document, prioritize it
2. ✓ May use general knowledge when appropriate
3. ✓ Always be clear about source of information
4. ✓ For factual questions, be accurate and cite sources when possible
"""


def get_constraint_prompt(
    constraint_level: ConstraintLevel = "strict",
    language: str = "he"
) -> str:
    """
    Get the appropriate constraint prompt for AI models.
    
    Args:
        constraint_level: How strict the constraint should be
        language: Language for messages
        
    Returns:
        Constraint prompt text
    """
    constraints = {
        "strict": STRICT_DOCUMENT_CONSTRAINT,
        "moderate": MODERATE_DOCUMENT_CONSTRAINT,
        "relaxed": RELAXED_DOCUMENT_CONSTRAINT
    }
    
    return constraints.get(constraint_level, STRICT_DOCUMENT_CONSTRAINT)


def get_task_constraint_level(task_type: str) -> ConstraintLevel:
    """
    Determine constraint level based on task type.
    
    DESIGN: Different tasks need different constraint levels
    - Document analysis tasks: STRICT (no hallucinations)
    - Homework help: MODERATE (can teach general concepts)
    - Chat/questions: RELAXED (general knowledge OK)
    
    Args:
        task_type: Type of task being performed
        
    Returns:
        Appropriate constraint level
    """
    # STRICT: Must use ONLY document content
    strict_tasks = [
        "summary",       # Summarize THIS document
        "flashcards",    # Create cards from THIS content
        "assessment",    # Test on THIS material
        "quiz",          # Quiz on THIS content
        "glossary",      # Terms from THIS document
        "diagram",       # Diagram of THIS content
        "heavy_file"     # Process THIS file
    ]
    
    # MODERATE: Document-first, but can supplement with teaching
    moderate_tasks = [
        "homework",      # Help with problems (may need general teaching)
    ]
    
    # RELAXED: General knowledge OK
    relaxed_tasks = [
        "chat",          # General questions
        "baby_capy",     # Simplified explanations
        "standard"       # Default
    ]
    
    if task_type in strict_tasks:
        return "strict"
    elif task_type in moderate_tasks:
        return "moderate"
    else:
        return "relaxed"


def build_constrained_context(
    task_type: str,
    document_content: str,
    user_context: str = "",
    language: str = "he"
) -> str:
    """
    Build a context string with appropriate constraints.
    
    This ensures the AI receives:
    1. The constraint instructions
    2. The document content
    3. Any additional context
    
    All properly formatted to prevent hallucinations.
    
    Args:
        task_type: Type of task
        document_content: The user's document content
        user_context: Additional context/instructions
        language: Language
        
    Returns:
        Complete context with constraints
    """
    constraint_level = get_task_constraint_level(task_type)
    constraint_prompt = get_constraint_prompt(constraint_level, language)
    
    # Build structured context
    context_parts = [constraint_prompt]
    
    # Add document content if provided
    if document_content:
        context_parts.append(f"""
───────────────────────────────────────
📄 DOCUMENT CONTENT (Your ONLY source):
───────────────────────────────────────

{document_content}

───────────────────────────────────────
        """)
    else:
        # No document = can't use strict constraint
        if constraint_level == "strict":
            context_parts.append("\n⚠️ WARNING: No document provided. Cannot apply strict constraint.")
    
    # Add user context if any
    if user_context:
        context_parts.append(f"""
Additional Instructions:
{user_context}
        """)
    
    return "\n".join(context_parts)


def validate_response_constraint(
    response: str,
    task_type: str,
    document_content: str
) -> dict:
    """
    Validate that AI response follows constraints (basic heuristics).
    
    This is a simple check, not foolproof, but catches obvious violations.
    
    Args:
        response: AI response to validate
        task_type: Type of task
        document_content: Original document
        
    Returns:
        Dict with validation results
    """
    constraint_level = get_task_constraint_level(task_type)
    
    # Only validate strict tasks
    if constraint_level != "strict":
        return {"valid": True, "warnings": []}
    
    warnings = []
    
    # Check for common hallucination indicators
    hallucination_phrases = [
        "i know",
        "generally speaking",
        "in my knowledge",
        "typically",
        "usually",
        "from my understanding",
        "it is well known"
    ]
    
    response_lower = response.lower()
    for phrase in hallucination_phrases:
        if phrase in response_lower:
            warnings.append(f"Possible hallucination indicator: '{phrase}'")
    
    # Check if response is suspiciously long compared to document
    if document_content and len(response) > len(document_content) * 2:
        warnings.append("Response significantly longer than document - possible added content")
    
    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "constraint_level": constraint_level
    }


# Quick access functions for common use cases
def get_summary_constraint(document_content: str, language: str = "he") -> str:
    """Get constraint for summary task."""
    return build_constrained_context("summary", document_content, "", language)


def get_flashcards_constraint(document_content: str, language: str = "he") -> str:
    """Get constraint for flashcard generation."""
    return build_constrained_context("flashcards", document_content, "", language)


def get_assessment_constraint(document_content: str, language: str = "he") -> str:
    """Get constraint for assessment generation."""
    return build_constrained_context("assessment", document_content, "", language)


def get_homework_constraint(problem: str, document_context: str = "", language: str = "he") -> str:
    """Get constraint for homework help (moderate level)."""
    return build_constrained_context("homework", document_context, problem, language)


def get_chat_constraint(user_question: str, document_context: str = "", language: str = "he") -> str:
    """Get constraint for chat (relaxed level)."""
    return build_constrained_context("chat", document_context, user_question, language)
