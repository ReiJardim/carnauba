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
        metadata = {"error": f"Failed to parse DXF: {str(e)}", "type": "DXF"}
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass
                
    return metadata

import zipfile

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
        return {"error": f"Failed to parse IFC: {str(e)}", "type": "IFC"}
