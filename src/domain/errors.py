"""
Custom application-specific exceptions.
"""

class BaseAppException(Exception):
    """Base exception for the application."""
    pass

class DocumentNotFoundError(BaseAppException):
    """Raised when a document is not found in the database."""
    pass

class AIClientError(BaseAppException):
    """Raised for errors related to the AI client."""
    pass

class InvalidFileTypeError(BaseAppException):
    """Raised for unsupported file types."""
    pass

class ParsingError(BaseAppException):
    """Raised when parsing AI output fails."""
    pass
