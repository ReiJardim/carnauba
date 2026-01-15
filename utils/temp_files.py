"""
Carnauba Viewer Temporary File Management

Context manager for automatic cleanup of temporary files.
"""
import logging
import os
import tempfile
from contextlib import contextmanager
from typing import Generator

from utils.exceptions import TempFileError

logger = logging.getLogger(__name__)


@contextmanager
def temp_file_handler(content: bytes, suffix: str) -> Generator[str, None, None]:
    """
    Context manager for temporary files with automatic cleanup.

    Creates a temporary file with the given content and suffix,
    yields the file path, and ensures cleanup on exit.

    Args:
        content: Binary content to write to the temporary file.
        suffix: File extension including the dot (e.g., ".dxf", ".ifc").

    Yields:
        str: Absolute path to the temporary file.

    Raises:
        TempFileError: If file creation or cleanup fails.

    Example:
        >>> with temp_file_handler(file_buffer.getvalue(), ".dxf") as tmp_path:
        ...     doc = ezdxf.readfile(tmp_path)
        ...     # Process document
        ... # File is automatically cleaned up
    """
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        logger.debug(f"Created temporary file: {tmp_path}")
        yield tmp_path
    except IOError as e:
        logger.error(f"Failed to create temporary file: {e}")
        raise TempFileError(f"Failed to create temporary file", original_error=e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.debug(f"Cleaned up temporary file: {tmp_path}")
            except OSError as cleanup_err:
                logger.warning(f"Failed to cleanup temp file {tmp_path}: {cleanup_err}")
