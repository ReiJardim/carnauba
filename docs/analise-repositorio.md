# Análise do Repositório Carnauba

> **Documento vivo** — deve ser atualizado a cada ciclo de desenvolvimento significativo (novos módulos, refatorações, marcos de produto).
>
> Última atualização: 2026-03-16 | Branch: `estrutural`

---

## Visão Geral

**Carnauba** é um SaaS MVP para visualização de arquivos de construção civil (PDF, DXF, IFC/BIM) e dimensionamento estrutural, construído em Python com Streamlit. O projeto está na branch `estrutural`, onde o módulo de dimensionamento é desenvolvido progressivamente.

---

## Análise Técnica de Software

### Arquitetura

Separação em 3 camadas bem definidas:

```
app.py                  → roteamento, tema, CSS global
p_livres/               → camada UI (páginas Streamlit)
    visualizacao.py     → visualizador multi-formato
    estrutural.py       → roteador de abas de dimensionamento
utils/                  → lógica de negócio pura
    parsers.py          → extração de metadados (PDF/DXF/IFC)
    renderers.py        → geração de visualizações interativas
    config.py           → constantes centralizadas
    exceptions.py       → hierarquia de exceções customizadas
    temp_files.py       → gerenciamento de arquivos temporários
    estrutura/
        escada/
            escadas.py  → motor de dimensionamento de escadas
```

Para adicionar um novo módulo estrutural (ex: vigas), o padrão já existe: criar `utils/estrutura/viga/vigas.py` e importar em `estrutural.py`.

### Pontos Fortes

**Gestão de estado** (`st.session_state`): metadados parseados uma vez e cacheados, evitando re-processamento a cada rerun. Navegação entre arquivos com controle correto de limites da lista.

**Gerenciamento de recursos** (`temp_files.py`): context manager com `try/finally` garante limpeza de arquivos temporários mesmo em caso de exceção.

**Renderização DXF**: entidades agrupadas por layer antes de criar traços Plotly — reduz o número de traces e melhora performance em DXFs complexos. Aspecto 1:1 forçado via `scaleanchor` (fundamental para desenho técnico).

**Renderização IFC 3D**: continua processando elementos mesmo quando a geometria de um falha — evita crash total por um elemento problemático.

**Motor de escadas** (`escadas.py`): 501 linhas, bem comentado em português, fluxo em wizard de abas. Funções de plot separadas por responsabilidade — fácil de manter e estender.

### Problemas Identificados

| Problema | Localização | Severidade |
|---|---|---|
| `exceptions.py` definido mas nunca utilizado | `parsers.py`, `renderers.py` | Baixa |
| `import matplotlib` sem uso | `renderers.py` | Mínima |
| `verify_dxf_logic.py` usa `unittest`, restante usa `pytest` | `tests/` | Baixa |
| Módulos estruturais (Reservatório, Pilares...) são placeholders | `estrutural.py` | Esperado (roadmap) |
| Módulo `escadas.py` sem cobertura de testes | `tests/` | Média |

### Cobertura de Testes

| Arquivo | Testes | Cobertura |
|---|---|---|
| `parsers.py` | 11 (TestDXF ×4, TestPDF ×2, TestIFC ×3+) | Boa |
| `renderers.py` | 3 (DXF ×2, PDF ×1) | Básica |
| `escadas.py` | **0** | Ausente |

Fixtures em `conftest.py` bem construídas com mock do Streamlit — base correta para expansão.

### Status por Módulo

| Módulo | Status | Qualidade |
|---|---|---|
| Visualizador PDF | Completo | Excelente |
| Visualizador DXF | Completo | Excelente |
| Visualizador IFC/BIM 3D | Completo | Excelente |
| Extração de metadados | Completo | Excelente |
| Navegação multi-arquivo | Completo | Excelente |
| Dimensionamento de escadas | Completo | Excelente |
| Reservatório | Placeholder | — |
| Pilares | Placeholder | — |
| Vigas | Placeholder | — |
| Lajes | Placeholder | — |
| Fundações | Placeholder | — |

### Histórico Git (marcos relevantes)

| Commit | Descrição |
|---|---|
| `612966e` | Corrige atribuição das abas para visualização da escada |
| `2a58645` | Implementação completa do dimensionamento de escadas + docs técnicos |
| `705caa5` | Estrutura inicial para visualização e dimensionamento |
| `db85a27` | Otimizações gerais |
| `8756c41` | Configurações DXF |
| `501b677` | Merge PR #3 — implementação IFC |

A branch `estrutural` adiciona **1.768 linhas e remove 289** em relação à `main`. É uma adição substancial e bem estruturada.

---

## Análise Técnica de Engenharia Civil

### Motor de Escadas — Escopo Implementado

Dimensionamento completo de **escadas retas de um único lance** conforme NBR 6118/6120.

#### Geometria

- Entradas: desnível total (H), espelho (e), piso (p), largura, espessura da laje
- Cálculo automático: número de espelhos, pisos, comprimento horizontal real
- **Fórmula de Blondel**: `60 ≤ 2e + p ≤ 64 cm` — implementada com alerta visual de conformidade
- `cos(α)` calculado para conversão correta de cargas na projeção horizontal

#### Carregamentos (NBR 6120)

| Carga | Tratamento |
|---|---|
| Peso próprio | Considera geometria inclinada: `h_média = h_inclinada + e/2` |
| Revestimentos | Entrada livre em kN/m² |
| Guarda-corpo | Conversão de carga linear para distribuída por largura |
| Variável (privativo) | 2,5 kN/m² |
| Variável (uso público) | 3,0 kN/m² |
| **Combinação ELU** | `pd = 1,4g + 1,4q` — Combinação Normal |

#### Modelos Estruturais Disponíveis

| Tipologia | M (vão) | V |
|---|---|---|
| Bi-apoiada | `qL²/8` | `qL/2` |
| Apoiada transversalmente | Span efetivo reduzido | — |
| Balanço (consolo) | `-qL²/2` | `qL` |

#### Dimensionamento à Flexão (ELU — NBR 6118)

- Cálculo de `d_útil` com desconto de cobrimento e raio da barra
- Método dos coeficientes (Kmd, Kx, z)
- Verificação `Kmd ≤ 0,32` para seção simplesmente armada
- Armadura mínima: `As,min = 0,0015 × b × h` (NBR 6118 item 17.3)
- Armadura de distribuição: `As,dist = max(As/5 ; 0,90 cm²/m)`

#### Verificação ao Cisalhamento

Implementa `VRd1` conforme NBR 6118 com fator `Kx` dependente de `d` e taxa de armadura. Alerta quando `Vd > VRd1` com recomendação de aumento de seção.

#### Detalhe Crítico: Empuxo ao Vazio

O módulo documenta e alerta sobre o detalhe de empuxo ao vazio na transição laje/escada — regra de detalhamento crítica para evitar fissuras de tração no nó de apoio. Demonstra domínio técnico além do cálculo numérico básico.

### Avaliação Técnica

O módulo é **tecnicamente correto e adequado para uso em projetos reais de escadas retas simples**. Acerta nos pontos críticos:

- Não simplifica a geometria inclinada
- Respeita os limites de norma com feedback visual
- Cobre as 3 tipologias estruturais de maior ocorrência em projetos
- A progressão por abas (Geometria → Cargas → Esforços → Dimensionamento) corresponde ao fluxo real de cálculo estrutural

### Limitações Atuais (por escopo)

- Apenas escadas retas de um lance (sem L, U ou helicoidal)
- Sem detalhamento de estribos (cisalhamento sem armadura transversal)
- Sem análise de torção para consolo com apoio lateral
- Sem verificação no ELS (estado limite de serviço: fissuras e deformações)

### Roadmap Técnico de Engenharia

| Módulo | Complexidade | Norma de Referência | Prioridade |
|---|---|---|---|
| Escadas em L e U | Média-alta | NBR 6118 | Alta |
| Reservatório | Média | NBR 6118 | Alta |
| Vigas | Média | NBR 6118 | Média |
| Lajes maciças/nervuradas | Média-alta | NBR 6118 | Média |
| Pilares (flambagem) | Alta | NBR 6118 item 15 | Baixa |
| Fundações | Alta | NBR 6122 | Baixa |

---

## Estado Atual e Direção

### Onde está

MVP funcional completo para visualização (PDF, DXF, IFC) com um módulo de dimensionamento estrutural correto (escadas retas). Base sólida de arquitetura pronta para escalar.

### Próximos passos técnicos recomendados

1. **Testes para `escadas.py`** — módulo mais crítico sem cobertura
2. **Integrar ou remover `exceptions.py`** — está definido mas não usado
3. **Escadas em L/U** — extensão natural com maior relevância em projetos reais
4. **Reservatório** — próximo módulo mais simples de implementar
5. **Merge `estrutural` → `main`** — código maduro para produção

### Próximos passos de produto

- Geração de relatório PDF com memória de cálculo (saída profissional para engenheiros)
- Autenticação de usuários para modelo SaaS multiusuário
- Ferramentas de medição sobre DXF/PDF (distância, área)
- Verificações no ELS (fissuras e deformações) para os módulos estruturais

---

## Resumo Executivo

**Software**: projeto bem arquitetado, código limpo, padrões corretos de gestão de estado e recursos, documentação completa. Os problemas existentes são menores e de fácil correção. Pronto para escalar.

**Engenharia Civil**: o módulo de escadas implementa o dimensionamento conforme NBR 6118/6120 de forma tecnicamente correta, com as 3 tipologias estruturais mais comuns, verificações de norma e alertas de detalhe crítico. Adequado para uso em projetos reais de escadas retas simples.

---

*Para atualizar este documento: revisar o status de cada módulo, atualizar o histórico git com novos marcos, e ajustar o roadmap conforme o que foi entregue.*
