"""
Carnauba Viewer Custom Exceptions

Custom exception classes for better error handling and debugging.
"""
from typing import Optional


class CarnaubaError(Exception):
    """Base exception for Carnauba Viewer."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class DXFParseError(CarnaubaError):
    """Error parsing DXF file."""
    pass


class DXFRenderError(CarnaubaError):
    """Error rendering DXF visualization."""
    pass


class IFCParseError(CarnaubaError):
    """Error parsing IFC file."""
    pass


class IFCRenderError(CarnaubaError):
    """Error rendering IFC geometry."""
    pass


class PDFParseError(CarnaubaError):
    """Error parsing PDF file."""
    pass


class PDFRenderError(CarnaubaError):
    """Error rendering PDF visualization."""
    pass


class UnsupportedFileTypeError(CarnaubaError):
    """Unsupported file type uploaded."""
    pass


class TempFileError(CarnaubaError):
    """Error managing temporary files."""
    pass
