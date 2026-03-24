import streamlit as st
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


# ── Funções auxiliares de dimensionamento ─────────────────────────────────────

def calcular_armadura_flexao(md, bw, d, fck, fyk=500):
    """Cálculo da armadura de flexão simples (seção retangular) — NBR 6118:2014."""
    fcd = 0.85 * (fck / 10) / 1.4   # kN/cm²
    fyd = (fyk / 10) / 1.15          # kN/cm²
    kmd = md / (bw * (d ** 2) * fcd)
    if kmd > 0.295:
        return None
    kx = 1.25 * (1 - math.sqrt(1 - 2 * kmd))
    z = d * (1 - 0.4 * kx)
    As = md / (z * fyd)
    return As


def verificar_cisalhamento(vd, bw, d, fck, as_efetiva):
    """Verificação de cisalhamento sem estribos — NBR 6118:2014 §19.4.1."""
    fctm = 0.3 * (fck ** (2 / 3))
    fctk_inf = 0.7 * fctm
    fctd = fctk_inf / 1.4
    rho = min(as_efetiva / (bw * d), 0.02)
    tau_rd = 0.25 * fctd
    tau_rd_kncm2 = tau_rd / 10
    d_m = d / 100.0
    k = max(1.6 - d_m, 1.0)
    t_rd = tau_rd_kncm2 * k * (1.2 + 40 * rho)
    vr1 = t_rd * bw * d
    status = "OK" if vd <= vr1 else "FALHA"
    return vr1, status


# ── Funções de plotagem ──────────────────────────────────────────────────────

def plot_corte_transversal(Lx, hw, ep, ef, et, nivel_agua=None):
    """Corte transversal do reservatório (vista frontal)."""
    fig = go.Figure()
    if nivel_agua is None:
        nivel_agua = hw

    # Dimensões totais externas
    L_ext = Lx + 2 * ep
    H_ext = ef + hw + et

    # Laje de fundo
    fig.add_trace(go.Scatter(
        x=[0, L_ext, L_ext, 0, 0],
        y=[0, 0, ef, ef, 0],
        fill='toself', fillcolor='rgba(150,150,150,0.5)',
        mode='lines', line=dict(color='black', width=2), name='Laje de Fundo'
    ))

    # Parede esquerda
    fig.add_trace(go.Scatter(
        x=[0, ep, ep, 0, 0],
        y=[ef, ef, ef + hw, ef + hw, ef],
        fill='toself', fillcolor='rgba(180,180,180,0.4)',
        mode='lines', line=dict(color='black', width=2), name='Parede'
    ))

    # Parede direita
    fig.add_trace(go.Scatter(
        x=[L_ext - ep, L_ext, L_ext, L_ext - ep, L_ext - ep],
        y=[ef, ef, ef + hw, ef + hw, ef],
        fill='toself', fillcolor='rgba(180,180,180,0.4)',
        mode='lines', line=dict(color='black', width=2), showlegend=False
    ))

    # Laje de tampa
    fig.add_trace(go.Scatter(
        x=[0, L_ext, L_ext, 0, 0],
        y=[ef + hw, ef + hw, H_ext, H_ext, ef + hw],
        fill='toself', fillcolor='rgba(150,150,150,0.5)',
        mode='lines', line=dict(color='black', width=2), name='Laje de Tampa'
    ))

    # Nível d'água
    if nivel_agua > 0:
        y_agua = ef + nivel_agua
        fig.add_trace(go.Scatter(
            x=[ep, L_ext - ep, L_ext - ep, ep, ep],
            y=[ef, ef, y_agua, y_agua, ef],
            fill='toself', fillcolor='rgba(30,144,255,0.25)',
            mode='lines', line=dict(color='dodgerblue', width=1, dash='dot'),
            name=f'Água (h={nivel_agua:.0f} cm)'
        ))

    # Cotas
    fig.add_annotation(x=L_ext / 2, y=-8, text=f"Lx = {Lx:.0f} cm (int.)",
                       showarrow=False, font=dict(size=10, color='navy'))
    fig.add_annotation(x=L_ext + 8, y=ef + hw / 2, text=f"hw = {hw:.0f} cm",
                       showarrow=False, textangle=-90, font=dict(size=10, color='navy'))
    fig.add_annotation(x=-8, y=ef / 2, text=f"ef = {ef:.0f}",
                       showarrow=False, font=dict(size=9, color='gray'))
    fig.add_annotation(x=-8, y=ef + hw + et / 2, text=f"et = {et:.0f}",
                       showarrow=False, font=dict(size=9, color='gray'))
    fig.add_annotation(x=ep / 2, y=ef + hw / 2, text=f"ep={ep:.0f}",
                       showarrow=False, font=dict(size=8, color='gray'), textangle=-90)

    fig.update_layout(
        title="Corte Transversal do Reservatório",
        xaxis_title="Comprimento (cm)", yaxis_title="Altura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=40, r=40, t=40, b=40), height=400, showlegend=True
    )
    return fig


def plot_planta(Lx, Ly, ep):
    """Vista superior (planta) do reservatório."""
    fig = go.Figure()
    L_ext_x = Lx + 2 * ep
    L_ext_y = Ly + 2 * ep

    # Contorno externo
    fig.add_trace(go.Scatter(
        x=[0, L_ext_x, L_ext_x, 0, 0],
        y=[0, 0, L_ext_y, L_ext_y, 0],
        mode='lines', line=dict(color='black', width=3),
        fill='toself', fillcolor='rgba(180,180,180,0.2)', name='Contorno externo'
    ))

    # Contorno interno
    fig.add_trace(go.Scatter(
        x=[ep, Lx + ep, Lx + ep, ep, ep],
        y=[ep, ep, Ly + ep, Ly + ep, ep],
        mode='lines', line=dict(color='blue', width=2, dash='dash'),
        fill='toself', fillcolor='rgba(30,144,255,0.15)', name='Volume interno (água)'
    ))

    # Cotas internas
    fig.add_annotation(x=(Lx + 2 * ep) / 2, y=-10, text=f"Lx = {Lx:.0f} cm",
                       showarrow=False, font=dict(size=11, color='navy'))
    fig.add_annotation(x=-10, y=(Ly + 2 * ep) / 2, text=f"Ly = {Ly:.0f} cm",
                       showarrow=False, textangle=-90, font=dict(size=11, color='navy'))
    fig.add_annotation(x=ep / 2, y=L_ext_y / 2, text=f"ep={ep:.0f}",
                       showarrow=False, font=dict(size=8, color='gray'), textangle=-90)

    fig.update_layout(
        title="Vista Superior (Planta)",
        xaxis_title="(cm)", yaxis_title="(cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=40, r=40, t=40, b=40), height=350, showlegend=True
    )
    return fig


def plot_pressao_hidrostatica(hw_m, gamma_w=10.0):
    """Diagrama de pressão hidrostática na parede."""
    fig = go.Figure()
    p_max = gamma_w * hw_m  # kN/m²

    # Eixo da parede
    fig.add_trace(go.Scatter(
        x=[0, 0], y=[0, hw_m], mode='lines',
        line=dict(color='black', width=4), name='Parede'
    ))

    # Diagrama triangular de pressão
    fig.add_trace(go.Scatter(
        x=[0, p_max, 0], y=[0, hw_m, hw_m],
        fill='toself', fillcolor='rgba(30,144,255,0.3)',
        mode='lines', line=dict(color='dodgerblue', width=2),
        name='Pressão hidrostática'
    ))

    # Setas de pressão
    n_setas = 8
    for i in range(1, n_setas + 1):
        y_s = i * hw_m / n_setas
        p_s = gamma_w * y_s
        fig.add_annotation(
            x=0, y=y_s, ax=p_s, ay=y_s,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.5,
            arrowwidth=1.5, arrowcolor="dodgerblue"
        )

    fig.add_annotation(x=p_max / 2, y=hw_m + 0.08,
                       text=f"p_max = γw·hw = {gamma_w:.0f}×{hw_m:.2f} = {p_max:.2f} kN/m²",
                       showarrow=False, font=dict(size=11, color='navy'))
    fig.add_annotation(x=-0.5, y=hw_m / 2, text="hw",
                       showarrow=False, font=dict(size=11), textangle=-90)

    fig.update_layout(
        title="Pressão Hidrostática na Parede (γw = 10 kN/m³)",
        xaxis_title="Pressão (kN/m²)", yaxis_title="Profundidade (m)",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=40, r=40, t=40, b=40), height=350, showlegend=False
    )
    return fig


def plot_esforcos_parede(hw_m, gamma_w=10.0, gamma_f=1.4):
    """Diagramas de momento fletor e cortante na parede (modelo cantilever)."""
    y = np.linspace(0, hw_m, 100)
    # Modelo: parede em balanço — engastada na base, livre no topo
    # y medido do topo para baixo
    M = gamma_f * gamma_w * y**3 / 6   # kN·m/m
    V = gamma_f * gamma_w * y**2 / 2   # kN/m

    M_max = M[-1]
    V_max = V[-1]

    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        f"Momento Fletor — Máx: {M_max:.2f} kN·m/m",
        f"Esforço Cortante — Máx: {V_max:.2f} kN/m"
    ))

    fig.add_trace(go.Scatter(
        x=M, y=y, fill='tozerox', mode='lines',
        line=dict(color='blue'), name='M(y)'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=V, y=y, fill='tozerox', mode='lines',
        line=dict(color='green'), name='V(y)'
    ), row=1, col=2)

    fig.update_yaxes(autorange="reversed", title_text="Profundidade (m)", row=1, col=1)
    fig.update_yaxes(autorange="reversed", title_text="Profundidade (m)", row=1, col=2)
    fig.update_xaxes(title_text="M (kN·m/m)", row=1, col=1)
    fig.update_xaxes(title_text="V (kN/m)", row=1, col=2)

    fig.update_layout(height=400, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_esforcos_laje(Lx_m, Ly_m, pd, nome="Laje"):
    """Diagrama de momentos fletores na laje (Marcus simplificado)."""
    fig = go.Figure()

    lam = Ly_m / Lx_m if Ly_m >= Lx_m else Lx_m / Ly_m
    if lam > 2.0:
        # Laje armada em uma direção
        M_unico = pd * min(Lx_m, Ly_m)**2 / 8
        x = np.linspace(0, min(Lx_m, Ly_m), 100)
        M = (pd * min(Lx_m, Ly_m) * x / 2) - (pd * x**2 / 2)
        fig.add_trace(go.Scatter(x=x, y=M, fill='tozeroy', mode='lines',
                                 line=dict(color='blue'),
                                 name=f'M (dir. curta) — Máx: {M_unico:.2f} kN·m/m'))
    else:
        # Marcus: distribuição proporcional de cargas
        px = pd * Ly_m**4 / (Lx_m**4 + Ly_m**4)
        py = pd * Lx_m**4 / (Lx_m**4 + Ly_m**4)
        Mx = px * Lx_m**2 / 8
        My = py * Ly_m**2 / 8

        x = np.linspace(0, Lx_m, 100)
        Mx_dist = (px * Lx_m * x / 2) - (px * x**2 / 2)
        fig.add_trace(go.Scatter(x=x, y=Mx_dist, fill='tozeroy', mode='lines',
                                 line=dict(color='blue'),
                                 name=f'Mx — Máx: {Mx:.2f} kN·m/m'))

        x2 = np.linspace(0, Ly_m, 100)
        My_dist = (py * Ly_m * x2 / 2) - (py * x2**2 / 2)
        fig.add_trace(go.Scatter(x=x2, y=My_dist, fill='tozeroy', mode='lines',
                                 line=dict(color='red'),
                                 name=f'My — Máx: {My:.2f} kN·m/m'))

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        title=f"Momentos Fletores — {nome} (apoiada em 4 bordas)",
        xaxis_title="Vão (m)", yaxis_title="M (kN·m/m)",
        height=350, margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def plot_3d_reservatorio(Lx, Ly, hw, ep, ef, et, opacidade=0.7):
    """Modelo 3D interativo do reservatório."""
    traces = []
    BOX_I = [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1]
    BOX_J = [1, 2, 6, 7, 4, 5, 6, 7, 3, 7, 5, 6]
    BOX_K = [2, 3, 5, 6, 5, 1, 7, 3, 7, 4, 6, 2]

    L_ext_x = Lx + 2 * ep
    L_ext_y = Ly + 2 * ep

    def add_box(x0, x1, y0, y1, z0, z1, cor, nome):
        xs = [x0, x1, x1, x0, x0, x1, x1, x0]
        ys = [y0, y0, y1, y1, y0, y0, y1, y1]
        zs = [z0] * 4 + [z1] * 4
        traces.append(go.Mesh3d(
            x=xs, y=ys, z=zs,
            i=BOX_I, j=BOX_J, k=BOX_K,
            color=cor, opacity=opacidade, flatshading=False,
            showscale=False, hoverinfo='text', hovertext=nome, name=nome
        ))

    # Laje de fundo
    add_box(0, L_ext_x, 0, L_ext_y, 0, ef, '#4a5560', 'Laje de Fundo')

    # Paredes
    add_box(0, ep, 0, L_ext_y, ef, ef + hw, '#7a8d9c', 'Parede Lx esq.')
    add_box(Lx + ep, L_ext_x, 0, L_ext_y, ef, ef + hw, '#7a8d9c', 'Parede Lx dir.')
    add_box(ep, Lx + ep, 0, ep, ef, ef + hw, '#5e7080', 'Parede Ly frontal')
    add_box(ep, Lx + ep, Ly + ep, L_ext_y, ef, ef + hw, '#5e7080', 'Parede Ly posterior')

    # Laje de tampa
    add_box(0, L_ext_x, 0, L_ext_y, ef + hw, ef + hw + et, '#4a5560', 'Laje de Tampa')

    # Água
    traces.append(go.Mesh3d(
        x=[ep, Lx + ep, Lx + ep, ep, ep, Lx + ep, Lx + ep, ep],
        y=[ep, ep, Ly + ep, Ly + ep, ep, ep, Ly + ep, Ly + ep],
        z=[ef] * 4 + [ef + hw * 0.9] * 4,
        i=BOX_I, j=BOX_J, k=BOX_K,
        color='dodgerblue', opacity=0.15, flatshading=False,
        showscale=False, hoverinfo='text', hovertext='Água', name='Água'
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        paper_bgcolor='#0e1117',
        scene=dict(
            bgcolor='#0e1117',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode='data',
            camera=dict(
                eye=dict(x=-1.6, y=-1.8, z=1.0),
                up=dict(x=0, y=0, z=1)
            )
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500, showlegend=False
    )
    return fig


def plot_detalhamento_parede(ep, cobrimento, phi_mm, phi_dist_mm, n_p, s_p, n_d, s_d):
    """Seção transversal da parede com posicionamento das armaduras."""
    fig = go.Figure()
    h = ep

    # Seção de concreto (largura 100 cm por metro de parede)
    fig.add_trace(go.Scatter(
        x=[0, 100, 100, 0, 0], y=[0, 0, h, h, 0],
        fill='toself', fillcolor='rgba(200,200,200,0.4)',
        mode='lines', line=dict(color='black', width=2), name='Concreto'
    ))

    # Linhas de cobrimento
    for yc in [cobrimento, h - cobrimento]:
        fig.add_shape(type="line", x0=0, x1=100, y0=yc, y1=yc,
                      line=dict(color='orange', width=1, dash='dot'))

    # Face interna (em contato com água) — armadura principal (tração)
    r_p = cobrimento + phi_mm / 20
    r_d = r_p + phi_mm / 10 + phi_dist_mm / 20

    # Barras principais (face interna — pressão da água empurra para fora)
    x_p = np.linspace(s_p / 2, 100 - s_p / 2, num=min(n_p, 30))
    fig.add_trace(go.Scatter(
        x=x_p, y=[r_p] * len(x_p), mode='markers',
        marker=dict(color='red', size=max(6, phi_mm * 0.5), symbol='circle'),
        name=f'Vertical: φ{phi_mm:.1f} c/{s_p:.1f}cm'
    ))

    # Barras de distribuição (horizontal)
    x_d = np.linspace(s_d / 2, 100 - s_d / 2, num=min(n_d, 30))
    fig.add_trace(go.Scatter(
        x=x_d, y=[r_d] * len(x_d), mode='markers',
        marker=dict(color='blue', size=max(5, phi_dist_mm * 0.5), symbol='circle'),
        name=f'Horizontal: φ{phi_dist_mm:.1f} c/{s_d:.1f}cm'
    ))

    fig.add_annotation(x=106, y=h / 2, text=f"ep = {h:.0f} cm",
                       showarrow=False, font=dict(size=10), xanchor='left')
    fig.add_annotation(x=-5, y=cobrimento / 2, text=f"c = {cobrimento:.1f}",
                       showarrow=False, font=dict(size=9, color='orange'), xanchor='right')

    fig.update_layout(
        title="Seção Transversal da Parede (b = 100 cm/m)",
        xaxis_title="Largura (cm)", yaxis_title="Espessura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1, range=[-2, h + 3]),
        xaxis=dict(range=[-15, 115]),
        margin=dict(l=50, r=70, t=40, b=20), height=300, showlegend=True
    )
    return fig


# ── Função principal ─────────────────────────────────────────────────────────

def show():
    st.header("Dimensionamento de Reservatórios — Projeto Completo", divider="blue")

    st.info("""
    **NOTA TÉCNICA E ESCOPO:**
    1. O dimensionamento abrange **reservatórios retangulares superiores** (caixas d'água elevadas),
       o tipo mais comum em edificações residenciais e comerciais de pequeno/médio porte.
    2. As paredes são modeladas como **lajes verticais em balanço** (engastadas na base, livres no topo)
       sob pressão hidrostática triangular — modelo conservador e amplamente aceito na prática brasileira.
    3. As lajes de fundo e tampa são calculadas pelo **Método de Marcus** (distribuição de cargas em 2 direções).
    """)

    tab_geo, tab_cargas, tab_esforcos, tab_armaduras, tab_geral = st.tabs([
        "1. Geometria",
        "2. Carregamentos",
        "3. Esforços",
        "4. Dimensionamento",
        "5. Visão Geral"
    ])

    # ── Inicialização do session_state ────────────────────────────────────────
    defaults = {
        'res_Lx': 200.0, 'res_Ly': 150.0, 'res_hw': 100.0,
        'res_ep': 10.0, 'res_ef': 10.0, 'res_et': 8.0,
        'res_pd_parede': 0.0, 'res_Md_parede': 0.0, 'res_Vd_parede': 0.0,
        'res_pd_fundo': 0.0, 'res_Mx_fundo': 0.0, 'res_My_fundo': 0.0,
        'res_pd_tampa': 0.0, 'res_Mx_tampa': 0.0, 'res_My_tampa': 0.0,
        'res_As_parede': 0.0, 'res_As_fundo': 0.0, 'res_As_tampa': 0.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ═════════════════════════════════════════════════════════════════════════
    #  ABA 1 — GEOMETRIA
    # ═════════════════════════════════════════════════════════════════════════
    with tab_geo:
        st.subheader("Parâmetros Geométricos do Reservatório")

        col1, col2 = st.columns(2)
        with col1:
            Lx = st.number_input("Dim. interna Lx [cm]:", min_value=50.0,
                                 value=st.session_state.res_Lx, step=10.0,
                                 help="Dimensão interna na direção X")
            Ly = st.number_input("Dim. interna Ly [cm]:", min_value=50.0,
                                 value=st.session_state.res_Ly, step=10.0,
                                 help="Dimensão interna na direção Y")
            hw = st.number_input("Altura da lâmina d'água (hw) [cm]:", min_value=30.0,
                                 max_value=300.0, value=st.session_state.res_hw, step=5.0)
        with col2:
            ep = st.number_input("Espessura das paredes (ep) [cm]:", min_value=7.0,
                                 max_value=30.0, value=st.session_state.res_ep, step=1.0)
            ef = st.number_input("Espessura da laje de fundo (ef) [cm]:", min_value=8.0,
                                 max_value=30.0, value=st.session_state.res_ef, step=1.0)
            et = st.number_input("Espessura da laje de tampa (et) [cm]:", min_value=7.0,
                                 max_value=25.0, value=st.session_state.res_et, step=1.0)

        st.session_state.res_Lx = Lx
        st.session_state.res_Ly = Ly
        st.session_state.res_hw = hw
        st.session_state.res_ep = ep
        st.session_state.res_ef = ef
        st.session_state.res_et = et

        # Volume e capacidade
        vol_cm3 = Lx * Ly * hw
        vol_litros = vol_cm3 / 1000.0
        vol_m3 = vol_cm3 / 1e6

        # Relação λ (para Marcus)
        Lx_m = Lx / 100.0
        Ly_m = Ly / 100.0
        hw_m = hw / 100.0
        lam = max(Lx_m, Ly_m) / min(Lx_m, Ly_m)

        st.markdown("### Resumo Geométrico")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Volume", f"{vol_litros:.0f} L")
        c2.metric("Volume", f"{vol_m3:.2f} m³")
        c3.metric("λ = Lmáx/Lmín", f"{lam:.2f}")
        c4.metric("Tipo de laje", "2 dir." if lam <= 2.0 else "1 dir.")

        # Pré-dimensionamento
        st.markdown("### Verificações de Pré-dimensionamento")
        L_min = min(Lx, Ly)

        ep_min = max(7.0, hw / 10.0)
        ef_min = max(8.0, L_min / 35.0)
        et_min = max(7.0, L_min / 40.0)

        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            if ep >= ep_min:
                st.success(f"ep = {ep:.0f} cm ≥ {ep_min:.1f} cm ✓")
            else:
                st.warning(f"ep = {ep:.0f} cm < {ep_min:.1f} cm — considere aumentar")
        with col_v2:
            if ef >= ef_min:
                st.success(f"ef = {ef:.0f} cm ≥ {ef_min:.1f} cm ✓")
            else:
                st.warning(f"ef = {ef:.0f} cm < {ef_min:.1f} cm — considere aumentar")
        with col_v3:
            if et >= et_min:
                st.success(f"et = {et:.0f} cm ≥ {et_min:.1f} cm ✓")
            else:
                st.warning(f"et = {et:.0f} cm < {et_min:.1f} cm — considere aumentar")

        # Visualizações
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.plotly_chart(plot_planta(Lx, Ly, ep), use_container_width=True)
        with col_p2:
            st.plotly_chart(plot_corte_transversal(Lx, hw, ep, ef, et),
                            use_container_width=True)

        # Memória de cálculo
        with st.expander("📋 Memória de Cálculo — Geometria", expanded=True):
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("**① Volume útil**")
                st.latex(f"V = L_x \\times L_y \\times h_w")
                st.latex(
                    f"V = {Lx:.0f} \\times {Ly:.0f} \\times {hw:.0f}"
                    f" = {vol_cm3:.0f} \\; \\mathrm{{cm^3}}"
                    f" = {vol_litros:.0f} \\; \\mathrm{{L}}"
                )
                st.markdown("**② Relação entre lados (para análise das lajes)**")
                st.latex(
                    f"\\lambda = \\frac{{L_{{max}}}}{{L_{{min}}}}"
                    f" = \\frac{{{max(Lx, Ly):.0f}}}{{{min(Lx, Ly):.0f}}}"
                    f" = {lam:.3f}"
                )
                if lam <= 2.0:
                    st.success("λ ≤ 2,0 → Laje armada em duas direções (Marcus)")
                else:
                    st.warning("λ > 2,0 → Laje armada em uma direção (faixa curta)")

            with col_g2:
                st.markdown("**③ Pré-dimensionamento das espessuras**")
                st.latex(f"e_p \\geq \\max(7\\,\\mathrm{{cm}},\\; h_w/10) = \\max(7,\\; {hw/10:.1f}) = {ep_min:.1f}\\;\\mathrm{{cm}}")
                st.latex(f"e_f \\geq \\max(8\\,\\mathrm{{cm}},\\; L_{{min}}/35) = \\max(8,\\; {L_min/35:.1f}) = {ef_min:.1f}\\;\\mathrm{{cm}}")
                st.latex(f"e_t \\geq \\max(7\\,\\mathrm{{cm}},\\; L_{{min}}/40) = \\max(7,\\; {L_min/40:.1f}) = {et_min:.1f}\\;\\mathrm{{cm}}")

                st.markdown("**Quadro dimensional:**")
                st.dataframe([
                    {"Parâmetro": "Lx (interna)", "Valor": f"{Lx:.0f} cm"},
                    {"Parâmetro": "Ly (interna)", "Valor": f"{Ly:.0f} cm"},
                    {"Parâmetro": "hw (lâmina)", "Valor": f"{hw:.0f} cm"},
                    {"Parâmetro": "ep (paredes)", "Valor": f"{ep:.0f} cm"},
                    {"Parâmetro": "ef (fundo)", "Valor": f"{ef:.0f} cm"},
                    {"Parâmetro": "et (tampa)", "Valor": f"{et:.0f} cm"},
                    {"Parâmetro": "Volume", "Valor": f"{vol_litros:.0f} L ({vol_m3:.2f} m³)"},
                    {"Parâmetro": "λ (Lmáx/Lmín)", "Valor": f"{lam:.3f}"},
                ], use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════════════
    #  ABA 2 — CARREGAMENTOS
    # ═════════════════════════════════════════════════════════════════════════
    with tab_cargas:
        st.subheader("Levantamento de Ações (kN/m²)")

        Lx = st.session_state.res_Lx
        Ly = st.session_state.res_Ly
        hw = st.session_state.res_hw
        ep = st.session_state.res_ep
        ef = st.session_state.res_ef
        et = st.session_state.res_et
        hw_m = hw / 100.0

        gamma_w = 10.0   # kN/m³
        gamma_c = 25.0   # kN/m³

        st.markdown("#### Paredes — Pressão Hidrostática")
        p_max = gamma_w * hw_m
        st.info(f"Pressão máxima na base: **p_max = γw × hw = {gamma_w:.0f} × {hw_m:.2f} = {p_max:.2f} kN/m²**")
        st.plotly_chart(plot_pressao_hidrostatica(hw_m, gamma_w), use_container_width=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Laje de Fundo — Permanentes (g)")
            pp_fundo = gamma_c * ef / 100.0
            peso_agua = gamma_w * hw_m
            revest_fundo = st.number_input("Revestimento do fundo [kN/m²]:", min_value=0.0,
                                           value=0.5, step=0.1, key="revest_fundo")
            g_fundo = pp_fundo + peso_agua + revest_fundo
            st.write(f"Peso próprio: {pp_fundo:.2f} kN/m²")
            st.write(f"Peso da água: {peso_agua:.2f} kN/m²")
            st.metric("Total g (fundo)", f"{g_fundo:.2f} kN/m²")

            pd_fundo = 1.4 * g_fundo
            st.session_state.res_pd_fundo = pd_fundo
            st.success(f"**pd (fundo, ELU) = 1,4 × {g_fundo:.2f} = {pd_fundo:.2f} kN/m²**")

        with col2:
            st.markdown("#### Laje de Tampa — Permanentes + Variáveis")
            pp_tampa = gamma_c * et / 100.0
            imp_tampa = st.number_input("Impermeabilização/Isolamento [kN/m²]:", min_value=0.0,
                                        value=1.0, step=0.1, key="imp_tampa")
            q_tampa = st.number_input("Sobrecarga de manutenção (q) [kN/m²]:", min_value=0.0,
                                      value=0.5, step=0.1, key="q_tampa",
                                      help="NBR 6120 — carga acidental para coberturas/reservatórios inacessíveis")
            g_tampa = pp_tampa + imp_tampa
            st.write(f"Peso próprio: {pp_tampa:.2f} kN/m²")
            st.metric("Total g (tampa)", f"{g_tampa:.2f} kN/m²")
            st.metric("Total q (tampa)", f"{q_tampa:.2f} kN/m²")

            pd_tampa = 1.4 * g_tampa + 1.4 * q_tampa
            st.session_state.res_pd_tampa = pd_tampa
            st.success(f"**pd (tampa, ELU) = 1,4 × {g_tampa:.2f} + 1,4 × {q_tampa:.2f} = {pd_tampa:.2f} kN/m²**")

        # ELU paredes
        pd_parede_max = 1.4 * p_max
        st.session_state.res_pd_parede = pd_parede_max

        # Memória de cálculo
        with st.expander("📋 Memória de Cálculo — Carregamentos", expanded=True):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("**① Pressão hidrostática nas paredes**")
                st.latex(r"p(y) = \gamma_w \cdot y \quad (\text{triangular, máx na base})")
                st.latex(f"p_{{max}} = {gamma_w:.0f} \\times {hw_m:.2f} = {p_max:.2f} \\; \\mathrm{{kN/m^2}}")
                st.latex(f"p_{{d,max}} = 1{{,}}4 \\times {p_max:.2f} = {pd_parede_max:.2f} \\; \\mathrm{{kN/m^2}}")

                st.markdown("**② Carga na laje de fundo**")
                st.latex(r"g_{fundo} = g_{pp} + g_{água} + g_{rev}")
                st.latex(f"g_{{fundo}} = {pp_fundo:.2f} + {peso_agua:.2f} + {revest_fundo:.2f} = {g_fundo:.2f} \\; \\mathrm{{kN/m^2}}")
                st.latex(f"p_{{d,fundo}} = 1{{,}}4 \\times {g_fundo:.2f} = {pd_fundo:.2f} \\; \\mathrm{{kN/m^2}}")

            with col_c2:
                st.markdown("**③ Carga na laje de tampa**")
                st.latex(r"g_{tampa} = g_{pp} + g_{imp}")
                st.latex(f"g_{{tampa}} = {pp_tampa:.2f} + {imp_tampa:.2f} = {g_tampa:.2f} \\; \\mathrm{{kN/m^2}}")
                st.latex(f"p_{{d,tampa}} = 1{{,}}4 \\times ({g_tampa:.2f} + {q_tampa:.2f}) = {pd_tampa:.2f} \\; \\mathrm{{kN/m^2}}")

                st.markdown("**Quadro de ações:**")
                st.dataframe([
                    {"Elemento": "Parede (base)",      "pd (kN/m²)": f"{pd_parede_max:.2f}"},
                    {"Elemento": "Laje de fundo",      "pd (kN/m²)": f"{pd_fundo:.2f}"},
                    {"Elemento": "Laje de tampa",      "pd (kN/m²)": f"{pd_tampa:.2f}"},
                ], use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════════════
    #  ABA 3 — ESFORÇOS
    # ═════════════════════════════════════════════════════════════════════════
    with tab_esforcos:
        st.subheader("Esforços Solicitantes de Cálculo")

        hw_m = st.session_state.res_hw / 100.0
        Lx_m = st.session_state.res_Lx / 100.0
        Ly_m = st.session_state.res_Ly / 100.0
        gamma_w = 10.0
        gamma_f = 1.4

        # ── PAREDES ──────────────────────────────────────────────────────────
        st.markdown("### Paredes — Modelo em Balanço Vertical")
        st.info("Cada parede é modelada como laje em balanço: engastada na laje de fundo, livre no topo.")

        Md_parede = gamma_f * gamma_w * hw_m**3 / 6   # kN·m/m
        Vd_parede = gamma_f * gamma_w * hw_m**2 / 2   # kN/m

        st.session_state.res_Md_parede = Md_parede
        st.session_state.res_Vd_parede = Vd_parede

        col_ep1, col_ep2 = st.columns(2)
        col_ep1.metric("Md (base da parede)", f"{Md_parede:.3f} kN·m/m")
        col_ep2.metric("Vd (base da parede)", f"{Vd_parede:.3f} kN/m")

        st.plotly_chart(plot_esforcos_parede(hw_m, gamma_w, gamma_f), use_container_width=True)

        # ── LAJES ────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### Lajes — Método de Marcus (Distribuição de Cargas em 2 Direções)")

        lam = max(Lx_m, Ly_m) / min(Lx_m, Ly_m)

        if lam > 2.0:
            st.warning(f"λ = {lam:.2f} > 2,0 — Lajes armadas **em uma direção** (faixa curta: L_min = {min(Lx_m, Ly_m):.2f} m)")
            L_curta = min(Lx_m, Ly_m)

            Mx_fundo = st.session_state.res_pd_fundo * L_curta**2 / 8
            My_fundo = 0.0
            Mx_tampa = st.session_state.res_pd_tampa * L_curta**2 / 8
            My_tampa = 0.0
        else:
            st.success(f"λ = {lam:.2f} ≤ 2,0 — Lajes armadas **em duas direções** (Marcus)")

            pd_f = st.session_state.res_pd_fundo
            px_f = pd_f * Ly_m**4 / (Lx_m**4 + Ly_m**4)
            py_f = pd_f * Lx_m**4 / (Lx_m**4 + Ly_m**4)
            Mx_fundo = px_f * Lx_m**2 / 8
            My_fundo = py_f * Ly_m**2 / 8

            pd_t = st.session_state.res_pd_tampa
            px_t = pd_t * Ly_m**4 / (Lx_m**4 + Ly_m**4)
            py_t = pd_t * Lx_m**4 / (Lx_m**4 + Ly_m**4)
            Mx_tampa = px_t * Lx_m**2 / 8
            My_tampa = py_t * Ly_m**2 / 8

        st.session_state.res_Mx_fundo = Mx_fundo
        st.session_state.res_My_fundo = My_fundo
        st.session_state.res_Mx_tampa = Mx_tampa
        st.session_state.res_My_tampa = My_tampa

        col_l1, col_l2 = st.columns(2)
        with col_l1:
            st.markdown("**Laje de Fundo**")
            st.metric("Mx (fundo)", f"{Mx_fundo:.3f} kN·m/m")
            if My_fundo > 0:
                st.metric("My (fundo)", f"{My_fundo:.3f} kN·m/m")
            st.plotly_chart(
                plot_esforcos_laje(Lx_m, Ly_m, st.session_state.res_pd_fundo, "Laje de Fundo"),
                use_container_width=True
            )

        with col_l2:
            st.markdown("**Laje de Tampa**")
            st.metric("Mx (tampa)", f"{Mx_tampa:.3f} kN·m/m")
            if My_tampa > 0:
                st.metric("My (tampa)", f"{My_tampa:.3f} kN·m/m")
            st.plotly_chart(
                plot_esforcos_laje(Lx_m, Ly_m, st.session_state.res_pd_tampa, "Laje de Tampa"),
                use_container_width=True
            )

        # Memória de cálculo — Esforços
        with st.expander("📋 Memória de Cálculo — Esforços", expanded=True):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.markdown("**① Paredes — Balanço sob carga triangular**")
                st.latex(r"M_d = \frac{\gamma_f \cdot \gamma_w \cdot h_w^3}{6}")
                st.latex(
                    f"M_d = \\frac{{{gamma_f:.1f} \\times {gamma_w:.0f} \\times {hw_m:.2f}^3}}{{6}}"
                    f" = {Md_parede:.4f} \\; \\mathrm{{kN \\cdot m/m}}"
                )
                st.latex(r"V_d = \frac{\gamma_f \cdot \gamma_w \cdot h_w^2}{2}")
                st.latex(
                    f"V_d = \\frac{{{gamma_f:.1f} \\times {gamma_w:.0f} \\times {hw_m:.2f}^2}}{{2}}"
                    f" = {Vd_parede:.4f} \\; \\mathrm{{kN/m}}"
                )

            with col_e2:
                if lam <= 2.0:
                    st.markdown("**② Lajes — Marcus (apoiadas em 4 bordas)**")
                    st.latex(r"p_x = p_d \cdot \frac{L_y^4}{L_x^4 + L_y^4}")
                    st.latex(r"M_x = \frac{p_x \cdot L_x^2}{8} \quad;\quad M_y = \frac{p_y \cdot L_y^2}{8}")
                else:
                    st.markdown("**② Lajes — Unidirecional (λ > 2)**")
                    st.latex(r"M = \frac{p_d \cdot L_{min}^2}{8}")

                st.markdown("**Quadro de esforços:**")
                rows = [
                    {"Elemento": "Parede (Md)", "Valor": f"{Md_parede:.3f} kN·m/m"},
                    {"Elemento": "Parede (Vd)", "Valor": f"{Vd_parede:.3f} kN/m"},
                    {"Elemento": "Laje Fundo (Mx)", "Valor": f"{Mx_fundo:.3f} kN·m/m"},
                ]
                if My_fundo > 0:
                    rows.append({"Elemento": "Laje Fundo (My)", "Valor": f"{My_fundo:.3f} kN·m/m"})
                rows.append({"Elemento": "Laje Tampa (Mx)", "Valor": f"{Mx_tampa:.3f} kN·m/m"})
                if My_tampa > 0:
                    rows.append({"Elemento": "Laje Tampa (My)", "Valor": f"{My_tampa:.3f} kN·m/m"})
                st.dataframe(rows, use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════════════
    #  ABA 4 — DIMENSIONAMENTO
    # ═════════════════════════════════════════════════════════════════════════
    with tab_armaduras:
        st.subheader("Dimensionamento ao ELU")

        col1, col2, col3 = st.columns(3)
        fck = col1.number_input("fck [MPa]:", min_value=20, max_value=50, value=25, step=5,
                                key="res_fck")
        cobrimento_int = col2.number_input("Cobrimento interno (contato c/ água) [cm]:",
                                           min_value=2.0, max_value=5.0, value=2.0, step=0.5,
                                           key="res_cob_int",
                                           help="Face em contato com a água — mínimo 2,0 cm")
        cobrimento_ext = col3.number_input("Cobrimento externo [cm]:",
                                           min_value=2.0, max_value=5.0, value=2.5, step=0.5,
                                           key="res_cob_ext")

        col4, col5 = st.columns(2)
        bitola_p = col4.selectbox("Bitola principal (φ) [mm]:", [8.0, 10.0, 12.5, 16.0], index=1,
                                  key="res_bitola_p")
        bitola_d = col5.selectbox("Bitola distribuição (φ_d) [mm]:", [6.3, 8.0, 10.0], index=0,
                                  key="res_bitola_d")

        ep = st.session_state.res_ep
        ef = st.session_state.res_ef
        et = st.session_state.res_et

        # ── DIMENSIONAMENTO DAS PAREDES ──────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🧱 Paredes")

        d_parede = ep - cobrimento_int - (bitola_p / 20.0)
        Md_parede_cm = st.session_state.res_Md_parede * 100  # kN·cm

        As_parede = calcular_armadura_flexao(Md_parede_cm, 100.0, d_parede, fck)

        if As_parede is None:
            st.error("Parede requer armadura dupla ou aumento de espessura!")
            st.session_state.res_As_parede = 0
        else:
            As_min_parede = 0.0015 * 100.0 * ep
            As_final_parede = max(As_parede, As_min_parede)
            st.session_state.res_As_parede = As_final_parede

            A_phi_p = math.pi * (bitola_p / 10) ** 2 / 4
            n_p = math.ceil(As_final_parede / A_phi_p)
            s_p = round(100.0 / n_p, 1)
            As_adot_p = n_p * A_phi_p

            A_phi_d = math.pi * (bitola_d / 10) ** 2 / 4
            As_dist_parede = max(As_final_parede / 5.0, 0.90)
            n_d = math.ceil(As_dist_parede / A_phi_d)
            s_d = round(100.0 / n_d, 1)
            As_adot_d = n_d * A_phi_d

            s_max_p = min(2.0 * ep, 20.0)
            s_max_d = min(3.0 * ep, 30.0)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.metric("As vertical (parede)", f"{As_final_parede:.2f} cm²/m")
                st.dataframe([
                    {"Item": "d (altura útil)", "Valor": f"{d_parede:.2f} cm"},
                    {"Item": "As,calc", "Valor": f"{As_parede:.3f} cm²/m"},
                    {"Item": "As,min (0,15%)", "Valor": f"{As_min_parede:.3f} cm²/m"},
                    {"Item": "As,final", "Valor": f"{As_final_parede:.3f} cm²/m"},
                    {"Item": f"Adotado: φ{bitola_p:.1f} c/{s_p:.1f}", "Valor": f"{As_adot_p:.3f} cm²/m"},
                    {"Item": "s ≤ s_máx", "Valor": f"{'✅' if s_p <= s_max_p else '❌'} {s_p:.1f} ≤ {s_max_p:.0f} cm"},
                ], use_container_width=True, hide_index=True)

            with col_p2:
                st.metric("As horizontal (parede)", f"{As_dist_parede:.2f} cm²/m")
                st.dataframe([
                    {"Item": "As,dist (mín 20% ou 0,90)", "Valor": f"{As_dist_parede:.3f} cm²/m"},
                    {"Item": f"Adotado: φ{bitola_d:.1f} c/{s_d:.1f}", "Valor": f"{As_adot_d:.3f} cm²/m"},
                    {"Item": "s ≤ s_máx", "Valor": f"{'✅' if s_d <= s_max_d else '❌'} {s_d:.1f} ≤ {s_max_d:.0f} cm"},
                ], use_container_width=True, hide_index=True)

            # Verificação ao cisalhamento
            Vd_par = st.session_state.res_Vd_parede
            vr1_p, status_p = verificar_cisalhamento(Vd_par, 100.0, d_parede, fck, As_final_parede)
            if status_p == "OK":
                st.success(f"Cisalhamento parede: Vsd = {Vd_par:.2f} kN ≤ VR1 = {vr1_p:.2f} kN ✓")
            else:
                st.error(f"Cisalhamento parede: Vsd = {Vd_par:.2f} kN > VR1 = {vr1_p:.2f} kN — FALHA")

            # Detalhamento da seção
            st.plotly_chart(
                plot_detalhamento_parede(ep, cobrimento_int, bitola_p, bitola_d, n_p, s_p, n_d, s_d),
                use_container_width=True
            )

        # ── DIMENSIONAMENTO DA LAJE DE FUNDO ─────────────────────────────────
        st.markdown("---")
        st.markdown("### 🏗️ Laje de Fundo")

        Mx_fundo = st.session_state.res_Mx_fundo
        My_fundo = st.session_state.res_My_fundo
        M_dim_fundo = max(Mx_fundo, My_fundo)

        d_fundo = ef - cobrimento_int - (bitola_p / 20.0)
        Md_fundo_cm = M_dim_fundo * 100

        As_fundo = calcular_armadura_flexao(Md_fundo_cm, 100.0, d_fundo, fck)
        if As_fundo is None:
            st.error("Laje de fundo requer armadura dupla ou aumento de espessura!")
            st.session_state.res_As_fundo = 0
        else:
            As_min_fundo = 0.0015 * 100.0 * ef
            As_final_fundo = max(As_fundo, As_min_fundo)
            st.session_state.res_As_fundo = As_final_fundo

            A_phi_f = math.pi * (bitola_p / 10) ** 2 / 4
            n_f = math.ceil(As_final_fundo / A_phi_f)
            s_f = round(100.0 / n_f, 1)
            As_adot_f = n_f * A_phi_f

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.metric("As (laje de fundo)", f"{As_final_fundo:.2f} cm²/m")
                st.dataframe([
                    {"Item": "d (altura útil)", "Valor": f"{d_fundo:.2f} cm"},
                    {"Item": "M dimensionante", "Valor": f"{M_dim_fundo:.3f} kN·m/m"},
                    {"Item": "As,calc", "Valor": f"{As_fundo:.3f} cm²/m"},
                    {"Item": "As,min", "Valor": f"{As_min_fundo:.3f} cm²/m"},
                    {"Item": "As,final", "Valor": f"{As_final_fundo:.3f} cm²/m"},
                    {"Item": f"φ{bitola_p:.1f} c/{s_f:.1f}", "Valor": f"{As_adot_f:.3f} cm²/m"},
                ], use_container_width=True, hide_index=True)

            with col_f2:
                if My_fundo > 0 and My_fundo != Mx_fundo:
                    M_sec = min(Mx_fundo, My_fundo)
                    Md_sec_cm = M_sec * 100
                    As_sec = calcular_armadura_flexao(Md_sec_cm, 100.0, d_fundo, fck)
                    if As_sec is not None:
                        As_sec_final = max(As_sec, As_min_fundo)
                        n_sec = math.ceil(As_sec_final / A_phi_f)
                        s_sec = round(100.0 / n_sec, 1)
                        st.metric("As (dir. secundária)", f"{As_sec_final:.2f} cm²/m")
                        st.dataframe([
                            {"Item": "M secundário", "Valor": f"{M_sec:.3f} kN·m/m"},
                            {"Item": "As,calc", "Valor": f"{As_sec:.3f} cm²/m"},
                            {"Item": f"φ{bitola_p:.1f} c/{s_sec:.1f}", "Valor": f"{max(As_sec, As_min_fundo):.3f} cm²/m"},
                        ], use_container_width=True, hide_index=True)

        # ── DIMENSIONAMENTO DA LAJE DE TAMPA ─────────────────────────────────
        st.markdown("---")
        st.markdown("### 🔝 Laje de Tampa")

        Mx_tampa = st.session_state.res_Mx_tampa
        My_tampa = st.session_state.res_My_tampa
        M_dim_tampa = max(Mx_tampa, My_tampa)

        d_tampa = et - cobrimento_ext - (bitola_p / 20.0)
        Md_tampa_cm = M_dim_tampa * 100

        As_tampa = calcular_armadura_flexao(Md_tampa_cm, 100.0, d_tampa, fck)
        if As_tampa is None:
            st.error("Laje de tampa requer armadura dupla ou aumento de espessura!")
            st.session_state.res_As_tampa = 0
        else:
            As_min_tampa = 0.0015 * 100.0 * et
            As_final_tampa = max(As_tampa, As_min_tampa)
            st.session_state.res_As_tampa = As_final_tampa

            A_phi_t = math.pi * (bitola_p / 10) ** 2 / 4
            n_t = math.ceil(As_final_tampa / A_phi_t)
            s_t = round(100.0 / n_t, 1)
            As_adot_t = n_t * A_phi_t

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.metric("As (laje de tampa)", f"{As_final_tampa:.2f} cm²/m")
                st.dataframe([
                    {"Item": "d (altura útil)", "Valor": f"{d_tampa:.2f} cm"},
                    {"Item": "M dimensionante", "Valor": f"{M_dim_tampa:.3f} kN·m/m"},
                    {"Item": "As,calc", "Valor": f"{As_tampa:.3f} cm²/m"},
                    {"Item": "As,min", "Valor": f"{As_min_tampa:.3f} cm²/m"},
                    {"Item": "As,final", "Valor": f"{As_final_tampa:.3f} cm²/m"},
                    {"Item": f"φ{bitola_p:.1f} c/{s_t:.1f}", "Valor": f"{As_adot_t:.3f} cm²/m"},
                ], use_container_width=True, hide_index=True)

            with col_t2:
                if My_tampa > 0 and My_tampa != Mx_tampa:
                    M_sec_t = min(Mx_tampa, My_tampa)
                    Md_sec_t_cm = M_sec_t * 100
                    As_sec_t = calcular_armadura_flexao(Md_sec_t_cm, 100.0, d_tampa, fck)
                    if As_sec_t is not None:
                        As_sec_t_final = max(As_sec_t, As_min_tampa)
                        n_sec_t = math.ceil(As_sec_t_final / A_phi_t)
                        s_sec_t = round(100.0 / n_sec_t, 1)
                        st.metric("As (dir. secundária)", f"{As_sec_t_final:.2f} cm²/m")
                        st.dataframe([
                            {"Item": "M secundário", "Valor": f"{M_sec_t:.3f} kN·m/m"},
                            {"Item": "As,calc", "Valor": f"{As_sec_t:.3f} cm²/m"},
                            {"Item": f"φ{bitola_p:.1f} c/{s_sec_t:.1f}", "Valor": f"{max(As_sec_t, As_min_tampa):.3f} cm²/m"},
                        ], use_container_width=True, hide_index=True)

        # ── MEMÓRIA DE CÁLCULO — DIMENSIONAMENTO ─────────────────────────────
        with st.expander("📋 Memória de Dimensionamento — Flexão ELU", expanded=True):
            st.markdown("**Formulação — Seção Retangular (NBR 6118:2014 §17.3)**")
            st.latex(r"f_{cd} = \frac{0{,}85 \cdot f_{ck}}{\gamma_c} \quad;\quad f_{yd} = \frac{f_{yk}}{\gamma_s}")
            st.latex(r"k_{md} = \frac{M_d}{b_w \cdot d^2 \cdot f_{cd}} \quad;\quad k_x = 1{,}25 \cdot (1 - \sqrt{1 - 2 \cdot k_{md}})")
            st.latex(r"z = d \cdot (1 - 0{,}4 \cdot k_x) \quad;\quad A_s = \frac{M_d}{z \cdot f_{yd}}")
            st.latex(r"A_{s,min} = 0{,}0015 \cdot b_w \cdot h \quad (\rho_{min} = 0{,}15\% \text{ para CA-50})")

            st.markdown("**Quadro resumo:**")
            rows_dim = []
            if st.session_state.res_As_parede > 0:
                rows_dim.append({"Elemento": "Parede (vertical)", "As (cm²/m)": f"{st.session_state.res_As_parede:.3f}"})
            if st.session_state.res_As_fundo > 0:
                rows_dim.append({"Elemento": "Laje de Fundo", "As (cm²/m)": f"{st.session_state.res_As_fundo:.3f}"})
            if st.session_state.res_As_tampa > 0:
                rows_dim.append({"Elemento": "Laje de Tampa", "As (cm²/m)": f"{st.session_state.res_As_tampa:.3f}"})
            if rows_dim:
                st.dataframe(rows_dim, use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════════════
    #  ABA 5 — VISÃO GERAL
    # ═════════════════════════════════════════════════════════════════════════
    with tab_geral:
        st.subheader("Visão Geral do Projeto")

        Lx = st.session_state.res_Lx
        Ly = st.session_state.res_Ly
        hw = st.session_state.res_hw
        ep = st.session_state.res_ep
        ef = st.session_state.res_ef
        et = st.session_state.res_et
        vol_litros = Lx * Ly * hw / 1000.0

        st.markdown("#### Modelo Tridimensional Interativo")
        opacidade = st.slider("Transparência do concreto", min_value=0.1, max_value=1.0,
                              value=0.7, step=0.05, key="res_opac_3d",
                              help="Reduza para ver o volume de água interno")
        st.plotly_chart(
            plot_3d_reservatorio(Lx, Ly, hw, ep, ef, et, opacidade=opacidade),
            use_container_width=True
        )

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.plotly_chart(plot_planta(Lx, Ly, ep), use_container_width=True,
                            key="planta_geral")
        with col_v2:
            st.plotly_chart(plot_corte_transversal(Lx, hw, ep, ef, et),
                            use_container_width=True, key="corte_geral")

        st.markdown("---")
        st.markdown("### Resumo de Engenharia")
        st.info(f"""
        **Geometria:** Reservatório retangular superior com dimensões internas
        {Lx:.0f} × {Ly:.0f} × {hw:.0f} cm (Lx × Ly × hw).
        Volume útil: **{vol_litros:.0f} litros** ({vol_litros/1000:.2f} m³).
        Paredes: ep = {ep:.0f} cm | Fundo: ef = {ef:.0f} cm | Tampa: et = {et:.0f} cm.

        **Esforços (ELU):**
        Parede — Md = {st.session_state.res_Md_parede:.3f} kN·m/m |
        Vd = {st.session_state.res_Vd_parede:.3f} kN/m |
        Laje Fundo — Mx = {st.session_state.res_Mx_fundo:.3f} kN·m/m |
        Laje Tampa — Mx = {st.session_state.res_Mx_tampa:.3f} kN·m/m

        **Armaduras:**
        Parede: **{st.session_state.res_As_parede:.2f} cm²/m** |
        Fundo: **{st.session_state.res_As_fundo:.2f} cm²/m** |
        Tampa: **{st.session_state.res_As_tampa:.2f} cm²/m**
        """)
