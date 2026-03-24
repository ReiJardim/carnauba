# Carnauba

![Logo Carnauba](assets/logo.png)

Plataforma SaaS para engenharia estrutural: visualização de projetos (PDF, DXF, IFC/BIM) e dimensionamento de elementos estruturais conforme normas brasileiras (NBR 6118, NBR 6120).

Desenvolvida em Python + Streamlit, com foco em praticidade para engenheiros civis — sem necessidade de software pesado instalado.

---

## Funcionalidades

### Visualização de Projetos
- **PDF** — renderização nativa com zoom e scroll (`streamlit-pdf-viewer`)
- **DXF** — plotagem 2D interativa de linhas e layers, dark mode (`ezdxf` + Plotly)
- **IFC / IFCZIP** — visualização 3D de malha BIM e árvore hierárquica (Projeto → Site → Edifício → Pavimento) (`ifcopenshell` + Plotly)
- Upload múltiplo, painel lateral com metadados técnicos (layers, entidades, versão, páginas)

### Dimensionamento Estrutural

#### Escadas (completo)
Motor de cálculo completo conforme **NBR 6118:2014** e **NBR 6120:2019**:

- **Geometria** — validação pela fórmula de Blondel (60 ≤ 2e + p ≤ 64), espessura mínima da laje
- **Cargas** — peso próprio, revestimento, sobrecarga de uso, combinações ELU/ELS
- **Esforços** — diagramas de momento fletor e força cortante ao longo do vão
- **Dimensionamento ao ELU** — cálculo de armadura principal e de distribuição, verificação de cisalhamento sem estribos (§19.4.1)
- **Detalhamento** — seleção comercial de barras (φ disponíveis), verificação de espaçamentos (§17.3.5.2), comprimentos de ancoragem (§9.3 / §9.4.2.5)
- **Detalhes de execução** — regras de amarração, sequência de montagem, cobrimentos, nó laje/escada (empuxo ao vazio)
- **Visualização 3D interativa** — modelo Plotly com prismas triangulares geometricamente corretos, piso inferior e laje superior de continuidade, armaduras principal e de distribuição modeladas internamente, slider de transparência do concreto

#### Reservatório (em desenvolvimento)
#### Pilares, Vigas, Lajes, Fundações (planejados)

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Interface | Streamlit |
| Visualização 3D/2D | Plotly |
| Cálculo numérico | NumPy |
| Leitura PDF | pypdf, streamlit-pdf-viewer |
| Leitura DXF | ezdxf |
| Leitura IFC | ifcopenshell |

---

## Instalação

```bash
# 1. Clonar
git clone <url-do-repositorio>
cd carnauba

# 2. Ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Dependências
pip install -r requirements.txt

# 4. Executar
streamlit run app.py
# Acesse em http://localhost:8501

# 5. Verificar ambiente
python verify_env.py

# Testes
pytest tests/ -v
```

---

## Estrutura do Projeto

```
carnauba/
├── app.py                          # Roteamento e tema global (dark + accent #FF6B6B)
├── p_livres/
│   ├── visualizacao.py             # Página: visualizador PDF / DXF / IFC
│   └── estrutural.py               # Página: abas de dimensionamento (Escada, Reservatório…)
├── utils/
│   ├── parsers.py                  # Extração de metadados (PDF, DXF, IFC)
│   ├── renderers.py                # Renderização (PDF iframe, DXF Plotly 2D, IFC Plotly 3D)
│   ├── config.py                   # Constantes (tipos IFC, cores, dimensões)
│   ├── exceptions.py               # Hierarquia de exceções (CarnaubaError, DXFParseError…)
│   ├── temp_files.py               # Context manager para limpeza de arquivos temporários
│   └── estrutura/
│       ├── escada/
│       │   └── escadas.py          # Motor completo de dimensionamento de escadas (~1600 linhas)
│       └── reservatorio/
│           └── reservatorio.py     # Dimensionamento de reservatórios (em desenvolvimento)
├── laboratorio/
│   └── docs/                       # Documentação técnica e referências de normas
│       ├── _meta/                  # Sistema de continuidade para sessões de LLM
│       └── referencia_tecnica/     # Referências NBR, notas de aula, exemplos
├── tests/
│   ├── test_parsers.py
│   └── test_renderers.py
└── .streamlit/
    └── config.toml                 # Tema dark, layout wide
```

---

## Status

| Módulo | Status |
|--------|--------|
| Visualizador PDF | Completo |
| Visualizador DXF | Completo |
| Visualizador IFC/BIM | Completo |
| Dimensionamento — Escadas | Completo |
| Dimensionamento — Reservatório | Em desenvolvimento |
| Dimensionamento — Pilares | Planejado |
| Dimensionamento — Vigas | Planejado |
| Dimensionamento — Lajes | Planejado |
| Dimensionamento — Fundações | Planejado |
