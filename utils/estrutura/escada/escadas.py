import streamlit as st
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

def calcular_armadura_flexao(md, bw, d, fck, fyk=500):
    fcd = (fck / 10) / 1.4  # kN/cm²
    fyd = (fyk / 10) / 1.15 # kN/cm²
    kmd = md / (bw * (d ** 2) * fcd)
    if kmd > 0.32:
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
    # fctd = fctk,inf / 1.4
    fctm = 0.3 * (fck ** (2/3)) # MPa
    fctk_inf = 0.7 * fctm
    fctd = fctk_inf / 1.4
    
    # Taxa de armadura longitudinal rho = As / (bw * d) <= 0.02
    rho = as_efetiva / (bw * d)
    rho = min(rho, 0.02)
    
    # Tau_rd
    tau_rd = 0.25 * fctd # MPa
    tau_rd_kncm2 = tau_rd / 10 # convertendo para kN/cm2
    
    # k = | 1.6 - d| >= 1.0 (com d em metros)
    d_m = d / 100.0
    k = max(1.6 - d_m, 1.0)
    
    # Para simplificar, usamos a parcela base do concreto (sem considerar compressão axial).
    # Vr1 = [tau_rd * k * (1.2 + 40*rho)] * bw * d
    t_rd = tau_rd_kncm2 * k * (1.2 + 40 * rho)
    vr1 = t_rd * bw * d
    
    status = "OK" if vd <= vr1 else "FALHA"
    return vr1, status

def plot_vista_lateral(p, e, h, n_espelhos, L, H):
    fig = go.Figure()
    
    # Coordenadas do degrau
    x_steps = [0, 0]
    y_steps = [0, e]
    
    for i in range(n_espelhos - 1):
        x_steps.extend([(i+1)*p, (i+1)*p])
        y_steps.extend([y_steps[-1], y_steps[-1]+e])
        
    # Fundo da laje
    alpha = math.atan(e/p)
    h_vert = h / math.cos(alpha)
    
    x_poly = x_steps + [L, 0, 0]
    y_poly = y_steps + [H - h_vert, -h_vert, 0]
    
    # Concreto
    fig.add_trace(go.Scatter(x=x_poly, y=y_poly, fill='toself', fillcolor='rgba(150, 150, 150, 0.4)', mode='lines', line=dict(color='black', width=2), name='Elevação'))
    
    # Cotas principais
    fig.add_annotation(x=L/2, y=-h_vert-10, text=f"Vão Horizontal L = {L:.1f} cm", showarrow=False, font=dict(size=12, color="blue"))
    fig.add_annotation(x=-20, y=H/2, text=f"Desnível H = {H:.1f} cm", showarrow=False, textangle=-90, font=dict(size=12, color="blue"))
    
    fig.update_layout(
        title=f"Vista Lateral (Elevação) - {n_espelhos} Espelhos",
        xaxis_title="Comprimento (cm)",
        yaxis_title="Altura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=40, r=40, t=40, b=40),
        height=400,
        showlegend=False
    )
    return fig

def plot_vista_superior(p, n_pisos, L, largura):
    fig = go.Figure()
    
    # Contorno
    fig.add_trace(go.Scatter(
        x=[0, L, L, 0, 0], 
        y=[0, 0, largura, largura, 0], 
        mode='lines', 
        line=dict(color='black', width=3),
        fill='toself',
        fillcolor='rgba(200, 200, 200, 0.2)'
    ))
    
    # Linhas dos degraus
    for i in range(1, n_pisos):
        fig.add_trace(go.Scatter(
            x=[i*p, i*p], 
            y=[0, largura], 
            mode='lines', 
            line=dict(color='black', width=1)
        ))
        
    # Seta de subida
    fig.add_annotation(
        x=L-10, y=largura/2, ax=10, ay=largura/2,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=2, arrowwidth=2, arrowcolor="red"
    )
    fig.add_annotation(x=L/2, y=largura/2 + 10, text="Sentido de Subida", showarrow=False, font=dict(color="red"))
    fig.add_annotation(x=L/2, y=-15, text=f"Comprimento Total = {L:.1f} cm", showarrow=False)
    fig.add_annotation(x=-15, y=largura/2, text=f"Largura = {largura:.1f} cm", showarrow=False, textangle=-90)

    fig.update_layout(
        title="Vista Superior (Planta)",
        xaxis_title="Comprimento (cm)",
        yaxis_title="Largura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
        showlegend=False
    )
    return fig

def plot_vista_3d(p, e, h, n_espelhos, largura, L, H):
    traces = []
    
    # Construção de faces em 3D
    for i in range(n_espelhos):
        # Espelho (Riser)
        traces.append(go.Mesh3d(
            x=[i*p, i*p, i*p, i*p],
            y=[0, largura, largura, 0],
            z=[i*e, i*e, (i+1)*e, (i+1)*e],
            i=[0, 0], j=[1, 2], k=[2, 3],
            color='lightblue', flatshading=True
        ))
        # Piso (Tread)
        if i < n_espelhos - 1:
            traces.append(go.Mesh3d(
                x=[i*p, (i+1)*p, (i+1)*p, i*p],
                y=[0, largura, largura, 0],
                z=[(i+1)*e, (i+1)*e, (i+1)*e, (i+1)*e],
                i=[0, 0], j=[1, 2], k=[2, 3],
                color='gray', flatshading=True
            ))
            
    # Laje inferior (Fundo)
    alpha = math.atan(e/p)
    h_vert = h / math.cos(alpha)
    traces.append(go.Mesh3d(
        x=[0, L, L, 0],
        y=[0, largura, largura, 0],
        z=[-h_vert, H - e - h_vert, H - e - h_vert, -h_vert],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color='darkgray', flatshading=True
    ))
    
    # Wireframe Lateral Esq e Dir
    x_wire = [0, 0]
    z_wire = [0, e]
    for i in range(n_espelhos - 1):
        x_wire.extend([(i+1)*p, (i+1)*p])
        z_wire.extend([z_wire[-1], z_wire[-1]+e])
    x_wire.extend([L, 0, 0])
    z_wire.extend([H - h_vert, -h_vert, 0])
    
    traces.append(go.Scatter3d(x=x_wire, y=[0]*len(x_wire), z=z_wire, mode='lines', line=dict(color='black', width=4)))
    traces.append(go.Scatter3d(x=x_wire, y=[largura]*len(x_wire), z=z_wire, mode='lines', line=dict(color='black', width=4)))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title="Visualização 3D da Escada",
        scene=dict(
            xaxis_title='Comprimento (X)',
            yaxis_title='Largura (Y)',
            zaxis_title='Altura (Z)',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=500,
        showlegend=False
    )
    return fig

def plot_carregamentos(L, pd):
    fig = go.Figure()
    # Viga
    fig.add_trace(go.Scatter(x=[0, L], y=[0, 0], mode='lines', line=dict(color='black', width=4), name='Eixo da Escada (Projeção)'))
    
    # Bloco de carga
    x_load = [0, 0, L, L, 0]
    y_load = [0, pd, pd, 0, 0]
    fig.add_trace(go.Scatter(x=x_load, y=y_load, fill='toself', fillcolor='rgba(255, 0, 0, 0.2)', mode='lines', line=dict(color='red', width=1), name='Carga (pd)'))
    
    for i in np.linspace(0, L, num=10):
        fig.add_annotation(
            x=i, y=0, ax=i, ay=pd,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="red"
        )
        
    fig.update_layout(
        title=f"Esquema Estático de Cargas (pd = {pd:.2f} kN/m²)",
        xaxis_title="Vão L (m)",
        yaxis_title="Carga (kN/m²)",
        yaxis=dict(range=[-pd*0.2, pd*1.2]),
        margin=dict(l=20, r=20, t=40, b=20),
        height=250
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
        
    fig = make_subplots(rows=1, cols=2, subplot_titles=(f"Momento Fletor (M) - Máx: {abs(max(M, key=abs)):.2f} kN.m", f"Esforço Cortante (V) - Máx: {abs(max(V, key=abs)):.2f} kN"))
    
    fig.add_trace(go.Scatter(x=x, y=M, fill='tozeroy', mode='lines', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=V, fill='tozeroy', mode='lines', line=dict(color='green')), row=1, col=2)
    
    if "Bi-apoiada" in modelo or "Transversalmente" in modelo:
        fig.update_yaxes(autorange="reversed", row=1, col=1) 
        
    fig.update_layout(height=350, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def plot_detalhamento(h, cobrimento, As_calc, As_dist, modelo, phi_mm):
    fig = go.Figure()
    
    # Seção Concreto (100cm x h)
    fig.add_trace(go.Scatter(x=[0, 100, 100, 0, 0], y=[0, 0, h, h, 0], fill='toself', fillcolor='rgba(200,200,200,0.5)', mode='lines', line=dict(color='black', width=2), name='Concreto'))
    
    is_balanco = "Balanço" in modelo
    rebar_y = h - cobrimento - (phi_mm/20) if is_balanco else cobrimento + (phi_mm/20)
    
    # Barras principais
    num_bars = int(max(As_calc / ((math.pi * (phi_mm/10)**2)/4), 3))
    x_bars = np.linspace(cobrimento+2, 100 - cobrimento - 2, num=num_bars)
    y_bars = [rebar_y] * num_bars
    
    fig.add_trace(go.Scatter(x=x_bars, y=y_bars, mode='markers', marker=dict(color='red', size=8), name=f'Armad. Principal ({num_bars} barras)'))
    
    # Barras de distribuição
    dist_y = rebar_y - 1 if is_balanco else rebar_y + 1
    fig.add_trace(go.Scatter(x=[cobrimento, 100-cobrimento], y=[dist_y, dist_y], mode='lines', line=dict(color='blue', width=3), name='Armad. Distribuição'))
    
    fig.update_layout(
        title="Seção Transversal da Laje (1 metro de largura)",
        xaxis_title="Largura (cm)",
        yaxis_title="Altura (cm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    return fig

def plot_empuxo_vazio():
    fig = go.Figure()
    # Concreto (L shape inverted for stair to landing)
    fig.add_trace(go.Scatter(x=[0, 50, 100, 100, 40, 0], y=[50, 0, 0, -20, -20, 30], fill='toself', fillcolor='rgba(200,200,200,0.3)', mode='lines', line=dict(color='gray', width=2), name='Geometria da Escada'))
    
    # Errado
    fig.add_trace(go.Scatter(x=[5, 45, 95], y=[45, -5, -5], mode='lines', line=dict(color='red', dash='dash', width=3), name='ERRADO (Gera Empuxo ao Vazio)'))
    
    # Correto
    fig.add_trace(go.Scatter(x=[5, 60], y=[45, -15], mode='lines', line=dict(color='green', width=3), name='CORRETO (Armaduras se cruzam)'))
    fig.add_trace(go.Scatter(x=[35, 95], y=[10, -5], mode='lines', line=dict(color='green', width=3), showlegend=False))
    
    fig.update_layout(
        title="Regra de Detalhamento em Transições de Lances",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=40, b=20),
        height=300
    )
    return fig

def show():
    st.header("Dimensionamento de Escadas - Projeto Completo", divider="blue")
    
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

    if 'H_total' not in st.session_state: st.session_state.H_total = 280.0
    if 'e_desejado' not in st.session_state: st.session_state.e_desejado = 17.5
    if 'largura' not in st.session_state: st.session_state.largura = 120.0
    if 'p_adotado' not in st.session_state: st.session_state.p_adotado = 28.0
    if 'h_laje' not in st.session_state: st.session_state.h_laje = 12.0
    if 'pd' not in st.session_state: st.session_state.pd = 0.0

    with tab_geo:
        st.subheader("Parâmetros Geométricos (Geração Automática do Lance)")
        
        col1, col2 = st.columns(2)
        with col1:
            H = st.number_input("Desnível Piso a Piso (H) [cm]:", min_value=50.0, value=st.session_state.H_total, step=5.0)
            e_desejado = st.number_input("Espelho Desejado (e) [cm]:", min_value=15.0, max_value=19.0, value=st.session_state.e_desejado, step=0.1)
        with col2:
            p = st.number_input("Piso / Passo (p) [cm]:", min_value=25.0, max_value=32.0, value=st.session_state.p_adotado, step=0.5)
            largura = st.number_input("Largura da Escada [cm]:", min_value=70.0, max_value=300.0, value=st.session_state.largura, step=5.0)
            
        h = st.number_input("Espessura da Laje (h) [cm]:", min_value=8.0, max_value=30.0, value=st.session_state.h_laje, step=1.0)
        
        st.session_state.H_total = H
        st.session_state.e_desejado = e_desejado
        st.session_state.p_adotado = p
        st.session_state.largura = largura
        st.session_state.h_laje = h

        # Cálculos de Geometria Exata
        n_espelhos = max(1, round(H / e_desejado))
        e_real = H / n_espelhos
        n_pisos = n_espelhos - 1
        L_real = n_pisos * p
        
        st.session_state.n_espelhos = n_espelhos
        st.session_state.e_real = e_real
        st.session_state.n_pisos = n_pisos
        st.session_state.L_real = L_real

        st.markdown("### Resumo Geométrico Calculado")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Qtd. Espelhos", f"{n_espelhos}")
        c2.metric("Qtd. Pisos", f"{n_pisos}")
        c3.metric("Espelho Real (e)", f"{e_real:.2f} cm")
        c4.metric("Comprimento (L)", f"{L_real:.1f} cm")

        blondel = 2 * e_real + p
        if 60 <= blondel <= 64:
            st.success(f"**Verificação de Conforto (Blondel):** {blondel:.1f} cm (Ideal)")
        else:
            st.warning(f"**Verificação de Conforto (Blondel):** {blondel:.1f} cm (Fora do ideal: 60 - 64 cm)")

        alpha_rad = math.atan(e_real / p)
        st.session_state.cos_alpha = math.cos(alpha_rad)
        
        # Injetando o gráfico dinâmico lateral na aba de Geometria!
        st.plotly_chart(plot_vista_lateral(p, e_real, h, n_espelhos, L_real, H), use_container_width=True, key="plot_lateral_geo")

    with tab_cargas:
        st.subheader("Levantamento de Ações (kN/m²)")
        h1 = h / st.session_state.cos_alpha
        h_media = h1 + (st.session_state.e_real / 2)
        pp_escada = (h_media / 100) * 25.0

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Permanentes (g)")
            revest = st.number_input("Revestimentos [kN/m²]:", min_value=0.0, value=1.0, step=0.1)
            # Guarda-corpo e Alvenaria transformados em carga por m2
            carga_lin_gc = st.number_input("Carga Linear (Guarda-Corpo/Parede) [kN/m]:", min_value=0.0, value=0.0, step=0.1, help="Ex: 0.8 kN/m para guarda-corpo")
            # Converte a carga linear distribuindo na largura da laje
            carga_gc_area = carga_lin_gc / (st.session_state.largura / 100.0) if st.session_state.largura > 0 else 0.0
            
            g_total = pp_escada + revest + carga_gc_area
            
            st.write(f"Espessura Média ($h_m$): {h_media:.2f} cm")
            if carga_lin_gc > 0:
                st.write(f"Guarda-Corpo/Parede convertido: {carga_gc_area:.2f} kN/m²")
            st.metric("Total Permanente (g)", f"{g_total:.2f} kN/m²")

        with col2:
            st.markdown("#### Variáveis (q)")
            tipo_uso = st.radio("Utilização:", ["Sem acesso público (2.5 kN/m²)", "Com acesso público (3.0 kN/m²)"])
            q_acidental = 2.5 if "Sem" in tipo_uso else 3.0
            st.metric("Total Acidental (q)", f"{q_acidental:.2f} kN/m²")

        pd = (1.4 * g_total) + (1.4 * q_acidental)
        st.session_state.pd = pd
        st.success(f"**Carga de Cálculo (ELU):** {pd:.2f} kN/m²")
        
        if pd > 0:
            st.plotly_chart(plot_carregamentos(st.session_state.L_real / 100.0, pd), use_container_width=True)

    with tab_esforcos:
        st.subheader("Modelagem e Esforços")
        modelo = st.selectbox("Modelo Estrutural Simplificado", [
            "Escada Armada Longitudinalmente (Bi-apoiada)",
            "Escada Armada Transversalmente (Apoiada em vigas laterais)",
            "Escada em Balanço (Engastada em um lado)"
        ])
        st.session_state.modelo = modelo
        
        vao_L = st.session_state.L_real / 100.0
        st.info(f"O Vão Teórico calculado automaticamente é **{vao_L:.2f} m**.")
        
        if pd > 0:
            if "Bi-apoiada" in modelo or "Transversalmente" in modelo:
                Md = (pd * (vao_L ** 2)) / 8
                Vd = (pd * vao_L) / 2
            else:
                Md = (pd * (vao_L ** 2)) / 2
                Vd = pd * vao_L
                
            st.session_state.Md_knm = Md
            st.session_state.Vd_kn = Vd

            st.plotly_chart(plot_esforcos(vao_L, pd, modelo), use_container_width=True)

    with tab_armaduras:
        st.subheader("Dimensionamento ao ELU")
        
        col1, col2, col3 = st.columns(3)
        fck = col1.number_input("fck [MPa]:", min_value=20, max_value=50, value=25, step=5)
        cobrimento = col2.number_input("Cobrimento [cm]:", min_value=1.5, max_value=5.0, value=2.0, step=0.5)
        bitola_est = col3.selectbox("Bitola Principal ($\phi$) [mm]:", [8.0, 10.0, 12.5, 16.0], index=1)
        
        d_util = st.session_state.h_laje - cobrimento - (bitola_est / 20.0)
        Md_cm = st.session_state.Md_knm * 100 
        
        As_calc = calcular_armadura_flexao(Md_cm, 100.0, d_util, fck)
        
        if As_calc is None:
            st.error("Seção requer armadura dupla ou redimensionamento da espessura!")
            st.session_state.As_final = 0
            st.session_state.As_dist = 0
        else:
            As_min = 0.0015 * 100.0 * st.session_state.h_laje
            As_final = max(As_calc, As_min)
            As_dist = max(As_final / 5.0, 0.90)
            
            st.session_state.As_final = As_final
            st.session_state.As_dist = As_dist
            
            col_res1, col_res2 = st.columns(2)
            col_res1.metric("Área de Aço Principal ($A_s$)", f"{As_final:.2f} cm²/m")
            col_res2.metric("Área de Aço Distribuição", f"{As_dist:.2f} cm²/m")
            
            # Verificação de cisalhamento Vd <= Vr1
            st.markdown("#### Verificação ao Esforço Cortante (Sem Estribos)")
            vr1, status_cisalhamento = verificar_cisalhamento(st.session_state.Vd_kn, 100.0, d_util, fck, As_final)
            if status_cisalhamento == "OK":
                st.success(f"**Verificação Atendida:** $V_{{sd}}$ ({st.session_state.Vd_kn:.2f} kN) $\le V_{{R1}}$ ({vr1:.2f} kN). A laje suporta o cisalhamento sem armadura transversal.")
            else:
                st.error(f"**Falha ao Cisalhamento:** $V_{{sd}}$ ({st.session_state.Vd_kn:.2f} kN) $> V_{{R1}}$ ({vr1:.2f} kN). É obrigatório o uso de armadura transversal (estribos) ou aumento da espessura da laje!")
            
            st.plotly_chart(plot_detalhamento(st.session_state.h_laje, cobrimento, As_final, As_dist, st.session_state.modelo, bitola_est), use_container_width=True)
            
            st.markdown("### ⚠️ Cuidado com Empuxo ao Vazio!")
            st.plotly_chart(plot_empuxo_vazio(), use_container_width=True)
            
            st.success("Dimensionamento à flexão concluído com sucesso!")

    with tab_geral:
        st.subheader("Visão Geral do Projeto Geométrico")
        st.markdown("Abaixo estão as 3 representações do arranjo físico completo da escada gerada a partir das especificações de desnível e pisada.")
        
        c_p = st.session_state.p_adotado
        c_e = st.session_state.e_real
        c_h = st.session_state.h_laje
        c_n = st.session_state.n_espelhos
        c_np = st.session_state.n_pisos
        c_L = st.session_state.L_real
        c_H = st.session_state.H_total
        c_larg = st.session_state.largura
        
        # Criação de duas colunas para a Planta e o Corte
        col_plot1, col_plot2 = st.columns(2)
        
        with col_plot1:
            # 2. Vista Superior (Planta)
            st.plotly_chart(plot_vista_superior(c_p, c_np, c_L, c_larg), use_container_width=True)
            
        with col_plot2:
            # 1. Vista Lateral (Elevação)
            st.plotly_chart(plot_vista_lateral(c_p, c_e, c_h, c_n, c_L, c_H), use_container_width=True, key="plot_lateral_geral")
        
        # 3. Vista 3D ocupando a largura total (ou também pode ir para colunas)
        st.markdown("#### Modelo Tridimensional interativo")
        st.plotly_chart(plot_vista_3d(c_p, c_e, c_h, c_n, c_larg, c_L, c_H), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### Resumo de Engenharia")
        st.info(f"""
        **Geometria:** Escada Reta de 1 Lance com desnível de {c_H} cm e vão horizontal de {c_L} cm. Composta por {c_n} espelhos de {c_e:.2f} cm e {c_np} pisos de {c_p} cm. Largura da laje: {c_larg} cm e espessura (h) = {c_h} cm. \n
        **Carregamento e Esforços:** Modelo {st.session_state.modelo}, Carga Majorada de {st.session_state.pd:.2f} kN/m², suportando um Momento Fletor de Cálculo ($M_d$) de {st.session_state.Md_knm:.2f} kN.m e Cortante ($V_d$) de {st.session_state.Vd_kn:.2f} kN. \n
        **Armaduras:** O detalhamento exige o arranjo de **{st.session_state.As_final:.2f} cm²/m** para a armadura principal e **{st.session_state.As_dist:.2f} cm²/m** para a armadura de distribuição (transversal).
        """)