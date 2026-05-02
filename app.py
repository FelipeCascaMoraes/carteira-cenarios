import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from portfolio import Carteira, Ativo, CLASSES, CLASSES_CORES
from market_data import get_batch_prices, TESOURO_TITULOS
from simulator import simular_carteira, impacto_por_ativo
from agent import extrair_choque
from agent_chat import narrar_resultado_stream, chat_stream, sugerir_rebalanceamento_stream
from stress_test import CENARIOS_HISTORICOS, rodar_todos
from risk_metricks import calcular_metricas, interpretar_sharpe, interpretar_drawdown
from analytics import (
    retorno_acumulado_carteira,
    acumulado_benchmarks,
    matriz_correlacao,
)

# ─── Config ──────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Carteira", page_icon="📊", layout="wide")

BG       = "#0f172a"
SURFACE  = "#1e293b"
BORDER   = "#334155"
MUTED    = "#64748b"
TEXT_SEC = "#94a3b8"
TEXT_PRI = "#e2e8f0"
ACCENT   = "#475569"

TEXT = TEXT_PRI
POS  = "#4ade80"
NEG  = "#f87171"

PLOT_LAYOUT = dict(
    plot_bgcolor=BG, paper_bgcolor=BG,
    font=dict(color=TEXT_SEC, family="DM Mono"),
    xaxis=dict(gridcolor=BORDER, zeroline=False),
    yaxis=dict(gridcolor=BORDER, zeroline=False),
    margin=dict(t=30, b=40, l=50, r=20),
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {{ font-family: 'Syne', sans-serif; }}

.stApp {{ background: {BG}; }}
section[data-testid="stSidebar"] {{ background: {BG} !important; border-right: 1px solid {BORDER}; }}

header[data-testid="stHeader"], [data-testid="stToolbar"] {{ background: {BG} !important; }}
header {{ background-color: {BG} !important; }}

/* Chat input — seletores atualizados */
div[data-testid="stChatInput"] {{
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
}}
div[data-testid="stChatInput"] > div {{
    background: #1e293b !important;
    border-radius: 12px !important;
}}
div[data-testid="stChatInput"] textarea {{
    background: #1e293b !important;
    color: #e2e8f0 !important;
}}
div[data-testid="stChatInput"]:focus-within {{
    border-color: #475569 !important;
    box-shadow: none !important;
}}

/* Container fixo no fundo */
[data-testid="stBottom"] > div {{
    background: #0f172a !important;
    border-top: 1px solid #334155 !important;
}}

p, span, li {{ color: {TEXT_SEC}; }}
strong {{ color: {TEXT_PRI} !important; }}
h1, h2, h3, h4 {{ color: {TEXT_PRI} !important; font-family: 'Syne', sans-serif !important; }}
h1 {{ font-weight: 800; letter-spacing: -0.02em; }}
h2 {{ font-weight: 700; }}

[data-testid="stMarkdownContainer"] p {{ color: {TEXT_SEC}; }}
[data-testid="stMarkdownContainer"] h4 {{ color: {TEXT_PRI} !important; }}
[data-testid="stCaptionContainer"] p {{ color: {MUTED} !important; }}
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label {{ color: {TEXT_SEC} !important; }}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div {{ color: {TEXT_SEC} !important; }}
section[data-testid="stSidebar"] strong {{ color: {TEXT_PRI} !important; }}

[data-testid="metric-container"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1rem 1.2rem !important;
    transition: border-color 0.2s;
}}
[data-testid="metric-container"]:hover {{ border-color: {MUTED}; }}
[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-size: 0.75rem !important; letter-spacing: 0.08em; text-transform: uppercase; }}
[data-testid="stMetricValue"] {{ color: {TEXT_PRI} !important; font-family: 'DM Mono', monospace !important; font-size: 1.4rem !important; }}
[data-testid="stMetricDelta"] {{ font-family: 'DM Mono', monospace !important; font-size: 0.85rem !important; }}

.stButton > button[kind="primary"] {{
    background: {ACCENT} !important;
    color: {TEXT_PRI} !important; border: none !important;
    border-radius: 8px !important; font-weight: 700 !important;
    letter-spacing: 0.03em;
    transition: background 0.2s, transform 0.1s;
}}
.stButton > button[kind="primary"]:hover {{ background: {MUTED} !important; transform: translateY(-1px); }}
.stButton > button:not([kind="primary"]) {{
    background: {SURFACE} !important; color: {TEXT_SEC} !important;
    border: 1px solid {BORDER} !important; border-radius: 8px !important;
    transition: all 0.2s;
}}
.stButton > button:not([kind="primary"]):hover {{ border-color: {MUTED} !important; color: {TEXT_PRI} !important; }}

[data-testid="stDataFrame"] {{ border: 1px solid {BORDER} !important; border-radius: 10px; overflow: hidden; }}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{
    background: {SURFACE} !important; border: 1px solid {BORDER} !important;
    color: {TEXT_PRI} !important; border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
}}
::placeholder {{ color: {MUTED} !important; opacity: 1; }}
.stSelectbox > div > div {{
    background: {SURFACE} !important; border: 1px solid {BORDER} !important;
    border-radius: 8px !important; color: {TEXT_PRI} !important;
}}
[data-testid="stSelectboxVirtualDropdown"] li,
[data-testid="stSelectboxVirtualDropdown"] span {{ color: {TEXT_PRI} !important; background: {SURFACE} !important; }}

[data-testid="stExpander"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
[data-testid="stExpander"] summary p {{ color: {MUTED} !important; }}

hr {{ border-color: {BORDER} !important; }}
[data-testid="stAlert"] {{ border-radius: 10px !important; }}
[data-testid="stAlert"] p {{ color: #93c5fd !important; }}
[data-testid="stRadio"] label {{ color: {TEXT_SEC} !important; font-size: 0.9rem; padding: 6px 0; transition: color 0.2s; }}
[data-testid="stRadio"] label:has(input:checked) {{ color: {TEXT_PRI} !important; }}

[data-testid="stChatMessage"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
}}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {{ color: #cbd5e1 !important; }}

textarea {{
    background: {SURFACE} !important; border: 1px solid {BORDER} !important;
    color: {TEXT_PRI} !important; border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
}}

[data-testid="stProgress"] > div > div {{ background: #3b82f6 !important; }}

.var-card {{
    background: #450a0a;
    border: 1px solid #7f1d1d;
    border-radius: 10px;
    padding: 1rem 1.2rem;
}}
.var-card p {{ color: #fca5a5 !important; }}
.var-card h3 {{ color: #f87171 !important; }}

.badge-positivo {{
    display: inline-block;
    background: #052e16; color: #4ade80;
    border: 1px solid #166534;
    border-radius: 20px; padding: 3px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem; font-weight: 600;
}}
.badge-negativo {{
    display: inline-block;
    background: #450a0a; color: #f87171;
    border: 1px solid #7f1d1d;
    border-radius: 20px; padding: 3px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem; font-weight: 600;
}}
.badge-neutro {{
    display: inline-block;
    background: {SURFACE}; color: {TEXT_SEC};
    border: 1px solid {BORDER};
    border-radius: 20px; padding: 3px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem; font-weight: 600;
}}
</style>
""", unsafe_allow_html=True)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def plotly_layout(extra=None):
    base = dict(
        plot_bgcolor=BG, paper_bgcolor=BG,
        font=dict(color=TEXT_SEC, family="DM Mono"),
        xaxis=dict(gridcolor=BORDER, zeroline=False),
        yaxis=dict(gridcolor=BORDER, zeroline=False),
        margin=dict(t=30, b=40, l=50, r=20),
    )
    if extra:
        base.update(extra)
    return base

def badge_retorno(pct):
    if pct > 0:
        return f'<span class="badge-positivo">▲ {pct:+.1f}%</span>'
    elif pct < 0:
        return f'<span class="badge-negativo">▼ {pct:+.1f}%</span>'
    else:
        return f'<span class="badge-neutro">→ 0.0%</span>'

# ─── Estado ──────────────────────────────────────────────────────────────────

if "carteira" not in st.session_state:
    st.session_state.carteira = Carteira.carregar_json()
if "historico_simulacoes" not in st.session_state:
    st.session_state.historico_simulacoes = []
if "historico_chat" not in st.session_state:
    st.session_state.historico_chat = []
if "benchmarks_cache" not in st.session_state:
    st.session_state.benchmarks_cache = None

carteira: Carteira = st.session_state.carteira

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 📊 Carteira")
    st.caption("Monte Carlo · IA · Macro")
    st.divider()
    pagina = st.radio("nav", [
        "🏠  Carteira",
        "🔮  Simulador",
        "💥  Stress Test",
        "📈  Análise",
        "💬  Assessor IA",
    ], label_visibility="collapsed")
    st.divider()
    if carteira.ativos:
        st.caption(f"**{len(carteira.ativos)}** ativos")
        pl = carteira.pl_total_pct
        cor = "🟢" if pl >= 0 else "🔴"
        st.caption(f"Patrimônio: **R$ {carteira.valor_total_atual:,.0f}**")
        st.caption(f"P&L total: {cor} **{pl:+.1f}%**")
        if st.session_state.historico_chat:
            n_msgs = len(st.session_state.historico_chat) // 2
            st.caption(f"💬 **{n_msgs}** msg(s) no chat")
    else:
        st.caption("Nenhum ativo cadastrado")

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — CARTEIRA
# ═══════════════════════════════════════════════════════════════════════════════

if pagina == "🏠  Carteira":
    st.title("Minha Carteira")

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
                st.info("Classe: Tesouro Direto")
            else:
                ticker = st.text_input("Ticker", placeholder="PETR4 / BTC / AAPL").upper().strip()
                nome   = st.text_input("Nome", placeholder="Ex: Petrobras PN")
                classe = st.selectbox("Classe", [k for k in CLASSES if k != "tesouro"],
                                      format_func=lambda x: CLASSES[x])
        with c2:
            if tipo == "Tesouro Direto":
                valor_investido = st.number_input("Valor investido (R$)", min_value=0.0, step=100.0, value=1000.0)
                preco_medio = st.number_input("Preço unitário (PU) na compra", min_value=0.0, step=0.01, value=0.0)
                quantidade = valor_investido / preco_medio if preco_medio > 0 else 1.0
                st.caption("💡 PU = preço do título na data da compra. Deixe 0 para buscar automaticamente.")
            else:
                quantidade  = st.number_input("Quantidade", min_value=0.0, step=1.0, value=1.0)
                preco_medio = st.number_input("Preço médio (R$)", min_value=0.0, step=0.01, value=0.0)
                st.caption("💡 Deixe 0 para buscar o preço atual automaticamente")

        if st.button("Adicionar à carteira", type="primary", use_container_width=True):
            if ticker and (preco_medio > 0 or tipo == "Tesouro Direto"):
                if preco_medio == 0:
                    with st.spinner("Buscando preço..."):
                        preco_medio = get_batch_prices([ticker]).get(ticker) or 0
                if preco_medio > 0:
                    if tipo == "Tesouro Direto":
                        quantidade = valor_investido / preco_medio
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

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Investido",   f"R$ {carteira.valor_total_investido:,.2f}")
    m2.metric("📈 Valor Atual", f"R$ {carteira.valor_total_atual:,.2f}")
    m3.metric("P&L (R$)",       f"R$ {carteira.pl_total_reais:+,.2f}",
              delta=f"{carteira.pl_total_pct:+.2f}%")
    m4.metric("Ativos",         len(carteira.ativos))

    st.markdown("**Por classe**")
    for classe, pct in sorted(carteira.alocacao_por_classe().items(), key=lambda x: -x[1]):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                f'border-bottom:1px solid {BORDER}">'
                f'<span style="color:{MUTED};font-size:0.85rem">{CLASSES.get(classe,classe)}</span>'
                f'<span style="color:{ACCENT};font-size:0.85rem;font-weight:600">{pct:.1f}%</span>'
                f'</div>', unsafe_allow_html=True)

    st.divider()

    # ── Evolução patrimonial ──────────────────────────────────────────────────
    st.markdown("**Evolução patrimonial (12 meses)**")

    with st.spinner("Carregando histórico..."):
        from analytics import retorno_acumulado_carteira
        acum = retorno_acumulado_carteira(carteira)

    if acum is not None and len(acum) > 1:
        valor_inicial = carteira.valor_total_investido
        serie_valor   = valor_inicial * (1 + acum)
        retorno_final = float(acum.iloc[-1]) * 100
        cor_linha     = POS if retorno_final >= 0 else NEG
        cor_fill      = "rgba(74,222,128,0.08)" if retorno_final >= 0 else "rgba(248,113,113,0.08)"

        fig_evol = go.Figure()
        fig_evol.add_trace(go.Scatter(
            x=serie_valor.index,
            y=serie_valor.values,
            mode="lines",
            fill="tozeroy",
            fillcolor=cor_fill,
            line=dict(color=cor_linha, width=2),
            hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>",
        ))
        fig_evol.add_hline(
            y=valor_inicial,
            line_color=MUTED, line_dash="dash", line_width=1,
            annotation_text="Investido",
            annotation_font_color=MUTED,
            annotation_position="bottom right",
        )
        fig_evol.update_layout(**plotly_layout())
        fig_evol.update_layout(
            yaxis_title="Valor (R$)",
            yaxis_tickprefix="R$ ",
            showlegend=False,
            height=220,
            margin=dict(t=10, b=40, l=80, r=20),
            hovermode="x unified",
        )
        st.plotly_chart(fig_evol, use_container_width=True)
    else:
        st.caption("Histórico insuficiente para gerar o gráfico.")

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

        prog = st.progress(0, text="🤖 Interpretando cenário...")
        choque, resumo = extrair_choque(cenario_texto)
        prog.progress(33, text="⚙️ Rodando simulações Monte Carlo...")

        st.info(f"**Interpretação:** {resumo}")

        choque_nz = {k: v for k, v in choque.items() if v != 0}
        if choque_nz:
            from macro_model import VARIAVEIS_MACRO
            cols_choque = st.columns(len(choque_nz))
            for i, (k, v) in enumerate(choque_nz.items()):
                cor = "normal" if v > 0 else "inverse"
                cols_choque[i].metric(VARIAVEIS_MACRO[k], f"{v:+.1f}%", delta_color=cor)

        resultado = simular_carteira(carteira, choque)
        prog.progress(80, text="📊 Gerando visualizações...")

        st.session_state.historico_simulacoes.append({
            "cenario": cenario_texto,
            "resumo": resumo,
            "p10": resultado.retorno_p10_pct,
            "p50": resultado.retorno_p50_pct,
            "p90": resultado.retorno_p90_pct,
            "impacto": resultado.impacto_choque_pct,
        })

        prog.progress(100, text="✅ Concluído!")
        prog.empty()

        st.divider()
        st.markdown(
            f"**Resultado do cenário:** "
            f"{badge_retorno(resultado.retorno_p50_pct)} mediano &nbsp;|&nbsp; "
            f"impacto direto do choque: {badge_retorno(resultado.impacto_choque_pct)}",
            unsafe_allow_html=True,
        )
        st.markdown("")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Valor Atual",      f"R$ {resultado.valor_base:,.2f}")
        r2.metric("Pessimista (P10)",
                  f"R$ {resultado.valor_p10:,.2f}",
                  delta=f"{resultado.retorno_p10_pct:+.1f}%",
                  help="10% das simulações terminam abaixo deste valor")
        r3.metric("Mediano (P50)",
                  f"R$ {resultado.valor_p50:,.2f}",
                  delta=f"{resultado.retorno_p50_pct:+.1f}%",
                  help="Resultado mais provável — metade das simulações acima, metade abaixo")
        r4.metric("Otimista (P90)",
                  f"R$ {resultado.valor_p90:,.2f}",
                  delta=f"{resultado.retorno_p90_pct:+.1f}%",
                  help="10% das simulações terminam acima deste valor")

        var_reais = resultado.valor_base - resultado.valor_p10
        var_pct   = abs(resultado.retorno_p10_pct)
        st.markdown(
            f'<div class="var-card">'
            f'<p style="font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase;margin:0 0 4px">'
            f'⚠️ Valor em Risco (VaR 90%)</p>'
            f'<h3 style="margin:0;font-family:DM Mono,monospace">R$ {var_reais:,.2f} &nbsp;'
            f'<span style="font-size:1rem">({var_pct:.1f}%)</span></h3>'
            f'<p style="margin:4px 0 0;font-size:0.8rem">Perda máxima esperada em 90% dos cenários simulados</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.divider()
        col_hist, col_tab = st.columns([3, 2])

        with col_hist:
            st.markdown("#### Distribuição dos cenários")
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=resultado.distribuicao, nbinsx=80,
                marker=dict(color="#3b82f6", opacity=0.75,
                            line=dict(color=BG, width=0.3)),
                name="Simulações",
            ))
            for val, label, cor, dash in [
                (resultado.valor_p10,  "P10",   "#f87171", "dash"),
                (resultado.valor_p50,  "P50",   "#fbbf24", "dash"),
                (resultado.valor_p90,  "P90",   "#4ade80", "dash"),
                (resultado.valor_base, "Atual", TEXT_PRI,  "solid"),
            ]:
                fig.add_vline(x=val, line_color=cor, line_dash=dash, line_width=1.5,
                              annotation_text=label, annotation_font_color=cor,
                              annotation_position="top")
            fig.update_layout(
                xaxis_title="Valor da carteira (R$)",
                yaxis_title="Frequência",
                showlegend=False,
                **plotly_layout(),
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
                use_container_width=True,
                hide_index=True,
                height=320,
            )

        st.divider()
        st.markdown("#### 🤖 Análise do assessor")
        tabela_ativos = carteira.para_dataframe()[
            ["Ticker", "Classe", "Atual (R$)", "% Carteira"]
        ].to_string(index=False)

        with st.chat_message("assistant"):
            st.write_stream(narrar_resultado_stream(
                cenario_texto, resumo, resultado, tabela_ativos,
                historico_simulacoes=st.session_state.historico_simulacoes,
            ))

        st.divider()
        resumo_export = (
            f"Cenário: {cenario_texto}\n"
            f"Interpretação: {resumo}\n\n"
            f"Valor atual:        R$ {resultado.valor_base:,.2f}\n"
            f"VaR (P10):          R$ {resultado.valor_p10:,.2f} ({resultado.retorno_p10_pct:+.1f}%)\n"
            f"Mediano (P50):      R$ {resultado.valor_p50:,.2f} ({resultado.retorno_p50_pct:+.1f}%)\n"
            f"Otimista (P90):     R$ {resultado.valor_p90:,.2f} ({resultado.retorno_p90_pct:+.1f}%)\n"
            f"Impacto do choque:  {resultado.impacto_choque_pct:+.1f}%\n"
        )
        st.download_button(
            "📥  Exportar resultado (.txt)",
            data=resumo_export,
            file_name=f"simulacao_{cenario_texto[:30].replace(' ','_')}.txt",
            mime="text/plain",
        )

    if st.session_state.historico_simulacoes:
        st.divider()
        st.markdown("#### 🕓 Histórico de simulações")
        df_hist = pd.DataFrame(st.session_state.historico_simulacoes)
        df_hist.columns = ["Cenário", "Interpretação", "P10 (%)", "P50 (%)", "P90 (%)", "Choque (%)"]

        fig_hist = go.Figure()
        for col, cor in [("P10 (%)", "#f87171"), ("P50 (%)", "#fbbf24"), ("P90 (%)", "#4ade80")]:
            fig_hist.add_trace(go.Bar(
                name=col.replace(" (%)", ""),
                x=df_hist["Cenário"],
                y=df_hist[col],
                marker_color=cor,
                opacity=0.85,
                text=df_hist[col].apply(lambda v: f"{v:+.1f}%"),
                textposition="outside",
                textfont=dict(family="DM Mono", size=10, color=TEXT_SEC),
            ))
        fig_hist.add_hline(y=0, line_color=BORDER, line_width=1)
        fig_hist.update_layout(**plotly_layout({"margin": dict(t=20, b=60, l=50, r=20)}))
        fig_hist.update_layout(
            barmode="group",
            yaxis=dict(ticksuffix="%"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SEC)),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

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
# PÁGINA 3 — STRESS TEST
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "💥  Stress Test":
    st.title("Stress Test Histórico")
    st.caption("Impacto dos maiores choques do mercado brasileiro na sua carteira")

    if not carteira.ativos:
        st.warning("Cadastre ativos na página Carteira primeiro.")
        st.stop()

    st.markdown("#### Cenários incluídos")
    df_cen = pd.DataFrame([{
        "Cenário":   c.nome,
        "Período":   c.periodo,
        "Descrição": c.descricao,
    } for c in CENARIOS_HISTORICOS])
    st.dataframe(df_cen, use_container_width=True, hide_index=True)

    st.divider()

    if st.button("💥  Rodar todos os stress tests", type="primary", use_container_width=True):
        prog_st = st.progress(0, text="Rodando cenários históricos...")
        df_res, resultados = rodar_todos(carteira)
        prog_st.progress(100, text="✅ Concluído!")
        prog_st.empty()

        st.markdown("#### Resultados comparativos")
        st.dataframe(
            df_res[["Cenário", "Período", "Choque direto", "P10 (%)", "P50 (%)", "P90 (%)"]
            ].style.format({
                "Choque direto": "{:+.1f}%",
                "P10 (%)":       "{:+.1f}%",
                "P50 (%)":       "{:+.1f}%",
                "P90 (%)":       "{:+.1f}%",
            }).background_gradient(subset=["P50 (%)"], cmap="RdYlGn", vmin=-40, vmax=20),
            use_container_width=True, hide_index=True,
        )

        st.divider()
        st.markdown("#### Impacto no patrimônio por cenário")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            fig_bar = go.Figure()
            nomes = df_res["Cenário"].tolist()
            for col, cor in [("P10 (%)", "#f87171"), ("P50 (%)", "#fbbf24"), ("P90 (%)", "#4ade80")]:
                fig_bar.add_trace(go.Bar(
                    name=col.replace(" (%)", ""),
                    x=nomes, y=df_res[col].tolist(),
                    marker_color=cor, opacity=0.85,
                    text=df_res[col].apply(lambda v: f"{v:+.1f}%"),
                    textposition="outside",
                    textfont=dict(family="DM Mono", size=10, color=TEXT_SEC),
                ))
            fig_bar.add_hline(y=0, line_color=BORDER, line_width=1)
            fig_bar.update_layout(**plotly_layout({"margin": dict(t=30, b=80, l=50, r=20)}))
            fig_bar.update_layout(
                barmode="group",
                xaxis=dict(gridcolor=BORDER, tickangle=-20, tickfont=dict(size=10, color=TEXT_SEC)),
                yaxis=dict(gridcolor=BORDER, zeroline=False, ticksuffix="%", tickfont=dict(color=MUTED)),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SEC)),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_g2:
            cores_r = ["#f87171" if v < 0 else "#4ade80" for v in df_res["Impacto (R$)"]]
            fig_r = go.Figure(go.Bar(
                x=df_res["Impacto (R$)"].tolist(),
                y=df_res["Cenário"].tolist(),
                orientation="h",
                marker_color=cores_r,
                text=df_res["Impacto (R$)"].apply(lambda v: f"R$ {v:+,.0f}"),
                textposition="outside",
                textfont=dict(family="DM Mono", size=10, color=TEXT_SEC),
                hovertemplate="<b>%{y}</b><br>R$ %{x:+,.2f}<extra></extra>",
            ))
            fig_r.update_layout(**plotly_layout({"margin": dict(t=40, b=20, l=10, r=100)}))
            fig_r.update_layout(
                title=dict(text="Impacto direto (R$)", font=dict(color=TEXT_SEC, size=13)),
                xaxis=dict(gridcolor=BORDER, zeroline=False, tickfont=dict(color=MUTED)),
                yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT_PRI, size=11)),
            )
            st.plotly_chart(fig_r, use_container_width=True)

        st.divider()

        idx_pior   = df_res["P50 (%)"].idxmin()
        idx_melhor = df_res["P50 (%)"].idxmax()

        c_pior, c_melhor = st.columns(2)
        with c_pior:
            row = df_res.iloc[idx_pior]
            st.error(
                f"**💀 Pior cenário: {row['Cenário']}**\n\n"
                f"Mediano: **{row['P50 (%)']:+.1f}%** "
                f"(R$ {row['P50 (R$)']:,.2f})\n\n"
                f"Pessimista: **{row['P10 (%)']:+.1f}%**"
            )
        with c_melhor:
            row = df_res.iloc[idx_melhor]
            st.success(
                f"**🟢 Cenário menos severo: {row['Cenário']}**\n\n"
                f"Mediano: **{row['P50 (%)']:+.1f}%** "
                f"(R$ {row['P50 (R$)']:,.2f})\n\n"
                f"Otimista: **{row['P90 (%)']:+.1f}%**"
            )

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — ANÁLISE
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "📈  Análise":
    st.title("Análise")

    if not carteira.ativos:
        st.warning("Cadastre ativos primeiro.")
        st.stop()

    df = carteira.para_dataframe()
    total = carteira.valor_total_atual

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Patrimônio",    f"R$ {total:,.2f}")
    k2.metric("P&L",           f"R$ {carteira.pl_total_reais:+,.2f}", delta=f"{carteira.pl_total_pct:+.1f}%")
    k3.metric("Ativos",        len(carteira.ativos))
    k4.metric("Classes",       df["Classe"].nunique())
    maior = df.loc[df["% Carteira"].idxmax()]
    k5.metric("Maior posição", maior["Ticker"], delta=f"{maior['% Carteira']:.1f}%")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Alocação por classe**")
        aloc  = carteira.alocacao_por_classe()
        cores = [CLASSES_CORES.get(k, ACCENT) for k in aloc]
        fig_pie = go.Figure(go.Pie(
            labels=[CLASSES.get(k, k) for k in aloc], values=list(aloc.values()),
            hole=0.5, marker=dict(colors=cores, line=dict(color="#fff", width=2)),
            textinfo="percent", textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        ))
        fig_pie.add_annotation(
            text=f"R$ {total:,.0f}", x=0.5, y=0.5,
            font=dict(size=12, color=TEXT), showarrow=False,
        )
        fig_pie.update_layout(**PLOT_LAYOUT)
        fig_pie.update_layout(
            showlegend=True,
            legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("**P&L por ativo**")
        df_pl    = df.sort_values("P&L (R$)")
        cores_pl = [NEG if v < 0 else POS for v in df_pl["P&L (R$)"]]
        fig_pl   = go.Figure(go.Bar(
            x=df_pl["P&L (R$)"], y=df_pl["Ticker"], orientation="h",
            marker_color=cores_pl, opacity=0.8,
            text=df_pl["P&L (R$)"].apply(lambda v: f"R$ {v:+,.0f}"),
            textposition="outside", textfont=dict(size=10, color=MUTED),
        ))
        fig_pl.add_vline(x=0, line_color=BORDER, line_width=1)
        fig_pl.update_layout(**PLOT_LAYOUT)
        fig_pl.update_layout(margin=dict(t=20, b=20, l=10, r=80))
        st.plotly_chart(fig_pl, use_container_width=True)

    st.divider()

    st.markdown("**Retorno acumulado — Carteira vs Benchmarks (12 meses)**")

    with st.spinner("Carregando histórico..."):
        acum_cart  = retorno_acumulado_carteira(carteira)
        acum_bench = acumulado_benchmarks()

    # Salva benchmarks no cache para o Assessor IA usar
    if acum_bench is not None and not acum_bench.empty:
        st.session_state.benchmarks_cache = {
            col: float(acum_bench[col].dropna().iloc[-1]) * 100
            for col in acum_bench.columns
            if not acum_bench[col].dropna().empty
        }

        if acum_cart is not None:
            fig_acum = go.Figure()

            idx = acum_cart.index
            acum_bench_aligned = acum_bench.reindex(idx, method="ffill").bfill()

            cores_bench = {
                "Ibovespa": "#f59e0b",
                "CDI":      "#4ade80",
                "IPCA":     "#f87171",
            }
            for col in acum_bench_aligned.columns:
                if col in cores_bench:
                    serie = acum_bench_aligned[col].dropna()
                    if len(serie) > 1:
                        fig_acum.add_trace(go.Scatter(
                            x=serie.index, y=serie.values * 100,
                            name=col, mode="lines",
                            line=dict(color=cores_bench[col], width=2),
                        ))

            # Carteira — fora do for, indentação no mesmo nível
            fig_acum.add_trace(go.Scatter(
                x=acum_cart.index, y=acum_cart.values * 100,
                name="Carteira", mode="lines",
                line=dict(color="#3b82f6", width=3),
            ))

            fig_acum.add_hline(y=0, line_color=BORDER, line_width=1)
            fig_acum.update_layout(**PLOT_LAYOUT)
            fig_acum.update_layout(
                yaxis_title="Retorno acumulado (%)",
                yaxis_ticksuffix="%",
                legend=dict(
                    bgcolor="rgba(30,41,59,0.9)",
                    bordercolor=BORDER,
                    borderwidth=1,
                    font=dict(size=12, color=TEXT_PRI),
                ),
                margin=dict(t=20, b=40, l=60, r=20),
                hovermode="x unified",
            )
            st.plotly_chart(fig_acum, use_container_width=True)

        resumo_bench = {"Carteira": f"{acum_cart.iloc[-1]*100:+.1f}%"}
        for col in acum_bench.columns:
            s = acum_bench[col].dropna()
            if len(s):
                resumo_bench[col] = f"{s.iloc[-1]*100:+.1f}%"
        st.dataframe(pd.DataFrame([resumo_bench]), use_container_width=True, hide_index=True)
    else:
        st.caption("Histórico insuficiente para gerar o gráfico.")

    st.divider()

    st.markdown("**Correlação entre ativos (últimos 12 meses)**")

    with st.spinner("Calculando correlações..."):
        corr = matriz_correlacao(carteira)

    if corr is not None and not corr.empty:
        fig_corr = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
            colorscale=[
                [0.0, "#dc2626"],
                [0.5, "#ffffff"],
                [1.0, "#16a34a"],
            ],
            zmin=-1, zmax=1,
            text=corr.round(2).values,
            texttemplate="%{text}",
            textfont=dict(size=11, color=TEXT),
            hovertemplate="<b>%{x} × %{y}</b><br>Correlação: %{z:.2f}<extra></extra>",
            showscale=True,
            colorbar=dict(thickness=12, len=0.8, tickfont=dict(size=10)),
        ))
        fig_corr.update_layout(**PLOT_LAYOUT)
        fig_corr.update_layout(
            xaxis=dict(side="bottom", tickfont=dict(size=11)),
            yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
            margin=dict(t=20, b=60, l=80, r=20),
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.caption("Verde = correlação positiva · Vermelho = correlação negativa · Branco = sem correlação")
    else:
        st.caption("São necessários pelo menos 2 ativos com histórico disponível.")

    st.divider()
# ═══════════════════════════════════════════════════════════════════════════════
# BLOCO DE RISCO — cole no app.py na página Análise,
# após o gráfico de correlação e antes de "Peso por ativo"
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Adicione este import no topo do app.py (junto com os outros imports):
# from risk_metrics import calcular_metricas, interpretar_sharpe, interpretar_drawdown

# 2. Cole o bloco abaixo no lugar certo da página Análise:

    st.divider()
    st.markdown("**Métricas de Risco (12 meses)**")

    with st.spinner("Calculando métricas de risco..."):
        metricas = calcular_metricas(carteira)

    if metricas:
        # ── KPIs de risco ─────────────────────────────────────────────────────
        r1, r2, r3, r4, r5 = st.columns(5)

        sharpe_label, sharpe_cor = interpretar_sharpe(metricas["sharpe"])
        dd_label, dd_cor         = interpretar_drawdown(metricas["max_drawdown"])

        r1.metric(
            "Volatilidade anual",
            f"{metricas['vol_anual']*100:.1f}%",
            help="Desvio padrão anualizado dos retornos diários"
        )
        r2.metric(
            "Sharpe Ratio",
            f"{metricas['sharpe']:.2f}",
            delta=sharpe_label,
            delta_color="normal" if metricas["sharpe"] >= 0.5 else "inverse",
            help="Retorno ajustado ao risco vs CDI. Acima de 1 = bom, acima de 2 = excelente"
        )
        r3.metric(
            "Sortino Ratio",
            f"{metricas['sortino']:.2f}",
            help="Igual ao Sharpe mas penaliza só a volatilidade negativa"
        )
        r4.metric(
            "Max Drawdown",
            f"{metricas['max_drawdown']*100:.1f}%",
            delta=dd_label,
            delta_color="inverse" if abs(metricas["max_drawdown"]) > 0.10 else "normal",
            help=f"Maior queda do pico até o vale. Ocorreu em {metricas['max_dd_date'].strftime('%d/%m/%Y')}"
        )
        r5.metric(
            "Beta (vs Ibov)",
            f"{metricas['beta']:.2f}" if metricas["beta"] is not None else "—",
            help="Beta > 1 = mais volátil que o Ibovespa. Beta < 1 = mais defensivo"
        )

        st.divider()

        # ── Gráfico de Drawdown ───────────────────────────────────────────────
        st.markdown("**Drawdown histórico**")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=metricas["serie_drawdown"].index,
            y=metricas["serie_drawdown"].values * 100,
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(248, 113, 113, 0.15)",
            line=dict(color="#f87171", width=1.5),
            name="Drawdown",
            hovertemplate="%{x|%d/%m/%Y}<br>%{y:.2f}%<extra></extra>",
        ))
        fig_dd.add_hline(
            y=metricas["max_drawdown"] * 100,
            line_color="#f87171", line_dash="dash", line_width=1,
            annotation_text=f"Máx: {metricas['max_drawdown']*100:.1f}%",
            annotation_font_color="#f87171",
        )
        fig_dd.update_layout(**plotly_layout())
        fig_dd.update_layout(
            yaxis_title="Drawdown (%)",
            yaxis_ticksuffix="%",
            showlegend=False,
            margin=dict(t=20, b=40, l=60, r=20),
            hovermode="x unified",
        )
        st.plotly_chart(fig_dd, use_container_width=True)

        # ── Interpretação textual ─────────────────────────────────────────────
        col_int1, col_int2 = st.columns(2)
        with col_int1:
            sharpe_label, _ = interpretar_sharpe(metricas["sharpe"])
            st.markdown(
                f'<div style="background:{SURFACE};border:1px solid {BORDER};'
                f'border-radius:10px;padding:1rem">'
                f'<p style="color:{MUTED};font-size:0.72rem;text-transform:uppercase;'
                f'letter-spacing:0.08em;margin:0 0 8px">Sharpe · {sharpe_label}</p>'
                f'<p style="color:{TEXT_SEC};font-size:0.85rem;margin:0">'
                f'Para cada unidade de risco assumida, a carteira gerou '
                f'<strong>{metricas["sharpe"]:.2f}x</strong> de retorno acima do CDI.'
                f'{"" if metricas["sharpe"] >= 1 else " Considere reduzir ativos de alta volatilidade."}'
                f'</p></div>',
                unsafe_allow_html=True
            )
        with col_int2:
            dd_label, _ = interpretar_drawdown(metricas["max_drawdown"])
            st.markdown(
                f'<div style="background:{SURFACE};border:1px solid {BORDER};'
                f'border-radius:10px;padding:1rem">'
                f'<p style="color:{MUTED};font-size:0.72rem;text-transform:uppercase;'
                f'letter-spacing:0.08em;margin:0 0 8px">Max Drawdown · {dd_label}</p>'
                f'<p style="color:{TEXT_SEC};font-size:0.85rem;margin:0">'
                f'A maior queda da carteira foi de '
                f'<strong>{metricas["max_drawdown"]*100:.1f}%</strong>, '
                f'ocorrida em {metricas["max_dd_date"].strftime("%d/%m/%Y")}.'
                f'</p></div>',
                unsafe_allow_html=True
            )
    else:
        st.caption("Histórico insuficiente para calcular métricas de risco.")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**Peso por ativo**")
        df_peso = df.sort_values("% Carteira", ascending=True)
        fig_peso = go.Figure(go.Bar(
            x=df_peso["% Carteira"], y=df_peso["Ticker"], orientation="h",
            marker_color=ACCENT, opacity=0.7,
            text=df_peso["% Carteira"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside", textfont=dict(size=10, color=MUTED),
        ))
        fig_peso.update_layout(**PLOT_LAYOUT)
        fig_peso.update_layout(
            xaxis=dict(gridcolor=BORDER, zeroline=False, ticksuffix="%"),
            margin=dict(t=20, b=20, l=10, r=60),
        )
        st.plotly_chart(fig_peso, use_container_width=True)

    with col4:
        st.markdown("**Concentração**")
        alertas = [(r["Ticker"], r["% Carteira"]) for _, r in df.iterrows() if r["% Carteira"] > 20]
        if alertas:
            for ticker, pct in alertas:
                if pct > 30: st.error(f"**{ticker}** representa {pct:.1f}% — alta concentração")
                else:        st.warning(f"**{ticker}** representa {pct:.1f}%")
        else:
            st.success("Nenhum ativo com concentração acima de 20%.")

        pesos   = df["% Carteira"].values / 100
        hhi     = np.sum(pesos ** 2)
        n_equiv = 1 / hhi if hhi > 0 else 1
        score   = min(100, int(n_equiv / len(df) * 100 + (1 - hhi) * 60))
        st.metric("Score de diversificação", f"{score} / 100",
                  delta="Bom" if score > 60 else "A melhorar",
                  delta_color="normal" if score > 60 else "inverse")

        st.markdown("**Por classe**")
        for classe, pct in sorted(carteira.alocacao_por_classe().items(), key=lambda x: -x[1]):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                f'border-bottom:1px solid {BORDER}">'
                f'<span style="color:{MUTED};font-size:0.85rem">{CLASSES.get(classe,classe)}</span>'
                f'<span style="color:{ACCENT};font-size:0.85rem;font-weight:600">{pct:.1f}%</span>'
                f'</div>', unsafe_allow_html=True)

    st.divider()

    

    

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 5 — ASSESSOR IA
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "💬  Assessor IA":
    st.title("Assessor IA")
    st.caption("Chat com contexto completo da sua carteira e histórico de simulações")

    if not carteira.ativos:
        st.warning("Cadastre ativos na página Carteira para o assessor ter contexto.")

    with st.expander("📋 Contexto carregado pelo assessor", expanded=False):
        col_ctx1, col_ctx2 = st.columns(2)
        with col_ctx1:
            st.caption(f"**Ativos na carteira:** {len(carteira.ativos)}")
            st.caption(f"**Valor total:** R$ {carteira.valor_total_atual:,.2f}")
            st.caption(f"**P&L total:** {carteira.pl_total_pct:+.1f}%")
        with col_ctx2:
            n_sims = len(st.session_state.historico_simulacoes)
            st.caption(f"**Simulações na memória:** {n_sims}")
            if n_sims:
                ultimas = [s['cenario'] for s in st.session_state.historico_simulacoes[-3:]]
                st.caption("Últimas: " + " · ".join(f'"{c[:25]}"' for c in ultimas))

    st.divider()

    col_proativo, col_limpar = st.columns([3, 1])
    with col_proativo:
        if st.button("🔍 Analisar rebalanceamento da carteira", type="primary", use_container_width=True):
            if carteira.ativos:
                with st.chat_message("assistant"):
                    resposta = st.write_stream(sugerir_rebalanceamento_stream(
                        carteira,
                        st.session_state.historico_simulacoes,
                        st.session_state.benchmarks_cache,
                    ))
                st.session_state.historico_chat.append({"role": "user", "content": "[Análise de rebalanceamento solicitada]"})
                st.session_state.historico_chat.append({"role": "assistant", "content": resposta})
            else:
                st.warning("Cadastre ativos primeiro.")
    with col_limpar:
        if st.button("🗑️ Limpar chat", use_container_width=True):
            st.session_state.historico_chat = []
            st.rerun()

    st.divider()

    for msg in st.session_state.historico_chat:
        if msg["content"] == "[Análise de rebalanceamento solicitada]":
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    SUGESTOES = [
        "Qual meu ativo mais arriscado?",
        "Como estou vs Ibovespa?",
        "Resuma os cenários simulados",
        "Onde estou concentrado demais?",
        "Me explica o VaR da última simulação",
    ]

    if not st.session_state.historico_chat:
        st.markdown("**Sugestões para começar:**")
        cols_sug = st.columns(len(SUGESTOES))
        for i, sug in enumerate(SUGESTOES):
            if cols_sug[i].button(sug, use_container_width=True, key=f"sug_{i}"):
                st.session_state._msg_rapida = sug
                st.rerun()

    pergunta = st.chat_input("Pergunte sobre sua carteira, simulações ou estratégia...")

    if hasattr(st.session_state, "_msg_rapida") and st.session_state._msg_rapida:
        pergunta = st.session_state._msg_rapida
        st.session_state._msg_rapida = None

    if pergunta:
        with st.chat_message("user"):
            st.markdown(pergunta)
        st.session_state.historico_chat.append({"role": "user", "content": pergunta})

        with st.chat_message("assistant"):
            resposta = st.write_stream(chat_stream(
                mensagem=pergunta,
                historico_chat=st.session_state.historico_chat[:-1],
                carteira=carteira,
                historico_simulacoes=st.session_state.historico_simulacoes,
                benchmarks=st.session_state.benchmarks_cache,
            ))

        st.session_state.historico_chat.append({"role": "assistant", "content": resposta})
        st.rerun()