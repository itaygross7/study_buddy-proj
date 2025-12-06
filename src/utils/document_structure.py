"""
Document structure parser - extracts hierarchical structure WITHOUT using AI.

This module analyzes document structure based on:
1. Markdown headers (# ## ###)
2. HTML headers (<h1> <h2> <h3>)
3. Bold/uppercase patterns
4. Numbering patterns (1. 2. 3. or 1.1 1.2)
5. Whitespace and formatting cues
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DocumentSection:
    """Represents a section in a document."""
    level: int  # 0 = root, 1 = chapter, 2 = section, 3 = subsection
    title: str
    content: str
    start_pos: int
    end_pos: int
    parent_title: Optional[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


def detect_markdown_headers(text: str) -> List[Tuple[int, int, str, int]]:
    """
    Detect markdown-style headers (# ## ###).
    
    Returns:
        List of (start_pos, end_pos, title, level) tuples
    """
    headers = []
    # Match lines starting with # (markdown headers)
    pattern = r'^(#{1,6})\s+(.+?)$'
    
    for match in re.finditer(pattern, text, re.MULTILINE):
        level = len(match.group(1))  # Count number of #
        title = match.group(2).strip()
        start_pos = match.start()
        end_pos = match.end()
        headers.append((start_pos, end_pos, title, level))
    
    return headers


def detect_numbered_sections(text: str) -> List[Tuple[int, int, str, int]]:
    """
    Detect numbered sections like "1. Introduction" or "1.1 Overview".
    
    Returns:
        List of (start_pos, end_pos, title, level) tuples
    """
    headers = []
    
    # Match patterns like "1. Title" or "1.1 Title" or "1.1.1 Title"
    pattern = r'^(\d+(?:\.\d+)*\.?)\s+([A-Z][^\n]+?)(?:\n|$)'
    
    for match in re.finditer(pattern, text, re.MULTILINE):
        number = match.group(1).rstrip('.')
        title = match.group(2).strip()
        
        # Determine level by counting dots
        level = number.count('.') + 1
        
        start_pos = match.start()
        end_pos = match.end()
        headers.append((start_pos, end_pos, title, level))
    
    return headers


def detect_bold_headers(text: str) -> List[Tuple[int, int, str, int]]:
    """
    Detect bold text that likely represents headers.
    Looks for **text** or lines in ALL CAPS.
    
    Returns:
        List of (start_pos, end_pos, title, level) tuples
    """
    headers = []
    
    # Match **bold text** on its own line
    bold_pattern = r'^\*\*(.+?)\*\*$'
    for match in re.finditer(bold_pattern, text, re.MULTILINE):
        title = match.group(1).strip()
        if len(title) > 3 and len(title) < 100:  # Reasonable header length
            headers.append((match.start(), match.end(), title, 2))
    
    # Match lines in ALL CAPS (likely headers)
    caps_pattern = r'^([A-Z][A-Z\s]{3,50})$'
    for match in re.finditer(caps_pattern, text, re.MULTILINE):
        title = match.group(1).strip()
        # Avoid matching acronyms or short words
        if ' ' in title and len(title.split()) > 1:
            headers.append((match.start(), match.end(), title, 2))
    
    return headers


def detect_html_headers(text: str) -> List[Tuple[int, int, str, int]]:
    """
    Detect HTML headers (<h1> <h2> etc).
    
    Returns:
        List of (start_pos, end_pos, title, level) tuples
    """
    headers = []
    
    # Match <h1>...</h1> through <h6>...</h6>
    pattern = r'<h([1-6])[^>]*>(.+?)</h\1>'
    
    for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
        level = int(match.group(1))
        title = re.sub(r'<[^>]+>', '', match.group(2)).strip()  # Remove inner HTML tags
        start_pos = match.start()
        end_pos = match.end()
        headers.append((start_pos, end_pos, title, level))
    
    return headers


def parse_document_structure(text: str) -> List[DocumentSection]:
    """
    Parse document into hierarchical sections based on structure.
    NO AI - uses only pattern matching and heuristics.
    
    Args:
        text: Full document text
        
    Returns:
        List of DocumentSection objects representing the document structure
    """
    # Detect all types of headers
    all_headers = []
    
    # Try different header detection methods
    all_headers.extend(detect_markdown_headers(text))
    all_headers.extend(detect_numbered_sections(text))
    all_headers.extend(detect_bold_headers(text))
    all_headers.extend(detect_html_headers(text))
    
    # Sort by position in text
    all_headers.sort(key=lambda x: x[0])
    
    # Remove duplicates (headers detected by multiple methods)
    unique_headers = []
    last_pos = -100
    for header in all_headers:
        if header[0] - last_pos > 10:  # At least 10 chars apart
            unique_headers.append(header)
            last_pos = header[0]
    
    if not unique_headers:
        # No structure detected - treat entire document as one section
        return [DocumentSection(
            level=0,
            title="Document Content",
            content=text,
            start_pos=0,
            end_pos=len(text),
            keywords=extract_keywords_simple(text)
        )]
    
    # Build sections from headers
    sections = []
    parent_stack = []  # Stack to track parent sections
    
    for i, (start_pos, header_end, title, level) in enumerate(unique_headers):
        # Find content for this section (from header end to next header start)
        if i < len(unique_headers) - 1:
            content_end = unique_headers[i + 1][0]
        else:
            content_end = len(text)
        
        content = text[header_end:content_end].strip()
        
        # Determine parent based on level
        parent_title = None
        while parent_stack and parent_stack[-1][0] >= level:
            parent_stack.pop()
        
        if parent_stack:
            parent_title = parent_stack[-1][1]
        
        section = DocumentSection(
            level=level,
            title=title,
            content=content,
            start_pos=start_pos,
            end_pos=content_end,
            parent_title=parent_title,
            keywords=extract_keywords_simple(content)
        )
        
        sections.append(section)
        parent_stack.append((level, title))
    
    return sections


def extract_keywords_simple(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords using simple frequency analysis (NO AI).
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    # Remove special characters and convert to lowercase
    words = re.findall(r'\b[a-zA-Zא-ת]{3,}\b', text.lower())
    
    # Common stop words (English and Hebrew)
    stop_words = {
        'the', 'is', 'at', 'which', 'on', 'and', 'or', 'but', 'in', 'with', 'to', 'for',
        'של', 'את', 'על', 'אל', 'זה', 'זו', 'היא', 'הוא', 'אני', 'אתה', 'הם', 'כל',
        'that', 'this', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does'
    }
    
    # Count word frequency
    word_freq = {}
    for word in words:
        if word not in stop_words and len(word) > 3:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_keywords]]


def create_section_summary(section: DocumentSection) -> str:
    """
    Create a brief summary of a section for quick scanning (NO AI).
    Just takes first few sentences.
    
    Args:
        section: DocumentSection to summarize
        
    Returns:
        Brief summary string
    """
    # Get first 2-3 sentences
    sentences = re.split(r'[.!?]\s+', section.content)
    summary_sentences = sentences[:3]
    summary = ' '.join(summary_sentences)
    
    # Limit to 300 chars
    if len(summary) > 300:
        summary = summary[:297] + '...'
    
    return summary


def get_section_hierarchy(sections: List[DocumentSection]) -> Dict:
    """
    Build a hierarchical representation of sections.
    
    Args:
        sections: List of DocumentSection objects
        
    Returns:
        Dictionary representing the hierarchy
    """
    hierarchy = {
        'title': 'Document Root',
        'level': 0,
        'children': []
    }
    
    stack = [hierarchy]
    
    for section in sections:
        section_node = {
            'title': section.title,
            'level': section.level,
            'keywords': section.keywords,
            'preview': section.content[:100] + '...' if len(section.content) > 100 else section.content,
            'children': []
        }
        
        # Find correct parent in stack
        while len(stack) > 1 and stack[-1]['level'] >= section.level:
            stack.pop()
        
        # Add to current parent
        stack[-1]['children'].append(section_node)
        
        # Push current section to stack
        stack.append(section_node)
    
    return hierarchy
