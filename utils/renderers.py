import base64
import io
import logging
import os
import tempfile
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

import ezdxf
from ezdxf import path as ezdxf_path
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

import ifcopenshell
import ifcopenshell.geom

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

from utils.config import (
    DXF_SUPPORTED_ENTITIES,
    DXF_FLATTENING_DISTANCE,
    IFC_TARGET_TYPES,
    IFC_ELEMENT_COLORS,
    IFC_TRANSPARENT_TYPES,
    IFC_TRANSPARENT_OPACITY,
    IFC_SOLID_OPACITY,
    UI_BACKGROUND_COLOR,
    UI_PAPER_COLOR,
    UI_FONT_COLOR,
    VIEWER_HEIGHT_2D,
    VIEWER_HEIGHT_3D,
    PDF_VIEWER_HEIGHT,
)

# Configure logging
logger = logging.getLogger(__name__)

def render_pdf(file_buffer):
    """
    Render PDF file using iframe for native browser interaction (zoom, scroll).
    
    Args:
        file_buffer: BytesIO buffer containing the PDF file.
    """
    binary_data = file_buffer.getvalue()
    base64_pdf = base64.b64encode(binary_data).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{PDF_VIEWER_HEIGHT}px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def render_dxf(file_buffer):
    """
    Render DXF file using ezdxf and Plotly for interactive visualization (Zoom/Pan).
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
        
        # Plotly Figure
        fig = go.Figure()
        
        entity_count = 0
        
        # Optimize: Collect all lines to plot in fewer traces if possible, 
        # but for individual entity interactivity (hover), separate traces are better.
        # For performance with large DXFs, we might need to bundle. 
        # For now, let's try a balanced approach: One trace per layer or similar?
        # Let's keep it simple: Iterate entities and plot. 
        # To avoid blowing up browser with thousands of traces, we can group by layer or color.
        
        # Group coordinates by layer to reduce number of traces (Performance optimization)
        layer_coords = {}
        
        for entity in msp:
            try:
        # Filter useful entities
                if entity.dxftype() not in DXF_SUPPORTED_ENTITIES:
                    continue
                
                p = ezdxf_path.make_path(entity)
                # Flatten curves to line segments
                vertices = list(p.flattening(distance=DXF_FLATTENING_DISTANCE))
                
                if len(vertices) < 2:
                    continue
                    
                layer_name = entity.dxf.layer
                if layer_name not in layer_coords:
                    layer_coords[layer_name] = {'x': [], 'y': []}
                
                # Add NaN to separate disconnected lines in a single Scatter trace
                xs = [v.x for v in vertices] + [None]
                ys = [v.y for v in vertices] + [None]
                
                layer_coords[layer_name]['x'].extend(xs)
                layer_coords[layer_name]['y'].extend(ys)
                
                entity_count += 1
            except Exception:
                continue

        if entity_count == 0:
            st.warning("Nenhuma geometria suportada encontrada neste DXF.")
            return

        # Create traces per layer
        for layer_name, coords in layer_coords.items():
            fig.add_trace(go.Scatter(
                x=coords['x'], 
                y=coords['y'],
                mode='lines',
                name=layer_name,
                line=dict(width=1), 
                connectgaps=False # Important for NaN usage
            ))

        # Layout settings for CAD-like feel
        fig.update_layout(
            plot_bgcolor=UI_BACKGROUND_COLOR,
            paper_bgcolor=UI_PAPER_COLOR,
            font=dict(color=UI_FONT_COLOR),
            showlegend=True,
            dragmode='pan',  # Default to pan for CAD
            height=VIEWER_HEIGHT_2D,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        # Ensure aspect ratio is 1:1 (crucial for CAD)
        fig.update_yaxes(
            scaleanchor="x", 
            scaleratio=1, 
            visible=False, 
            showgrid=False
        )
        fig.update_xaxes(
            visible=False, 
            showgrid=False
        )

        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erro ao renderizar DXF: {e}")
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass



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

        with tab_3d:
            st.info("Renderizando geometria 3D... Isso pode levar alguns segundos dependendo da complexidade.")
            try:
                # Configuration for geometry extraction
                settings = ifcopenshell.geom.settings()
                settings.set(settings.USE_WORLD_COORDS, True)
                
                # Create a Plotly Figure
                fig = go.Figure()

                has_geometry = False
                
                # Iterate and process
                for ifc_type in IFC_TARGET_TYPES:
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
                                    color=IFC_ELEMENT_COLORS.get(ifc_type, "white"),
                                    opacity=IFC_TRANSPARENT_OPACITY if ifc_type in IFC_TRANSPARENT_TYPES else IFC_SOLID_OPACITY,
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
                            bgcolor=UI_BACKGROUND_COLOR
                        ),
                        margin=dict(l=0, r=0, t=0, b=0),
                        height=VIEWER_HEIGHT_3D,
                        paper_bgcolor=UI_PAPER_COLOR,
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
            for ifc_type in IFC_TARGET_TYPES:
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
