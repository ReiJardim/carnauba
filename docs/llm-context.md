# Carnauba Construction Viewer - LLM Context Document

> ⚠️ **ATENÇÃO LLMs**: 
> 1. **LEIA ESTE DOCUMENTO INTEIRO** antes de fazer qualquer modificação no código
> 2. **ATUALIZE ESTE DOCUMENTO** após concluir suas mudanças (seção "Revision History")
> 3. Este documento existe para **otimizar seu contexto** - ele contém tudo que você precisa saber sobre este sistema
> 4. Veja também o workflow: `.agent/workflows/llm-context.md`

> **Purpose**: This document serves as a comprehensive context reference for Large Language Models (LLMs) working on this codebase. It should be read first before making any code modifications to understand the system's architecture, conventions, and current state.

> **Maintenance Protocol**: This document MUST be updated whenever significant code changes are made. Add an entry to the "Revision History" section at the bottom with: Date, Model/Tool, and Summary of Changes.

---

## 1. System Overview

**Carnauba Viewer** is a Streamlit-based web application (SaaS pilot) designed for construction professionals (engineers and architects) to visualize project files without heavy desktop software (AutoCAD, Revit, etc.).

### Core Purpose
- Upload and view multiple construction files in a unified interface
- Support for PDF (drawings), DXF (CAD files), and IFC (BIM models)
- Extract and display technical metadata
- Provide interactive visualization with zoom/pan capabilities

### Technology Stack
- **Framework**: Streamlit (Python web framework)
- **Language**: Python 3.9+
- **Deployment**: Local/Cloud-ready

---

## 2. Repository Structure

```
/home/rei/reijardim/carnauba/
├── app.py                    # Main Streamlit application (entry point)
├── requirements.txt          # Python dependencies
├── README.md                 # User-facing documentation
├── verify_env.py            # Environment verification script
├── .gitignore               # Git ignore rules (includes __pycache__, .venv, lab/)
│
├── utils/                   # Core business logic modules
│   ├── __init__.py          # Empty package initializer
│   ├── parsers.py           # Metadata extraction logic (PDF, DXF, IFC)
│   └── renderers.py         # Visualization/rendering logic (PDF, DXF, IFC)
│
├── assets/                  # Static resources
│   └── logo.png             # App logo (displayed in sidebar)
│
├── lab/                     # Test data directory (gitignored)
│   ├── *.dxf                # Sample DXF files for testing
│   └── *.ifc                # Sample IFC files for testing
│
└── tests/                   # Test scripts
    └── verify_dxf_logic.py  # Unit tests for DXF parsing/rendering
```

---

## 3. Core Dependencies

From `requirements.txt`:

| Package                | Version    | Purpose                                      |
|------------------------|------------|----------------------------------------------|
| `streamlit`            | ≥1.30.0    | Web framework (UI, session state)            |
| `streamlit-pdf-viewer` | Latest     | PDF rendering component                      |
| `ezdxf`                | Latest     | DXF file parsing and geometry extraction     |
| `matplotlib`           | Latest     | *(Legacy)* Previously used for DXF rendering |
| `plotly`               | Latest     | Interactive 2D/3D visualization              |
| `ifcopenshell`         | Latest     | IFC (BIM) file parsing and geometry          |
| `pypdf`                | Latest     | PDF metadata extraction                      |
| `pandas`               | Latest     | Data manipulation for IFC quantitative data  |
| `numpy`                | Latest     | Numerical operations for geometry            |

---

## 4. Application Architecture

### 4.1 Entry Point: `app.py`

**Responsibilities**:
- Streamlit page configuration (wide layout, dark theme)
- Session state management (`uploaded_files`, `current_index`, `file_metadata`, `fullscreen`)
- File upload handling (sidebar)
- File navigation logic (previous/next buttons)
- Routing to appropriate parser and renderer based on file extension
- Layout management (viewer column vs info panel, fullscreen mode)

**Key Components**:
1. **Sidebar**: Logo, file uploader, about section
2. **Main Area**: 
   - Header with filename and fullscreen toggle
   - Viewer area (calls `render_*` functions)
   - Navigation controls (prev/next)
3. **Info Panel** (right column, hidden in fullscreen):
   - File metadata card (name, size, type)
   - Technical details expander (format-specific metadata)

**Session State Variables**:
- `uploaded_files`: List of uploaded file objects
- `current_index`: Index of currently displayed file
- `file_metadata`: Dictionary caching parsed metadata {filename: metadata_dict}
- `fullscreen`: Boolean toggle for fullscreen mode

### 4.2 Module: `utils/parsers.py`

**Purpose**: Extract metadata from uploaded files without rendering them.

**Functions**:

1. **`parse_pdf_metadata(file_buffer)`**
   - Input: BytesIO buffer of PDF file
   - Output: Dictionary with `type`, `pages`, `info` (metadata)
   - Library: `pypdf.PdfReader`
   - Error handling: Returns `{"error": ..., "type": "PDF"}` on failure

2. **`parse_dxf_metadata(file_buffer)`**
   - Input: BytesIO buffer of DXF file
   - Output: Dictionary with `type`, `version`, `layers_count`, `layers` (first 10)
   - Implementation:
     - Saves buffer to temporary file (handles binary/text DXF)
     - Uses `ezdxf.readfile()` for robust parsing
     - Extracts layer names and DXF version
     - Cleans up temp file in `finally` block
   - Error handling: Returns `{"error": ..., "type": "DXF"}` on failure

3. **`parse_ifc_metadata(file_buffer)`**
   - Input: BytesIO buffer of IFC or IFCZIP file
   - Output: Dictionary with `type`, `schema`, `project_name`, `counts` (walls, windows, doors, slabs)
   - Implementation:
     - Detects if file is ZIP (IFCZIP format)
     - Extracts first `.ifc` from ZIP if necessary
     - Saves to temporary file for `ifcopenshell.open()`
     - Queries entity counts (`IfcWall`, `IfcWindow`, etc.)
     - Extracts project name from `IfcProject`
     - Cleans up temp file
   - Error handling: Returns `{"error": ..., "type": "IFC"}` on failure

**Common Pattern**: All parsers use temporary files for robust library compatibility and include proper cleanup in `finally` blocks.

### 4.3 Module: `utils/renderers.py`

**Purpose**: Generate visual representations of files in the Streamlit UI.

**Functions**:

1. **`render_pdf(file_buffer)`**
   - Implementation: Base64-encodes PDF and embeds in iframe for native browser rendering
   - Interactivity: Native PDF viewer (zoom, scroll, print)
   - Height: 800px

2. **`render_dxf(file_buffer)`**
   - **Current Implementation** (as of 2026-01-02):
     - Saves buffer to temporary file
     - Loads using `ezdxf.readfile()` (handles binary/text DXF)
     - Uses `ezdxf.path.make_path()` to extract geometry from entities
     - Supported entities: LINE, LWPOLYLINE, POLYLINE, CIRCLE, ARC, SPLINE, ELLIPSE
     - Flattens curves to line segments (0.1 unit tolerance)
     - Groups coordinates by **layer** for performance (reduces Plotly traces)
     - Uses `plotly.graph_objects.Scatter` with `mode='lines'`
     - Separates disconnected lines with `None` (NaN) values
     - **Interactivity**: Zoom (scroll), Pan (drag), Layer toggle (legend)
     - **Layout**: Dark theme (`#0e1117`), aspect ratio 1:1 (critical for CAD), dragmode='pan'
     - Cleans up temp file
   - **Previous Implementation** (deprecated): Used Matplotlib with `RenderContext` and `MatplotlibBackend` (static image)

3. **`render_ifc(file_buffer)`**
   - Implementation:
     - Handles both `.ifc` and `.ifczip` formats
     - Saves to temporary file, loads with `ifcopenshell.open()`
     - Creates **two tabs**:
       - **Tab 1: "Visualização 3D"**:
         - Uses `ifcopenshell.geom.settings()` with `USE_WORLD_COORDS=True`
         - Iterates through target entity types (walls, slabs, windows, doors, columns, beams, etc.)
         - Calls `ifcopenshell.geom.create_shape()` to extract mesh geometry
         - Converts flat vertex/face arrays to numpy for Plotly
         - Creates `plotly.graph_objects.Mesh3d` traces
         - Color-codes by entity type (walls=lightgrey, windows=lightblue, etc.)
         - Sets windows/curtain walls to 40% opacity for transparency
         - **Interactivity**: 3D orbit, zoom, pan
         - **Layout**: Dark theme, hidden axes
       - **Tab 2: "Dados & Quantitativos"**:
         - Displays pandas DataFrame with element counts
         - Shows project hierarchy (Project → Site → Building → Storey)
     - Cleans up temp file
   - Error handling: Displays user-friendly error messages via `st.error()`

**Common Patterns**:
- All renderers use temporary files for library compatibility
- Dark theme integration (`#0e1117` background)
- Proper error handling with user feedback
- Resource cleanup in `finally` blocks

---

## 5. Key Workflows

### 5.1 File Upload and Display Flow

```
User uploads files via sidebar
  ↓
Streamlit processes upload
  ↓
Session state updated (uploaded_files, current_index reset)
  ↓
App.py checks if metadata cached for current file
  ↓
NO → Calls appropriate parse_*_metadata() → Caches result
  ↓
Displays metadata in info panel
  ↓
Calls appropriate render_*() function
  ↓
User sees visualization
```

### 5.2 File Navigation Flow

```
User clicks "Próximo" or "Anterior"
  ↓
Session callback updates current_index
  ↓
st.rerun() triggers full page refresh
  ↓
App re-renders with new current_index
  ↓
Metadata retrieved from cache (if exists)
  ↓
New file visualized
```

### 5.3 DXF Rendering Pipeline (Current)

```
User uploads DXF
  ↓
parse_dxf_metadata() extracts layers, version
  ↓
render_dxf() called
  ↓
Temp file created
  ↓
ezdxf.readfile() loads document
  ↓
Iterate modelspace entities
  ↓
Filter: LINE, LWPOLYLINE, CIRCLE, ARC, etc.
  ↓
ezdxf.path.make_path() → flatten to vertices
  ↓
Group by layer {layer_name: {x: [...], y: [...]}}
  ↓
Create Plotly Scatter trace per layer
  ↓
Apply 1:1 aspect ratio constraint
  ↓
st.plotly_chart() displays interactive plot
  ↓
Temp file cleaned up
```

---

## 6. Code Conventions and Patterns

### 6.1 Error Handling
- **Parser functions**: Always return dictionary with `"error"` key on failure, never raise exceptions
- **Renderer functions**: Use `st.error()` to display user-friendly messages, wrap main logic in try-except
- **Resource cleanup**: Always use `finally` blocks to delete temporary files

### 6.2 Temporary File Usage
- **Purpose**: Many libraries (ezdxf, ifcopenshell) work best with file paths rather than streams
- **Pattern**:
  ```python
  tmp_path = None
  try:
      with tempfile.NamedTemporaryFile(delete=False, suffix=".ext") as tmp:
          tmp.write(file_buffer.getvalue())
          tmp_path = tmp.name
      # Use tmp_path...
  finally:
      if tmp_path and os.path.exists(tmp_path):
          try:
              os.unlink(tmp_path)
          except:
              pass
  ```

### 6.3 Session State Management
- All stateful data stored in `st.session_state`
- Initialize with `if 'key' not in st.session_state:` checks
- Use `st.rerun()` to trigger UI refresh after state changes

### 6.4 Styling
- **Dark Mode**: Background `#0e1117`, text `#fafafa`
- **Cards**: Background `#262730`, border `#464b59`
- **CAD Visualization**: Always maintain 1:1 aspect ratio for DXF/drawings

### 6.5 Performance Optimization
- **Metadata Caching**: Parse metadata once per file, store in session_state
- **DXF Grouping**: Group entities by layer to reduce number of Plotly traces (critical for large files)
- **IFC Batching**: Iterate entities but skip geometry creation on errors (continue rather than fail)

---

## 7. Known Issues and Limitations

### 7.1 DXF Rendering
- **Issue**: Empty or black visualization
  - **Cause**: No supported entities in modelspace, or all entities filtered out
  - **Solution**: Displays warning "Nenhuma geometria suportada encontrada..."
- **Issue**: Binary DXF files previously failed
  - **Status**: ✅ FIXED (2026-01-02) - Now uses `ezdxf.readfile()` with temp files

### 7.2 IFC Rendering
- **Performance**: Large IFC files (>100MB) may take 10-30 seconds to render
- **Geometry Extraction**: Some elements may fail silently (wrapped in try-except continue)
- **Browser Limits**: Very complex models may overwhelm Plotly (thousands of meshes)

### 7.3 General
- **No Measurement Tools**: Interactive measurement (distance, area) not yet implemented
- **Limited File Formats**: Only PDF, DXF, IFC/IFCZIP supported
- **No Authentication**: Currently single-user, no login system

---

## 8. Testing

### 8.1 Manual Testing
- **Test files**: Located in `lab/` directory (gitignored)
- **Procedure**:
  1. Run `streamlit run app.py`
  2. Upload sample files from `lab/`
  3. Verify metadata extraction in info panel
  4. Test interactivity (zoom, pan, layer toggle)
  5. Test navigation between files

### 8.2 Unit Tests
- **Location**: `tests/verify_dxf_logic.py`
- **Purpose**: Test DXF parsing and rendering logic
- **Run**: `python tests/verify_dxf_logic.py`
- **Note**: Tests mock Streamlit components (`st.plotly_chart`, etc.)

### 8.3 Environment Verification
- **Script**: `verify_env.py`
- **Purpose**: Check that all dependencies are installed and importable
- **Run**: `python verify_env.py`

---

## 9. Development Guidelines for LLMs

### When Adding New Features
1. ✅ Update this document in "Revision History" section
2. ✅ Follow existing error handling patterns (try-except, finally cleanup)
3. ✅ Add metadata extraction to `parsers.py` if new file type
4. ✅ Add rendering logic to `renderers.py`
5. ✅ Update `app.py` routing logic for new file extensions
6. ✅ Test with sample files in `lab/`
7. ✅ Update `README.md` if user-facing feature

### When Fixing Bugs
1. ✅ Identify root cause (check temp file cleanup, error handling)
2. ✅ Verify fix doesn't break existing functionality
3. ✅ Update this document in "Known Issues" section (mark as fixed)
4. ✅ Add entry to "Revision History"

### When Refactoring
1. ✅ Maintain backward compatibility with session state
2. ✅ Keep dark theme consistency
3. ✅ Preserve temp file cleanup patterns
4. ✅ Update architecture diagrams if structural changes
5. ✅ Document reason for refactoring in "Revision History"

---

## 10. Quick Reference

### File Extensions Mapping
- `.pdf` → `parse_pdf_metadata()` + `render_pdf()`
- `.dxf` → `parse_dxf_metadata()` + `render_dxf()`
- `.ifc` → `parse_ifc_metadata()` + `render_ifc()`
- `.ifczip` → `parse_ifc_metadata()` + `render_ifc()`

### Session State Keys
- `uploaded_files`: List[UploadedFile]
- `current_index`: int
- `file_metadata`: Dict[str, Dict]
- `fullscreen`: bool

### Color Palette
- Background: `#0e1117`
- Text: `#fafafa`
- Card BG: `#262730`
- Border: `#464b59`

### Important Directories
- Code: `utils/`
- Assets: `assets/`
- Test Data: `lab/` (gitignored)
- Tests: `tests/`

---

## 11. Revision History

| Date       | Model/Tool      | Summary of Changes                                                                                     |
|------------|-----------------|--------------------------------------------------------------------------------------------------------|
| 2026-01-02 | Claude 4.5 Sonnet | **Initial document creation**. Documented full system architecture, DXF fix (binary support via temp files), DXF rendering switch from Matplotlib to Plotly for interactivity. |

---

**End of LLM Context Document**

*Remember to update this document whenever you make significant changes to the codebase. This ensures all future LLM interactions have accurate context.*

| 2026-01-15 | Gemini 2.5 Pro | **Fase 2 Qualidade de Código**: Criado `utils/exceptions.py` (8 exceções customizadas), `utils/temp_files.py` (context manager), type hints em parsers.py e renderers.py, expandido testes (11 testes em test_parsers.py e test_renderers.py). |
