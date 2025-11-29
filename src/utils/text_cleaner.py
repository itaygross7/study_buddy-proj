import re

def clean_text(text: str) -> str:
    """
    Performs basic text cleaning.
    - Replaces multiple whitespace characters (including newlines) with a single space.
    - Removes leading/trailing whitespace.
    """
    if not isinstance(text, str):
        return ""
    # Replace multiple whitespace chars (space, tab, newline) with a single space
    cleaned_text = re.sub(r'\s+', ' ', text)
    return cleaned_text.strip()
