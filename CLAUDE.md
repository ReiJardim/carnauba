# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Carnauba is a Streamlit-based SaaS MVP for construction file visualization (PDF, DXF, IFC/BIM) and structural dimensioning following Brazilian building codes (NBR 6118, NBR 6120).

## Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the application
streamlit run app.py

# Run tests
pytest tests/ -v

# Run a single test file
pytest tests/test_parsers.py -v

# Verify dependencies
python verify_env.py
```

## Architecture

### Entry Point & Navigation

`app.py` sets up Streamlit navigation with two sections:
- **Projetos** → `p_livres/visualizacao.py` (file viewer)
- **Dimensionamento** → `p_livres/estrutural.py` (structural calculations)

### Layer Structure

```
app.py              → Page routing, global CSS/theme
p_livres/           → Page modules (UI layer)
utils/              → Core business logic
  parsers.py        → Metadata extraction (PDF/DXF/IFC)
  renderers.py      → Visualization (PDF iframe, DXF Plotly 2D, IFC Plotly 3D)
  config.py         → Constants (IFC element types, colors, dimensions)
  exceptions.py     → Custom exception hierarchy (CarnaubaError, DXFParseError…)
  temp_files.py     → Context manager for temp file cleanup
  estrutura/escada/
    escadas.py      → Stair calculation engine (geometry → loads → efforts → reinforcement)
```

### Key Patterns

- **State management:** `st.session_state` persists uploaded files across Streamlit reruns; metadata is lazily parsed and cached.
- **File support:** PDF (pypdf + streamlit-pdf-viewer), DXF (ezdxf + Plotly), IFC/IFCZIP (ifcopenshell + Plotly 3D mesh).
- **Structural engine:** `escadas.py` implements full stair design per Brazilian codes — Blondel formula validation, load combinations, bending/shear diagrams, reinforcement dimensioning (ELU), and shear verification without stirrups.

### UI/UX Conventions

- Dark theme with red accent `#FF6B6B` (configured in `.streamlit/config.toml` and overridden via injected CSS in `app.py`).
- Wide layout: ~75% viewer / 25% info panel.
- Tabbed interface for structural calculation categories.
- Comments in the codebase are written in Portuguese.
