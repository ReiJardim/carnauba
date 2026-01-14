"""
Carnauba Viewer Configuration Module

Centralized configuration for the Carnauba Viewer application.
Contains constants, color schemes, and application settings.
"""
import logging

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO


def setup_logging():
    """Configure application-wide logging."""
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)


# =============================================================================
# SUPPORTED FILE TYPES
# =============================================================================
SUPPORTED_EXTENSIONS = ["pdf", "dxf", "ifc", "ifczip"]

# File type categories
FILE_TYPE_PDF = "pdf"
FILE_TYPE_DXF = "dxf"
FILE_TYPE_IFC = "ifc"
FILE_TYPE_IFCZIP = "ifczip"


# =============================================================================
# IFC CONFIGURATION
# =============================================================================
# IFC element types to render in 3D visualization
IFC_TARGET_TYPES = [
    "IfcWall",
    "IfcSlab",
    "IfcWindow",
    "IfcDoor",
    "IfcColumn",
    "IfcBeam",
    "IfcRoof",
    "IfcStair",
    "IfcRailing",
    "IfcCurtainWall",
    "IfcRamp",
    "IfcMember",
    "IfcPlate",
    "IfcCovering",
    "IfcFurnishingElement",
    "IfcFlowTerminal",
    "IfcFlowSegment",
    "IfcBuildingElementProxy",
]

# Color mapping for IFC element types
IFC_ELEMENT_COLORS = {
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
    "IfcCovering": "whitesmoke",
}

# Transparent IFC elements (windows, curtain walls)
IFC_TRANSPARENT_TYPES = ["IfcWindow", "IfcCurtainWall"]
IFC_TRANSPARENT_OPACITY = 0.4
IFC_SOLID_OPACITY = 1.0


# =============================================================================
# DXF CONFIGURATION
# =============================================================================
# DXF entity types to render
DXF_SUPPORTED_ENTITIES = [
    "LINE",
    "LWPOLYLINE",
    "POLYLINE",
    "CIRCLE",
    "ARC",
    "SPLINE",
    "ELLIPSE",
]

# DXF flattening distance for curves (lower = more precision, higher = faster)
DXF_FLATTENING_DISTANCE = 0.1


# =============================================================================
# UI CONFIGURATION
# =============================================================================
# Dark mode colors
UI_BACKGROUND_COLOR = "#0e1117"
UI_PAPER_COLOR = "#0e1117"
UI_FONT_COLOR = "#fafafa"

# Viewer dimensions
VIEWER_HEIGHT_2D = 700
VIEWER_HEIGHT_3D = 600
PDF_VIEWER_HEIGHT = 800


# =============================================================================
# METADATA DISPLAY
# =============================================================================
# Maximum number of layers to display in DXF metadata
MAX_LAYERS_DISPLAY = 10
