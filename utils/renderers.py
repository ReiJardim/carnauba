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
    tmp_path = None
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(file_buffer.getvalue())
            tmp_path = tmp.name

        # Read using readfile which handles binary/encoding automatically
        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()

        # Matplotlib setup
        fig = plt.figure(facecolor='#0e1117') # Dark background
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        
        # Render
        ctx = RenderContext(doc)
        ctx.set_current_layout(msp)
        
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)
        
        st.pyplot(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erro ao renderizar DXF: {e}")
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

import zipfile
import multiprocessing
import plotly.graph_objects as go
import numpy as np
import ifcopenshell.geom
import pandas as pd

def render_ifc(file_buffer):
    """
    Render IFC file (Structure Tree & 3D Visualization). Supports .ifc and .ifczip.
    """
    try:
        tmp_path = None
        is_zip = False
        
        try:
             # Reset buffer position
             file_buffer.seek(0)
             with zipfile.ZipFile(file_buffer) as zf:
                is_zip = True
                ifc_files = [f for f in zf.namelist() if f.lower().endswith('.ifc')]
                if not ifc_files:
                    st.error("No .ifc file found inside the zip archive.")
                    return
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                    tmp.write(zf.read(ifc_files[0]))
                    tmp_path = tmp.name
        except zipfile.BadZipFile:
            pass

        if not is_zip:
            file_buffer.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                tmp.write(file_buffer.getvalue())
                tmp_path = tmp.name
        
        ifcopenshell_file = ifcopenshell.open(tmp_path)
        
        # Tabs for Tree View vs 3D View
        tab_3d, tab_data = st.tabs(["Visualização 3D", "Dados & Quantitativos"])
        
        # Elements to render (Expanded list for better coverage)
        target_types = [
            "IfcWall", "IfcSlab", "IfcWindow", "IfcDoor", "IfcColumn", "IfcBeam",
            "IfcRoof", "IfcStair", "IfcRailing", "IfcCurtainWall", "IfcRamp",
            "IfcMember", "IfcPlate", "IfcCovering", "IfcFurnishingElement",
            "IfcFlowTerminal", "IfcFlowSegment", "IfcBuildingElementProxy"
        ]

        with tab_3d:
            st.info("Renderizando geometria 3D... Isso pode levar alguns segundos dependendo da complexidade.")
            try:
                # Configuration for geometry extraction
                settings = ifcopenshell.geom.settings()
                settings.set(settings.USE_WORLD_COORDS, True)
                
                # Create a Plotly Figure
                fig = go.Figure()
                
                # Simple material colors
                colors = {
                    "IfcWall": "lightgrey",
                    "IfcSlab": "grey",
                    "IfcWindow": "lightblue",
                    "IfcDoor": "brown",
                    "IfcColumn": "darkgrey",
                    "IfcBeam": "orange",
                    "IfcRoof": "darkred",
                    "IfcStair": "lightbrown",
                    "IfcRailing": "gold",
                    "IfcCurtainWall": "aliceblue",
                    "IfcFurnishingElement": "purple",
                    "IfcFlowTerminal": "cyan",
                    "IfcFlowSegment": "blue",
                    "IfcCovering": "whitesmoke"
                }

                has_geometry = False
                
                # Iterate and process
                for ifc_type in target_types:
                    elements = ifcopenshell_file.by_type(ifc_type)
                    if not elements:
                        continue
                        
                    # Batch processing could be done here, but simple loop for now
                    for element in elements:
                        try:
                            if element.Representation: # Check if element has representation
                                shape = ifcopenshell.geom.create_shape(settings, element)
                                verts = shape.geometry.verts # Flat list x, y, z, ...
                                faces = shape.geometry.faces # Flat list i1, i2, i3, ...
                                
                                # Convert to numpy for easier handling
                                verts = np.array(verts).reshape((-1, 3))
                                faces = np.array(faces).reshape((-1, 3))
                                
                                x, y, z = verts.T
                                i, j, k = faces.T
                                
                                mesh = go.Mesh3d(
                                    x=x, y=y, z=z,
                                    i=i, j=j, k=k,
                                    color=colors.get(ifc_type, "white"),
                                    opacity=0.4 if ifc_type in ["IfcWindow", "IfcCurtainWall"] else 1.0,
                                    name=f"{ifc_type} - {element.GlobalId}",
                                    showscale=False,
                                    hoverinfo='text',
                                    text=f"{element.Name}<br>Type: {ifc_type}"
                                )
                                fig.add_trace(mesh)
                                has_geometry = True
                        except Exception as geom_err:
                            # Geometry creation might fail for specific elements
                            continue

                if has_geometry:
                    fig.update_layout(
                        scene=dict(
                            xaxis=dict(visible=False),
                            yaxis=dict(visible=False),
                            zaxis=dict(visible=False),
                            dragmode='orbit',
                            bgcolor='#0e1117'
                        ),
                        margin=dict(l=0, r=0, t=0, b=0),
                        height=600,
                        paper_bgcolor='#0e1117',
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Não foi possível extrair geometria 3D compativel deste arquivo.")

            except Exception as e:
                st.error(f"Erro ao processar geometria 3D: {str(e)}")


        with tab_data:
            st.subheader("📊 Quantitativos")
            
            # Calculate quantities
            quantities = []
            for ifc_type in target_types:
                elements = ifcopenshell_file.by_type(ifc_type)
                count = len(elements)
                if count > 0:
                    quantities.append({"Elemento": ifc_type, "Quantidade": count})
            
            if quantities:
                df = pd.DataFrame(quantities)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum elemento construtivo principal identificado na lista padrão.")

            st.divider()
            st.subheader("🏗️ Estrutura do Projeto")
            project = ifcopenshell_file.by_type("IfcProject")
            if project:
                st.markdown(f"**Projeto:** {project[0].Name}")
                
            sites = ifcopenshell_file.by_type("IfcSite")
            for site in sites:
                st.markdown(f"**- Site:** {site.Name}")
                buildings = ifcopenshell_file.by_type("IfcBuilding")
                for building in buildings:
                     st.markdown(f"**-- Edifício:** {building.Name}")
                     storeys = ifcopenshell_file.by_type("IfcBuildingStorey")
                     for storey in storeys:
                         st.markdown(f"**--- Pavimento:** {storey.Name}")
        
        os.unlink(tmp_path)
            
    except Exception as e:
        st.error(f"Erro ao ler arquivo IFC: {e}")
