import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io
import tempfile
import ifcopenshell
import os

def render_pdf(file_buffer):
    """
    Render PDF file using iframe for native browser interaction (zoom, scroll).
    """
    import base64
    
    binary_data = file_buffer.getvalue()
    base64_pdf = base64.b64encode(binary_data).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def render_dxf(file_buffer):
    """
    Render DXF file using ezdxf and matplotlib.
    """
    try:
        # Decode and read DXF
        content = file_buffer.getvalue().decode('utf-8', errors='ignore')
        doc = ezdxf.read(io.StringIO(content))
        msp = doc.modelspace()

        # Matplotlib setup
        fig = plt.figure(facecolor='#0e1117') # Dark background
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        
        # Render
        ctx = RenderContext(doc)
        # Use dark theme logic for colors if needed, but for now simple swap
        ctx.set_current_layout(msp)
        
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)
        
        # Style tweaks
        # Make lines visible on dark background? default ezdxf colors might be black on white logic.
        # We might need to override. 
        # For this MVP, let's keep it simple. If it's black on black, we might not see it.
        # Generally CAD drawings use colors that are visible on dark.
        
        st.pyplot(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erro ao renderizar DXF: {e}")

def render_ifc(file_buffer):
    """
    Render IFC file (Structure Tree & Placeholder 3D).
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            tmp.write(file_buffer.getvalue())
            tmp_path = tmp.name
            
        f = ifcopenshell.open(tmp_path)
        
        st.subheader("Estrutura do Projeto")
        
        project = f.by_type("IfcProject")
        if project:
            st.markdown(f"**Projeto:** {project[0].Name}")
            
        sites = f.by_type("IfcSite")
        for site in sites:
            st.markdown(f"**- Site:** {site.Name}")
            buildings = f.by_type("IfcBuilding") # Simplify logic: getting all buildings, not just walking tree correctly for MVP speed
            for building in buildings:
                 st.markdown(f"**-- Edifício:** {building.Name}")
                 storeys = f.by_type("IfcBuildingStorey")
                 for storey in storeys:
                     st.markdown(f"**--- Pavimento:** {storey.Name}")

        st.info("Visualização 3D interativa em desenvolvimento.")
        
        os.unlink(tmp_path)
        
    except Exception as e:
        st.error(f"Erro ao renderizar IFC: {e}")
