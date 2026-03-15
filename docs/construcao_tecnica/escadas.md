# Memorial Técnico e Normativo: Dimensionamento de Escadas em Concreto Armado

Este documento consolida os princípios teóricos, exigências normativas (NBR 6118, NBR 6120) e diretrizes de cálculo estrutural extraídas das referências técnicas clássicas (Araújo, UFRGS, USP e UFBA) para o dimensionamento de escadas em concreto armado. 

O conteúdo aqui documentado servirá de base arquitetural e analítica para o desenvolvimento da interface e do motor de cálculo em Python (`utils/estrutura/escada/escadas.py`).

---

## 1. Concepção Geométrica e Conforto

A definição geométrica da escada é o primeiro passo do dimensionamento, garantindo não apenas a sua funcionalidade arquitetônica, mas a integridade biomecânica e conforto do usuário (Fórmula de Blondel).

* **Piso (p) ou Passo:** Largura do degrau. Recomendado entre 26 cm e 32 cm.
* **Espelho (e):** Altura do degrau. Recomendado entre 16 cm e 19 cm.
* **Fórmula de Blondel:** $2e + p = \text{60 a 64 cm}$ (Usualmente fixado o valor de 63 ou 64 cm para otimização).
* **Ângulo de Inclinação ($\alpha$):** $\cos(\alpha) = \frac{p}{\sqrt{p^2 + e^2}}$ ou $\tan(\alpha) = \frac{e}{p}$.

### Limites Práticos de Largura da Escada
* Secundárias / Serviço: 70 a 90 cm.
* Residenciais / Escritórios: Mínimo de 100 cm a 120 cm.

---

## 2. Levantamento de Cargas (NBR 6120)

As escadas são modeladas estruturalmente sob a ação de cargas verticais uniformemente distribuídas por projeção horizontal ($m^2$).

### 2.1. Peso Próprio (Carga Permanente - g1)
A escada não possui espessura constante ao longo da sua seção transversal real devido aos degraus. Modela-se a laje através de uma **espessura média ($h_m$)**.

* **No trecho inclinado:**
  * Espessura vertical ($h_1$): $h_1 = \frac{h}{\cos(\alpha)}$ onde $h$ é a espessura efetiva da garganta da laje.
  * Espessura média com os degraus ($h_m$): $h_m = h_1 + \frac{e}{2}$
  * Carga do peso próprio ($g_{pp}$): $g_{pp} = h_m \times \gamma_{concreto}$ (adotar $\gamma_c = 25 \text{ kN/m}^3$).
* **Nos patamares:**
  * A laje é plana, sem degraus. Espessura é o próprio $h$.
  * Carga do peso próprio ($g_{patamar}$): $g_p = h \times 25 \text{ kN/m}^3$.

### 2.2. Revestimentos e Acabamentos (Carga Permanente - g2)
* Piso, contrapiso e reboco inferior costumam ser admitidos na faixa de **0,8 a 1,2 kN/m²** (projeção horizontal).

### 2.3. Cargas Variáveis / Acidentais (q)
Adotadas conforme o tipo de utilização, projetadas horizontalmente:
* Escadas **sem acesso público** (residências unifamiliares): **2,5 kN/m²**.
* Escadas **com acesso ao público** (escritórios, edifícios residenciais, comércio): **3,0 kN/m²**.

### 2.4. Ações Complementares (Guarda-corpos e Paredes)
* Carga linear nas bordas para muretas de tijolos ou guarda-corpos. 
* Em escadas armadas longitudinalmente, a carga linear do guarda-corpo ($P_{gc}$ em kN/m) deve ser dividida pela largura da escada para ser convertida em carga por área ($\frac{P_{gc}}{L}$).
* Se existirem degraus isolados, verificar também o ELU com **carga concentrada de 2,5 kN** aplicada na posição mais desfavorável (ponta do balanço).

---

## 3. Tipologias Estruturais e Modelos Analíticos

Escadas podem ser tratadas como lajes ou vigas inclinadas em diversos arranjos estáticos. O módulo computacional deve prever os seguintes arranjos principais:

### 3.1. Escada Armada Transversalmente
* Laje com vão livre correspondente à largura da escada (vão $L$). 
* Apoia-se em duas vigas laterais inclinadas ou paredes.
* **Solicitações:**
  * Momento Fletor ($M_{d,max}$): $M = \frac{p \cdot L^2}{8}$
  * Esforço Cortante ($V_{d,max}$): $V = \frac{p \cdot L}{2}$

### 3.2. Escada Armada Longitudinalmente
* Laje cujos apoios são transversais ao sentido do tráfego (geralmente patamares ou vigas de patamar no topo e base do lance).
* Modelada como uma viga isostática inclinada projetada no plano horizontal.
* Comprimento do Vão ($l$): Vão horizontal de apoio a apoio.
* **Solicitações:**
  * Momento Fletor: $M = \frac{p \cdot l^2}{8}$
  * Esforço Cortante: A força cortante atuante perpendicular ao eixo inclinado da laje sofre a influência da inclinação: $V_x = \frac{p \cdot l}{2} \cdot \cos(\alpha)$.
  * Força Normal: Nas escadas biapoiadas comuns (apoios do tipo rolete e pino), surge um pequeno esforço normal de compressão/tração $N_x = \frac{p \cdot l}{2} \cdot \text{sen}(\alpha)$. Geralmente desprezado no cálculo de flexão simples.

### 3.3. Escada em Balanço (Engastada em Viga Lateral)
* Cada degrau, ou a laje inteira, fica engastada em apenas uma viga/parede lateral.
* **Solicitações:**
  * Momento Fletor na raiz: $M = -\left(\frac{p \cdot L^2}{2} + P_{gc} \cdot L\right)$
  * Atenção especial à torção repassada para a viga de suporte lateral.

### 3.4. Escadas de Dois Lances com Patamar Intermediário (Configurações L, U)
* O patamar pode ser considerado uma laje armada em cruz apoiando o lance inclinado (reações de apoio transferidas).
* Em processos simplificados, o lance inclinado descarrega uma reação na laje do patamar, e o sistema é resolvido como um carregamento misto contínuo.
* **Intersecções ortogonais:** As armaduras de flexão de um lance devem se sobrepor ao outro de forma cautelosa. Sempre colocar por baixo a armadura principal da laje primária de apoio.

---

## 4. Dimensionamento e Detalhamento em Concreto Armado (ELU)

### 4.1. Dimensionamento à Flexão Simples
Trata-se de uma seção retangular de base $b = 100 \text{ cm}$ e altura $h$ (espessura da garganta da escada).
1. Altura útil: $d = h - c - \frac{\phi}{2}$ ($c$ = cobrimento).
2. Cálculo da linha neutra ($x$) e área de aço ($A_s$) por metro linear, seguindo o equacionamento clássico ou tabelas universais $K_c$, $K_s$:
   * $A_s = \frac{M_{d}}{z \cdot f_{yd}}$

### 4.2. Armaduras Mínimas e de Distribuição
* **Armadura Principal Mínima ($A_{s,min}$):**
  * Para aços CA-50, $0,15\%$ da seção de concreto efetiva: $A_{s,min} = 0,0015 \cdot 100 \cdot h$.
* **Armadura de Distribuição Secundária ($A_{s,dist}$):** 
  A armadura secundária transversal garante o travamento da malha e distribuição pontual de carga. Deve ser o maior valor entre:
  * $\frac{A_{s,principal}}{5}$
  * $0,90 \text{ cm}^2/\text{m}$ (ex: $3$ barras por metro - $\phi 5.0 \text{ c/} 33$).

### 4.3. Verificação do Esforço Cortante ($V_{sd}$)
As escadas maciças geralmente dispensam armaduras transversais (estribos). Deve-se garantir imperativamente que $V_{sd} \le V_{R1}$ (força cortante resistente para peças sem estribos), dada por:
$$ V_{R1} = \tau_{wd} \cdot b_w \cdot d $$
Onde o valor da tensão varia normativamente dependendo da taxa de armadura tracionada da seção e do tipo de concreto.

### 4.4. Fenômeno de Empuxo ao Vazio e Detalhamento em Nós
**Esta é a falha mais comum e catastrófica no projeto de escadas de lances angulados:**
* Quando ocorre a inflexão do lance inclinado para o patamar (ângulo côncavo interno de armadura tracionada), a força resultante de tração das barras tenta se "retificar", causando o chamado **Empuxo ao Vazio**. 
* Se a barra for dobrada diretamente acompanhando a geometria do concreto no canto interno reentrante, a força resultante arrancará o cobrimento de concreto de cima e a escada irá ceder.
* **Regra OBRIGATÓRIA de detalhamento:** No cruzamento de inflexão interna (lance -> patamar superior), as barras NUNCA podem ser dobradas contínuas internamente. Elas devem se **cruzar**, de forma que a armadura inferior do lance inclinado atravesse a seção e ancore no banzo superior do patamar, e vice-versa (ver detalhe gráfico clássico em tesoura).

---

## 5. Passos para a Estruturação do Módulo Python (`utils/estrutura/escada/escadas.py`)

A interface Streamlit que será construída deve refletir as fases deste memorial em um fluxo procedural (Wizard) de projeto:

1. **Aba de Parâmetros de Geometria:** Inputs para (h_piso a piso, comprimento disponível, $p$, $e$). Validação imediata com a Fórmula de Blondel.
2. **Aba de Carregamentos:** Seleção do uso (Público/Privado), tipo de acabamento, e inputs dinâmicos para guarda-corpo. O motor calculará automaticamente $h_{media}$ e gerará a carga total $p_d \ (\text{ELU})$.
3. **Aba de Esforços Analíticos:** O usuário escolhe o tipo estático da escada (Longitudinal bi-apoiada, Transversal, Balanço, L/U). A interface plota o diagrama de momento fletor (ex: $M = qL^2/8$).
4. **Aba de Armaduras:** Output final das armaduras (Principal longitudinal, Secundária de distribuição), com indicação de bitolas ($\phi$) e espaçamentos (cm), garantindo os critérios de $A_{s,min}$.
5. **Painel de Avisos:** Alertas dinâmicos recomendando cruzamento de armaduras (empuxo ao vazio) em casos de lances angulados.

---
**Fim do Memorial.**