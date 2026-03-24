

import streamlit as st
import os
from utils.parsers import parse_pdf_metadata, parse_dxf_metadata, parse_ifc_metadata
from utils.renderers import render_pdf, render_dxf, render_ifc




# --- Gerenciamento de Estado ---
if 'uploaded_files' not in st.session_state:
    st.session_state['uploaded_files'] = []
    
if 'current_index' not in st.session_state:
    st.session_state['current_index'] = 0

if 'file_metadata' not in st.session_state:
    st.session_state['file_metadata'] = {}

if 'fullscreen' not in st.session_state:
    st.session_state['fullscreen'] = False

# --- Sidebar (Upload) ---
with st.sidebar:
    # Módulo de Upload
    uploaded = st.file_uploader("Carregar arquivos de projeto", 
                                type=["pdf", "dxf", "ifc", "ifczip"], 
                                accept_multiple_files=True)
    
    st.markdown("---")
    st.markdown("### Sobre")
    st.info("Visualizador multiprojeto para arquivos de construção civil (PDF, DXF, IFC).")

# --- Lógica de Upload ---
if uploaded:
    current_filenames = [f.name for f in st.session_state['uploaded_files']]
    new_filenames = [f.name for f in uploaded]
    
    if set(current_filenames) != set(new_filenames):
        st.session_state['uploaded_files'] = uploaded
        st.session_state['current_index'] = 0
        st.session_state['file_metadata'] = {} # Limpar cache de metadados
        st.rerun()

files = st.session_state['uploaded_files']

if not files:
    st.info("👈 Por favor, utilize a barra lateral para fazer upload de arquivos.")
    st.stop()

# --- Navegação e Seleção do Arquivo Atual ---
if st.session_state['current_index'] >= len(files):
    st.session_state['current_index'] = 0
    
current_file = files[st.session_state['current_index']]
file_ext = current_file.name.split('.')[-1].lower()

# --- Extração de Metadados (Lazy Loading) ---
if current_file.name not in st.session_state['file_metadata']:
    # Processar metadados
    with st.spinner(f"Processando {current_file.name}..."):
        if file_ext == "pdf":
            st.session_state['file_metadata'][current_file.name] = parse_pdf_metadata(current_file)
        elif file_ext == "dxf":
            st.session_state['file_metadata'][current_file.name] = parse_dxf_metadata(current_file)
        elif file_ext in ["ifc", "ifczip"]:
            st.session_state['file_metadata'][current_file.name] = parse_ifc_metadata(current_file)
        else:
            st.session_state['file_metadata'][current_file.name] = {"type": "Desconhecido"}

metadata = st.session_state['file_metadata'][current_file.name]

# --- Layout Grid Principal ---
# Se fullscreen estiver ativo, usa 1 coluna (100%), senão usa [3, 1]
if st.session_state['fullscreen']:
    col_viewer = st.container()
    col_info = None 
else:
    col_viewer, col_info = st.columns([3, 1])

with col_viewer:
    # Header do Viewer com controles
    c1, c2, c3 = st.columns([6, 2, 1])
    with c1:
        st.header(f"Visualizando: {current_file.name}")
    with c3:
        # Botão Fullscreen
        if st.button("⛶", help="Alternar Tela Cheia"):
            st.session_state['fullscreen'] = not st.session_state['fullscreen']
            st.rerun()

    # Área de Renderização
    if file_ext == "pdf":
        render_pdf(current_file)
    elif file_ext == "dxf":
        render_dxf(current_file)
    elif file_ext in ["ifc", "ifczip"]:
        render_ifc(current_file)
    else:
        st.warning("Formato não suportado para visualização.")
        
    # Navegação (Agora dentro da coluna do viewer)
    st.markdown("---")
    
    # Layout de navegação compacto
    nav_c1, nav_c2, nav_c3 = st.columns([1, 2, 1])
    
    def prev_file():
        if st.session_state['current_index'] > 0:
            st.session_state['current_index'] -= 1

    def next_file():
        if st.session_state['current_index'] < len(files) - 1:
            st.session_state['current_index'] += 1

    with nav_c1:
        if st.button("⬅️ Anterior", disabled=(st.session_state['current_index'] == 0), use_container_width=True):
            prev_file()
            st.rerun()

    with nav_c2:
         st.markdown(f"<div style='text-align: center; padding-top: 5px; color: #888;'>Arquivo {st.session_state['current_index'] + 1} / {len(files)}</div>", unsafe_allow_html=True)

    with nav_c3:
        if st.button("Próximo ➡️", disabled=(st.session_state['current_index'] == len(files) - 1), use_container_width=True):
            next_file()
            st.rerun()

# --- Info Panel (Só renderiza se não for fullscreen) ---
if not st.session_state['fullscreen'] and col_info:
    with col_info:
        st.markdown("### 📋 Informações")
        
        # Card de Informações Gerais
        st.markdown(f"""
        <div class="metric-card">
            <strong>Arquivo:</strong> {current_file.name}<br>
            <strong>Tamanho:</strong> {current_file.size / 1024:.2f} KB<br>
            <strong>Tipo:</strong> {metadata.get('type', file_ext.upper())}
        </div>
        """, unsafe_allow_html=True)
        
        # Detalhes Específicos
        with st.expander("Detalhes Técnicos", expanded=True):
            if "error" in metadata:
                st.error(metadata["error"])
            else:
                if file_ext == "pdf":
                    st.write(f"**Páginas:** {metadata.get('pages', '-')}")
                    
                elif file_ext == "dxf":
                    st.write(f"**Versão DXF:** {metadata.get('version', '-')}")
                    st.write(f"**Layers ({metadata.get('layers_count', 0)}):**")
                    for layer in metadata.get('layers', []):
                        st.text(layer) # text is more compact than code
                        
                elif file_ext in ["ifc", "ifczip"]:
                    st.write(f"**Projeto:** {metadata.get('project_name', '-')}")
                    st.write(f"**Schema:** {metadata.get('schema', '-')}")
                    st.write("**Contagem de Elementos:**")
                    counts = metadata.get('counts', {})
                    for k, v in counts.items():
                        st.write(f"- {k}: {v}")