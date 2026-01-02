# Carnauba Construction Viewer 🏗️

**Carnauba Viewer** é uma aplicação web (SaaS Pilot) desenvolvida em Python e Streamlit para visualização ágil de arquivos de construção civil.

O objetivo é permitir que engenheiros e arquitetos carreguem múltiplos arquivos de projeto e naveguem por eles em uma interface unificada, extraindo metadados essenciais e fornecendo visualização rápida sem necessidade de software pesado (CAD/BIM) instalado.

## 🚀 Funcionalidades

- **Upload Múltiplo:** Suporte para carregar vários arquivos de uma vez.
- **Visualizador de PDF:** Renderização nativa com zoom e scroll.
- **Visualizador de DXF:** Plotagem 2D das linhas e layers (Dark Mode).
- **Visualizador de IFC:** Inspeção da árvore hierárquica (Projeto -> Site -> Edifício -> Pavimento) e contagem de elementos.
- **Extração de Metadados:** Painel lateral com informações técnicas (Layers, Versão, Entidades, Páginas).
- **Interface Premium:** Layout "Wide", Dark Mode e navegação fluida entre arquivos.

## 🛠️ Stack Tecnológica

- **Frontend/Backend:** [Streamlit](https://streamlit.io/)
- **Processamento de Arquivos:**
  - `pypdf` (Metadados PDF)
  - `ezdxf` & `matplotlib` (Renderização DXF)
  - `ifcopenshell` (Parsing IFC)

## 📦 Instalação e Execução

### Pré-requisitos
- Python 3.9+
- Linux/Mac (Recomendado) ou Windows

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone <url-do-repositorio>
   cd carnauba
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate   # Windows
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute a aplicação:**
   ```bash
   streamlit run app.py
   ```

5. **Acesse no navegador:**
   Geralmente em `http://localhost:8501`

## 📂 Estrutura do Projeto

```
carnauba/
├── app.py                # Aplicação Principal (Streamlit)
├── requirements.txt      # Dependências
├── assets/               # Imagens e logos
└── utils/
    ├── parsers.py        # Extração de métadados (PDF, DXF, IFC)
    └── renderers.py      # Lógica de visualização
```

## 📝 Status do Projeto
Este projeto é um MVP (Minimum Viable Product).
- [x] Visualização Básica (PDF, DXF)
- [x] Leitura de árvore IFC
- [ ] Visualização 3D avançada para IFC
- [ ] Interatividade avançada no Canvas DXF (Pan/Zoom dinâmico)
