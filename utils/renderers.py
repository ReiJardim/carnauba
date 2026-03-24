"""
Carnauba Viewer Renderers

Functions for rendering PDF, DXF, and IFC files using Streamlit and Plotly.
"""
import base64
import io
import logging
import os
import tempfile
import zipfile
from typing import Any

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
from utils.temp_files import temp_file_handler

# Configure logging
logger = logging.getLogger(__name__)


def render_pdf(file_buffer: io.BytesIO) -> None:
    """
    Render PDF file using iframe for native browser interaction (zoom, scroll).

    Args:
        file_buffer: BytesIO buffer containing the PDF file.
    """
    binary_data = file_buffer.getvalue()
    base64_pdf = base64.b64encode(binary_data).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{PDF_VIEWER_HEIGHT}px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


def render_dxf(file_buffer: io.BytesIO) -> None:
    """
    Render DXF file using ezdxf and Plotly for interactive visualization (Zoom/Pan).

    Args:
        file_buffer: BytesIO buffer containing the DXF file.
    """
    try:
        with temp_file_handler(file_buffer.getvalue(), ".dxf") as tmp_path:
            # Read using readfile which handles binary/encoding automatically
            doc = ezdxf.readfile(tmp_path)
            msp = doc.modelspace()

            # Plotly Figure
            fig = go.Figure()

            entity_count = 0

            # Group coordinates by layer to reduce number of traces (Performance optimization)
            layer_coords: dict[str, dict[str, list[float | None]]] = {}

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
                    xs: list[float | None] = [v.x for v in vertices] + [None]
                    ys: list[float | None] = [v.y for v in vertices] + [None]

                    layer_coords[layer_name]['x'].extend(xs)
                    layer_coords[layer_name]['y'].extend(ys)

                    entity_count += 1
                except Exception as e:
                    logger.debug(f"Failed to process DXF entity: {e}")
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
                    connectgaps=False  # Important for NaN usage
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
        logger.error(f"Failed to render DXF: {e}")
        st.error(f"Erro ao renderizar DXF: {e}")


def render_ifc(file_buffer: io.BytesIO) -> None:
    """
    Render IFC file (Structure Tree & 3D Visualization). Supports .ifc and .ifczip.

    Args:
        file_buffer: BytesIO buffer containing the IFC or IFCZIP file.
    """
    try:
        content: bytes

        # Check if it's a zip file
        file_buffer.seek(0)
        try:
            with zipfile.ZipFile(file_buffer) as zf:
                ifc_files = [f for f in zf.namelist() if f.lower().endswith('.ifc')]
                if not ifc_files:
                    st.error("No .ifc file found inside the zip archive.")
                    return
                content = zf.read(ifc_files[0])
        except zipfile.BadZipFile:
            # Not a zip, assume standard IFC
            file_buffer.seek(0)
            content = file_buffer.getvalue()

        with temp_file_handler(content, ".ifc") as tmp_path:
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

                        for element in elements:
                            try:
                                if element.Representation:
                                    shape = ifcopenshell.geom.create_shape(settings, element)
                                    verts = shape.geometry.verts
                                    faces = shape.geometry.faces

                                    # Convert to numpy for easier handling
                                    verts_arr = np.array(verts).reshape((-1, 3))
                                    faces_arr = np.array(faces).reshape((-1, 3))

                                    x, y, z = verts_arr.T
                                    i, j, k = faces_arr.T

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
                                logger.debug(f"Failed to create geometry for {ifc_type}: {geom_err}")
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
                    logger.error(f"Failed to process IFC 3D geometry: {e}")
                    st.error(f"Erro ao processar geometria 3D: {str(e)}")

            with tab_data:
                st.subheader("📊 Quantitativos")

                # Calculate quantities
                quantities: list[dict[str, Any]] = []
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

    except Exception as e:
        logger.error(f"Failed to render IFC: {e}")
        st.error(f"Erro ao ler arquivo IFC: {e}")
