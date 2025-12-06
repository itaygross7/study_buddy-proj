"""
Input Handler - Flexible Multi-Format Input Processing

PURPOSE: Make the app accept ALL different types of user input
- Text (plain, formatted, Hebrew, English, mixed)
- Files (PDF, DOCX, TXT, images with OCR, audio, video)
- Various encodings and formats
- Malformed or partial input

PRINCIPLE: Be flexible, graceful, and user-friendly
"""

from typing import Dict, Any, Optional, Union, List
import mimetypes
import os
from dataclasses import dataclass

from sb_utils.logger_utils import logger


@dataclass
class ProcessedInput:
    """
    Standardized input structure after processing.
    All inputs are converted to this format.
    """
    content: str  # Main content (text extracted from any source)
    content_type: str  # Type: 'text', 'document', 'audio', 'video', 'image', 'mixed'
    original_format: str  # Original format: 'txt', 'pdf', 'docx', etc.
    metadata: Dict[str, Any]  # Additional metadata
    user_id: str  # User who submitted
    language: str  # Detected or specified language
    encoding: str  # Character encoding used
    success: bool  # Whether processing succeeded
    warnings: List[str]  # Any warnings during processing
    
    def is_valid(self) -> bool:
        """Check if input is valid for AI processing."""
        return self.success and bool(self.content.strip())
    
    def get_display_info(self) -> str:
        """Get user-friendly description of input."""
        if self.content_type == 'text':
            return f"טקסט ({len(self.content)} תווים)"
        elif self.content_type == 'document':
            return f"מסמך {self.original_format.upper()} ({len(self.content)} תווים)"
        else:
            return f"{self.content_type} - {self.original_format}"


class InputNormalizer:
    """
    Microservice: Input Normalization
    Accepts ANY input format and normalizes it
    """
    
    @staticmethod
    def normalize_text(
        text: str, 
        user_id: str,
        language: str = "auto",
        metadata: Dict[str, Any] = None
    ) -> ProcessedInput:
        """
        Normalize plain text input.
        Handles various encodings, formats, and edge cases.
        
        Args:
            text: Input text (any encoding, any format)
            user_id: User ID
            language: Language ('auto' for detection, 'he', 'en', etc.)
            metadata: Additional metadata
            
        Returns:
            ProcessedInput object
        """
        warnings = []
        
        # Handle None or empty
        if text is None:
            text = ""
            warnings.append("Empty input received")
        
        # Ensure string
        if not isinstance(text, str):
            text = str(text)
            warnings.append(f"Converted {type(text).__name__} to string")
        
        # Normalize whitespace
        original_length = len(text)
        text = text.strip()
        
        if len(text) == 0:
            warnings.append("Input contains only whitespace")
        elif len(text) < original_length * 0.5:
            warnings.append("Removed significant whitespace")
        
        # Detect encoding issues
        try:
            # Try to encode/decode to catch issues
            text.encode('utf-8').decode('utf-8')
        except UnicodeError as e:
            warnings.append(f"Encoding issue detected: {e}")
            # Try to fix common issues
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        # Auto-detect language if needed
        if language == "auto":
            language = InputNormalizer._detect_language(text)
        
        # Build metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'original_length': original_length,
            'processed_length': len(text),
            'whitespace_normalized': original_length != len(text)
        })
        
        return ProcessedInput(
            content=text,
            content_type='text',
            original_format='text',
            metadata=metadata,
            user_id=user_id,
            language=language,
            encoding='utf-8',
            success=bool(text.strip()),
            warnings=warnings
        )
    
    @staticmethod
    def normalize_document(
        file_path: str,
        filename: str,
        user_id: str,
        extracted_text: str = None,
        language: str = "auto"
    ) -> ProcessedInput:
        """
        Normalize document input (PDF, DOCX, etc.).
        
        Args:
            file_path: Path to file
            filename: Original filename
            user_id: User ID
            extracted_text: Pre-extracted text (if available)
            language: Language
            
        Returns:
            ProcessedInput object
        """
        warnings = []
        
        # Detect file type
        mime_type, _ = mimetypes.guess_type(filename)
        file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
        
        # Use pre-extracted text if available
        if extracted_text:
            content = extracted_text
            warnings.append("Using pre-extracted text")
        else:
            content = ""
            warnings.append("No extracted text provided")
        
        # Auto-detect language
        if language == "auto" and content:
            language = InputNormalizer._detect_language(content)
        elif not content:
            language = "he"  # Default
        
        # Determine content type
        content_type_map = {
            'pdf': 'document',
            'doc': 'document',
            'docx': 'document',
            'txt': 'document',
            'md': 'document',
            'rtf': 'document',
            'odt': 'document',
            'jpg': 'image',
            'jpeg': 'image',
            'png': 'image',
            'gif': 'image',
            'mp3': 'audio',
            'wav': 'audio',
            'mp4': 'video',
            'avi': 'video'
        }
        
        content_type = content_type_map.get(file_ext, 'document')
        
        metadata = {
            'filename': filename,
            'mime_type': mime_type,
            'file_extension': file_ext,
            'file_path': file_path,
            'content_length': len(content) if content else 0
        }
        
        return ProcessedInput(
            content=content,
            content_type=content_type,
            original_format=file_ext,
            metadata=metadata,
            user_id=user_id,
            language=language,
            encoding='utf-8',
            success=bool(content),
            warnings=warnings
        )
    
    @staticmethod
    def normalize_mixed(
        inputs: List[Union[str, Dict[str, Any]]],
        user_id: str,
        language: str = "auto"
    ) -> ProcessedInput:
        """
        Normalize mixed input (text + files).
        
        Args:
            inputs: List of text strings or file dicts
            user_id: User ID
            language: Language
            
        Returns:
            ProcessedInput combining all inputs
        """
        warnings = []
        content_parts = []
        formats = []
        
        for idx, item in enumerate(inputs):
            if isinstance(item, str):
                # Text input
                processed = InputNormalizer.normalize_text(item, user_id, language)
                content_parts.append(processed.content)
                formats.append('text')
                warnings.extend(processed.warnings)
            elif isinstance(item, dict):
                # Document input
                file_path = item.get('file_path', '')
                filename = item.get('filename', f'file_{idx}')
                extracted_text = item.get('extracted_text', '')
                
                processed = InputNormalizer.normalize_document(
                    file_path, filename, user_id, extracted_text, language
                )
                content_parts.append(f"\n=== {filename} ===\n{processed.content}")
                formats.append(processed.original_format)
                warnings.extend(processed.warnings)
        
        # Combine all content
        combined_content = "\n\n".join(filter(None, content_parts))
        
        # Auto-detect language from combined content
        if language == "auto":
            language = InputNormalizer._detect_language(combined_content)
        
        metadata = {
            'num_inputs': len(inputs),
            'formats': formats,
            'combined_length': len(combined_content)
        }
        
        return ProcessedInput(
            content=combined_content,
            content_type='mixed',
            original_format='mixed',
            metadata=metadata,
            user_id=user_id,
            language=language,
            encoding='utf-8',
            success=bool(combined_content.strip()),
            warnings=warnings
        )
    
    @staticmethod
    def _detect_language(text: str) -> str:
        """
        Simple language detection (Hebrew vs English vs Mixed).
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code: 'he', 'en', or 'mixed'
        """
        if not text:
            return "he"  # Default
        
        # Count Hebrew and English characters
        hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
        english_chars = sum(1 for c in text if c.isalpha() and c.isascii())
        
        total_alpha = hebrew_chars + english_chars
        if total_alpha == 0:
            return "he"  # Default
        
        hebrew_ratio = hebrew_chars / total_alpha
        
        if hebrew_ratio > 0.7:
            return "he"
        elif hebrew_ratio < 0.3:
            return "en"
        else:
            return "mixed"


class InputValidator:
    """
    Microservice: Input Validation
    Validates and provides feedback on input quality
    """
    
    @staticmethod
    def validate(processed_input: ProcessedInput) -> Dict[str, Any]:
        """
        Validate processed input and provide user feedback.
        
        Args:
            processed_input: ProcessedInput object
            
        Returns:
            Validation result with user-friendly messages
        """
        validation = {
            'is_valid': processed_input.is_valid(),
            'quality': 'good',
            'messages': [],
            'suggestions': []
        }
        
        # Check if empty
        if not processed_input.content.strip():
            validation['is_valid'] = False
            validation['quality'] = 'invalid'
            validation['messages'].append("⚠️ הקלט ריק - אנא הוסף תוכן")
            validation['suggestions'].append("העלה מסמך או הקלד טקסט")
            return validation
        
        # Check if too short
        content_length = len(processed_input.content)
        if content_length < 50:
            validation['quality'] = 'low'
            validation['messages'].append("⚠️ הקלט קצר מאוד")
            validation['suggestions'].append("הוסף עוד תוכן לתשובות טובות יותר")
        
        # Check if too long
        elif content_length > 100000:  # 100K chars
            validation['quality'] = 'acceptable'
            validation['messages'].append("ℹ️ המסמך ארוך מאוד - העיבוד יקח זמן")
            validation['suggestions'].append("שקול לחלק למסמכים קטנים יותר")
        
        # Check for encoding issues
        if any('encoding' in w.lower() for w in processed_input.warnings):
            validation['quality'] = 'acceptable'
            validation['messages'].append("⚠️ זוהו בעיות קידוד - התוכן נוקה")
        
        # Check for warnings
        if processed_input.warnings:
            validation['messages'].append(f"ℹ️ {len(processed_input.warnings)} אזהרות")
        
        # Positive feedback for good input
        if validation['quality'] == 'good':
            validation['messages'].append("✓ הקלט תקין ומוכן לעיבוד")
        
        return validation


def process_user_input(
    input_data: Union[str, Dict[str, Any], List],
    user_id: str,
    language: str = "auto"
) -> ProcessedInput:
    """
    Main entry point: Process ANY user input.
    
    This function accepts all different types of input and normalizes them.
    
    Args:
        input_data: Can be:
            - str: Plain text
            - dict: Single file {'file_path': ..., 'filename': ..., 'extracted_text': ...}
            - list: Mixed inputs (text + files)
        user_id: User ID
        language: Language
        
    Returns:
        ProcessedInput object
    """
    try:
        if isinstance(input_data, str):
            # Plain text
            return InputNormalizer.normalize_text(input_data, user_id, language)
        
        elif isinstance(input_data, dict):
            # Single document
            file_path = input_data.get('file_path', '')
            filename = input_data.get('filename', 'document')
            extracted_text = input_data.get('extracted_text', input_data.get('content', ''))
            
            return InputNormalizer.normalize_document(
                file_path, filename, user_id, extracted_text, language
            )
        
        elif isinstance(input_data, list):
            # Mixed inputs
            return InputNormalizer.normalize_mixed(input_data, user_id, language)
        
        else:
            # Unknown type - try to convert to string
            logger.warning(f"Unknown input type: {type(input_data)}, converting to string")
            return InputNormalizer.normalize_text(str(input_data), user_id, language)
    
    except Exception as e:
        logger.error(f"Input processing failed: {e}", exc_info=True)
        # Return failed input with error
        return ProcessedInput(
            content="",
            content_type='error',
            original_format='unknown',
            metadata={'error': str(e)},
            user_id=user_id,
            language=language or "he",
            encoding='utf-8',
            success=False,
            warnings=[f"Processing error: {str(e)}"]
        )


def get_user_feedback(processed_input: ProcessedInput) -> str:
    """
    Generate user-friendly feedback message about their input.
    
    Args:
        processed_input: ProcessedInput object
        
    Returns:
        Hebrew feedback message for user
    """
    validation = InputValidator.validate(processed_input)
    
    if not validation['is_valid']:
        return " | ".join(validation['messages'] + validation['suggestions'])
    
    # Build positive feedback
    feedback_parts = []
    
    # Input type
    feedback_parts.append(f"📄 {processed_input.get_display_info()}")
    
    # Quality indicator
    quality_emoji = {
        'good': '✓',
        'acceptable': 'ℹ️',
        'low': '⚠️',
        'invalid': '❌'
    }
    emoji = quality_emoji.get(validation['quality'], 'ℹ️')
    feedback_parts.append(f"{emoji} איכות: {validation['quality']}")
    
    # Messages
    if validation['messages']:
        feedback_parts.extend(validation['messages'])
    
    return " | ".join(feedback_parts)
