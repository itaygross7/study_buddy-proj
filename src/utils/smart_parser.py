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

    heading_pattern = re.compile(r"^[A-Z][A-Za-z\s]{5,50}$")

    for line in text.split('\\n'):
        stripped_line = line.strip()
        if 1 < len(stripped_line.split()) < 7 and heading_pattern.match(stripped_line):
            if current_content:
                chunks.append({
                    "heading": current_heading,
                    "content": " ".join(current_content).strip()
                })
            
            current_heading = stripped_line
            current_content = []
        else:
            current_content.append(stripped_line)
    
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

def get_smart_context(document_id: str, query: str, max_len: int = 4000) -> Optional[str]:
    """
    "Sniper Retrieval" - Retrieves the most relevant chunks for a given query.
    If no specific query is given, it returns a general context.
    """
    try:
        pickle_path = os.path.join(SMART_REPO_CACHE_DIR, document_id, "chunks.pkl")
        if not os.path.exists(pickle_path):
            return None

        with open(pickle_path, "rb") as f:
            chunks: List[Dict[str, str]] = pickle.load(f)
        
        # If query is generic, just use the first few chunks.
        if "general" in query.lower() or not query:
            relevant_chunks = chunks[:3] # Return first 3 chunks for a generic summary
        else:
            # Simple keyword search. A real RAG would use vector search here.
            query_words = set(query.lower().split())
            relevant_chunks = [
                chunk for chunk in chunks 
                if any(word in chunk["content"].lower() for word in query_words)
            ]

        if not relevant_chunks:
            logger.warning(f"Smart repo for doc {document_id} exists, but no relevant chunks found for query: '{query}'.")
            return None

        # Combine chunks into a single context string, respecting max_len
        final_context = ""
        for chunk in relevant_chunks:
            chunk_text = f"Context from section '{chunk['heading']}':\\n{chunk['content']}\\n\\n"
            if len(final_context) + len(chunk_text) > max_len:
                break
            final_context += chunk_text
        
        logger.info(f"Smart retrieval successful for doc {document_id}. Using {len(relevant_chunks)} chunks.")
        return final_context.strip()

    except Exception as e:
        logger.error(f"Failed to retrieve from smart repository for doc {document_id}: {e}", exc_info=True)
        return None
