import streamlit as st
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


def calcular_armadura_flexao(md, bw, d, fck, fyk=500):
    # αc = 0.85 deve ser absorvido em fcd para que a fórmula kx = 1.25*(1-√(1-2*kmd))
    # seja válida (derivada de kmd = 0.8*kx*(1-0.4*kx) com fcd = αc*fck/γc).
    fcd = 0.85 * (fck / 10) / 1.4  # kN/cm²  — αc·fck/γc
    fyd = (fyk / 10) / 1.15         # kN/cm²
    kmd = md / (bw * (d ** 2) * fcd)
    # NBR 6118:2014 limita kx ≤ 0.45 para CA-50 → kmd_max = 0.8*0.45*(1-0.18) ≈ 0.295
    if kmd > 0.295:
        return None
    kx = 1.25 * (1 - math.sqrt(1 - 2 * kmd))
    z = d * (1 - 0.4 * kx)
    As = md / (z * fyd)
    return As


def verificar_cisalhamento(vd, bw, d, fck, as_efetiva):
    """
    Verifica a força cortante resistente de projeto para lajes sem armadura de cisalhamento.
    vd: Esforço cortante de cálculo (kN)
    bw: Largura (cm) - usar 100 cm para lajes
    d: Altura útil (cm)
    fck: fck em MPa
    as_efetiva: Área de aço na seção mais tracionada (cm²)
    Retorna (vr1, status) onde vr1 é a força resistente em kN.
    """
    fctm = 0.3 * (fck ** (2/3))
    fctk_inf = 0.7 * fctm
    fctd = fctk_inf / 1.4
    rho = as_efetiva / (bw * d)
    rho = min(rho, 0.02)
    tau_rd = 0.25 * fctd
    tau_rd_kncm2 = tau_rd / 10
    d_m = d / 100.0
    k = max(1.6 - d_m, 1.0)
    t_rd = tau_rd_kncm2 * k * (1.2 + 40 * rho)
    vr1 = t_rd * bw * d
    status = "OK" if vd <= vr1 else "FALHA"
    return vr1, status


def plot_vista_lateral(p, e, h, n_espelhos, L, H):
    fig = go.Figure()

    x_steps = [0, 0]
    y_steps = [0, e]

    for i in range(n_espelhos - 1):
        x_steps.extend([(i+1)*p, (i+1)*p])
        y_steps.extend([y_steps[-1], y_steps[-1]+e])

    alpha = math.atan(e/p)
    h_vert = h / math.cos(alpha)

    # O intrados deve ser paralelo à inclinação e/p (não H/L).
    y_intrados_direita = (n_espelhos - 1) * e - h_vert  # = L*(e/p) - h_vert

    x_poly = x_steps + [L, 0, 0]
    y_poly = y_steps + [y_intrados_direita, -h_vert, 0]

    fig.add_trace(go.Scatter(
        x=x_poly, y=y_poly,
        fill='toself', fillcolor='rgba(150, 150, 150, 0.4)',
        mode='lines', line=dict(color='black', width=2), name='Elevação'
    ))

    fig.add_annotation(x=L/2, y=-h_vert-10, text=f"Vão Horizontal L = {L:.1f} cm",
                       showarrow=False, font=dict(size=12, color="blue"))
    fig.add_annotation(x=-20, y=H/2, text=f"Desnível H = {H:.1f} cm",
                       showarrow=False, textangle=-90, font=dict(size=12, color="blue"))

    fig.update_layout(
        title=f"Vista Lateral (Elevação) — {n_espelhos} Espelhos",
        xaxis_title="Comprimento (cm)", yaxis_title="Altura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=40, r=40, t=40, b=40), height=400, showlegend=False
    )
    return fig


def plot_vista_superior(p, n_pisos, L, largura):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0, L, L, 0, 0], y=[0, 0, largura, largura, 0],
        mode='lines', line=dict(color='black', width=3),
        fill='toself', fillcolor='rgba(200, 200, 200, 0.2)'
    ))
    for i in range(1, n_pisos):
        fig.add_trace(go.Scatter(
            x=[i*p, i*p], y=[0, largura],
            mode='lines', line=dict(color='black', width=1)
        ))
    fig.add_annotation(
        x=L-10, y=largura/2, ax=10, ay=largura/2,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=2, arrowwidth=2, arrowcolor="red"
    )
    fig.add_annotation(x=L/2, y=largura/2 + 10, text="Sentido de Subida",
                       showarrow=False, font=dict(color="red"))
    fig.add_annotation(x=L/2, y=-15, text=f"Comprimento Total = {L:.1f} cm", showarrow=False)
    fig.add_annotation(x=-15, y=largura/2, text=f"Largura = {largura:.1f} cm",
                       showarrow=False, textangle=-90)
    fig.update_layout(
        title="Vista Superior (Planta)", xaxis_title="Comprimento (cm)", yaxis_title="Largura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=40, r=40, t=40, b=40), height=300, showlegend=False
    )
    return fig


def plot_vista_3d(p, e, h, n_espelhos, largura, L, H):
    """
    Modelo 3D interativo com geometria estruturalmente correta:
    - Laje inclinada contínua (paralelepípedo inclinado)
    - Cada degrau = prisma triangular sentado sobre a laje (sem interseção)
    """
    LUZ     = dict(ambient=0.45, diffuse=0.85, specular=0.25, roughness=0.55, fresnel=0.1)
    LUZ_POS = dict(x=200, y=-300, z=500)
    traces  = []
    n       = n_espelhos

    # ── Índices para paralelepípedo (8 vértices) ───────────────────────────────
    # Vértices 0-3: face "inferior"  |  4-7: face "superior" (mesmo x,y)
    BOX_I = [0, 0,  4, 4,  0, 0,  2, 2,  0, 0,  1, 1]
    BOX_J = [1, 2,  6, 7,  4, 5,  6, 7,  3, 7,  5, 6]
    BOX_K = [2, 3,  5, 6,  5, 1,  7, 3,  7, 4,  6, 2]

    # ── Índices para prisma triangular (6 vértices) ────────────────────────────
    # v0=(x0,0,z0)  v1=(x0,0,z1)  v2=(x1,0,z1)   ← face frontal y=0
    # v3=(x0,L,z0)  v4=(x0,L,z1)  v5=(x1,L,z1)   ← face traseira y=larg
    # Faces: frontal(0,1,2) | traseira(3,5,4) | espelho(0,3,4,1) |
    #        piso(1,4,5,2)  | base inclinada(0,2,5,3)
    PRI_I = [0, 3,  0, 0,  1, 1,  0, 0]
    PRI_J = [1, 5,  3, 4,  4, 5,  2, 5]
    PRI_K = [2, 4,  4, 1,  5, 2,  5, 3]

    # ── Laje inclinada ─────────────────────────────────────────────────────────
    alpha  = math.atan2(e, p)
    h_vert = h / math.cos(alpha)          # espessura projetada verticalmente
    span_x = n * p
    span_z = n * e
    # face superior (toca os degraus): z vai de 0 a span_z linearmente com x
    # face inferior: deslocada h_vert para baixo
    xs_l = [0, span_x, span_x, 0,         0, span_x, span_x, 0      ]
    ys_l = [0, 0,      largura, largura,   0, 0,      largura, largura]
    zs_l = [0, span_z, span_z, 0,         -h_vert, span_z-h_vert, span_z-h_vert, -h_vert]
    traces.append(go.Mesh3d(
        x=xs_l, y=ys_l, z=zs_l,
        i=BOX_I, j=BOX_J, k=BOX_K,
        color='#3d4f5c', flatshading=False,
        lighting=LUZ, lightposition=LUZ_POS,
        showscale=False, hoverinfo='skip', name='Laje'
    ))

    # ── Degraus (prismas triangulares) ─────────────────────────────────────────
    cores = ['#7a8d9c', '#5e7080']
    for step in range(n):
        x0 = step * p;       x1 = (step + 1) * p
        z0 = step * e;       z1 = (step + 1) * e
        # 6 vértices do prisma: v0-v2 lado y=0, v3-v5 lado y=largura
        xs_p = [x0, x0, x1,   x0, x0, x1   ]
        ys_p = [0,  0,  0,    largura, largura, largura]
        zs_p = [z0, z1, z1,   z0, z1, z1   ]
        traces.append(go.Mesh3d(
            x=xs_p, y=ys_p, z=zs_p,
            i=PRI_I, j=PRI_J, k=PRI_K,
            color=cores[step % 2], flatshading=False,
            lighting=LUZ, lightposition=LUZ_POS,
            showscale=False, hoverinfo='skip', name=f'Degrau {step+1}'
        ))

    # ── Piso de saída (laje inferior horizontal) ───────────────────────────────
    # Extensão à esquerda da escada — piso do pavimento inferior
    pad = 2 * p   # comprimento do trecho de piso mostrado

    def slab_horizontal(x0, x1, z_top, espessura, cor, nome):
        """Paralelepípedo horizontal com espessura dada."""
        z_bot = z_top - espessura
        xs = [x0, x1, x1, x0,   x0, x1, x1, x0]
        ys = [0,  0,  largura, largura,   0, 0, largura, largura]
        zs = [z_top]*4 + [z_bot]*4
        return go.Mesh3d(
            x=xs, y=ys, z=zs,
            i=BOX_I, j=BOX_J, k=BOX_K,
            color=cor, flatshading=False,
            lighting=LUZ, lightposition=LUZ_POS,
            showscale=False, hoverinfo='skip', name=nome
        )

    # Piso inferior: nível z=0, mesma espessura vertical da laje inclinada
    traces.append(slab_horizontal(-pad, 0, 0.0, h_vert, '#2e3d4a', 'Piso inferior'))

    # Laje superior: nível z=span_z, mesma espessura vertical da laje inclinada
    traces.append(slab_horizontal(span_x, span_x + pad, span_z, h_vert, '#2e3d4a', 'Laje superior'))

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
                eye=dict(x=-1.4, y=-2.2, z=1.1),
                up=dict(x=0, y=0, z=1)
            )
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=520, showlegend=False
    )
    return fig


def create_plotter_escada_3d(p_cm, e_cm, h_cm, n_espelhos, largura_cm, angulo="Frontal oblíquo"):
    """
    Gera um plotter PyVista com modelo 3D realista da escada.
    p_cm: largura do piso (cm)
    e_cm: altura do espelho (cm)
    h_cm: espessura da laje (cm)
    n_espelhos: número de espelhos (degraus)
    largura_cm: largura transversal da escada (cm)
    angulo: "Frontal oblíquo" | "Lateral" | "Superior"
    """
    import pyvista as pv
    import numpy as np

    pl = pv.Plotter(window_size=[900, 520], off_screen=True)
    pl.background_color = "#0e1117"

    # Converte cm → m para visualização mais natural
    p = p_cm / 100.0
    e = e_cm / 100.0
    h = h_cm / 100.0
    larg = largura_cm / 100.0
    n = n_espelhos

    # Cor do concreto — cinza médio
    cor_degrau  = "#8a9ba8"
    cor_laje    = "#5c6a75"
    cor_piso    = "#4a5560"

    # ── Laje inclinada (intrados) ──────────────────────────────────────────────
    # Vértices da placa inclinada (espessura h na direção perpendicular à rampa)
    alpha = math.atan2(e, p)
    cos_a = math.cos(alpha)
    sin_a = math.sin(alpha)
    dx = h * sin_a   # componente X do vetor normal à rampa
    dz = h * cos_a   # componente Z do vetor normal à rampa (para baixo)

    x0, z0 = 0.0, 0.0
    x1, z1 = n * p, n * e
    # face superior da laje (intrados → tangencia o perfil escalonado)
    pts_top = np.array([
        [x0,    0.0,  z0],
        [x1,    0.0,  z1],
        [x1,   larg,  z1],
        [x0,   larg,  z0],
    ])
    # face inferior (afastada h na normal à rampa)
    pts_bot = pts_top + np.array([dx, 0, -dz])

    laje_faces = np.array([
        [4, 0, 1, 2, 3],  # topo
        [4, 4, 5, 6, 7],  # fundo
        [4, 0, 1, 5, 4],  # front
        [4, 3, 2, 6, 7],  # back
        [4, 0, 3, 7, 4],  # left
        [4, 1, 2, 6, 5],  # right
    ])
    laje_pts = np.vstack([pts_top, pts_bot])
    laje_mesh = pv.PolyData(laje_pts, laje_faces)
    pl.add_mesh(laje_mesh, color=cor_laje, smooth_shading=True,
                specular=0.3, specular_power=15, show_edges=False)

    # ── Degraus (cubóides sobre a laje) ───────────────────────────────────────
    for i in range(n):
        xL = i * p
        xR = xL + p
        zB = i * e        # base do degrau = topo da laje no ponto
        zT = zB + e       # topo do degrau

        verts = np.array([
            [xL, 0.0,  zB], [xR, 0.0,  zB], [xR, larg,  zB], [xL, larg,  zB],  # base
            [xL, 0.0,  zT], [xR, 0.0,  zT], [xR, larg,  zT], [xL, larg,  zT],  # topo
        ])
        faces = np.array([
            [4, 0, 1, 2, 3],   # bottom
            [4, 4, 5, 6, 7],   # top
            [4, 0, 1, 5, 4],   # front
            [4, 3, 2, 6, 7],   # back
            [4, 0, 3, 7, 4],   # left
            [4, 1, 2, 6, 5],   # right
        ])
        step_mesh = pv.PolyData(verts, faces)
        # Alterna tonalidade para profundidade visual
        shade = cor_degrau if i % 2 == 0 else cor_piso
        pl.add_mesh(step_mesh, color=shade, smooth_shading=True,
                    specular=0.5, specular_power=20, show_edges=True,
                    edge_color="#222831", line_width=0.5)

    # ── Iluminação ────────────────────────────────────────────────────────────
    pl.remove_all_lights()
    pl.add_light(pv.Light(
        position=(n * p * 2, -larg * 2, n * e * 3),
        focal_point=(n * p / 2, larg / 2, n * e / 2),
        intensity=1.2, light_type="scene light"
    ))
    pl.add_light(pv.Light(
        position=(-p, larg * 2, n * e * 2),
        focal_point=(n * p / 2, larg / 2, n * e / 2),
        intensity=0.5, light_type="scene light"
    ))

    # ── Câmera por ângulo ─────────────────────────────────────────────────────
    cx = n * p / 2
    cy = larg / 2
    cz = n * e / 2
    dist = max(n * p, n * e, larg) * 2.0

    if angulo == "Lateral":
        pl.camera.position = (cx, cy - dist * 1.8, cz + dist * 0.3)
        pl.camera.focal_point = (cx, cy, cz)
        pl.camera.up = (0, 0, 1)
    elif angulo == "Superior":
        pl.camera.position = (cx, cy, cz + dist * 2.2)
        pl.camera.focal_point = (cx, cy, cz)
        pl.camera.up = (1, 0, 0)
    else:  # Frontal oblíquo (padrão)
        pl.camera.position = (cx - n * p * 0.8, cy - larg * 2.5, cz + n * e * 1.2)
        pl.camera.focal_point = (cx, cy, cz)
        pl.camera.up = (0, 0, 1)

    pl.camera.zoom(0.9)
    return pl


def plot_carregamentos(L, pd):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, L], y=[0, 0], mode='lines',
                             line=dict(color='black', width=4), name='Eixo'))
    x_load = [0, 0, L, L, 0]
    y_load = [0, pd, pd, 0, 0]
    fig.add_trace(go.Scatter(x=x_load, y=y_load, fill='toself',
                             fillcolor='rgba(255, 0, 0, 0.2)', mode='lines',
                             line=dict(color='red', width=1), name='Carga (pd)'))
    for i in np.linspace(0, L, num=10):
        fig.add_annotation(x=i, y=0, ax=i, ay=pd, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="red")
    fig.update_layout(
        title=f"Esquema Estático de Cargas (pd = {pd:.2f} kN/m²)",
        xaxis_title="Vão L (m)", yaxis_title="Carga (kN/m²)",
        yaxis=dict(range=[-pd*0.2, pd*1.2]),
        margin=dict(l=20, r=20, t=40, b=20), height=250
    )
    return fig


def plot_esforcos(L, pd, modelo):
    x = np.linspace(0, L, 100)
    if "Bi-apoiada" in modelo or "Transversalmente" in modelo:
        M = (pd * L * x / 2) - (pd * x**2 / 2)
        V = (pd * L / 2) - (pd * x)
    else:
        M = - (pd * (L - x)**2) / 2
        V = pd * (L - x)
    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        f"Momento Fletor (M) — Máx: {abs(max(M, key=abs)):.2f} kN.m",
        f"Esforço Cortante (V) — Máx: {abs(max(V, key=abs)):.2f} kN"
    ))
    fig.add_trace(go.Scatter(x=x, y=M, fill='tozeroy', mode='lines',
                             line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=V, fill='tozeroy', mode='lines',
                             line=dict(color='green')), row=1, col=2)
    if "Bi-apoiada" in modelo or "Transversalmente" in modelo:
        fig.update_yaxes(autorange="reversed", row=1, col=1)
    fig.update_layout(height=350, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plot_detalhamento(h, cobrimento, modelo, phi_mm, phi_dist_mm, n_p, s_p, n_d, s_d):
    fig = go.Figure()

    is_balanco = "Balanço" in modelo

    # Seção de concreto
    fig.add_trace(go.Scatter(
        x=[0, 100, 100, 0, 0], y=[0, 0, h, h, 0],
        fill='toself', fillcolor='rgba(200,200,200,0.4)',
        mode='lines', line=dict(color='black', width=2), name='Concreto'
    ))

    # Linhas de cobrimento (tracejadas laranja)
    for yc in [cobrimento, h - cobrimento]:
        fig.add_shape(type="line", x0=0, x1=100, y0=yc, y1=yc,
                      line=dict(color='orange', width=1, dash='dot'))

    # Posições das camadas:
    # - principal: junto à face mais tracionada
    # - distribuição: camada imediatamente acima (ou abaixo) da principal
    r_p = cobrimento + phi_mm / 20              # centro da barra principal (face inferior)
    r_d = r_p + phi_mm / 10 + phi_dist_mm / 20  # centro da distribuição, acima
    if is_balanco:
        r_p = h - cobrimento - phi_mm / 20
        r_d = r_p - phi_mm / 10 - phi_dist_mm / 20

    # Barras principais (pontos vermelhos com tamanho proporcional à bitola)
    x_p = np.linspace(s_p / 2, 100 - s_p / 2, num=min(n_p, 30))
    fig.add_trace(go.Scatter(
        x=x_p, y=[r_p] * len(x_p), mode='markers',
        marker=dict(color='red', size=max(6, phi_mm * 0.5), symbol='circle'),
        name=f'Principal: φ{phi_mm:.1f} c/{s_p:.1f}cm'
    ))

    # Barras de distribuição (pontos azuis)
    x_d = np.linspace(s_d / 2, 100 - s_d / 2, num=min(n_d, 30))
    fig.add_trace(go.Scatter(
        x=x_d, y=[r_d] * len(x_d), mode='markers',
        marker=dict(color='blue', size=max(5, phi_dist_mm * 0.5), symbol='circle'),
        name=f'Distribuição: φ{phi_dist_mm:.1f} c/{s_d:.1f}cm'
    ))

    # Cotas laterais (direita): h total
    fig.add_annotation(x=106, y=h / 2, text=f"h = {h:.0f} cm",
                       showarrow=False, font=dict(size=10), xanchor='left')
    # Cota d (altura útil)
    d_plot = r_p if not is_balanco else (h - r_p)
    fig.add_annotation(x=-5, y=r_p / 2, text=f"d = {d_plot:.1f} cm",
                       showarrow=False, font=dict(size=9, color='gray'), xanchor='right')
    # Cota cobrimento
    fig.add_annotation(x=-5, y=cobrimento / 2, text=f"c = {cobrimento:.1f} cm",
                       showarrow=False, font=dict(size=9, color='orange'), xanchor='right')

    fig.update_layout(
        title=f"Seção Transversal (b = 100 cm) — {modelo.split('(')[0].strip()}",
        xaxis_title="Largura (cm)", yaxis_title="Altura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1, range=[-2, h + 3]),
        xaxis=dict(range=[-20, 120]),
        margin=dict(l=60, r=80, t=40, b=20), height=360, showlegend=True
    )
    return fig


def plot_detalhe_longitudinal(L_cm, h_cm, cobrimento, phi_mm, phi_dist_mm, lb_p_cm, s_p, s_d, modelo):
    """
    Vista longitudinal esquemática da laje de escada mostrando:
    - Corpo da laje com apoios
    - Armadura principal com zonas de ancoragem
    - Armadura de distribuição (indicadores perpendiculares)
    - Cotas: L, lb, h, cobrimento
    """
    fig = go.Figure()
    is_balanco = "Balanço" in modelo

    r_p = cobrimento + phi_mm / 20
    r_d = r_p + phi_mm / 10 + phi_dist_mm / 20
    if is_balanco:
        r_p = h_cm - cobrimento - phi_mm / 20
        r_d = r_p - phi_mm / 10 - phi_dist_mm / 20

    pad = lb_p_cm + 20

    # Apoios (blocos hachurados)
    for xs, xe, label in [(-pad, 0, "Apoio inf.\n(piso/laje)"), (L_cm, L_cm + pad, "Apoio sup.\n(patamar)")]:
        fig.add_shape(type='rect', x0=xs, x1=xe, y0=-4, y1=h_cm,
                      fillcolor='rgba(100,100,100,0.18)', line=dict(color='black', width=1))
        fig.add_annotation(x=(xs + xe) / 2, y=-10, text=label,
                           showarrow=False, font=dict(size=8, color='gray'), xanchor='center')

    # Corpo da laje
    fig.add_trace(go.Scatter(
        x=[0, L_cm, L_cm, 0, 0], y=[0, 0, h_cm, h_cm, 0],
        fill='toself', fillcolor='rgba(200,200,200,0.4)',
        mode='lines', line=dict(color='black', width=2), name='Laje (vista longitudinal)'
    ))

    # Linha de cobrimento
    fig.add_shape(type='line', x0=0, x1=L_cm, y0=cobrimento, y1=cobrimento,
                  line=dict(color='orange', width=1, dash='dot'))

    # Armadura principal — vão
    fig.add_trace(go.Scatter(
        x=[0, L_cm], y=[r_p, r_p],
        mode='lines', line=dict(color='red', width=4),
        name=f'Principal φ{phi_mm:.1f} c/{s_p:.1f}cm'
    ))
    # Ancoragem esquerda
    fig.add_trace(go.Scatter(
        x=[-lb_p_cm, 0], y=[r_p, r_p],
        mode='lines', line=dict(color='red', width=4, dash='dash'),
        name=f'Ancoragem ≥ {lb_p_cm:.0f}cm (cada apoio)'
    ))
    # Ancoragem direita
    fig.add_trace(go.Scatter(
        x=[L_cm, L_cm + lb_p_cm], y=[r_p, r_p],
        mode='lines', line=dict(color='red', width=4, dash='dash'), showlegend=False
    ))

    # Armadura de distribuição — cruzes ao longo do vão (perpendicular ao plano)
    n_d_show = min(14, max(4, int(L_cm / s_d)))
    xd_pts = np.linspace(s_d / 2, L_cm - s_d / 2, num=n_d_show)
    sz = 1.8
    for xd in xd_pts:
        fig.add_trace(go.Scatter(x=[xd - sz, xd + sz], y=[r_d, r_d],
                                 mode='lines', line=dict(color='steelblue', width=2), showlegend=False))
        fig.add_trace(go.Scatter(x=[xd, xd], y=[r_d - sz, r_d + sz],
                                 mode='lines', line=dict(color='steelblue', width=2), showlegend=False))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                             line=dict(color='steelblue', width=2),
                             name=f'Distribuição φ{phi_dist_mm:.1f} c/{s_d:.1f}cm (⊗ perp. ao vão)'))

    # Cotas
    fig.add_annotation(x=L_cm / 2, y=-14, text=f"L = {L_cm:.0f} cm (projeção horizontal)",
                       showarrow=False, font=dict(size=11, color='navy'))
    fig.add_annotation(x=-lb_p_cm / 2, y=r_p + 4, text=f"lb≥{lb_p_cm:.0f}cm",
                       showarrow=False, font=dict(size=9, color='darkred'))
    fig.add_annotation(x=L_cm + lb_p_cm / 2, y=r_p + 4, text=f"lb≥{lb_p_cm:.0f}cm",
                       showarrow=False, font=dict(size=9, color='darkred'))
    fig.add_annotation(x=L_cm + pad + 3, y=h_cm / 2, text=f"h={h_cm:.0f}cm",
                       showarrow=False, textangle=-90, font=dict(size=9), xanchor='left')
    fig.add_annotation(x=-3, y=cobrimento / 2, text=f"c={cobrimento:.0f}cm",
                       showarrow=False, font=dict(size=8, color='darkorange'), xanchor='right')

    fig.update_layout(
        title="Vista Longitudinal Esquemática — Armaduras no Vão",
        xaxis_title="Comprimento (cm)", yaxis_title="Altura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1, range=[-18, h_cm + 12]),
        xaxis=dict(range=[-pad - 8, L_cm + pad + 12]),
        margin=dict(l=20, r=20, t=40, b=20), height=300
    )
    return fig


def plot_empuxo_vazio():
    """
    Detalhe do nó de transição laje horizontal / laje de escada inclinada.
    Painel esquerdo: caso ERRADO (empuxo ao vazio).
    Painel direito:  caso CORRETO (barras se cruzam).
    """
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["❌ ERRADO — Empuxo ao Vazio", "✅ CORRETO — Barras se Cruzam"],
        horizontal_spacing=0.06
    )

    h  = 12    # espessura esquemática (cm)
    lb = 22    # ancoragem esquemática
    incl = 0.52  # slope dy/dx da escada

    cos_a = 1.0 / math.sqrt(1 + incl ** 2)
    lb_x  = lb * cos_a  # projeção horizontal de lb ao longo da escada

    for col, correct in [(1, False), (2, True)]:
        # ── Laje de piso (horizontal) ────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=[-lb - 10, 8, 8, -lb - 10, -lb - 10],
            y=[0, 0, h, h, 0],
            fill='toself', fillcolor='rgba(170,170,170,0.4)',
            mode='lines', line=dict(color='black', width=2), showlegend=False
        ), row=1, col=col)

        # ── Laje de escada (inclinada) ────────────────────────────────────────
        dx = 48
        dy = incl * dx
        fig.add_trace(go.Scatter(
            x=[0, dx, dx, 0, 0],
            y=[h, h + dy, h + dy + h, h + h, h],
            fill='toself', fillcolor='rgba(150,150,150,0.4)',
            mode='lines', line=dict(color='black', width=2), showlegend=False
        ), row=1, col=col)

        c     = 2.0
        y_lj  = c + 0.6                   # barra na laje de piso (face tracionada, embaixo)
        y_esc_node = h + c + 0.6          # barra da escada no nó (face tracionada, embaixo)

        if correct:
            # Barra da LAJE → cruza para dentro da escada (lb horizontal)
            fig.add_trace(go.Scatter(
                x=[-lb - 10, lb], y=[y_lj, y_lj],
                mode='lines', line=dict(color='green', width=3), showlegend=False
            ), row=1, col=col)

            # Barra da ESCADA → cruza para dentro da laje (lb ao longo da inclinação)
            x0_esc = -lb_x
            y0_esc = y_esc_node - lb_x * incl
            fig.add_trace(go.Scatter(
                x=[x0_esc, dx], y=[y0_esc, h + dy + c + 0.6],
                mode='lines', line=dict(color='green', width=3, dash='dash'), showlegend=False
            ), row=1, col=col)

            # Círculo no nó
            fig.add_shape(type='circle', x0=-4, y0=h - 4, x1=4, y1=h + 4,
                          fillcolor='rgba(0,180,0,0.15)',
                          line=dict(color='green', width=2), row=1, col=col)

            # Anotações lb
            fig.add_annotation(x=lb / 2, y=y_lj - 4.5, text=f"lb≥{lb:.0f}cm\n(laje→escada)",
                               showarrow=False, font=dict(size=8, color='darkgreen'),
                               xanchor='center', row=1, col=col)
            fig.add_annotation(x=-lb_x / 2 - 1, y=y0_esc - 2, text=f"lb\n(escada→laje)",
                               showarrow=False, font=dict(size=8, color='darkgreen'),
                               xanchor='right', row=1, col=col)
            fig.add_annotation(x=4, y=h + 9, text="Barras cruzam o nó ✅\nTração transferida",
                               showarrow=False, font=dict(size=8, color='darkgreen'),
                               xanchor='left', bgcolor='rgba(200,255,200,0.6)', row=1, col=col)
        else:
            # Barra da LAJE → para na face do nó
            fig.add_trace(go.Scatter(
                x=[-lb - 10, -1], y=[y_lj, y_lj],
                mode='lines', line=dict(color='red', width=3), showlegend=False
            ), row=1, col=col)

            # Barra da ESCADA → começa na face do nó
            fig.add_trace(go.Scatter(
                x=[1, dx], y=[y_esc_node + 1 * incl, h + dy + c + 0.6],
                mode='lines', line=dict(color='red', width=3), showlegend=False
            ), row=1, col=col)

            # Indicador de fissura no vértice
            fig.add_trace(go.Scatter(
                x=[0, 4, -3, 1], y=[h, h + 6, h + 5, h],
                mode='lines', line=dict(color='darkred', width=2, dash='dot'), showlegend=False
            ), row=1, col=col)
            fig.add_annotation(x=4, y=h + 9,
                               text="Barras NÃO cruzam ❌\nEmpuxo ao vazio\n→ FISSURA no vértice",
                               showarrow=False, font=dict(size=8, color='darkred'),
                               xanchor='left', bgcolor='rgba(255,200,200,0.6)', row=1, col=col)

        # Rótulos dos elementos
        fig.add_annotation(x=-lb / 2 - 5, y=-3, text="Laje de piso",
                           showarrow=False, font=dict(size=8, color='gray'),
                           xanchor='center', row=1, col=col)
        fig.add_annotation(x=dx * 0.7, y=h + dy * 0.5, text="Laje de escada",
                           showarrow=False, font=dict(size=8, color='gray'),
                           xanchor='left', textangle=-27, row=1, col=col)

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        title="Detalhe de Amarração no Nó Laje/Escada — NBR 6118:2014",
        height=400, showlegend=False,
        margin=dict(l=10, r=10, t=80, b=10)
    )
    return fig


def show():
    st.header("Dimensionamento de Escadas — Projeto Completo", divider="blue")

    st.info("""
    **NOTA TÉCNICA E ESCOPO:**
    1. O cálculo de flexão e as solicitações apresentadas nesta interface resolvem a estática analítica para a tipologia de **Escada de Um Lance (Escada Reta)**, armadas nas direções principais ou em balanço lateral (seção retangular equivalente).
    2. Modelos em L, U ou O, que interagem com patamares cruzados, necessitam de análises de reação de apoio bidirecional nas inflexões, devendo essas lajes ser resolvidas por meio de reações transferidas (metodologia abordada nas literaturas base, mas fora do escopo analítico automatizado desta versão isolada).
    """)

    tab_geo, tab_cargas, tab_esforcos, tab_armaduras, tab_geral = st.tabs([
        "1. Geometria Geral",
        "2. Carregamentos",
        "3. Esforços",
        "4. Dimensionamento",
        "5. Visão Geral (Projetos)"
    ])

    if 'H_total'  not in st.session_state: st.session_state.H_total  = 280.0
    if 'e_desejado' not in st.session_state: st.session_state.e_desejado = 17.5
    if 'largura'  not in st.session_state: st.session_state.largura  = 120.0
    if 'p_adotado' not in st.session_state: st.session_state.p_adotado = 28.0
    if 'h_laje'   not in st.session_state: st.session_state.h_laje   = 12.0
    if 'pd'       not in st.session_state: st.session_state.pd       = 0.0
    if 'Md_knm'   not in st.session_state: st.session_state.Md_knm   = 0.0
    if 'Vd_kn'    not in st.session_state: st.session_state.Vd_kn    = 0.0
    if 'modelo'   not in st.session_state: st.session_state.modelo   = "Escada Armada Longitudinalmente (Bi-apoiada)"
    if 'As_final' not in st.session_state: st.session_state.As_final = 0.0
    if 'As_dist'  not in st.session_state: st.session_state.As_dist  = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    with tab_geo:
        st.subheader("Parâmetros Geométricos (Geração Automática do Lance)")

        col1, col2 = st.columns(2)
        with col1:
            H = st.number_input("Desnível Piso a Piso (H) [cm]:", min_value=50.0,
                                value=st.session_state.H_total, step=5.0)
            e_desejado = st.number_input("Espelho Desejado (e) [cm]:", min_value=15.0,
                                         max_value=19.0, value=st.session_state.e_desejado, step=0.1)
        with col2:
            p = st.number_input("Piso / Passo (p) [cm]:", min_value=25.0, max_value=32.0,
                                value=st.session_state.p_adotado, step=0.5)
            largura = st.number_input("Largura da Escada [cm]:", min_value=70.0, max_value=300.0,
                                      value=st.session_state.largura, step=5.0)
        h = st.number_input("Espessura da Laje (h) [cm]:", min_value=8.0, max_value=30.0,
                            value=st.session_state.h_laje, step=1.0)

        st.session_state.H_total   = H
        st.session_state.e_desejado = e_desejado
        st.session_state.p_adotado  = p
        st.session_state.largura    = largura
        st.session_state.h_laje     = h

        n_espelhos = max(1, round(H / e_desejado))
        e_real     = H / n_espelhos
        n_pisos    = n_espelhos - 1
        L_real     = n_pisos * p

        st.session_state.n_espelhos = n_espelhos
        st.session_state.e_real     = e_real
        st.session_state.n_pisos    = n_pisos
        st.session_state.L_real     = L_real

        st.markdown("### Resumo Geométrico Calculado")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Qtd. Espelhos", f"{n_espelhos}")
        c2.metric("Qtd. Pisos",    f"{n_pisos}")
        c3.metric("Espelho Real (e)", f"{e_real:.2f} cm")
        c4.metric("Comprimento (L)",  f"{L_real:.1f} cm")

        blondel = 2 * e_real + p
        if 60 <= blondel <= 64:
            st.success(f"**Verificação de Conforto (Blondel):** {blondel:.1f} cm — Ideal")
        else:
            st.warning(f"**Verificação de Conforto (Blondel):** {blondel:.1f} cm — Fora do ideal: 60–64 cm")

        alpha_rad  = math.atan(e_real / p)
        alpha_deg  = math.degrees(alpha_rad)
        cos_alpha  = math.cos(alpha_rad)
        st.session_state.cos_alpha = cos_alpha

        st.plotly_chart(plot_vista_lateral(p, e_real, h, n_espelhos, L_real, H),
                        use_container_width=True, key="plot_lateral_geo")

        # ── MEMÓRIA DE CÁLCULO — GEOMETRIA ───────────────────────────────────
        with st.expander("📋 Memória de Cálculo — Geometria do Lance", expanded=True):
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("**① Número de espelhos**")
                st.latex(
                    f"n = \\mathrm{{round}}\\left(\\frac{{H}}{{e_{{des}}}}\\right)"
                    f" = \\mathrm{{round}}\\left(\\frac{{{H:.1f}}}{{{e_desejado:.1f}}}\\right)"
                    f" = {n_espelhos}"
                )

                st.markdown("**② Espelho real** *(redistribuição do erro de arredondamento)*")
                st.latex(
                    f"e_{{real}} = \\frac{{H}}{{n}} = \\frac{{{H:.1f}}}{{{n_espelhos}}}"
                    f" = {e_real:.4f} \\; \\mathrm{{cm}}"
                )

                st.markdown("**③ Pisos e comprimento horizontal do lance**")
                st.latex(f"n_{{pisos}} = n - 1 = {n_espelhos} - 1 = {n_pisos}")
                st.latex(
                    f"L = n_{{pisos}} \\times p = {n_pisos} \\times {p:.1f}"
                    f" = {L_real:.1f} \\; \\mathrm{{cm}}"
                )

                st.markdown("**④ Relação L/h — pré-dimensionamento da espessura**")
                lh = L_real / h
                st.latex(f"L/h = {L_real:.0f} / {h:.0f} = {lh:.1f}")
                if lh <= 30:
                    st.success(f"L/h = {lh:.1f} ≤ 30 — espessura adequada ✓")
                else:
                    st.warning(f"L/h = {lh:.1f} > 30 — considere aumentar h para controle de flechas (ELS)")

            with col_g2:
                st.markdown("**⑤ Verificação de Blondel** *(NBR 9050:2020 — item 6.6.5)*")
                st.latex(r"60 \leq 2e + p \leq 64 \; \mathrm{cm}")
                st.latex(
                    f"2 \\times {e_real:.2f} + {p:.1f} = {blondel:.2f} \\; \\mathrm{{cm}}"
                )

                st.markdown("**⑥ Ângulo de inclinação**")
                st.latex(
                    f"\\alpha = \\arctan\\!\\left(\\frac{{e}}{{p}}\\right)"
                    f" = \\arctan\\!\\left(\\frac{{{e_real:.2f}}}{{{p:.1f}}}\\right)"
                    f" = {alpha_deg:.3f}^\\circ"
                )
                if 25 <= alpha_deg <= 45:
                    st.success(f"α = {alpha_deg:.1f}° ∈ [25°, 45°] — inclinação confortável ✓")
                elif alpha_deg > 45:
                    st.error(f"α = {alpha_deg:.1f}° > 45° — íngreme demais")
                else:
                    st.warning(f"α = {alpha_deg:.1f}° < 25° — muito suave")

                st.markdown("**⑦ Fator de inclinação cos(α)**")
                st.latex(f"\\cos\\alpha = \\cos({alpha_deg:.3f}^\\circ) = {cos_alpha:.6f}")

                st.markdown("**Quadro dimensional:**")
                st.dataframe([
                    {"Parâmetro": "Desnível H",         "Valor": f"{H:.1f} cm"},
                    {"Parâmetro": "Espelho real e",      "Valor": f"{e_real:.3f} cm"},
                    {"Parâmetro": "Piso p",              "Valor": f"{p:.1f} cm"},
                    {"Parâmetro": "Nº Espelhos",         "Valor": str(n_espelhos)},
                    {"Parâmetro": "Nº Pisos",            "Valor": str(n_pisos)},
                    {"Parâmetro": "Vão horizontal L",    "Valor": f"{L_real:.1f} cm"},
                    {"Parâmetro": "Largura",             "Valor": f"{largura:.1f} cm"},
                    {"Parâmetro": "Espessura h",         "Valor": f"{h:.1f} cm"},
                    {"Parâmetro": "Ângulo α",            "Valor": f"{alpha_deg:.2f}°"},
                    {"Parâmetro": "cos α",               "Valor": f"{cos_alpha:.6f}"},
                    {"Parâmetro": "Blondel 2e+p",        "Valor": f"{blondel:.2f} cm"},
                    {"Parâmetro": "L/h",                 "Valor": f"{lh:.1f}"},
                ], use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    with tab_cargas:
        st.subheader("Levantamento de Ações (kN/m²)")

        h_ss       = st.session_state.h_laje
        cos_alpha  = st.session_state.cos_alpha
        e_real_ss  = st.session_state.e_real
        h_incl     = h_ss / cos_alpha
        h_media    = h_incl + (e_real_ss / 2)
        pp_escada  = (h_media / 100) * 25.0

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Permanentes (g)")
            revest       = st.number_input("Revestimentos [kN/m²]:", min_value=0.0, value=1.0, step=0.1)
            carga_lin_gc = st.number_input("Carga Linear (Guarda-Corpo/Parede) [kN/m]:", min_value=0.0,
                                           value=0.0, step=0.1,
                                           help="Ex: 0.8 kN/m para guarda-corpo")
            carga_gc_area = (carga_lin_gc / (st.session_state.largura / 100.0)
                             if st.session_state.largura > 0 else 0.0)
            g_total = pp_escada + revest + carga_gc_area
            st.write(f"Espessura Média ($h_m$): {h_media:.2f} cm")
            if carga_lin_gc > 0:
                st.write(f"Guarda-Corpo/Parede convertido: {carga_gc_area:.2f} kN/m²")
            st.metric("Total Permanente (g)", f"{g_total:.2f} kN/m²")
        with col2:
            st.markdown("#### Variáveis (q)")
            tipo_uso    = st.radio("Utilização:", ["Sem acesso público (2.5 kN/m²)", "Com acesso público (3.0 kN/m²)"])
            q_acidental = 2.5 if "Sem" in tipo_uso else 3.0
            st.metric("Total Acidental (q)", f"{q_acidental:.2f} kN/m²")

        pd = (1.4 * g_total) + (1.4 * q_acidental)
        st.session_state.pd = pd
        st.success(f"**Carga de Cálculo (ELU):** {pd:.2f} kN/m²")

        if pd > 0:
            st.plotly_chart(plot_carregamentos(st.session_state.L_real / 100.0, pd),
                            use_container_width=True)

        # ── MEMÓRIA DE CÁLCULO — CARREGAMENTOS ───────────────────────────────
        with st.expander("📋 Memória de Cálculo — Levantamento de Ações", expanded=True):
            col_c1, col_c2 = st.columns(2)

            with col_c1:
                st.markdown("**① Espessura vertical da laje inclinada**")
                st.markdown("A laje é inclinada. A espessura perpendicular h é convertida para a direção vertical:")
                st.latex(r"h_{incl} = \frac{h}{\cos\alpha}")
                st.latex(
                    f"h_{{incl}} = \\frac{{{h_ss:.1f}}}{{{cos_alpha:.6f}}}"
                    f" = {h_incl:.4f} \\; \\mathrm{{cm}}"
                )

                st.markdown("**② Espessura média equivalente** *(laje + dentes dos degraus)*")
                st.markdown("Os dentes (triângulos dos degraus) contribuem com altura média e/2:")
                st.latex(r"h_m = h_{incl} + \frac{e_{real}}{2}")
                st.latex(
                    f"h_m = {h_incl:.4f} + \\frac{{{e_real_ss:.4f}}}{{2}}"
                    f" = {h_media:.4f} \\; \\mathrm{{cm}}"
                )

                st.markdown("**③ Peso próprio** *(γc = 25 kN/m³ — NBR 6120:2019 Tab. 1)*")
                st.latex(r"g_{pp} = \gamma_c \cdot \frac{h_m}{100}")
                st.latex(
                    f"g_{{pp}} = 25{{,}}0 \\times \\frac{{{h_media:.4f}}}{{100}}"
                    f" = {pp_escada:.4f} \\; \\mathrm{{kN/m^2}}"
                )

                st.markdown("**④ Total de ações permanentes**")
                st.latex(r"g = g_{pp} + g_{rev} + g_{gc}")
                st.latex(
                    f"g = {pp_escada:.4f} + {revest:.2f} + {carga_gc_area:.4f}"
                    f" = {g_total:.4f} \\; \\mathrm{{kN/m^2}}"
                )

            with col_c2:
                st.markdown("**⑤ Ação variável** *(NBR 6120:2019 — Tab. 2)*")
                uso_desc = "privativo" if q_acidental == 2.5 else "uso público"
                st.latex(f"q = {q_acidental:.1f} \\; \\mathrm{{kN/m^2}} \\quad (\\text{{{uso_desc}}})")

                st.markdown("**⑥ Combinação ELU — Combinação Normal** *(NBR 6118:2014 — item 11.7.2)*")
                st.latex(r"p_d = \gamma_g \cdot g + \gamma_q \cdot q = 1{,}4 \cdot g + 1{,}4 \cdot q")
                st.latex(
                    f"p_d = 1{{,}}4 \\times {g_total:.4f} + 1{{,}}4 \\times {q_acidental:.2f}"
                    f" = {1.4*g_total:.4f} + {1.4*q_acidental:.4f}"
                    f" = {pd:.4f} \\; \\mathrm{{kN/m^2}}"
                )

                st.markdown("**Quadro de ações:**")
                st.dataframe([
                    {"Ação": "Peso próprio (gpp)",       "γf": "—",   "kN/m²": f"{pp_escada:.3f}"},
                    {"Ação": "Revestimentos (grev)",     "γf": "—",   "kN/m²": f"{revest:.3f}"},
                    {"Ação": "Guarda-corpo (ggc)",       "γf": "—",   "kN/m²": f"{carga_gc_area:.3f}"},
                    {"Ação": "Total permanente (g)",     "γf": "—",   "kN/m²": f"{g_total:.3f}"},
                    {"Ação": "Variável (q)",              "γf": "—",   "kN/m²": f"{q_acidental:.3f}"},
                    {"Ação": "Carga de cálculo ELU (pd)","γf": "1,4", "kN/m²": f"{pd:.3f}"},
                ], use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    with tab_esforcos:
        st.subheader("Modelagem e Esforços")

        # leitura defensiva: pd pode não estar no escopo local se tabs forem re-renderizadas
        pd = st.session_state.pd

        modelo = st.selectbox("Modelo Estrutural Simplificado", [
            "Escada Armada Longitudinalmente (Bi-apoiada)",
            "Escada Armada Transversalmente (Apoiada em vigas laterais)",
            "Escada em Balanço (Engastada em um lado)"
        ])
        st.session_state.modelo = modelo

        if "Longitudinalmente" in modelo or "Bi-apoiada" in modelo:
            vao_L    = st.session_state.L_real / 100.0
            desc_vao = f"vão longitudinal L = {vao_L:.2f} m"
        else:
            vao_L    = st.session_state.largura / 100.0
            desc_vao = f"vão transversal (largura) = {vao_L:.2f} m"

        st.info(f"Vão estrutural para este modelo: **{desc_vao}**")

        if pd > 0:
            if "Bi-apoiada" in modelo or "Transversalmente" in modelo:
                Md = (pd * (vao_L ** 2)) / 8
                Vd = (pd * vao_L) / 2
            else:
                Md = (pd * (vao_L ** 2)) / 2
                Vd = pd * vao_L

            st.session_state.Md_knm = Md
            st.session_state.Vd_kn  = Vd

            st.plotly_chart(plot_esforcos(vao_L, pd, modelo), use_container_width=True)

            # ── MEMÓRIA DE CÁLCULO — ESFORÇOS ────────────────────────────────
            with st.expander("📋 Memória de Cálculo — Esforços Solicitantes de Cálculo", expanded=True):
                col_e1, col_e2 = st.columns(2)

                with col_e1:
                    if "Bi-apoiada" in modelo or "Transversalmente" in modelo:
                        st.markdown("**Esquema estático:** Viga biapoiada — carga distribuída uniforme")
                        st.markdown("**① Reações de apoio** *(simetria → RA = RB)*")
                        st.latex(r"R_A = R_B = \frac{p_d \cdot L}{2}")
                        st.latex(
                            f"R_A = R_B = \\frac{{{pd:.4f} \\times {vao_L:.4f}}}{{2}}"
                            f" = {Vd:.4f} \\; \\mathrm{{kN/m}}"
                        )
                        st.markdown("**② Cortante** em função de x *(origem no apoio esquerdo)*")
                        st.latex(r"V(x) = R_A - p_d \cdot x = \frac{p_d \cdot L}{2} - p_d \cdot x")
                        st.latex(
                            f"V(0) = +{Vd:.3f} \\; \\mathrm{{kN/m}}"
                            f"\\qquad V(L) = -{Vd:.3f} \\; \\mathrm{{kN/m}}"
                        )
                        st.markdown("**③ Momento fletor máximo** *(x = L/2 — meio do vão)*")
                        st.latex(r"M_d = \frac{p_d \cdot L^2}{8}")
                        st.latex(
                            f"M_d = \\frac{{{pd:.4f} \\times {vao_L:.4f}^2}}{{8}}"
                            f" = \\frac{{{pd:.4f} \\times {vao_L**2:.5f}}}{{8}}"
                            f" = {Md:.4f} \\; \\mathrm{{kN \\cdot m/m}}"
                        )
                    else:
                        st.markdown("**Esquema estático:** Balanço — carga distribuída uniforme, engaste em x = 0")
                        st.markdown("**① Reação no engaste**")
                        st.latex(r"R_{eng} = p_d \cdot L")
                        st.latex(
                            f"R_{{eng}} = {pd:.4f} \\times {vao_L:.4f}"
                            f" = {Vd:.4f} \\; \\mathrm{{kN/m}}"
                        )
                        st.markdown("**② Cortante** em função de x *(origem na extremidade livre)*")
                        st.latex(r"V(x) = p_d \cdot (L - x)")
                        st.latex(
                            f"V(0) = {Vd:.3f} \\; \\mathrm{{kN/m}}"
                            f"\\qquad V(L) = 0"
                        )
                        st.markdown("**③ Momento fletor máximo** *(x = 0 — no engaste)*")
                        st.latex(r"M_d = \frac{p_d \cdot L^2}{2}")
                        st.latex(
                            f"M_d = \\frac{{{pd:.4f} \\times {vao_L:.4f}^2}}{{2}}"
                            f" = \\frac{{{pd:.4f} \\times {vao_L**2:.5f}}}{{2}}"
                            f" = {Md:.4f} \\; \\mathrm{{kN \\cdot m/m}}"
                        )

                with col_e2:
                    st.markdown("**④ Verificação L/h — rigidez mínima**")
                    h_ref   = st.session_state.h_laje
                    lh_esf  = (vao_L * 100) / h_ref
                    st.latex(
                        f"L/h = {vao_L*100:.0f} / {h_ref:.0f} = {lh_esf:.1f}"
                    )
                    if lh_esf <= 30:
                        st.success(f"L/h = {lh_esf:.1f} ≤ 30 — rigidez satisfatória ✓")
                    else:
                        st.warning(f"L/h = {lh_esf:.1f} > 30 — recomenda-se verificação de flechas (ELS)")

                    st.markdown("**Quadro de esforços:**")
                    st.dataframe([
                        {"Grandeza": "Vão estrutural L",    "Valor": f"{vao_L:.3f} m"},
                        {"Grandeza": "Carga de cálculo pd", "Valor": f"{pd:.3f} kN/m²"},
                        {"Grandeza": "Cortante máx. Vd",    "Valor": f"{Vd:.3f} kN/m"},
                        {"Grandeza": "Momento máx. Md",     "Valor": f"{Md:.3f} kN·m/m"},
                    ], use_container_width=True, hide_index=True)
        else:
            st.info("Calcule os carregamentos na aba anterior para visualizar os esforços.")

    # ─────────────────────────────────────────────────────────────────────────
    with tab_armaduras:
        st.subheader("Dimensionamento ao ELU")

        col1, col2, col3, col4 = st.columns(4)
        fck        = col1.number_input("fck [MPa]:", min_value=20, max_value=50, value=25, step=5)
        cobrimento = col2.number_input("Cobrimento [cm]:", min_value=1.5, max_value=5.0,
                                       value=2.0, step=0.5)
        bitola_est  = col3.selectbox("Bitola Principal (φ) [mm]:", [8.0, 10.0, 12.5, 16.0], index=1)
        bitola_dist = col4.selectbox("Bitola Distribuição (φ_d) [mm]:", [6.3, 8.0, 10.0, 12.5], index=0)

        d_util = st.session_state.h_laje - cobrimento - (bitola_est / 20.0)
        Md_cm  = st.session_state.Md_knm * 100

        As_calc = calcular_armadura_flexao(Md_cm, 100.0, d_util, fck)

        if As_calc is None:
            st.error("Seção requer armadura dupla ou redimensionamento da espessura!")
            st.session_state.As_final = 0
            st.session_state.As_dist  = 0
        else:
            As_min   = 0.0015 * 100.0 * st.session_state.h_laje
            As_final = max(As_calc, As_min)
            As_dist  = max(As_final / 5.0, 0.90)

            st.session_state.As_final = As_final
            st.session_state.As_dist  = As_dist

            col_res1, col_res2 = st.columns(2)
            col_res1.metric("Área de Aço Principal ($A_s$)", f"{As_final:.2f} cm²/m")
            col_res2.metric("Área de Aço Distribuição",       f"{As_dist:.2f} cm²/m")

            # ── SELEÇÃO COMERCIAL E ESPAÇAMENTOS ─────────────────────────────
            st.markdown("---")
            st.markdown("#### 🔩 Seleção Comercial de Barras e Verificação de Espaçamentos *(NBR 6118:2014 — §17.3.5.2)*")

            A_phi_p = math.pi * (bitola_est  / 10) ** 2 / 4   # cm² por barra
            A_phi_d = math.pi * (bitola_dist / 10) ** 2 / 4

            n_p = math.ceil(As_final / A_phi_p)
            s_p = round(100.0 / n_p, 1)
            As_adot_p = n_p * A_phi_p

            n_d = math.ceil(As_dist / A_phi_d)
            s_d = round(100.0 / n_d, 1)
            As_adot_d = n_d * A_phi_d

            # Limites NBR 6118:2014 §17.3.5.2
            h_ref = st.session_state.h_laje
            s_max_p = min(2.0 * h_ref, 20.0)   # principal: ≤ min(2h, 20cm)
            s_max_d = min(3.0 * h_ref, 30.0)   # distribuição: ≤ min(3h, 30cm)

            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                st.markdown("**Armadura Principal**")
                ok_p = s_p <= s_max_p
                st.dataframe([
                    {"Item": "Bitola φ",             "Valor": f"{bitola_est:.1f} mm"},
                    {"Item": "Área / barra (Aφ)",    "Valor": f"{A_phi_p:.4f} cm²"},
                    {"Item": "Nº barras / metro",    "Valor": str(n_p)},
                    {"Item": "Espaçamento adotado s","Valor": f"{s_p:.1f} cm"},
                    {"Item": "As adotado",           "Valor": f"{As_adot_p:.3f} cm²/m"},
                    {"Item": "s_máx (NBR §17.3.5.2)","Valor": f"{s_max_p:.0f} cm"},
                    {"Item": "s ≤ s_máx",            "Valor": f"{'✅' if ok_p else '❌'} {s_p:.1f} ≤ {s_max_p:.0f} cm"},
                ], use_container_width=True, hide_index=True)
                if not ok_p:
                    st.error(f"s = {s_p:.1f} cm > {s_max_p:.0f} cm — reduza o espaçamento")

            with col_sel2:
                st.markdown("**Armadura de Distribuição**")
                ok_d = s_d <= s_max_d
                st.dataframe([
                    {"Item": "Bitola φ_dist",        "Valor": f"{bitola_dist:.1f} mm"},
                    {"Item": "Área / barra (Aφ)",    "Valor": f"{A_phi_d:.4f} cm²"},
                    {"Item": "Nº barras / metro",    "Valor": str(n_d)},
                    {"Item": "Espaçamento adotado s","Valor": f"{s_d:.1f} cm"},
                    {"Item": "As adotado",           "Valor": f"{As_adot_d:.3f} cm²/m"},
                    {"Item": "s_máx (NBR §17.3.5.2)","Valor": f"{s_max_d:.0f} cm"},
                    {"Item": "s ≤ s_máx",            "Valor": f"{'✅' if ok_d else '❌'} {s_d:.1f} ≤ {s_max_d:.0f} cm"},
                ], use_container_width=True, hide_index=True)
                if not ok_d:
                    st.error(f"s = {s_d:.1f} cm > {s_max_d:.0f} cm — reduza o espaçamento")

            # ── COMPRIMENTO DE ANCORAGEM ──────────────────────────────────────
            st.markdown("---")
            st.markdown("#### ⚓ Comprimento de Ancoragem nos Apoios *(NBR 6118:2014 — §9.3 e §9.4.2.5)*")

            _fctm_a = 0.3 * (fck ** (2 / 3))          # MPa
            _fctd_a = 0.7 * _fctm_a / 1.4              # MPa
            fbd_mpa  = 2.25 * _fctd_a                  # MPa — η1=η2=1 (boa aderência, φ≤32mm)
            fyd_mpa  = 500.0 / 1.15                    # MPa

            # lb_básico = φ·fyd / (4·fbd)
            lb_p      = (bitola_est  / 10) * fyd_mpa / (4 * fbd_mpa)   # cm
            lb_d      = (bitola_dist / 10) * fyd_mpa / (4 * fbd_mpa)   # cm
            lb_nec_p  = lb_p * (As_calc / As_adot_p)                    # cm — redução proporc.
            lb_min_p  = max(10 * bitola_est  / 10, 10.0, lb_nec_p)      # cm
            lb_min_d  = max(10 * bitola_dist / 10, 10.0, lb_d)          # cm

            col_anc1, col_anc2 = st.columns(2)
            with col_anc1:
                st.markdown("**Armadura Principal**")
                st.latex(r"f_{bd} = 2{,}25 \cdot \eta_1 \cdot \eta_2 \cdot f_{ctd} \quad (\eta_1 = \eta_2 = 1)")
                st.latex(
                    f"f_{{bd}} = 2{{,}}25 \\times {_fctd_a:.4f}"
                    f" = {fbd_mpa:.4f} \\; \\mathrm{{MPa}}"
                )
                st.latex(r"l_b = \frac{\phi \cdot f_{yd}}{4 \cdot f_{bd}}")
                st.latex(
                    f"l_b = \\frac{{{bitola_est/10:.2f} \\times {fyd_mpa:.1f}}}"
                    f"{{4 \\times {fbd_mpa:.4f}}} = {lb_p:.1f} \\; \\mathrm{{cm}}"
                )
                st.latex(
                    f"l_{{b,nec}} = {lb_p:.1f} \\times \\frac{{{As_calc:.3f}}}{{{As_adot_p:.3f}}}"
                    f" = {lb_nec_p:.1f} \\; \\mathrm{{cm}}"
                )
                st.info(
                    f"**Ancorar ≥ {lb_min_p:.0f} cm** nos apoios  \n"
                    f"= max(10φ = {10*bitola_est/10:.0f} cm,  10 cm,  lb,nec = {lb_nec_p:.1f} cm)"
                )

            with col_anc2:
                st.markdown("**Armadura de Distribuição**")
                st.latex(
                    f"l_b = \\frac{{{bitola_dist/10:.2f} \\times {fyd_mpa:.1f}}}"
                    f"{{4 \\times {fbd_mpa:.4f}}} = {lb_d:.1f} \\; \\mathrm{{cm}}"
                )
                st.info(
                    f"**Ancorar ≥ {lb_min_d:.0f} cm** nos apoios  \n"
                    f"= max(10φ = {10*bitola_dist/10:.0f} cm,  10 cm,  lb = {lb_d:.1f} cm)"
                )

            # ── VERIFICAÇÃO AO CISALHAMENTO ───────────────────────────────────
            st.markdown("---")
            st.markdown("#### Verificação ao Esforço Cortante (Sem Estribos)")
            vr1, status_cisalhamento = verificar_cisalhamento(
                st.session_state.Vd_kn, 100.0, d_util, fck, As_final)
            if status_cisalhamento == "OK":
                st.success(
                    f"**Verificação Atendida:** $V_{{sd}}$ ({st.session_state.Vd_kn:.2f} kN) "
                    f"$\\le V_{{R1}}$ ({vr1:.2f} kN). Laje resiste ao cisalhamento sem estribos.")
            else:
                st.error(
                    f"**Falha ao Cisalhamento:** $V_{{sd}}$ ({st.session_state.Vd_kn:.2f} kN) "
                    f"$> V_{{R1}}$ ({vr1:.2f} kN). Necessário estribos ou aumento da espessura!")

            # ── SEÇÃO TRANSVERSAL ─────────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### 📐 Seção Transversal — Posicionamento das Armaduras")
            st.plotly_chart(
                plot_detalhamento(st.session_state.h_laje, cobrimento,
                                  st.session_state.modelo, bitola_est, bitola_dist,
                                  n_p, s_p, n_d, s_d),
                use_container_width=True)

            # ── VISTA LONGITUDINAL ────────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### 📏 Vista Longitudinal — Armaduras no Vão e Ancoragens")
            st.plotly_chart(
                plot_detalhe_longitudinal(
                    st.session_state.L_real, st.session_state.h_laje, cobrimento,
                    bitola_est, bitola_dist, lb_min_p, s_p, s_d, st.session_state.modelo),
                use_container_width=True)

            # ── REGRAS DE AMARRAÇÃO E EXECUÇÃO ───────────────────────────────
            st.markdown("---")
            with st.expander("📐 Regras de Amarração, Posicionamento e Execução", expanded=True):
                col_am1, col_am2 = st.columns(2)

                with col_am1:
                    st.markdown("##### Amarração das Barras")
                    st.markdown("""
**Regra geral (NBR 6118:2014 §9.4.6 e práticas de detalhamento):**
- Amarrar **em todos os cruzamentos** de armadura principal × distribuição com **arame recozido nº 18 (Ø 1,2 mm)** — torniquete simples
- Em lajes com φ ≤ 10 mm e ρ ≤ ρ_min: pode-se amarrar **em xadrez** (cruzamentos alternados), desde que as barras da borda sejam todas amarradas
- **Nunca deixar cruzamentos soltos** — risco de deslocamento durante concretagem

**Sequência de montagem:**
1. Espaçadores de cobrimento (espaçados ≤ 100 cm entre si)
2. Armadura **principal embaixo** (para laje bi-apoiada/transversal)
3. Armadura de **distribuição em cima** da principal
4. Amarrar todos os cruzamentos
5. Para **balanço**: principal fica **em cima**, distribuição abaixo
                    """)

                    st.markdown("##### Espaçamento Mínimo entre Barras")
                    st.markdown("""
*(NBR 6118:2014 §18.3.2.2)*

$$a_{min} = \\max(\\phi_{max};\\ d_{brita}+0{,}5\\,\\text{cm};\\ 2\\,\\text{cm})$$

- Para lajes com barras ≤ φ12,5: geralmente `a_min = 2 cm`
- O espaçamento adotado já satisfaz este limite se `s ≥ φ + 2 cm`
                    """)

                with col_am2:
                    st.markdown("##### Ancoragem nos Apoios — Detalhes Críticos")
                    st.markdown(f"""
**Apoio inferior (ligação escada → laje de piso):**
- A barra principal da escada deve penetrar **≥ {lb_min_p:.0f} cm** na laje de piso (reta ou com gancho)
- A barra principal da laje de piso deve penetrar **≥ {lb_min_p:.0f} cm** dentro da laje de escada
- As barras de ambos os elementos **devem se cruzar** no nó — nunca terminar alinhadas na face

**Apoio superior (ligação escada → patamar ou laje superior):**
- Idem ao apoio inferior — barras da escada cruzam para dentro do patamar
- Comprimento de ancoragem mínimo: **{lb_min_p:.0f} cm** a partir da face do apoio

**Gancho alternativo (quando não há espaço para ancoragem reta):**
- Dobra de **90°** com prolongamento reto ≥ max(4φ; 6 cm) após a dobra *(NBR §9.4.6.2)*
- Dobra de **180°** com prolongamento reto ≥ max(4φ; 6 cm) após a dobra

**Comprimentos calculados para esta escada:**
| Armadura | φ (mm) | lb calculado | lb,nec | **Adotar** |
|---|---|---|---|---|
| Principal | {bitola_est:.1f} | {lb_p:.0f} cm | {lb_nec_p:.0f} cm | **{lb_min_p:.0f} cm** |
| Distribuição | {bitola_dist:.1f} | {lb_d:.0f} cm | {lb_d:.0f} cm | **{lb_min_d:.0f} cm** |
                    """)

                    st.markdown("##### Espaçadores de Cobrimento")
                    st.markdown(f"""
- Usar espaçadores plásticos ou de argamassa para garantir cobrimento nominal = **{cobrimento:.0f} cm**
- Espaçar a cada **≤ 100 cm** em ambas as direções
- Instalar na face inferior E nas laterais da laje
- Nunca usar madeira, pedras ou entulho como espaçador
                    """)

            # ── DETALHE DO NÓ — EMPUXO AO VAZIO ─────────────────────────────
            st.markdown("---")
            st.markdown("### ⚠️ Detalhe Crítico: Amarração no Nó Laje/Escada")
            st.error(
                "**Empuxo ao Vazio** — Nos nós de transição entre a laje de escada e a laje horizontal "
                "(piso ou patamar), as barras dos dois elementos **devem obrigatoriamente se cruzar**. "
                "Se as barras terminarem alinhadas na face do nó, a força de tração no vértice não tem "
                "como ser transferida e **gera fissura diagonal no vértice** — falha de detalhamento, "
                "não de dimensionamento."
            )
            st.plotly_chart(plot_empuxo_vazio(), use_container_width=True)
            st.success("Dimensionamento à flexão concluído com sucesso!")

            # ── MEMÓRIA DE CÁLCULO — DIMENSIONAMENTO ELU ─────────────────────
            with st.expander("📋 Memória de Dimensionamento — Flexão ELU (NBR 6118:2014 item 17.3)", expanded=True):
                # Recomputa intermediários para exibição (espelha calcular_armadura_flexao)
                _fcd  = 0.85 * (fck / 10) / 1.4
                _fyd  = (500.0 / 10) / 1.15
                _kmd  = Md_cm / (100.0 * d_util**2 * _fcd)
                _kx   = 1.25 * (1 - math.sqrt(max(0.0, 1 - 2 * _kmd)))
                _z    = d_util * (1 - 0.4 * _kx)

                col_d1, col_d2 = st.columns(2)

                with col_d1:
                    st.markdown("**① Altura útil da seção transversal**")
                    st.latex(r"d = h - c_{nom} - \frac{\phi}{2}")
                    st.latex(
                        f"d = {st.session_state.h_laje:.1f} - {cobrimento:.1f}"
                        f" - \\frac{{{bitola_est:.1f}/10}}{{2}}"
                        f" = {d_util:.4f} \\; \\mathrm{{cm}}"
                    )

                    st.markdown("**② Resistências de cálculo** *(NBR 6118:2014 — itens 12.3.3 e 8.2.1)*")
                    st.latex(r"f_{cd} = \frac{\alpha_c \cdot f_{ck}}{\gamma_c} \quad (\alpha_c = 0{,}85 \;;\; \gamma_c = 1{,}4)")
                    st.latex(
                        f"f_{{cd}} = \\frac{{0{{,}}85 \\times {fck}}}{{1{{,}}4 \\times 10}}"
                        f" = {_fcd:.6f} \\; \\mathrm{{kN/cm^2}}"
                        f" = {_fcd*10:.4f} \\; \\mathrm{{MPa}}"
                    )
                    st.latex(r"f_{yd} = \frac{f_{yk}}{\gamma_s} \quad (f_{yk} = 500 \; \mathrm{MPa} \;;\; \gamma_s = 1{,}15)")
                    st.latex(
                        f"f_{{yd}} = \\frac{{500}}{{1{{,}}15 \\times 10}}"
                        f" = {_fyd:.6f} \\; \\mathrm{{kN/cm^2}}"
                        f" = {_fyd*10:.2f} \\; \\mathrm{{MPa}}"
                    )

                    st.markdown("**③ Momento de cálculo — conversão de unidades**")
                    st.latex(
                        f"M_d = {st.session_state.Md_knm:.4f} \\; \\mathrm{{kN \\cdot m/m}}"
                        f" \\times 100 = {Md_cm:.4f} \\; \\mathrm{{kN \\cdot cm/m}}"
                    )

                    st.markdown("**④ Coeficiente adimensional de momento fletor**")
                    st.latex(r"k_{md} = \frac{M_d}{b_w \cdot d^2 \cdot f_{cd}}")
                    denominador = 100.0 * d_util**2 * _fcd
                    st.latex(
                        f"k_{{md}} = \\frac{{{Md_cm:.4f}}}{{100 \\times {d_util:.4f}^2 \\times {_fcd:.6f}}}"
                        f" = \\frac{{{Md_cm:.4f}}}{{{denominador:.4f}}}"
                        f" = {_kmd:.6f}"
                    )
                    if _kmd <= 0.295:
                        st.success(f"kmd = {_kmd:.4f} ≤ 0,295 — seção simplesmente armada ✓")
                    else:
                        st.error(f"kmd = {_kmd:.4f} > 0,295 — seção requer armadura dupla ✗")

                with col_d2:
                    st.markdown("**⑤ Profundidade relativa da linha neutra** *(NBR 6118:2014 — Eq. 17.1)*")
                    st.latex(r"k_x = 1{,}25 \cdot \left(1 - \sqrt{1 - 2 \cdot k_{md}}\right)")
                    st.latex(
                        f"k_x = 1{{,}}25 \\cdot \\left(1 - \\sqrt{{1 - 2 \\times {_kmd:.6f}}}\\right)"
                        f" = {_kx:.6f}"
                    )
                    if _kx <= 0.45:
                        st.success(f"kx = {_kx:.4f} ≤ 0,45 — Domínio 2→3, CA-50 ✓")
                    else:
                        st.error(f"kx = {_kx:.4f} > 0,45 — Domínio 4, armadura dupla necessária ✗")

                    st.markdown("**⑥ Braço de alavanca interno**")
                    st.latex(r"z = d \cdot (1 - 0{,}4 \cdot k_x)")
                    st.latex(
                        f"z = {d_util:.4f} \\cdot (1 - 0{{,}}4 \\times {_kx:.6f})"
                        f" = {_z:.5f} \\; \\mathrm{{cm}}"
                    )

                    st.markdown("**⑦ Área de aço calculada**")
                    st.latex(r"A_{s,calc} = \frac{M_d}{z \cdot f_{yd}}")
                    st.latex(
                        f"A_{{s,calc}} = \\frac{{{Md_cm:.4f}}}{{{_z:.5f} \\times {_fyd:.6f}}}"
                        f" = {As_calc:.5f} \\; \\mathrm{{cm^2/m}}"
                    )

                    st.markdown("**⑧ Armadura mínima** *(NBR 6118:2014 — Tab. 17.3 — ρmin = 0,15% para CA-50)*")
                    st.latex(r"A_{s,min} = 0{,}0015 \cdot b_w \cdot h")
                    st.latex(
                        f"A_{{s,min}} = 0{{,}}0015 \\times 100 \\times {st.session_state.h_laje:.1f}"
                        f" = {As_min:.4f} \\; \\mathrm{{cm^2/m}}"
                    )

                    governa = "calculada governa" if As_calc >= As_min else "mínima governa"
                    st.markdown("**⑨ Área de aço final adotada**")
                    st.latex(
                        f"A_{{s,final}} = \\max({As_calc:.4f};\\; {As_min:.4f})"
                        f" = {As_final:.4f} \\; \\mathrm{{cm^2/m}} \\quad [{governa}]"
                    )

                    st.markdown("**⑩ Armadura de distribuição** *(NBR 6118:2014 — item 17.3.5.2 — mín 20% e 0,90 cm²/m)*")
                    st.latex(
                        f"A_{{s,dist}} = \\max\\!\\left(\\frac{{{As_final:.4f}}}{{5}};\\; 0{{,}}90\\right)"
                        f" = {As_dist:.4f} \\; \\mathrm{{cm^2/m}}"
                    )

            # ── MEMÓRIA DE VERIFICAÇÃO — CISALHAMENTO ────────────────────────
            with st.expander("📋 Memória de Verificação — Esforço Cortante (NBR 6118:2014 — item 19.4.1)", expanded=True):
                # Recomputa intermediários para exibição (espelha verificar_cisalhamento)
                _fctm         = 0.3 * (fck ** (2/3))
                _fctk_inf     = 0.7 * _fctm
                _fctd         = _fctk_inf / 1.4
                _tau_rd       = 0.25 * _fctd
                _tau_rd_kncm2 = _tau_rd / 10.0
                _rho_raw      = As_final / (100.0 * d_util)
                _rho          = min(_rho_raw, 0.02)
                _d_m          = d_util / 100.0
                _k_cis        = max(1.6 - _d_m, 1.0)
                _t_rd         = _tau_rd_kncm2 * _k_cis * (1.2 + 40 * _rho)
                _vr1          = _t_rd * 100.0 * d_util
                Vd_val        = st.session_state.Vd_kn

                col_v1, col_v2 = st.columns(2)

                with col_v1:
                    st.markdown("**① Resistência à tração do concreto** *(NBR 6118:2014 — Tab. 8.1)*")
                    st.latex(r"f_{ctm} = 0{,}3 \cdot f_{ck}^{2/3} \quad (\mathrm{MPa})")
                    st.latex(
                        f"f_{{ctm}} = 0{{,}}3 \\times {fck}^{{2/3}}"
                        f" = 0{{,}}3 \\times {fck**(2/3):.5f}"
                        f" = {_fctm:.5f} \\; \\mathrm{{MPa}}"
                    )
                    st.latex(r"f_{ctk,inf} = 0{,}7 \cdot f_{ctm}")
                    st.latex(
                        f"f_{{ctk,inf}} = 0{{,}}7 \\times {_fctm:.5f}"
                        f" = {_fctk_inf:.5f} \\; \\mathrm{{MPa}}"
                    )
                    st.latex(r"f_{ctd} = \frac{f_{ctk,inf}}{\gamma_c} = \frac{f_{ctk,inf}}{1{,}4}")
                    st.latex(
                        f"f_{{ctd}} = \\frac{{{_fctk_inf:.5f}}}{{1{{,}}4}}"
                        f" = {_fctd:.5f} \\; \\mathrm{{MPa}}"
                    )

                    st.markdown("**② Tensão de referência ao cisalhamento**")
                    st.latex(r"\tau_{Rd} = 0{,}25 \cdot f_{ctd}")
                    st.latex(
                        f"\\tau_{{Rd}} = 0{{,}}25 \\times {_fctd:.5f}"
                        f" = {_tau_rd:.5f} \\; \\mathrm{{MPa}}"
                        f" = {_tau_rd_kncm2:.6f} \\; \\mathrm{{kN/cm^2}}"
                    )

                with col_v2:
                    st.markdown("**③ Fator de tamanho k e taxa de armadura ρl**")
                    st.latex(r"k = \max(1{,}6 - d_{[m]},\; 1{,}0)")
                    st.latex(
                        f"k = \\max(1{{,}}6 - {_d_m:.4f},\\; 1{{,}}0)"
                        f" = \\max({1.6-_d_m:.4f},\\; 1{{,}}0)"
                        f" = {_k_cis:.4f}"
                    )
                    st.latex(r"\rho_l = \frac{A_s}{b_w \cdot d} \leq 0{,}02")
                    st.latex(
                        f"\\rho_l = \\frac{{{As_final:.4f}}}{{100 \\times {d_util:.4f}}}"
                        f" = {_rho_raw:.6f}"
                        f" \\Rightarrow \\rho_{{adot}} = {_rho:.6f}"
                    )
                    if _rho_raw >= 0.02:
                        st.info("ρl limitado a 0,02 conforme NBR 6118:2014")

                    st.markdown("**④ Força cortante resistente — Modelo I** *(sem armadura transversal)*")
                    st.latex(r"V_{Rd1} = \left[\tau_{Rd} \cdot k \cdot (1{,}2 + 40\rho_l)\right] \cdot b_w \cdot d")
                    st.latex(
                        f"V_{{Rd1}} = [{_tau_rd_kncm2:.6f} \\times {_k_cis:.4f} \\times"
                        f"(1{{,}}2 + 40 \\times {_rho:.6f})]"
                        f" \\times 100 \\times {d_util:.4f}"
                    )
                    st.latex(
                        f"V_{{Rd1}} = {_t_rd:.7f} \\times {100*d_util:.2f}"
                        f" = {_vr1:.4f} \\; \\mathrm{{kN/m}}"
                    )

                    st.markdown("**⑤ Verificação final**")
                    st.latex(f"V_{{sd}} = {Vd_val:.4f} \\; \\mathrm{{kN/m}}")
                    if Vd_val <= _vr1:
                        st.latex(
                            f"{Vd_val:.4f} \\leq {_vr1:.4f} \\; \\mathrm{{kN/m}}"
                            f"\\quad \\Rightarrow \\quad \\text{{ATENDE}}"
                        )
                        st.success("Verificação ao cisalhamento atendida — sem estribos ✓")
                    else:
                        st.latex(
                            f"{Vd_val:.4f} > {_vr1:.4f} \\; \\mathrm{{kN/m}}"
                            f"\\quad \\Rightarrow \\quad \\text{{FALHA}}"
                        )
                        st.error("Falha ao cisalhamento — necessário estribos ou aumento de h ✗")

                st.markdown("**Quadro resumo de dimensionamento:**")
                st.dataframe([
                    {"Grandeza": "d — Altura útil",         "Valor": f"{d_util:.3f} cm",        "Referência": "—"},
                    {"Grandeza": "fcd",                      "Valor": f"{_fcd:.5f} kN/cm²",      "Referência": "NBR 6118 §12.3.3"},
                    {"Grandeza": "fyd",                      "Valor": f"{_fyd:.4f} kN/cm²",      "Referência": "NBR 6118 §12.3.3"},
                    {"Grandeza": "Md",                       "Valor": f"{Md_cm:.3f} kN·cm/m",    "Referência": "—"},
                    {"Grandeza": "kmd",                      "Valor": f"{_kmd:.5f}",              "Referência": "≤ 0,295"},
                    {"Grandeza": "kx",                       "Valor": f"{_kx:.5f}",               "Referência": "≤ 0,45 (CA-50)"},
                    {"Grandeza": "z — Braço de alavanca",    "Valor": f"{_z:.4f} cm",             "Referência": "—"},
                    {"Grandeza": "As,calc",                  "Valor": f"{As_calc:.3f} cm²/m",     "Referência": "—"},
                    {"Grandeza": "As,min",                   "Valor": f"{As_min:.3f} cm²/m",      "Referência": "NBR 6118 Tab. 17.3"},
                    {"Grandeza": "As,final",                 "Valor": f"{As_final:.3f} cm²/m",    "Referência": "—"},
                    {"Grandeza": "As,dist",                  "Valor": f"{As_dist:.3f} cm²/m",     "Referência": "NBR 6118 §17.3.5.2"},
                    {"Grandeza": "VRd1",                     "Valor": f"{_vr1:.3f} kN/m",         "Referência": "NBR 6118 §19.4.1"},
                    {"Grandeza": "Vsd",                      "Valor": f"{Vd_val:.3f} kN/m",       "Referência": "—"},
                    {"Grandeza": "Cisalhamento",             "Valor": "ATENDE" if Vd_val <= _vr1 else "FALHA", "Referência": "—"},
                ], use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    with tab_geral:
        st.subheader("Visão Geral do Projeto Geométrico")
        st.markdown("Abaixo estão as 3 representações do arranjo físico completo da escada.")

        c_p    = st.session_state.p_adotado
        c_e    = st.session_state.e_real
        c_h    = st.session_state.h_laje
        c_n    = st.session_state.n_espelhos
        c_np   = st.session_state.n_pisos
        c_L    = st.session_state.L_real
        c_H    = st.session_state.H_total
        c_larg = st.session_state.largura

        col_plot1, col_plot2 = st.columns(2)
        with col_plot1:
            st.plotly_chart(plot_vista_superior(c_p, c_np, c_L, c_larg),
                            use_container_width=True)
        with col_plot2:
            st.plotly_chart(plot_vista_lateral(c_p, c_e, c_h, c_n, c_L, c_H),
                            use_container_width=True, key="plot_lateral_geral")

        st.markdown("#### Modelo Tridimensional interativo")
        st.plotly_chart(plot_vista_3d(c_p, c_e, c_h, c_n, c_larg, c_L, c_H),
                        use_container_width=True, key="plot_3d_geral")

        st.markdown("---")
        st.markdown("### Resumo de Engenharia")
        st.info(f"""
        **Geometria:** Escada Reta de 1 Lance com desnível de {c_H} cm e vão horizontal de {c_L} cm. \
Composta por {c_n} espelhos de {c_e:.2f} cm e {c_np} pisos de {c_p} cm. \
Largura da laje: {c_larg} cm e espessura (h) = {c_h} cm.

        **Carregamento e Esforços:** Modelo {st.session_state.modelo}, \
Carga Majorada de {st.session_state.pd:.2f} kN/m², \
Momento de Cálculo ($M_d$) = {st.session_state.Md_knm:.2f} kN.m e \
Cortante ($V_d$) = {st.session_state.Vd_kn:.2f} kN.

        **Armaduras:** \
$A_{{s,principal}}$ = **{st.session_state.As_final:.2f} cm²/m** | \
$A_{{s,distribuição}}$ = **{st.session_state.As_dist:.2f} cm²/m**
        """)
