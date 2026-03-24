"""
Carnauba Viewer Parsers

Functions for extracting metadata from PDF, DXF, and IFC files.
"""
import io
import logging
import os
import tempfile
import zipfile
from typing import Any

import ezdxf
import ifcopenshell

from utils.temp_files import temp_file_handler

# Configure logging
logger = logging.getLogger(__name__)

# PDF reader with fallback
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    logger.warning("pypdf not installed. PDF metadata extraction will be limited.")
    PYPDF_AVAILABLE = False
    PdfReader = None  # type: ignore


def parse_pdf_metadata(file_buffer: io.BytesIO) -> dict[str, Any]:
    """
    Extract metadata from PDF file buffer.

    Args:
        file_buffer: BytesIO buffer containing the PDF file.

    Returns:
        dict: Metadata dictionary with type, pages, and info keys.
              Contains 'error' key if parsing fails.
    """
    if not PYPDF_AVAILABLE:
        return {"error": "pypdf not installed", "type": "PDF"}

    try:
        reader = PdfReader(file_buffer)
        num_pages = len(reader.pages)
        return {
            "type": "PDF",
            "pages": num_pages,
            "info": reader.metadata
        }
    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        return {"error": f"Failed to parse PDF: {str(e)}", "type": "PDF"}


def parse_dxf_metadata(file_buffer: io.BytesIO) -> dict[str, Any]:
    """
    Extract metadata from DXF file buffer.

    Args:
        file_buffer: BytesIO buffer containing the DXF file.

    Returns:
        dict: Metadata dictionary with type, version, layers_count, and layers.
              Contains 'error' key if parsing fails.
    """
    try:
        with temp_file_handler(file_buffer.getvalue(), ".dxf") as tmp_path:
            doc = ezdxf.readfile(tmp_path)
            layers = [layer.dxf.name for layer in doc.layers]

            return {
                "type": "DXF",
                "version": doc.dxfversion,
                "layers_count": len(layers),
                "layers": layers[:10]  # Show first 10
            }
    except Exception as e:
        logger.error(f"Failed to parse DXF: {e}")
        return {"error": f"Failed to parse DXF: {str(e)}", "type": "DXF"}


def parse_ifc_metadata(file_buffer: io.BytesIO) -> dict[str, Any]:
    """
    Extract metadata from IFC file buffer (supports .ifc and .ifczip).

    Args:
        file_buffer: BytesIO buffer containing the IFC or IFCZIP file.

    Returns:
        dict: Metadata dictionary with type, schema, project_name, and counts.
              Contains 'error' key if parsing fails.
    """
    try:
        tmp_path: str | None = None
        content: bytes

        # Check if it's a zip file
        file_buffer.seek(0)
        try:
            with zipfile.ZipFile(file_buffer) as zf:
                # Find first .ifc file in zip
                ifc_files = [f for f in zf.namelist() if f.lower().endswith('.ifc')]
                if not ifc_files:
                    return {"error": "No .ifc file found in zip archive", "type": "IFC"}
                content = zf.read(ifc_files[0])
        except zipfile.BadZipFile:
            # Not a zip, assume standard IFC
            file_buffer.seek(0)
            content = file_buffer.getvalue()

        with temp_file_handler(content, ".ifc") as tmp_path:
            ifc_file = ifcopenshell.open(tmp_path)

            # Extract metadata
            schema = ifc_file.schema
            walls = len(ifc_file.by_type("IfcWall"))
            windows = len(ifc_file.by_type("IfcWindow"))
            slabs = len(ifc_file.by_type("IfcSlab"))
            doors = len(ifc_file.by_type("IfcDoor"))

            project = ifc_file.by_type("IfcProject")
            project_name = project[0].Name if project else "Unknown"

            return {
                "type": "IFC",
                "schema": schema,
                "project_name": project_name,
                "counts": {
                    "Walls": walls,
                    "Windows": windows,
                    "Doors": doors,
                    "Slabs": slabs
                }
            }
    except Exception as e:
        logger.error(f"Failed to parse IFC: {e}")
        return {"error": f"Failed to parse IFC: {str(e)}", "type": "IFC"}
