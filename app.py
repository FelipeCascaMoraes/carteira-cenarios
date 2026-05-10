import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from portfolio import Carteira, Ativo, CLASSES, CLASSES_CORES
from market_data import get_batch_prices, TESOURO_TITULOS
from simulator import simular_carteira, impacto_por_ativo
from agent import extrair_choque
from agent_chat import narrar_resultado_stream, chat_stream, sugerir_rebalanceamento_stream
from stress_test import CENARIOS_HISTORICOS, rodar_todos
from risk_metrics import calcular_metricas, interpretar_sharpe, interpretar_drawdown
from analytics import retorno_acumulado_carteira, acumulado_benchmarks, matriz_correlacao
from database import carregar_carteira, salvar_ativo, remover_ativo, salvar_carteira, limpar_carteira
from auth import is_logged_in, mostrar_tela_login, fazer_logout, get_user

st.set_page_config(page_title="Carteira", page_icon="📊", layout="wide")

BG       = "#0f172a"
SURFACE  = "#1e293b"
BORDER   = "#334155"
MUTED    = "#64748b"
TEXT_SEC = "#94a3b8"
TEXT_PRI = "#e2e8f0"
ACCENT   = "#3b82f6"
TEXT     = TEXT_PRI
POS      = "#4ade80"
NEG      = "#f87171"

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

/* Esconde ícone de link nos títulos */
h1 a, h2 a, h3 a {{ display: none !important; }}
h1 svg, h2 svg, h3 svg {{ display: none !important; }}

/* Chat input */
div[data-testid="stChatInput"] {{ background: {SURFACE} !important; border: 1px solid {BORDER} !important; border-radius: 12px !important; }}
div[data-testid="stChatInput"] > div {{ background: {SURFACE} !important; border-radius: 12px !important; }}
div[data-testid="stChatInput"] textarea {{ background: {SURFACE} !important; color: {TEXT_PRI} !important; }}
div[data-testid="stChatInput"]:focus-within {{ border-color: {ACCENT} !important; box-shadow: none !important; }}
[data-testid="stBottom"] > div {{ background: {BG} !important; border-top: 1px solid {BORDER} !important; }}
[data-testid="InputInstructions"] {{ display: none !important; }}

/* Tipografia */
p, span, li {{ color: {TEXT_SEC}; }}
strong {{ color: {TEXT_PRI} !important; }}
h1 {{ color: {TEXT_PRI} !important; font-family: 'Syne', sans-serif !important; font-weight: 800 !important; letter-spacing: -0.03em !important; font-size: 1.75rem !important; margin-bottom: 0 !important; }}
h2, h3, h4 {{ color: {TEXT_PRI} !important; font-family: 'Syne', sans-serif !important; }}
[data-testid="stMarkdownContainer"] p {{ color: {TEXT_SEC}; }}
[data-testid="stCaptionContainer"] p {{ color: {MUTED} !important; }}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {{
    color: {MUTED} !important; font-size: 0.7rem !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
    font-family: 'DM Mono', monospace !important;
}}
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] div {{ color: {TEXT_SEC} !important; }}

/* Métricas */
[data-testid="metric-container"] {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 14px; padding: 1.1rem 1.3rem !important;
    transition: border-color 0.2s, transform 0.15s;
}}
[data-testid="metric-container"]:hover {{ border-color: {MUTED}; transform: translateY(-2px); }}
[data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-size: 0.65rem !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; font-family: 'DM Mono', monospace !important; }}
[data-testid="stMetricValue"] {{ color: {TEXT_PRI} !important; font-family: 'DM Mono', monospace !important; font-size: 1.4rem !important; font-weight: 500 !important; }}
[data-testid="stMetricDelta"] {{ font-family: 'DM Mono', monospace !important; font-size: 0.78rem !important; }}

/* Botão primário — azul */
.stButton > button[kind="primary"] {{
    background: {ACCENT} !important; color: #fff !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 700 !important; font-family: 'Syne', sans-serif !important;
    letter-spacing: 0.02em; font-size: 0.875rem !important;
    padding: 0.5rem 1rem !important;
    transition: background 0.2s, transform 0.1s, box-shadow 0.2s;
}}
.stButton > button[kind="primary"]:hover {{
    background: #2563eb !important; transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(59,130,246,0.3) !important;
}}
.stButton > button[kind="primary"]:active {{ transform: translateY(0); }}

/* Botão secundário — outline */
.stButton > button:not([kind="primary"]) {{
    background: transparent !important; color: {TEXT_SEC} !important;
    border: 1px solid {BORDER} !important; border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important; font-size: 0.875rem !important;
    transition: all 0.2s;
}}
.stButton > button:not([kind="primary"]):hover {{
    background: {SURFACE} !important; border-color: {MUTED} !important; color: {TEXT_PRI} !important;
}}

/* Botão Sair — vermelho */
section[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important; color: #f87171 !important;
    border: 1px solid #7f1d1d !important; border-radius: 10px !important;
    transition: all 0.2s;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: #450a0a !important; border-color: #f87171 !important; color: #fca5a5 !important;
}}

/* Inputs */
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER} !important; border-radius: 12px; overflow: hidden; }}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{
    background: {SURFACE} !important; border: 1px solid {BORDER} !important;
    color: {TEXT_PRI} !important; border-radius: 10px !important;
    font-family: 'DM Mono', monospace !important; transition: border-color 0.2s;
}}
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus {{
    border-color: {ACCENT} !important; box-shadow: none !important;
}}
::placeholder {{ color: {MUTED} !important; opacity: 1; }}
.stSelectbox > div > div {{
    background: {SURFACE} !important; border: 1px solid {BORDER} !important;
    border-radius: 10px !important; color: {TEXT_PRI} !important;
}}
[data-testid="stSelectboxVirtualDropdown"] li,
[data-testid="stSelectboxVirtualDropdown"] span {{ color: {TEXT_PRI} !important; background: {SURFACE} !important; }}
[data-testid="stExpander"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
[data-testid="stExpander"] summary p {{ color: {MUTED} !important; font-size: 0.85rem !important; }}
hr {{ border-color: {BORDER} !important; opacity: 0.4; margin: 1.5rem 0 !important; }}
[data-testid="stAlert"] {{ border-radius: 10px !important; }}
[data-testid="stAlert"] p {{ color: #93c5fd !important; }}
[data-testid="stRadio"] label {{ color: {TEXT_SEC} !important; font-size: 0.875rem; padding: 6px 0; transition: color 0.2s; }}
[data-testid="stRadio"] label:has(input:checked) {{ color: {TEXT_PRI} !important; font-weight: 600; }}
[data-testid="stChatMessage"] {{
    background: {SURFACE} !important; border: 1px solid {BORDER} !important; border-radius: 14px !important;
}}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span, [data-testid="stChatMessage"] div {{ color: #cbd5e1 !important; }}
textarea {{ background: {SURFACE} !important; border: 1px solid {BORDER} !important; color: {TEXT_PRI} !important; border-radius: 10px !important; font-family: 'Syne', sans-serif !important; }}
[data-testid="stProgress"] > div > div {{ background: {ACCENT} !important; border-radius: 4px !important; }}

/* Cards */
.var-card {{ background: #450a0a; border: 1px solid #7f1d1d; border-radius: 12px; padding: 1.2rem 1.5rem; }}
.var-card p {{ color: #fca5a5 !important; }}
.var-card h3 {{ color: #f87171 !important; font-family: 'DM Mono', monospace !important; margin: 0; }}
.info-card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; padding: 1rem 1.25rem; }}
.section-label {{ color: {MUTED}; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.12em; font-family: 'DM Mono', monospace; margin-bottom: 0.6rem; display: block; }}
.badge-positivo {{ display: inline-flex; align-items: center; gap: 4px; background: #052e16; color: #4ade80; border: 1px solid #166534; border-radius: 20px; padding: 3px 12px; font-family: 'DM Mono', monospace; font-size: 0.8rem; font-weight: 600; }}
.badge-negativo {{ display: inline-flex; align-items: center; gap: 4px; background: #450a0a; color: #f87171; border: 1px solid #7f1d1d; border-radius: 20px; padding: 3px 12px; font-family: 'DM Mono', monospace; font-size: 0.8rem; font-weight: 600; }}
.badge-neutro {{ display: inline-flex; align-items: center; gap: 4px; background: {SURFACE}; color: {TEXT_SEC}; border: 1px solid {BORDER}; border-radius: 20px; padding: 3px 12px; font-family: 'DM Mono', monospace; font-size: 0.8rem; font-weight: 600; }}
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
    if pct > 0:   return f'<span class="badge-positivo">▲ {pct:+.1f}%</span>'
    elif pct < 0: return f'<span class="badge-negativo">▼ {pct:+.1f}%</span>'
    else:         return f'<span class="badge-neutro">→ 0.0%</span>'

def sec(label):
    """Label de seção estilizado."""
    st.markdown(f'<span class="section-label">{label}</span>', unsafe_allow_html=True)

def page_header(titulo, sub=""):
    st.markdown(f"""
<div style="margin-bottom:1.75rem">
    <h1 style="margin:0 0 0.2rem">{titulo}</h1>
    {"" if not sub else f'<span style="color:{MUTED};font-size:0.8rem;font-family:Syne,sans-serif">{sub}</span>'}
</div>
""", unsafe_allow_html=True)

# ─── Auth ────────────────────────────────────────────────────────────────────

if not is_logged_in():
    mostrar_tela_login()
    st.stop()

# ─── Estado ──────────────────────────────────────────────────────────────────

if "carteira" not in st.session_state:
    st.session_state.carteira = carregar_carteira()
if "historico_simulacoes" not in st.session_state:
    st.session_state.historico_simulacoes = []
if "historico_chat" not in st.session_state:
    st.session_state.historico_chat = []
if "benchmarks_cache" not in st.session_state:
    st.session_state.benchmarks_cache = None

carteira: Carteira = st.session_state.carteira

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
<div style="padding:1.5rem 0 1rem;display:flex;align-items:center;gap:10px">
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
        <rect width="36" height="36" rx="10" fill="#1e293b"/>
        <rect x="0.5" y="0.5" width="35" height="35" rx="9.5" stroke="#334155"/>
        <polyline points="6,26 13,17 18,21 24,11 30,15"
                  fill="none" stroke="#3b82f6" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="30" cy="15" r="2.5" fill="#4ade80"/>
    </svg>
    <div>
        <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;color:#e2e8f0;letter-spacing:-0.01em;line-height:1.1">Carteira</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.6rem;color:#475569;letter-spacing:0.1em;text-transform:uppercase">Monte Carlo · IA</div>
    </div>
</div>
""", unsafe_allow_html=True)

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
        pl_cor  = "#4ade80" if carteira.pl_total_pct >= 0 else "#f87171"
        pl_seta = "▲" if carteira.pl_total_pct >= 0 else "▼"
        st.markdown(f"""
<div style="display:flex;flex-direction:column;gap:8px;padding:0.1rem 0">
    <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="color:#475569;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;font-family:'DM Mono',monospace">Patrimônio</span>
        <span style="color:#e2e8f0;font-size:0.82rem;font-weight:600;font-family:'DM Mono',monospace">R$ {carteira.valor_total_atual:,.0f}</span>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="color:#475569;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;font-family:'DM Mono',monospace">P&L</span>
        <span style="color:{pl_cor};font-size:0.82rem;font-weight:600;font-family:'DM Mono',monospace">{pl_seta} {carteira.pl_total_pct:+.1f}%</span>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="color:#475569;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;font-family:'DM Mono',monospace">Ativos</span>
        <span style="color:#94a3b8;font-size:0.82rem;font-family:'DM Mono',monospace">{len(carteira.ativos)}</span>
    </div>
</div>
""", unsafe_allow_html=True)
        if st.session_state.historico_chat:
            n_msgs = len(st.session_state.historico_chat) // 2
            st.markdown(f"""
<div style="margin-top:8px;padding:6px 10px;background:#1e293b;border:1px solid #334155;border-radius:8px">
    <span style="color:#475569;font-size:0.68rem;font-family:'DM Mono',monospace">💬 {n_msgs} msg(s) no chat</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="padding:8px 10px;background:{SURFACE};border:1px solid {BORDER};border-radius:8px">
    <span style="color:{MUTED};font-size:0.75rem;font-family:'DM Mono',monospace">Nenhum ativo cadastrado</span>
</div>
""", unsafe_allow_html=True)

    st.divider()
    user = get_user()
    if user:
        initials = user.user.email[:2].upper()
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
    <div style="width:28px;height:28px;border-radius:50%;background:#1e3a5f;display:flex;align-items:center;justify-content:center;flex-shrink:0">
        <span style="color:#60a5fa;font-size:0.7rem;font-weight:700;font-family:'DM Mono',monospace">{initials}</span>
    </div>
    <span style="color:#64748b;font-size:0.72rem;font-family:'DM Mono',monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:120px">{user.user.email}</span>
</div>
""", unsafe_allow_html=True)
    if st.button("Sair", use_container_width=True):
        fazer_logout()
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — CARTEIRA
# ═══════════════════════════════════════════════════════════════════════════════

if pagina == "🏠  Carteira":
    page_header("Minha Carteira", "Visão geral dos seus ativos")

    with st.expander("➕  Adicionar ativo", expanded=not carteira.ativos):
        tipo = st.radio("Tipo", ["Ação / FII / Cripto / Commodity", "Tesouro Direto"], horizontal=True)
        c1, c2 = st.columns(2)
        with c1:
            if tipo == "Tesouro Direto":
                ticker = st.selectbox("Título", list(TESOURO_TITULOS.keys()),
                                      format_func=lambda x: f"{x} — {TESOURO_TITULOS[x]}")
                nome, classe = TESOURO_TITULOS[ticker], "tesouro"
                st.info("Classe: Tesouro Direto")
            else:
                ticker = st.text_input("Ticker", placeholder="PETR4 / BTC / AAPL").upper().strip()
                nome   = st.text_input("Nome", placeholder="Ex: Petrobras PN")
                classe = st.selectbox("Classe", [k for k in CLASSES if k != "tesouro"],
                                      format_func=lambda x: CLASSES[x])
        with c2:
            if tipo == "Tesouro Direto":
                valor_investido = st.number_input("Valor investido (R$)", min_value=0.0, step=100.0, value=1000.0)
                preco_medio     = st.number_input("Preço unitário (PU)", min_value=0.0, step=0.01, value=0.0)
                quantidade      = valor_investido / preco_medio if preco_medio > 0 else 1.0
                st.caption("💡 Deixe 0 para buscar automaticamente")
            else:
                quantidade  = st.number_input("Quantidade", min_value=0.0, step=1.0, value=1.0)
                preco_medio = st.number_input("Preço médio (R$)", min_value=0.0, step=0.01, value=0.0)
                st.caption("💡 Deixe 0 para buscar o preço atual")

        if st.button("Adicionar à carteira", type="primary", use_container_width=True):
            if ticker and (preco_medio > 0 or tipo == "Tesouro Direto"):
                if preco_medio == 0:
                    with st.spinner("Buscando preço..."):
                        preco_medio = get_batch_prices([ticker]).get(ticker) or 0
                if preco_medio > 0:
                    if tipo == "Tesouro Direto":
                        quantidade = valor_investido / preco_medio
                    novo = Ativo(ticker=ticker, nome=nome or ticker, classe=classe,
                                 quantidade=quantidade, preco_medio=preco_medio)
                    carteira.adicionar(novo)
                    salvar_ativo(novo)
                    st.success(f"✅ {ticker} adicionado!")
                    st.rerun()
                else:
                    st.error("Não foi possível buscar o preço. Insira manualmente.")
            else:
                st.error("Preencha ticker e preço médio.")

    if not carteira.ativos:
        st.markdown(f"""
<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:14px;padding:3rem;text-align:center;margin-top:1rem">
    <div style="font-size:2.5rem;margin-bottom:0.75rem">📭</div>
    <div style="color:{TEXT_PRI};font-weight:700;font-size:1.1rem;margin-bottom:0.4rem">Carteira vazia</div>
    <div style="color:{MUTED};font-size:0.85rem">Adicione seu primeiro ativo acima para começar</div>
</div>
""", unsafe_allow_html=True)
        st.stop()

    # ── Ações ─────────────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns([4, 1.2, 1.2])
    with col_a:
        if st.button("🔄  Atualizar preços de mercado", type="primary", use_container_width=True):
            with st.spinner("Buscando preços..."):
                precos = get_batch_prices([a.ticker for a in carteira.ativos])
                nao_enc = [t for t, p in precos.items() if not p]
                for t, p in precos.items():
                    if p: carteira.atualizar_preco(t, p)
                salvar_carteira(carteira)
            st.warning(f"Não encontrados: {', '.join(nao_enc)}") if nao_enc else st.success("✅ Preços atualizados!")
            st.rerun()
    with col_b:
        with st.expander("🗑️  Remover"):
            ticker_rem = st.selectbox("", [a.ticker for a in carteira.ativos], label_visibility="collapsed")
            if st.button("Remover", use_container_width=True):
                carteira.remover(ticker_rem)
                remover_ativo(ticker_rem)
                st.rerun()
    with col_c:
        if st.button("🧹  Limpar tudo", use_container_width=True):
            st.session_state.carteira = Carteira()
            limpar_carteira()
            st.rerun()

    st.divider()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Investido",   f"R$ {carteira.valor_total_investido:,.2f}")
    m2.metric("📈 Valor Atual", f"R$ {carteira.valor_total_atual:,.2f}")
    m3.metric("P&L",            f"R$ {carteira.pl_total_reais:+,.2f}", delta=f"{carteira.pl_total_pct:+.2f}%")
    m4.metric("Ativos",         len(carteira.ativos))

    st.divider()

    # ── Gráfico evolução ──────────────────────────────────────────────────────
    sec("Evolução patrimonial — 12 meses")
    with st.spinner(""):
        acum = retorno_acumulado_carteira(carteira)

    if acum is not None and len(acum) > 1:
        valor_inicial = carteira.valor_total_investido
        serie_valor   = valor_inicial * (1 + acum)
        retorno_final = float(acum.iloc[-1]) * 100
        cor_linha = POS if retorno_final >= 0 else NEG
        cor_fill  = "rgba(74,222,128,0.06)" if retorno_final >= 0 else "rgba(248,113,113,0.06)"

        fig_evol = go.Figure()
        fig_evol.add_trace(go.Scatter(
            x=serie_valor.index, y=serie_valor.values,
            mode="lines", fill="tozeroy", fillcolor=cor_fill,
            line=dict(color=cor_linha, width=2),
            hovertemplate="%{x|%d/%m/%Y}<br><b>R$ %{y:,.2f}</b><extra></extra>",
        ))
        fig_evol.add_hline(y=valor_inicial, line_color=BORDER, line_dash="dash", line_width=1,
                           annotation_text="Investido", annotation_font_color=MUTED,
                           annotation_position="bottom left")
        fig_evol.update_layout(**plotly_layout({"margin": dict(t=10, b=40, l=80, r=40)}),
                               yaxis_tickprefix="R$ ", showlegend=False,
                               height=200, hovermode="x unified")
        st.plotly_chart(fig_evol, use_container_width=True, key="evol_carteira")
    else:
        st.caption("Histórico insuficiente para gerar o gráfico.")

    st.divider()

    # ── Tabela ────────────────────────────────────────────────────────────────
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
        use_container_width=True, hide_index=True,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — SIMULADOR
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "🔮  Simulador":
    page_header("Simulador de Cenários", "Monte Carlo com choques macroeconômicos")

    if not carteira.ativos:
        st.warning("Cadastre ativos na página Carteira primeiro.")
        st.stop()

    exemplos = ["e se o dólar subir 20%?", "e se o Fed cortar juros em 1 ponto?",
                "crise global severa", "e se a Selic cair para 10%?", "petróleo desaba 30%"]
    cols = st.columns(len(exemplos))
    for i, ex in enumerate(exemplos):
        if cols[i].button(ex, use_container_width=True):
            st.session_state.cenario_texto = ex
            st.rerun()

    cenario_texto = st.text_area("cenario", value=st.session_state.get("cenario_texto", ""),
                                  placeholder="Ex: e se a Selic subir 2 pontos e o dólar cair 10%?",
                                  label_visibility="collapsed", height=80)

    if st.button("🚀  Simular cenário", type="primary", use_container_width=True):
        if not cenario_texto.strip():
            st.error("Digite um cenário.")
            st.stop()

        prog = st.progress(0, text="🤖 Interpretando cenário...")
        choque, resumo = extrair_choque(cenario_texto)
        prog.progress(33, text="⚙️ Rodando Monte Carlo...")
        st.info(f"**Interpretação:** {resumo}")

        choque_nz = {k: v for k, v in choque.items() if v != 0}
        if choque_nz:
            from macro_model import VARIAVEIS_MACRO
            cols_c = st.columns(len(choque_nz))
            for i, (k, v) in enumerate(choque_nz.items()):
                cols_c[i].metric(VARIAVEIS_MACRO[k], f"{v:+.1f}%",
                                 delta_color="normal" if v > 0 else "inverse")

        resultado = simular_carteira(carteira, choque)
        prog.progress(80, text="📊 Gerando visualizações...")
        st.session_state.historico_simulacoes.append({
            "cenario": cenario_texto, "resumo": resumo,
            "p10": resultado.retorno_p10_pct, "p50": resultado.retorno_p50_pct,
            "p90": resultado.retorno_p90_pct, "impacto": resultado.impacto_choque_pct,
        })
        prog.progress(100, text="✅ Concluído!")
        prog.empty()

        st.divider()
        st.markdown(
            f"**Resultado:** {badge_retorno(resultado.retorno_p50_pct)} mediano &nbsp;·&nbsp; "
            f"choque: {badge_retorno(resultado.impacto_choque_pct)}",
            unsafe_allow_html=True)
        st.markdown("")

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Valor Atual", f"R$ {resultado.valor_base:,.2f}")
        r2.metric("P10 — Pessimista", f"R$ {resultado.valor_p10:,.2f}", delta=f"{resultado.retorno_p10_pct:+.1f}%")
        r3.metric("P50 — Mediano",    f"R$ {resultado.valor_p50:,.2f}", delta=f"{resultado.retorno_p50_pct:+.1f}%")
        r4.metric("P90 — Otimista",   f"R$ {resultado.valor_p90:,.2f}", delta=f"{resultado.retorno_p90_pct:+.1f}%")

        var_reais = resultado.valor_base - resultado.valor_p10
        st.markdown(
            f'<div class="var-card">'
            f'<p style="font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;margin:0 0 6px;font-family:DM Mono,monospace">⚠️ Valor em Risco (VaR 90%)</p>'
            f'<h3>R$ {var_reais:,.2f} <span style="font-size:0.85rem;opacity:0.7">({abs(resultado.retorno_p10_pct):.1f}%)</span></h3>'
            f'<p style="margin:6px 0 0;font-size:0.78rem;opacity:0.75">Perda máxima esperada em 90% dos cenários simulados</p>'
            f'</div>', unsafe_allow_html=True)

        st.divider()
        col_hist, col_tab = st.columns([3, 2])
        with col_hist:
            sec("Distribuição dos cenários")
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=resultado.distribuicao, nbinsx=80,
                                       marker=dict(color=ACCENT, opacity=0.55, line=dict(color=BG, width=0.3))))
            for val, label, cor, dash in [
                (resultado.valor_p10, "P10", "#f87171", "dash"),
                (resultado.valor_p50, "P50", "#fbbf24", "dash"),
                (resultado.valor_p90, "P90", "#4ade80", "dash"),
                (resultado.valor_base, "Atual", TEXT_PRI, "solid"),
            ]:
                fig.add_vline(x=val, line_color=cor, line_dash=dash, line_width=1.5,
                              annotation_text=label, annotation_font_color=cor, annotation_position="top")
            fig.update_layout(xaxis_title="Valor (R$)", yaxis_title="Freq.", showlegend=False, **plotly_layout())
            st.plotly_chart(fig, use_container_width=True, key="hist_sim")

        with col_tab:
            sec("Impacto por ativo")
            df_imp = impacto_por_ativo(carteira, choque).sort_values("Impacto (R$)")
            st.dataframe(df_imp.style.format({
                "Valor Atual (R$)": "R$ {:,.2f}", "Impacto (%)": "{:+.2f}%", "Impacto (R$)": "R$ {:+,.2f}",
            }).background_gradient(subset=["Impacto (R$)"], cmap="RdYlGn"),
            use_container_width=True, hide_index=True, height=320)

        st.divider()
        sec("🤖 Análise do assessor")
        tabela_ativos = carteira.para_dataframe()[["Ticker", "Classe", "Atual (R$)", "% Carteira"]].to_string(index=False)
        with st.chat_message("assistant"):
            st.write_stream(narrar_resultado_stream(
                cenario_texto, resumo, resultado, tabela_ativos,
                historico_simulacoes=st.session_state.historico_simulacoes))

        st.divider()
        resumo_exp = (f"Cenário: {cenario_texto}\nInterpretação: {resumo}\n\n"
                      f"Valor atual: R$ {resultado.valor_base:,.2f}\n"
                      f"P10: R$ {resultado.valor_p10:,.2f} ({resultado.retorno_p10_pct:+.1f}%)\n"
                      f"P50: R$ {resultado.valor_p50:,.2f} ({resultado.retorno_p50_pct:+.1f}%)\n"
                      f"P90: R$ {resultado.valor_p90:,.2f} ({resultado.retorno_p90_pct:+.1f}%)\n"
                      f"Impacto: {resultado.impacto_choque_pct:+.1f}%\n")
        st.download_button("📥  Exportar (.txt)", data=resumo_exp,
                           file_name=f"sim_{cenario_texto[:25].replace(' ','_')}.txt", mime="text/plain")

    if st.session_state.historico_simulacoes:
        st.divider()
        sec("Histórico de simulações")
        df_hist = pd.DataFrame(st.session_state.historico_simulacoes)
        df_hist.columns = ["Cenário", "Interpretação", "P10 (%)", "P50 (%)", "P90 (%)", "Choque (%)"]
        fig_hist = go.Figure()
        for col, cor in [("P10 (%)", "#f87171"), ("P50 (%)", "#fbbf24"), ("P90 (%)", "#4ade80")]:
            fig_hist.add_trace(go.Bar(
                name=col.replace(" (%)", ""), x=df_hist["Cenário"], y=df_hist[col],
                marker_color=cor, opacity=0.85,
                text=df_hist[col].apply(lambda v: f"{v:+.1f}%"),
                textposition="outside", textfont=dict(family="DM Mono", size=10, color=TEXT_SEC),
            ))
        fig_hist.add_hline(y=0, line_color=BORDER, line_width=1)
        fig_hist.update_layout(**plotly_layout({"margin": dict(t=20, b=60, l=50, r=20)}))
        fig_hist.update_layout(barmode="group", yaxis=dict(ticksuffix="%"),
                               legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SEC)))
        st.plotly_chart(fig_hist, use_container_width=True, key="hist_comparativo")
        st.dataframe(
            df_hist.style.format({"P10 (%)": "{:+.1f}%", "P50 (%)": "{:+.1f}%",
                                   "P90 (%)": "{:+.1f}%", "Choque (%)": "{:+.1f}%"})
            .background_gradient(subset=["P50 (%)"], cmap="RdYlGn", vmin=-30, vmax=30),
            use_container_width=True, hide_index=True)
        if st.button("🗑️ Limpar histórico"):
            st.session_state.historico_simulacoes = []
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — STRESS TEST
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "💥  Stress Test":
    page_header("Stress Test Histórico", "Impacto dos maiores choques do mercado na sua carteira")

    if not carteira.ativos:
        st.warning("Cadastre ativos primeiro.")
        st.stop()

    st.dataframe(pd.DataFrame([{"Cenário": c.nome, "Período": c.periodo, "Descrição": c.descricao}
                                for c in CENARIOS_HISTORICOS]),
                 use_container_width=True, hide_index=True)
    st.divider()

    if st.button("💥  Rodar todos os stress tests", type="primary", use_container_width=True):
        prog = st.progress(0, text="Rodando cenários históricos...")
        df_res, _ = rodar_todos(carteira)
        prog.progress(100, text="✅ Concluído!")
        prog.empty()

        st.dataframe(
            df_res[["Cenário", "Período", "Choque direto", "P10 (%)", "P50 (%)", "P90 (%)"]
            ].style.format({"Choque direto": "{:+.1f}%", "P10 (%)": "{:+.1f}%",
                             "P50 (%)": "{:+.1f}%", "P90 (%)": "{:+.1f}%"})
            .background_gradient(subset=["P50 (%)"], cmap="RdYlGn", vmin=-40, vmax=20),
            use_container_width=True, hide_index=True)

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_bar = go.Figure()
            for col, cor in [("P10 (%)", "#f87171"), ("P50 (%)", "#fbbf24"), ("P90 (%)", "#4ade80")]:
                fig_bar.add_trace(go.Bar(
                    name=col.replace(" (%)", ""), x=df_res["Cenário"].tolist(), y=df_res[col].tolist(),
                    marker_color=cor, opacity=0.85,
                    text=df_res[col].apply(lambda v: f"{v:+.1f}%"),
                    textposition="outside", textfont=dict(family="DM Mono", size=10, color=TEXT_SEC),
                ))
            fig_bar.add_hline(y=0, line_color=BORDER, line_width=1)
            fig_bar.update_layout(**plotly_layout({"margin": dict(t=30, b=80, l=50, r=20)}))
            fig_bar.update_layout(barmode="group",
                                  xaxis=dict(tickangle=-20, tickfont=dict(size=10, color=TEXT_SEC)),
                                  yaxis=dict(zeroline=False, ticksuffix="%"),
                                  legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SEC)))
            st.plotly_chart(fig_bar, use_container_width=True, key="stress_bar")

        with col_g2:
            fig_r = go.Figure(go.Bar(
                x=df_res["Impacto (R$)"].tolist(), y=df_res["Cenário"].tolist(), orientation="h",
                marker_color=["#f87171" if v < 0 else "#4ade80" for v in df_res["Impacto (R$)"]],
                text=df_res["Impacto (R$)"].apply(lambda v: f"R$ {v:+,.0f}"),
                textposition="outside", textfont=dict(family="DM Mono", size=10, color=TEXT_SEC),
                hovertemplate="<b>%{y}</b><br>R$ %{x:+,.2f}<extra></extra>",
            ))
            fig_r.update_layout(**plotly_layout({"margin": dict(t=40, b=20, l=10, r=110)}))
            fig_r.update_layout(title=dict(text="Impacto direto (R$)", font=dict(color=TEXT_SEC, size=12)),
                                xaxis=dict(zeroline=False), yaxis=dict(gridcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig_r, use_container_width=True, key="stress_reais")

        st.divider()
        c_pior, c_melhor = st.columns(2)
        with c_pior:
            row = df_res.iloc[df_res["P50 (%)"].idxmin()]
            st.error(f"**💀 Pior cenário: {row['Cenário']}**\n\nMediano: **{row['P50 (%)']:+.1f}%** (R$ {row['P50 (R$)']:,.2f})\nPessimista: **{row['P10 (%)']:+.1f}%**")
        with c_melhor:
            row = df_res.iloc[df_res["P50 (%)"].idxmax()]
            st.success(f"**🟢 Menos severo: {row['Cenário']}**\n\nMediano: **{row['P50 (%)']:+.1f}%** (R$ {row['P50 (R$)']:,.2f})\nOtimista: **{row['P90 (%)']:+.1f}%**")

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — ANÁLISE
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "📈  Análise":
    page_header("Análise", "Performance, risco e diversificação")

    if not carteira.ativos:
        st.warning("Cadastre ativos primeiro.")
        st.stop()

    df    = carteira.para_dataframe()
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
        sec("Alocação por classe")
        aloc = carteira.alocacao_por_classe()
        fig_pie = go.Figure(go.Pie(
            labels=[CLASSES.get(k, k) for k in aloc], values=list(aloc.values()),
            hole=0.55, marker=dict(colors=[CLASSES_CORES.get(k, ACCENT) for k in aloc],
                                   line=dict(color=BG, width=3)),
            textinfo="percent", textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        ))
        fig_pie.add_annotation(text=f"R$ {total:,.0f}", x=0.5, y=0.5,
                               font=dict(size=12, color=TEXT_PRI, family="DM Mono"), showarrow=False)
        layout_pie = {**PLOT_LAYOUT, "margin": dict(t=10, b=10, l=10, r=10)}
        fig_pie.update_layout(**layout_pie, showlegend=True,
                              legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig_pie, use_container_width=True, key="pie_analise")

    with col2:
        sec("P&L por ativo")
        df_pl = df.sort_values("P&L (R$)")
        fig_pl = go.Figure(go.Bar(
            x=df_pl["P&L (R$)"], y=df_pl["Ticker"], orientation="h",
            marker_color=[NEG if v < 0 else POS for v in df_pl["P&L (R$)"]], opacity=0.85,
            text=df_pl["P&L (R$)"].apply(lambda v: f"R$ {v:+,.0f}"),
            textposition="outside", textfont=dict(size=10, color=MUTED),
        ))
        fig_pl.add_vline(x=0, line_color=BORDER, line_width=1)
        fig_pl.update_layout(**plotly_layout({"margin": dict(t=10, b=10, l=10, r=80)}))
        st.plotly_chart(fig_pl, use_container_width=True, key="pl_analise")

    st.divider()
    sec("Volatilidade anualizada por ativo")
    with st.spinner(""):
        from market_data import get_historical_returns, is_tesouro
        vols = []
        for ativo in carteira.ativos:
            if is_tesouro(ativo.ticker):
                vols.append({"Ticker": ativo.ticker, "Volatilidade (%)": 0.5})
            else:
                r = get_historical_returns(ativo.ticker)
                if r is not None and len(r) > 10:
                    vols.append({"Ticker": ativo.ticker, "Volatilidade (%)": float(np.std(r) * np.sqrt(252) * 100)})

    if vols:
        df_vol = pd.DataFrame(vols).sort_values("Volatilidade (%)", ascending=True)
        def cor_vol(v):
            if v < 15: return "#4ade80"
            if v < 30: return "#fbbf24"
            if v < 50: return "#fb923c"
            return "#f87171"
        fig_vol = go.Figure(go.Bar(
            x=df_vol["Volatilidade (%)"], y=df_vol["Ticker"], orientation="h",
            marker_color=[cor_vol(v) for v in df_vol["Volatilidade (%)"]],
            opacity=0.85,
            text=df_vol["Volatilidade (%)"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside", textfont=dict(size=10, color=MUTED),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
        ))
        for x, label in [(15, "Baixo"), (30, "Moderado"), (50, "Alto")]:
            fig_vol.add_vline(x=x, line_color=BORDER, line_dash="dash", line_width=1,
                              annotation_text=label, annotation_font_color=MUTED,
                              annotation_font_size=10, annotation_position="top")
        fig_vol.update_layout(**plotly_layout({"margin": dict(t=30, b=10, l=10, r=80)}), xaxis_ticksuffix="%")
        st.plotly_chart(fig_vol, use_container_width=True, key="vol_analise")
        st.markdown(
            f'<span style="color:#4ade80;font-family:DM Mono,monospace;font-size:0.72rem">■ Baixo &lt;15%</span>&nbsp;&nbsp;'
            f'<span style="color:#fbbf24;font-family:DM Mono,monospace;font-size:0.72rem">■ Moderado 15–30%</span>&nbsp;&nbsp;'
            f'<span style="color:#fb923c;font-family:DM Mono,monospace;font-size:0.72rem">■ Alto 30–50%</span>&nbsp;&nbsp;'
            f'<span style="color:#f87171;font-family:DM Mono,monospace;font-size:0.72rem">■ Muito alto &gt;50%</span>',
            unsafe_allow_html=True)

    st.divider()
    sec("Retorno acumulado vs benchmarks — 12 meses")
    with st.spinner(""):
        acum_cart  = retorno_acumulado_carteira(carteira)
        acum_bench = acumulado_benchmarks()

    if acum_bench is not None and not acum_bench.empty:
        st.session_state.benchmarks_cache = {
            col: float(acum_bench[col].dropna().iloc[-1]) * 100
            for col in acum_bench.columns if not acum_bench[col].dropna().empty
        }

    if acum_cart is not None:
        fig_acum = go.Figure()
        acum_bench_aligned = acum_bench.reindex(acum_cart.index, method="ffill").bfill()
        for col, cor in [("Ibovespa", "#f59e0b"), ("CDI", "#4ade80"), ("IPCA", "#f87171")]:
            serie = acum_bench_aligned.get(col, pd.Series()).dropna()
            if len(serie) > 1:
                fig_acum.add_trace(go.Scatter(x=serie.index, y=serie.values * 100,
                                              name=col, mode="lines", line=dict(color=cor, width=2)))
        fig_acum.add_trace(go.Scatter(x=acum_cart.index, y=acum_cart.values * 100,
                                      name="Carteira", mode="lines", line=dict(color=ACCENT, width=3)))
        fig_acum.add_hline(y=0, line_color=BORDER, line_width=1)
        fig_acum.update_layout(**plotly_layout({"margin": dict(t=20, b=40, l=60, r=20)}),
                               yaxis_ticksuffix="%",
                               legend=dict(bgcolor="rgba(30,41,59,0.95)", bordercolor=BORDER,
                                           borderwidth=1, font=dict(size=11, color=TEXT_PRI)),
                               hovermode="x unified")
        st.plotly_chart(fig_acum, use_container_width=True, key="acum_analise")
        resumo_bench = {"Carteira": f"{acum_cart.iloc[-1]*100:+.1f}%"}
        for col in acum_bench.columns:
            s = acum_bench[col].dropna()
            if len(s): resumo_bench[col] = f"{s.iloc[-1]*100:+.1f}%"
        st.dataframe(pd.DataFrame([resumo_bench]), use_container_width=True, hide_index=True)

    st.divider()
    sec("Correlação entre ativos — 12 meses")
    with st.spinner(""):
        corr = matriz_correlacao(carteira)

    if corr is not None and not corr.empty:
        fig_corr = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
            colorscale=[[0.0, "#dc2626"], [0.5, "#1e293b"], [1.0, "#16a34a"]],
            zmin=-1, zmax=1, text=corr.round(2).values, texttemplate="%{text}",
            textfont=dict(size=11, color=TEXT_PRI),
            hovertemplate="<b>%{x} × %{y}</b><br>%{z:.2f}<extra></extra>",
            showscale=True, colorbar=dict(thickness=10, len=0.8, tickfont=dict(size=10)),
        ))
        fig_corr.update_layout(**plotly_layout({
            "margin": dict(t=20, b=60, l=80, r=20),
            "xaxis": dict(gridcolor=BORDER, zeroline=False, side="bottom", tickfont=dict(size=11)),
            "yaxis": dict(gridcolor=BORDER, zeroline=False, tickfont=dict(size=11), autorange="reversed"),
        }))
        st.plotly_chart(fig_corr, use_container_width=True, key="corr_analise")
        st.caption("Verde = correlação positiva · Vermelho = negativa")

    st.divider()
    sec("Métricas de risco — 12 meses")
    with st.spinner(""):
        metricas = calcular_metricas(carteira)

    if metricas:
        r1, r2, r3, r4, r5 = st.columns(5)
        sharpe_label, _ = interpretar_sharpe(metricas["sharpe"])
        dd_label, _     = interpretar_drawdown(metricas["max_drawdown"])
        r1.metric("Volatilidade",  f"{metricas['vol_anual']*100:.1f}%",  help="Desvio padrão anualizado")
        r2.metric("Sharpe",        f"{metricas['sharpe']:.2f}",          delta=sharpe_label, delta_color="normal" if metricas["sharpe"] >= 0.5 else "inverse")
        r3.metric("Sortino",       f"{metricas['sortino']:.2f}",         help="Sharpe penalizando só volatilidade negativa")
        r4.metric("Max Drawdown",  f"{metricas['max_drawdown']*100:.1f}%", delta=dd_label, delta_color="inverse" if abs(metricas["max_drawdown"]) > 0.10 else "normal")
        r5.metric("Beta vs Ibov",  f"{metricas['beta']:.2f}" if metricas["beta"] else "—")

        st.divider()
        sec("Drawdown histórico")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=metricas["serie_drawdown"].index, y=metricas["serie_drawdown"].values * 100,
            mode="lines", fill="tozeroy", fillcolor="rgba(248,113,113,0.08)",
            line=dict(color="#f87171", width=1.5),
            hovertemplate="%{x|%d/%m/%Y}<br>%{y:.2f}%<extra></extra>",
        ))
        fig_dd.add_hline(y=metricas["max_drawdown"] * 100, line_color="#f87171",
                         line_dash="dash", line_width=1,
                         annotation_text=f"Máx: {metricas['max_drawdown']*100:.1f}%",
                         annotation_font_color="#f87171")
        fig_dd.update_layout(**plotly_layout({"margin": dict(t=20, b=40, l=60, r=20)}),
                             yaxis_ticksuffix="%", showlegend=False, hovermode="x unified")
        st.plotly_chart(fig_dd, use_container_width=True, key="dd_analise")

        col_int1, col_int2 = st.columns(2)
        with col_int1:
            st.markdown(f'<div class="info-card"><p style="color:{MUTED};font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;margin:0 0 8px;font-family:DM Mono,monospace">Sharpe · {sharpe_label}</p><p style="color:{TEXT_SEC};font-size:0.85rem;margin:0">Para cada unidade de risco, gerou <strong style="color:{TEXT_PRI}">{metricas["sharpe"]:.2f}x</strong> acima do CDI.{"" if metricas["sharpe"] >= 1 else " Considere reduzir ativos voláteis."}</p></div>', unsafe_allow_html=True)
        with col_int2:
            st.markdown(f'<div class="info-card"><p style="color:{MUTED};font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;margin:0 0 8px;font-family:DM Mono,monospace">Max Drawdown · {dd_label}</p><p style="color:{TEXT_SEC};font-size:0.85rem;margin:0">Maior queda: <strong style="color:{TEXT_PRI}">{metricas["max_drawdown"]*100:.1f}%</strong> em {metricas["max_dd_date"].strftime("%d/%m/%Y")}.</p></div>', unsafe_allow_html=True)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        sec("Peso por ativo")
        df_peso = df.sort_values("% Carteira", ascending=True)
        fig_peso = go.Figure(go.Bar(
            x=df_peso["% Carteira"], y=df_peso["Ticker"], orientation="h",
            marker_color=ACCENT, opacity=0.65,
            text=df_peso["% Carteira"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside", textfont=dict(size=10, color=MUTED),
        ))
        fig_peso.update_layout(**plotly_layout({"margin": dict(t=10, b=10, l=10, r=60)}), xaxis_ticksuffix="%")
        st.plotly_chart(fig_peso, use_container_width=True, key="peso_analise")

    with col4:
        sec("Concentração")
        alertas = [(r["Ticker"], r["% Carteira"]) for _, r in df.iterrows() if r["% Carteira"] > 20]
        if alertas:
            for ticker, pct in alertas:
                if pct > 30: st.error(f"**{ticker}** representa {pct:.1f}% — alta concentração")
                else:        st.warning(f"**{ticker}** representa {pct:.1f}%")
        else:
            st.success("✅ Nenhum ativo acima de 20%")

        pesos  = df["% Carteira"].values / 100
        hhi    = np.sum(pesos ** 2)
        n_eq   = 1 / hhi if hhi > 0 else 1
        score  = min(100, int(n_eq / len(df) * 100 + (1 - hhi) * 60))
        st.metric("Score de diversificação", f"{score} / 100",
                  delta="Bom" if score > 60 else "A melhorar",
                  delta_color="normal" if score > 60 else "inverse")

        st.markdown(f'<div style="margin-top:1rem">', unsafe_allow_html=True)
        for classe, pct in sorted(carteira.alocacao_por_classe().items(), key=lambda x: -x[1]):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {BORDER}">'
                f'<span style="color:{MUTED};font-size:0.82rem">{CLASSES.get(classe,classe)}</span>'
                f'<span style="color:{TEXT_SEC};font-size:0.82rem;font-family:DM Mono,monospace">{pct:.1f}%</span>'
                f'</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 5 — ASSESSOR IA
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "💬  Assessor IA":
    page_header("Assessor IA", "Chat com contexto completo da carteira e simulações")

    if not carteira.ativos:
        st.warning("Cadastre ativos para o assessor ter contexto.")

    with st.expander("📋 Contexto carregado", expanded=False):
        col_ctx1, col_ctx2 = st.columns(2)
        with col_ctx1:
            st.caption(f"**Ativos:** {len(carteira.ativos)}")
            st.caption(f"**Valor:** R$ {carteira.valor_total_atual:,.2f}")
            st.caption(f"**P&L:** {carteira.pl_total_pct:+.1f}%")
        with col_ctx2:
            n_sims = len(st.session_state.historico_simulacoes)
            st.caption(f"**Simulações:** {n_sims}")
            if n_sims:
                ultimas = [s['cenario'] for s in st.session_state.historico_simulacoes[-3:]]
                st.caption(" · ".join(f'"{c[:20]}"' for c in ultimas))

    st.divider()

    col_p, col_l = st.columns([3, 1])
    with col_p:
        if st.button("🔍  Analisar rebalanceamento", type="primary", use_container_width=True):
            if carteira.ativos:
                with st.chat_message("assistant"):
                    resposta = st.write_stream(sugerir_rebalanceamento_stream(
                        carteira, st.session_state.historico_simulacoes, st.session_state.benchmarks_cache))
                st.session_state.historico_chat.append({"role": "user", "content": "[rebalanceamento]"})
                st.session_state.historico_chat.append({"role": "assistant", "content": resposta})
            else:
                st.warning("Cadastre ativos primeiro.")
    with col_l:
        if st.button("🗑️  Limpar", use_container_width=True):
            st.session_state.historico_chat = []
            st.rerun()

    st.divider()

    for msg in st.session_state.historico_chat:
        if msg["content"] == "[rebalanceamento]":
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not st.session_state.historico_chat:
        sec("Sugestões para começar")
        SUGESTOES = ["Qual meu ativo mais arriscado?", "Como estou vs Ibovespa?",
                     "Resuma os cenários simulados", "Onde estou concentrado demais?", "Me explica o VaR"]
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