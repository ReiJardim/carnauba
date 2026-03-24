"""
Carnauba Viewer Test Configuration

Shared fixtures and configuration for pytest.
"""
import io
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    """Mock Streamlit module for all tests."""
    mock = MagicMock()
    monkeypatch.setitem(sys.modules, 'streamlit', mock)
    monkeypatch.setitem(sys.modules, 'streamlit.components', MagicMock())
    monkeypatch.setitem(sys.modules, 'streamlit.components.v1', MagicMock())
    monkeypatch.setitem(sys.modules, 'streamlit_pdf_viewer', MagicMock())
    return mock


@pytest.fixture
def sample_dxf_content() -> bytes:
    """Simple valid DXF content for testing."""
    return b"""  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1009
  0
ENDSEC
  0
SECTION
  2
ENTITIES
  0
LINE
  8
0
 10
0.0
 20
0.0
 30
0.0
 11
1.0
 21
1.0
 31
0.0
  0
ENDSEC
  0
EOF
"""


@pytest.fixture
def sample_dxf_buffer(sample_dxf_content) -> io.BytesIO:
    """BytesIO buffer with sample DXF content."""
    return io.BytesIO(sample_dxf_content)


@pytest.fixture
def empty_buffer() -> io.BytesIO:
    """Empty BytesIO buffer for error testing."""
    return io.BytesIO(b"")


@pytest.fixture
def invalid_dxf_buffer() -> io.BytesIO:
    """Invalid DXF content for error testing."""
    return io.BytesIO(b"This is not a valid DXF file content")
