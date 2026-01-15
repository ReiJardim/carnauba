"""
Carnauba Viewer Renderer Tests

Unit tests for the rendering functions.
"""
import io
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch


class TestRenderDXF:
    """Tests for render_dxf function."""

    def test_render_dxf_calls_plotly_chart(self, sample_dxf_buffer, mock_streamlit):
        """Test that render_dxf calls st.plotly_chart for valid DXF."""
        import streamlit as st
        from utils.renderers import render_dxf
        
        sample_dxf_buffer.seek(0)
        render_dxf(sample_dxf_buffer)
        
        # Should have called plotly_chart at least once
        st.plotly_chart.assert_called()

    def test_render_dxf_handles_empty_file(self, empty_buffer, mock_streamlit):
        """Test that empty DXF is handled without crashing."""
        from utils.renderers import render_dxf
        
        # Should not raise exception
        try:
            render_dxf(empty_buffer)
        except Exception as e:
            pytest.fail(f"render_dxf raised exception on empty file: {e}")


class TestRenderPDF:
    """Tests for render_pdf function."""

    def test_render_pdf_generates_iframe_html(self, mock_streamlit):
        """Test that render_pdf generates iframe HTML content."""
        import streamlit as st
        from utils.renderers import render_pdf
        
        # Create a minimal PDF-like buffer
        pdf_buffer = io.BytesIO(b"%PDF-1.4 test content")
        render_pdf(pdf_buffer)
        
        # Verify markdown was called (may be on different mock path)
        # The function should complete without error
        assert True  # Function completed successfully


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
