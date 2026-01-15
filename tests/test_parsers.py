"""
Carnauba Viewer Parser Tests

Unit tests for the metadata parsing functions.
"""
import io
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest


class TestParseDXFMetadata:
    """Tests for parse_dxf_metadata function."""

    def test_parse_dxf_returns_dict(self, sample_dxf_buffer):
        """Test that parse_dxf_metadata returns a dictionary."""
        from utils.parsers import parse_dxf_metadata
        
        result = parse_dxf_metadata(sample_dxf_buffer)
        
        assert isinstance(result, dict)
        assert "type" in result
        assert result["type"] == "DXF"

    def test_parse_dxf_extracts_version(self, sample_dxf_buffer):
        """Test that DXF version is extracted."""
        from utils.parsers import parse_dxf_metadata
        
        result = parse_dxf_metadata(sample_dxf_buffer)
        
        assert "version" in result
        assert result["version"] is not None

    def test_parse_dxf_extracts_layers(self, sample_dxf_buffer):
        """Test that layers are extracted."""
        from utils.parsers import parse_dxf_metadata
        
        result = parse_dxf_metadata(sample_dxf_buffer)
        
        assert "layers_count" in result
        assert "layers" in result
        assert isinstance(result["layers"], list)

    def test_parse_dxf_handles_invalid_file(self, invalid_dxf_buffer):
        """Test that invalid DXF files are handled gracefully."""
        from utils.parsers import parse_dxf_metadata
        
        result = parse_dxf_metadata(invalid_dxf_buffer)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert result["type"] == "DXF"


class TestParsePDFMetadata:
    """Tests for parse_pdf_metadata function."""

    def test_parse_pdf_returns_dict(self):
        """Test that parse_pdf_metadata returns a dictionary."""
        from utils.parsers import parse_pdf_metadata
        
        # Empty buffer will fail but should return error dict
        result = parse_pdf_metadata(io.BytesIO(b""))
        
        assert isinstance(result, dict)
        assert "type" in result
        assert result["type"] == "PDF"

    def test_parse_pdf_handles_invalid_file(self, invalid_dxf_buffer):
        """Test that invalid PDF files are handled gracefully."""
        from utils.parsers import parse_pdf_metadata
        
        result = parse_pdf_metadata(invalid_dxf_buffer)
        
        assert isinstance(result, dict)
        # Should have either error or valid data
        assert "type" in result


class TestParseIFCMetadata:
    """Tests for parse_ifc_metadata function."""

    def test_parse_ifc_returns_dict(self):
        """Test that parse_ifc_metadata returns a dictionary."""
        from utils.parsers import parse_ifc_metadata
        
        # Empty buffer will fail but should return error dict
        result = parse_ifc_metadata(io.BytesIO(b""))
        
        assert isinstance(result, dict)
        assert "type" in result
        assert result["type"] == "IFC"

    def test_parse_ifc_handles_invalid_file(self, invalid_dxf_buffer):
        """Test that invalid IFC files are handled gracefully."""
        from utils.parsers import parse_ifc_metadata
        
        result = parse_ifc_metadata(invalid_dxf_buffer)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert result["type"] == "IFC"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
