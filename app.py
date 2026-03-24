import streamlit as st
import os

# 1. Configuração da Página DEVE ser o primeiro comando Streamlit
st.set_page_config(
    page_title="Carnauba Viewer",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))

# --- CSS Customizado para Dark Mode e Estilo Premium ---
st.markdown("""
<style>
    
    .css-1d391kg {
        padding-top: 1rem;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    /* Estilo para Cards de Metadados */
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        border: 1px solid #464b59;
    }
    
    /* Ajuste de largura do Sidebar */
    [data-testid="stSidebar"] {
        min-width: 200px;
        max-width: 300px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Logo e Título acima da navegação
# st.logo coloca o logo automaticamente na parte superior esquerda (se a versão for suportada)
if os.path.exists("assets/logo.png"):
    st.logo("assets/logo.png")

with st.sidebar:
    # Caso prefira a imagem maior centralizada na sidebar antes do título, descomente abaixo
    # if os.path.exists("assets/logo.png"):
    #     st.image("assets/logo.png", width=150)
    # else:
    if not os.path.exists("assets/logo.png"):
        st.write("🏗️")
        
    st.title("Carnauba Viewer")
    st.markdown("---")


st.divider()

# 3. Navegação da Página
pg = st.navigation(
    {
        "Projetos": [
            st.Page(os.path.join(DIRETORIO_ATUAL, "p_livres", "visualizacao.py"), title="Visualização de Projetos"),
        ],
        "Dimensionamento": [
            st.Page(os.path.join(DIRETORIO_ATUAL, "p_livres", "estrutural.py"), title="Dimensionamento Estrutural", default=False),
        ],
    }
)

pg.run()
