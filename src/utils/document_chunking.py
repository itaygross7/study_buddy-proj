"""
Document chunking and indexing utilities for fast retrieval.

This module provides functionality to:
1. Split documents into semantic chunks (paragraphs, sections)
2. Create metadata for each chunk for fast filtering
3. Store chunks efficiently in MongoDB
4. Retrieve relevant chunks based on query
"""

import re
from typing import List, Dict, Optional
from datetime import datetime, timezone
import hashlib


def chunk_text_by_paragraphs(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into chunks by paragraphs with overlap for context continuity.
    
    Args:
        text: The text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) == 0:
        return []
    
    # Split by double newlines (paragraphs) or single newlines
    paragraphs = re.split(r'\n\s*\n|\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for paragraph in paragraphs:
        para_len = len(paragraph)
        
        # If single paragraph exceeds max size, split it
        if para_len > max_chunk_size:
            # Save current chunk if exists
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split long paragraph into sentences
            sentences = re.split(r'[.!?]\s+', paragraph)
            temp_chunk = []
            temp_size = 0
            
            for sentence in sentences:
                sent_len = len(sentence)
                if temp_size + sent_len > max_chunk_size and temp_chunk:
                    chunks.append(' '.join(temp_chunk) + '.')
                    # Keep overlap
                    if len(temp_chunk) > 1:
                        temp_chunk = temp_chunk[-1:]
                        temp_size = len(temp_chunk[0])
                    else:
                        temp_chunk = []
                        temp_size = 0
                
                temp_chunk.append(sentence)
                temp_size += sent_len
            
            if temp_chunk:
                chunks.append(' '.join(temp_chunk))
            continue
        
        # Check if adding this paragraph exceeds max size
        if current_size + para_len > max_chunk_size and current_chunk:
            # Save current chunk
            chunks.append('\n\n'.join(current_chunk))
            
            # Keep last paragraph for overlap
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-1]
                if len(overlap_text) <= overlap:
                    current_chunk = [overlap_text]
                    current_size = len(overlap_text)
                else:
                    current_chunk = []
                    current_size = 0
            else:
                current_chunk = []
                current_size = 0
        
        current_chunk.append(paragraph)
        current_size += para_len
    
    # Add remaining chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


def create_chunk_metadata(chunk: str, chunk_index: int, total_chunks: int, 
                         document_id: str, filename: str) -> Dict:
    """
    Create metadata for a text chunk.
    
    Args:
        chunk: The text content
        chunk_index: Index of this chunk in the document
        total_chunks: Total number of chunks in the document
        document_id: ID of the parent document
        filename: Original filename
        
    Returns:
        Dictionary with chunk metadata
    """
    # Create a hash of the chunk for deduplication
    chunk_hash = hashlib.md5(chunk.encode('utf-8')).hexdigest()
    
    # Extract key terms (simple frequency-based for now)
    words = re.findall(r'\b\w+\b', chunk.lower())
    word_freq = {}
    for word in words:
        if len(word) > 3:  # Only consider words longer than 3 chars
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get top 10 most frequent words as keywords
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    keywords = [word for word, freq in keywords]
    
    return {
        'chunk_hash': chunk_hash,
        'chunk_index': chunk_index,
        'total_chunks': total_chunks,
        'char_count': len(chunk),
        'word_count': len(words),
        'keywords': keywords,
        'preview': chunk[:200],  # First 200 chars for quick preview
        'document_id': document_id,
        'filename': filename,
        'created_at': datetime.now(timezone.utc)
    }


def smart_retrieve_chunks(db, course_id: str, user_id: str, 
                         query: Optional[str] = None, 
                         max_chunks: int = 5,
                         max_total_chars: int = 4000) -> str:
    """
    Retrieve relevant chunks from a course based on query.
    
    If query is provided, retrieves chunks with matching keywords.
    Otherwise, retrieves most recent chunks.
    
    Args:
        db: Database connection
        course_id: Course ID
        user_id: User ID for ownership verification
        query: Optional search query
        max_chunks: Maximum number of chunks to retrieve
        max_total_chars: Maximum total characters in context
        
    Returns:
        Combined context string
    """
    # Build query filter
    filter_query = {
        "course_id": course_id,
        "user_id": user_id
    }
    
    # If search query provided, filter by keywords
    if query:
        # Extract keywords from query
        query_words = re.findall(r'\b\w+\b', query.lower())
        query_words = [w for w in query_words if len(w) > 3]
        
        if query_words:
            # Match chunks that contain any of the query keywords
            filter_query["keywords"] = {"$in": query_words}
    
    # Retrieve chunks, sorted by relevance (keyword match count) or recency
    chunks_cursor = db.document_chunks.find(filter_query).sort("created_at", -1).limit(max_chunks * 2)
    
    # Score chunks by keyword matches if query provided
    chunks_with_scores = []
    for chunk_doc in chunks_cursor:
        score = 0
        if query:
            chunk_keywords = set(chunk_doc.get('keywords', []))
            query_words_set = set(query_words)
            score = len(chunk_keywords.intersection(query_words_set))
        chunks_with_scores.append((score, chunk_doc))
    
    # Sort by score (descending) if query provided
    if query:
        chunks_with_scores.sort(key=lambda x: x[0], reverse=True)
    
    # Build context from top chunks
    context_parts = []
    total_chars = 0
    chunks_used = 0
    
    for score, chunk_doc in chunks_with_scores:
        if chunks_used >= max_chunks:
            break
        
        chunk_text = chunk_doc.get('content', '')
        chunk_len = len(chunk_text)
        
        if total_chars + chunk_len > max_total_chars:
            # Add partial chunk if there's space
            remaining = max_total_chars - total_chars
            if remaining > 200:  # Only add if meaningful
                context_parts.append(chunk_text[:remaining] + "...")
            break
        
        # Add metadata header for context
        filename = chunk_doc.get('filename', 'Unknown')
        chunk_idx = chunk_doc.get('chunk_index', 0)
        header = f"--- {filename} (חלק {chunk_idx + 1}) ---\n"
        
        context_parts.append(header + chunk_text)
        total_chars += len(header) + chunk_len
        chunks_used += 1
    
    if not context_parts:
        return "לא נמצא חומר רלוונטי בקורס."
    
    return "\n\n".join(context_parts)


def index_document_chunks(db, document_id: str, filename: str, text: str, 
                         course_id: str, user_id: str) -> int:
    """
    Chunk and index a document for fast retrieval.
    
    Args:
        db: Database connection
        document_id: Document ID
        filename: Original filename
        text: Full document text
        course_id: Course ID
        user_id: User ID
        
    Returns:
        Number of chunks created
    """
    # Remove any existing chunks for this document
    db.document_chunks.delete_many({"document_id": document_id})
    
    # Create chunks
    chunks = chunk_text_by_paragraphs(text, max_chunk_size=1000, overlap=100)
    
    if not chunks:
        return 0
    
    # Create metadata and insert chunks
    chunk_docs = []
    for idx, chunk in enumerate(chunks):
        metadata = create_chunk_metadata(chunk, idx, len(chunks), document_id, filename)
        
        chunk_doc = {
            'document_id': document_id,
            'course_id': course_id,
            'user_id': user_id,
            'filename': filename,
            'content': chunk,
            **metadata
        }
        chunk_docs.append(chunk_doc)
    
    # Bulk insert for performance
    if chunk_docs:
        db.document_chunks.insert_many(chunk_docs)
    
    return len(chunks)
