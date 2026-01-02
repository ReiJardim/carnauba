import io
import tempfile
import os
import ezdxf
import ifcopenshell
from pypdf import PdfReader # streamlit-pdf-viewer uses pypdf internally often, but let's standardise if possible or just use what works.
# Actually I'll use standard pypdf if available or just simple logic.
# Wait, pypdf is not in requirements explicitly but streamlit-pdf-viewer likely depends on it or similar?
# Let's check requirements.txt again. I only put `streamlit-pdf-viewer`.
# I should probably add `pypdf` to requirements.txt to be safe for metadata extraction.
# OR I can just use `streamlit-pdf-viewer`'s rendering, but for metadata (page count), pypdf is good.
# I'll rely on pypdf being there or add it. Let's add it to imports and requirements if I fail.
# Actually, let's just use `pypdf` for page count.

try:
    from pypdf import PdfReader
except ImportError:
    # Fallback or error if not installed.
    # I will assume I need to install it.
    pass

def parse_pdf_metadata(file_buffer):
    """
    Extract metadata from PDF file buffer.
    """
    try:
        reader = PdfReader(file_buffer)
        num_pages = len(reader.pages)
        return {
            "type": "PDF",
            "pages": num_pages,
            "info": reader.metadata
        }
    except Exception as e:
        return {"error": f"Failed to parse PDF: {str(e)}", "type": "PDF"}

def parse_dxf_metadata(file_buffer):
    """
    Extract metadata from DXF file buffer.
    """
    try:
        # ezdxf reads from stream (text mode usually tailored for files, but let's try reading bytes)
        # ezdxf.read() expects a filename or a stream.
        # file_buffer is bytes. ezdxf expects text stream usually for DXF.
        # let's decode to string.
        content = file_buffer.getvalue().decode('utf-8', errors='ignore')
        doc = ezdxf.read(io.StringIO(content))
        
        layers = [layer.dxf.name for layer in doc.layers]
        return {
            "type": "DXF",
            "version": doc.dxfversion,
            "layers_count": len(layers),
            "layers": layers[:10]  # Show first 10
        }
    except Exception as e:
        return {"error": f"Failed to parse DXF: {str(e)}", "type": "DXF"}

def parse_ifc_metadata(file_buffer):
    """
    Extract metadata from IFC file buffer.
    """
    # ifcopenshell needs a file path usually.
    try:
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
        return {"error": f"Failed to parse IFC: {str(e)}", "type": "IFC"}
