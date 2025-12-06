import os
import re
import pickle
from typing import List, Dict, Optional
from sb_utils.logger_utils import logger

SMART_REPO_CACHE_DIR = "smart_repo_cache"

def _parse_text_to_chunks(text: str) -> List[Dict[str, str]]:
    """
    A simple structural parser to split text into chunks based on headings.
    This heuristic looks for lines that are short and likely to be titles.
    """
    chunks = []
    current_heading = "Introduction"
    current_content = []

    # A simple regex to find potential headings (short lines, title case, etc.)
    # This can be made much more sophisticated.
    heading_pattern = re.compile(r"^[A-Z][A-Za-z\s]{5,50}$")

    for line in text.split('\\n'):
        stripped_line = line.strip()
        if 1 < len(stripped_line.split()) < 7 and heading_pattern.match(stripped_line):
            # Found a new heading. Save the previous chunk.
            if current_content:
                chunks.append({
                    "heading": current_heading,
                    "content": " ".join(current_content).strip()
                })
            
            current_heading = stripped_line
            current_content = []
        else:
            current_content.append(stripped_line)
    
    # Append the last chunk
    if current_content:
        chunks.append({
            "heading": current_heading,
            "content": " ".join(current_content).strip()
        })
    
    logger.info(f"Dissected text into {len(chunks)} smart chunks.")
    return chunks

def create_smart_repository(document_id: str, text_content: str) -> Optional[str]:
    """
    Parses text content, creates a structured repository on disk, and pickles the chunks.

    Args:
        document_id: The unique ID of the document.
        text_content: The full text of the document.

    Returns:
        The path to the created repository directory, or None on failure.
    """
    try:
        chunks = _parse_text_to_chunks(text_content)
        if not chunks:
            logger.warning(f"Smart parser produced no chunks for document {document_id}.")
            return None

        repo_path = os.path.join(SMART_REPO_CACHE_DIR, document_id)
        os.makedirs(repo_path, exist_ok=True)

        pickle_path = os.path.join(repo_path, "chunks.pkl")
        with open(pickle_path, "wb") as f:
            pickle.dump(chunks, f)
        
        logger.info(f"Successfully created smart repository for document {document_id} at {repo_path}")
        return repo_path
    except Exception as e:
        logger.error(f"Failed to create smart repository for document {document_id}: {e}", exc_info=True)
        return None
