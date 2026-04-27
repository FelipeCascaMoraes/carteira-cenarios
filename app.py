import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from portfolio import Carteira, Ativo, CLASSES, CLASSES_CORES
from market_data import get_batch_prices, TESOURO_TITULOS
from simulator import simular_carteira, impacto_por_ativo
from agent import extrair_choque, narrar_resultado

# ─── Config ──────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Carteira", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

/* Fundo geral */
.stApp { background: #0a0a0f; }
section[data-testid="stSidebar"] { background: #0d0d14 !important; border-right: 1px solid #1e1e2e; }

/* Cards de métrica */
[data-testid="metric-container"] {
    background: #111118;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 1rem 1.2rem !important;
    transition: border-color 0.2s;
}
[data-testid="metric-container"]:hover { border-color: #4f8ef7; }
[data-testid="stMetricLabel"] { color: #555570 !important; font-size: 0.75rem !important; letter-spacing: 0.08em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: #e8e8f0 !important; font-family: 'DM Mono', monospace !important; font-size: 1.4rem !important; }
[data-testid="stMetricDelta"] { font-family: 'DM Mono', monospace !important; font-size: 0.85rem !important; }

/* Botão primário */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f8ef7, #7c5cfc) !important;
    color: #fff !important; border: none !important;
    border-radius: 8px !important; font-weight: 700 !important;
    letter-spacing: 0.03em;
    transition: opacity 0.2s, transform 0.1s;
}
.stButton > button[kind="primary"]:hover { opacity: 0.88; transform: translateY(-1px); }
.stButton > button:not([kind="primary"]) {
    background: #111118 !important; color: #8888aa !important;
    border: 1px solid #2a2a3a !important; border-radius: 8px !important;
    transition: all 0.2s;
}
.stButton > button:not([kind="primary"]):hover { border-color: #4f8ef7 !important; color: #e8e8f0 !important; }

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid #1e1e2e !important; border-radius: 10px; overflow: hidden; }

/* Inputs */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
    background: #111118 !important; border: 1px solid #2a2a3a !important;
    color: #e8e8f0 !important; border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
}
.stSelectbox > div > div {
    background: #111118 !important; border: 1px solid #2a2a3a !important;
    border-radius: 8px !important; color: #e8e8f0 !important;
}

/* Expander */
[data-testid="stExpander"] { background: #111118; border: 1px solid #1e1e2e; border-radius: 10px; }

/* Divider */
hr { border-color: #1e1e2e !important; }

/* Títulos */
h1, h2, h3 { color: #e8e8f0 !important; font-family: 'Syne', sans-serif !important; }
h1 { font-weight: 800; letter-spacing: -0.02em; }
h2 { font-weight: 700; }

/* Info/warning */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* Tag de classe */
.classe-tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Sidebar nav */
[data-testid="stRadio"] label {
    color: #8888aa !important;
    font-size: 0.9rem;
    padding: 6px 0;
    transition: color 0.2s;
}
[data-testid="stRadio"] label:has(input:checked) { color: #e8e8f0 !important; }

/* Chat message */
[data-testid="stChatMessage"] {
    background: #111118 !important;
    border: 1px solid #1e1e2e !important;
    border-radius: 12px !important;
}

/* Textarea */
textarea {
    background: #111118 !important; border: 1px solid #2a2a3a !important;
    color: #e8e8f0 !important; border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Estado ──────────────────────────────────────────────────────────────────

if "carteira" not in st.session_state:
    st.session_state.carteira = Carteira.carregar_json()
if "historico_simulacoes" not in st.session_state:
    st.session_state.historico_simulacoes = []

carteira: Carteira = st.session_state.carteira

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 📊 Carteira")
    st.caption("Monte Carlo · IA · Macro")
    st.divider()
    pagina = st.radio("nav", ["🏠  Carteira", "🔮  Simulador", "📈  Análise"],
                      label_visibility="collapsed")
    st.divider()
    if carteira.ativos:
        st.caption(f"**{len(carteira.ativos)}** ativos")
        pl = carteira.pl_total_pct
        cor = "🟢" if pl >= 0 else "🔴"
        st.caption(f"Patrimônio: **R$ {carteira.valor_total_atual:,.0f}**")
        st.caption(f"P&L total: {cor} **{pl:+.1f}%**")
    else:
        st.caption("Nenhum ativo cadastrado")

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — CARTEIRA
# ═══════════════════════════════════════════════════════════════════════════════

if pagina == "🏠  Carteira":
    st.title("Minha Carteira")

    # ── Formulário ───────────────────────────────────────────────────────────
    with st.expander("➕  Adicionar ativo", expanded=not carteira.ativos):

        tipo = st.radio("Tipo de ativo", ["Ação / FII / Cripto / Commodity", "Tesouro Direto"],
                        horizontal=True)

        c1, c2 = st.columns(2)
        with c1:
            if tipo == "Tesouro Direto":
                opcoes_tesouro = list(TESOURO_TITULOS.keys())
                ticker = st.selectbox("Título", opcoes_tesouro,
                                      format_func=lambda x: f"{x} — {TESOURO_TITULOS[x]}")
                nome = TESOURO_TITULOS[ticker]
                classe = "tesouro"
                st.info(f"Classe: Tesouro Direto")
            else:
                ticker = st.text_input("Ticker", placeholder="PETR4 / BTC / AAPL").upper().strip()
                nome   = st.text_input("Nome", placeholder="Ex: Petrobras PN")
                classe = st.selectbox("Classe", [k for k in CLASSES if k != "tesouro"],
                                      format_func=lambda x: CLASSES[x])
        with c2:
            quantidade  = st.number_input("Quantidade",  min_value=0.0, step=1.0,  value=1.0)
            preco_medio = st.number_input("Preço médio (R$)", min_value=0.0, step=0.01, value=0.0)
            st.caption("💡 Deixe o preço médio 0 se quiser buscar o preço atual automaticamente")

        if st.button("Adicionar à carteira", type="primary", use_container_width=True):
            if ticker and (preco_medio > 0 or tipo == "Tesouro Direto"):
                if preco_medio == 0:
                    with st.spinner("Buscando preço..."):
                        preco_medio = get_batch_prices([ticker]).get(ticker) or 0
                if preco_medio > 0:
                    carteira.adicionar(Ativo(ticker=ticker, nome=nome or ticker,
                                            classe=classe, quantidade=quantidade,
                                            preco_medio=preco_medio))
                    carteira.salvar_json()
                    st.success(f"✅ {ticker} adicionado!")
                    st.rerun()
                else:
                    st.error("Não foi possível buscar o preço. Insira manualmente.")
            else:
                st.error("Preencha ticker e preço médio.")

    if not carteira.ativos:
        st.info("Nenhum ativo ainda. Adicione acima para começar.")
        st.stop()

    # ── Ações ────────────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns([3, 1, 1])
    with col_a:
        if st.button("🔄  Atualizar preços de mercado", use_container_width=True):
            with st.spinner("Buscando preços..."):
                precos = get_batch_prices([a.ticker for a in carteira.ativos])
                nao_encontrados = []
                for t, p in precos.items():
                    if p:
                        carteira.atualizar_preco(t, p)
                    else:
                        nao_encontrados.append(t)
                carteira.salvar_json()
            if nao_encontrados:
                st.warning(f"Não encontrados: {', '.join(nao_encontrados)}")
            else:
                st.success("Preços atualizados!")
            st.rerun()
    with col_b:
        with st.expander("🗑️  Remover"):
            ticker_rem = st.selectbox("Ativo", [a.ticker for a in carteira.ativos],
                                      label_visibility="collapsed")
            if st.button("Remover", type="secondary", use_container_width=True):
                carteira.remover(ticker_rem)
                carteira.salvar_json()
                st.rerun()
    with col_c:
        if st.button("🧹  Limpar tudo", use_container_width=True):
            st.session_state.carteira = Carteira()
            Carteira().salvar_json()
            st.rerun()

    # ── Métricas ─────────────────────────────────────────────────────────────
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Investido",    f"R$ {carteira.valor_total_investido:,.2f}")
    m2.metric("📈 Valor Atual",  f"R$ {carteira.valor_total_atual:,.2f}")
    m3.metric("P&L (R$)",        f"R$ {carteira.pl_total_reais:+,.2f}",
              delta=f"{carteira.pl_total_pct:+.2f}%")
    m4.metric("Ativos",          len(carteira.ativos))

    # ── Tabela ───────────────────────────────────────────────────────────────
    st.divider()
    df = carteira.para_dataframe()

    def fmt_preco_atual(v):
        return f"R$ {v:.2f}" if v and not pd.isna(v) else "—"

    st.dataframe(
        df.style.format({
            "Preço Médio":    "R$ {:.2f}",
            "Preço Atual":    fmt_preco_atual,
            "Investido (R$)": "R$ {:,.2f}",
            "Atual (R$)":     "R$ {:,.2f}",
            "P&L (R$)":       "R$ {:+,.2f}",
            "P&L (%)":        "{:+.2f}%",
            "% Carteira":     "{:.1f}%",
        }).background_gradient(subset=["P&L (%)"], cmap="RdYlGn", vmin=-20, vmax=20),
        use_container_width=True,
        hide_index=True,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — SIMULADOR
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "🔮  Simulador":
    st.title("Simulador de Cenários")

    if not carteira.ativos:
        st.warning("Cadastre ativos na página Carteira primeiro.")
        st.stop()

    # ── Input ────────────────────────────────────────────────────────────────
    st.markdown("#### Descreva o cenário em português")

    exemplos = [
        "e se o dólar subir 20%?",
        "e se o Fed cortar juros em 1 ponto?",
        "crise global severa",
        "e se a Selic cair para 10%?",
        "petróleo desaba 30%",
    ]
    cols = st.columns(len(exemplos))
    for i, ex in enumerate(exemplos):
        if cols[i].button(ex, use_container_width=True):
            st.session_state.cenario_texto = ex
            st.rerun()

    cenario_texto = st.text_area(
        "cenario", value=st.session_state.get("cenario_texto", ""),
        placeholder="Ex: e se a Selic subir 2 pontos e o dólar cair 10%?",
        label_visibility="collapsed", height=80,
    )

    if st.button("🚀  Simular cenário", type="primary", use_container_width=True):
        if not cenario_texto.strip():
            st.error("Digite um cenário.")
            st.stop()

        # 1. Extração
        with st.spinner("🤖 Interpretando cenário..."):
            choque, resumo = extrair_choque(cenario_texto)

        st.info(f"**Interpretação:** {resumo}")

        choque_nz = {k: v for k, v in choque.items() if v != 0}
        if choque_nz:
            from macro_model import VARIAVEIS_MACRO
            cols_choque = st.columns(len(choque_nz))
            for i, (k, v) in enumerate(choque_nz.items()):
                cor = "normal" if v > 0 else "inverse"
                cols_choque[i].metric(VARIAVEIS_MACRO[k], f"{v:+.1f}%", delta_color=cor)

        # 2. Monte Carlo
        with st.spinner("⚙️ Rodando 10.000 simulações..."):
            resultado = simular_carteira(carteira, choque)

        # Salva histórico
        st.session_state.historico_simulacoes.append({
            "cenario": cenario_texto,
            "resumo": resumo,
            "p10": resultado.retorno_p10_pct,
            "p50": resultado.retorno_p50_pct,
            "p90": resultado.retorno_p90_pct,
            "impacto": resultado.impacto_choque_pct,
        })

        # 3. Métricas
        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Valor Atual",      f"R$ {resultado.valor_base:,.2f}")
        r2.metric("Pessimista (P10)", f"R$ {resultado.valor_p10:,.2f}",
                  delta=f"{resultado.retorno_p10_pct:+.1f}%")
        r3.metric("Mediano (P50)",    f"R$ {resultado.valor_p50:,.2f}",
                  delta=f"{resultado.retorno_p50_pct:+.1f}%")
        r4.metric("Otimista (P90)",   f"R$ {resultado.valor_p90:,.2f}",
                  delta=f"{resultado.retorno_p90_pct:+.1f}%")

        # 4. Histograma + tabela
        st.divider()
        col_hist, col_tab = st.columns([3, 2])

        with col_hist:
            st.markdown("#### Distribuição dos cenários")
            fig = go.Figure()

            # Área preenchida com gradiente
            fig.add_trace(go.Histogram(
                x=resultado.distribuicao, nbinsx=80,
                marker=dict(color="#4f8ef7", opacity=0.75,
                            line=dict(color="#1a1a2e", width=0.3)),
                name="Simulações",
            ))
            for val, label, cor, dash in [
                (resultado.valor_p10, "P10", "#f87171", "dash"),
                (resultado.valor_p50, "P50", "#fbbf24", "dash"),
                (resultado.valor_p90, "P90", "#34d399", "dash"),
                (resultado.valor_base, "Atual", "#e8e8f0", "solid"),
            ]:
                fig.add_vline(x=val, line_color=cor, line_dash=dash, line_width=1.5,
                              annotation_text=label, annotation_font_color=cor,
                              annotation_position="top")

            fig.update_layout(
                xaxis_title="Valor da carteira (R$)",
                yaxis_title="Frequência",
                plot_bgcolor="#0a0a0f", paper_bgcolor="#0a0a0f",
                font=dict(color="#8888aa", family="DM Mono"),
                xaxis=dict(gridcolor="#1e1e2e", zeroline=False),
                yaxis=dict(gridcolor="#1e1e2e", zeroline=False),
                showlegend=False, margin=dict(t=30, b=40, l=50, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_tab:
            st.markdown("#### Impacto por ativo")
            df_imp = impacto_por_ativo(carteira, choque).sort_values("Impacto (R$)")
            st.dataframe(
                df_imp.style.format({
                    "Valor Atual (R$)": "R$ {:,.2f}",
                    "Impacto (%)":      "{:+.2f}%",
                    "Impacto (R$)":     "R$ {:+,.2f}",
                }).background_gradient(subset=["Impacto (R$)"], cmap="RdYlGn"),
                use_container_width=True, hide_index=True,
            )

        # 5. Narrativa streaming
        st.divider()
        st.markdown("#### 🤖 Análise do assessor")
        tabela_ativos = carteira.para_dataframe()[
            ["Ticker", "Classe", "Atual (R$)", "% Carteira"]
        ].to_string(index=False)

        with st.chat_message("assistant"):
            st.write_stream(narrar_resultado_stream(
                cenario_texto, resumo, resultado, tabela_ativos
            ))

    # ── Histórico ────────────────────────────────────────────────────────────
    if st.session_state.historico_simulacoes:
        st.divider()
        st.markdown("#### 🕓 Histórico de simulações")
        df_hist = pd.DataFrame(st.session_state.historico_simulacoes)
        df_hist.columns = ["Cenário", "Interpretação", "P10 (%)", "P50 (%)", "P90 (%)", "Choque (%)"]
        st.dataframe(
            df_hist.style.format({
                "P10 (%)": "{:+.1f}%", "P50 (%)": "{:+.1f}%",
                "P90 (%)": "{:+.1f}%", "Choque (%)": "{:+.1f}%",
            }).background_gradient(subset=["P50 (%)"], cmap="RdYlGn", vmin=-30, vmax=30),
            use_container_width=True, hide_index=True,
        )
        if st.button("🗑️ Limpar histórico"):
            st.session_state.historico_simulacoes = []
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — ANÁLISE
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "📈  Análise":
    st.title("Análise da Carteira")

    if not carteira.ativos:
        st.warning("Cadastre ativos na página Carteira primeiro.")
        st.stop()

    df = carteira.para_dataframe()
    total = carteira.valor_total_atual

    # ── Linha 1: KPIs ────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Patrimônio",     f"R$ {total:,.2f}")
    k2.metric("P&L Total",      f"R$ {carteira.pl_total_reais:+,.2f}",
              delta=f"{carteira.pl_total_pct:+.1f}%")
    k3.metric("Ativos",         len(carteira.ativos))
    k4.metric("Classes",        df["Classe"].nunique())

    # Maior posição
    maior = df.loc[df["% Carteira"].idxmax()]
    k5.metric("Maior posição",  maior["Ticker"],
              delta=f"{maior['% Carteira']:.1f}% da carteira")

    st.divider()

    # ── Linha 2: Pizza + barras P&L ──────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Alocação por classe")
        aloc = carteira.alocacao_por_classe()
        labels = [CLASSES.get(k, k) for k in aloc]
        values = list(aloc.values())
        cores  = [CLASSES_CORES.get(k, "#4f8ef7") for k in aloc]

        fig_pie = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.55,
            marker=dict(colors=cores, line=dict(color="#0a0a0f", width=2)),
            textinfo="percent", textfont=dict(family="DM Mono", size=12, color="#e8e8f0"),
            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        ))
        fig_pie.add_annotation(
            text=f"<b>R$ {total:,.0f}</b>", x=0.5, y=0.5,
            font=dict(size=14, color="#e8e8f0", family="DM Mono"),
            showarrow=False,
        )
        fig_pie.update_layout(
            plot_bgcolor="#0a0a0f", paper_bgcolor="#0a0a0f",
            font=dict(color="#8888aa"),
            showlegend=True,
            legend=dict(font=dict(color="#8888aa", size=11), bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("#### P&L por ativo")
        df_pl = df.sort_values("P&L (R$)")
        cores_pl = ["#f87171" if v < 0 else "#34d399" for v in df_pl["P&L (R$)"]]

        fig_pl = go.Figure(go.Bar(
            x=df_pl["P&L (R$)"], y=df_pl["Ticker"],
            orientation="h",
            marker_color=cores_pl,
            text=df_pl["P&L (R$)"].apply(lambda v: f"R$ {v:+,.0f}"),
            textposition="outside",
            textfont=dict(family="DM Mono", size=11, color="#8888aa"),
            hovertemplate="<b>%{y}</b><br>P&L: R$ %{x:+,.2f}<extra></extra>",
        ))
        fig_pl.add_vline(x=0, line_color="#2a2a3a", line_width=1)
        fig_pl.update_layout(
            plot_bgcolor="#0a0a0f", paper_bgcolor="#0a0a0f",
            xaxis=dict(gridcolor="#1e1e2e", zeroline=False, tickfont=dict(family="DM Mono", color="#555570")),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(family="DM Mono", color="#e8e8f0")),
            font=dict(color="#8888aa"),
            margin=dict(t=20, b=20, l=10, r=80),
        )
        st.plotly_chart(fig_pl, use_container_width=True)

    st.divider()

    # ── Linha 3: Peso por ativo + alerta concentração ────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### Peso por ativo")
        df_peso = df.sort_values("% Carteira", ascending=True)
        fig_peso = go.Figure(go.Bar(
            x=df_peso["% Carteira"], y=df_peso["Ticker"],
            orientation="h",
            marker=dict(
                color=df_peso["% Carteira"],
                colorscale=[[0, "#1e3a5f"], [0.5, "#4f8ef7"], [1, "#7c5cfc"]],
                showscale=False,
            ),
            text=df_peso["% Carteira"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            textfont=dict(family="DM Mono", size=11, color="#8888aa"),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
        ))
        fig_peso.update_layout(
            plot_bgcolor="#0a0a0f", paper_bgcolor="#0a0a0f",
            xaxis=dict(gridcolor="#1e1e2e", zeroline=False,
                       tickfont=dict(family="DM Mono", color="#555570"),
                       ticksuffix="%"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)",
                       tickfont=dict(family="DM Mono", color="#e8e8f0")),
            margin=dict(t=20, b=20, l=10, r=60),
        )
        st.plotly_chart(fig_peso, use_container_width=True)

    with col4:
        st.markdown("#### Concentração e risco")

        # Alertas de concentração
        for _, row in df.iterrows():
            pct = row["% Carteira"]
            if pct > 30:
                st.error(f"⚠️ **{row['Ticker']}** representa **{pct:.1f}%** da carteira — alta concentração")
            elif pct > 20:
                st.warning(f"🟡 **{row['Ticker']}** representa **{pct:.1f}%** da carteira")

        # Score de diversificação (HHI simplificado)
        pesos = df["% Carteira"].values / 100
        hhi = np.sum(pesos ** 2)
        n_equiv = 1 / hhi if hhi > 0 else 1
        score = min(100, int(n_equiv / len(df) * 100 + (1 - hhi) * 60))

        st.metric("Score de diversificação", f"{score}/100",
                  delta="Bom" if score > 60 else "Melhorar",
                  delta_color="normal" if score > 60 else "inverse")

        # Breakdown por classe
        st.markdown("**Alocação por classe**")
        for classe, pct in sorted(carteira.alocacao_por_classe().items(),
                                  key=lambda x: -x[1]):
            cor = CLASSES_CORES.get(classe, "#4f8ef7")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 0;border-bottom:1px solid #1e1e2e">'
                f'<span style="color:#8888aa;font-size:0.85rem">{CLASSES.get(classe, classe)}</span>'
                f'<span style="color:{cor};font-family:DM Mono,monospace;font-size:0.85rem;font-weight:600">'
                f'{pct:.1f}%</span></div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Linha 4: Tabela completa ──────────────────────────────────────────────
    st.markdown("#### Visão detalhada")
    st.dataframe(
        df.style.format({
            "Preço Médio":    "R$ {:.2f}",
            "Investido (R$)": "R$ {:,.2f}",
            "Atual (R$)":     "R$ {:,.2f}",
            "P&L (R$)":       "R$ {:+,.2f}",
            "P&L (%)":        "{:+.2f}%",
            "% Carteira":     "{:.1f}%",
        }).background_gradient(subset=["P&L (%)"], cmap="RdYlGn", vmin=-20, vmax=20),
        use_container_width=True, hide_index=True,
    )
