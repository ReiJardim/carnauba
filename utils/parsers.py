import io
import tempfile
import os
import zipfile
import logging

import ezdxf
import ifcopenshell

# Configure logging
logger = logging.getLogger(__name__)

# PDF reader with fallback
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    logger.warning("pypdf not installed. PDF metadata extraction will be limited.")
    PYPDF_AVAILABLE = False
    PdfReader = None


def parse_pdf_metadata(file_buffer):
    """
    Extract metadata from PDF file buffer.
    
    Args:
        file_buffer: BytesIO buffer containing the PDF file.
        
    Returns:
        dict: Metadata dictionary with type, pages, and info keys.
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

def parse_dxf_metadata(file_buffer):
    """
    Extract metadata from DXF file buffer.
    """
    tmp_path = None
    try:
        # Save to temp file to let ezdxf handle encoding/binary detection
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(file_buffer.getvalue())
            tmp_path = tmp.name

        doc = ezdxf.readfile(tmp_path)
        
        layers = [layer.dxf.name for layer in doc.layers]
        
        metadata = {
            "type": "DXF",
            "version": doc.dxfversion,
            "layers_count": len(layers),
            "layers": layers[:10]  # Show first 10
        }
        
    except Exception as e:
        logger.error(f"Failed to parse DXF: {e}")
        metadata = {"error": f"Failed to parse DXF: {str(e)}", "type": "DXF"}
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError as cleanup_err:
                logger.warning(f"Failed to cleanup temp file {tmp_path}: {cleanup_err}")
                
    return metadata



def parse_ifc_metadata(file_buffer):
    """
    Extract metadata from IFC file buffer (supports .ifc and .ifczip).
    """
    try:
        tmp_path = None
        
        # Determine if it's a zip file or check extension from buffer manually if needed.
        # Here we trust the caller usually, but let's be robust.
        is_zip = False
        try:
           with zipfile.ZipFile(file_buffer) as zf:
               is_zip = True
               # Find first .ifc file in zip
               ifc_files = [f for f in zf.namelist() if f.lower().endswith('.ifc')]
               if not ifc_files:
                   return {"error": "No .ifc file found in zip archive", "type": "IFC"}
               
               with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                   tmp.write(zf.read(ifc_files[0]))
                   tmp_path = tmp.name
        except zipfile.BadZipFile:
            # Not a zip, assume standard IFC
            pass
            
        if not is_zip:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                tmp.write(file_buffer.getvalue())
                tmp_path = tmp.name
        
        f = ifcopenshell.open(tmp_path)
        
        # Schema
        schema = f.schema
        
        # Counts
        walls = len(f.by_type("IfcWall"))
        windows = len(f.by_type("IfcWindow"))
        slabs = len(f.by_type("IfcSlab"))
        doors = len(f.by_type("IfcDoor"))
        
        project = f.by_type("IfcProject")
        project_name = project[0].Name if project else "Unknown"

        os.unlink(tmp_path)
        
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
