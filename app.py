# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from portfolio import Carteira, Ativo, CLASSES
from market_data import get_batch_prices
from simulator import simular_carteira, impacto_por_ativo
from agent import extrair_choque, narrar_resultado_stream

# ─── Config ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Simulador de Carteira",
    page_icon="📊",
    layout="wide",
)

# ─── Estado ──────────────────────────────────────────────────────────────────

if "carteira" not in st.session_state:
    st.session_state.carteira = Carteira.carregar_json()

carteira: Carteira = st.session_state.carteira

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📊 Simulador")
    st.caption("Monte Carlo + IA")
    st.divider()
    pagina = st.radio(
        "Navegação",
        ["📊 Carteira", "🔮 Simulador", "📈 Análise"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"{len(carteira.ativos)} ativo(s) cadastrado(s)")
    if carteira.ativos:
        st.caption(f"Total: R$ {carteira.valor_total_atual:,.2f}")

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — CARTEIRA
# ═══════════════════════════════════════════════════════════════════════════════

if pagina == "📊 Carteira":
    st.header("Minha Carteira")

    # ── Formulário de adição ─────────────────────────────────────────────────
    with st.expander("➕ Adicionar ativo", expanded=not carteira.ativos):
        c1, c2 = st.columns(2)
        with c1:
            ticker     = st.text_input("Ticker", placeholder="PETR4 / AAPL / BTC").upper().strip()
            nome       = st.text_input("Nome", placeholder="Ex: Petrobras PN")
            classe     = st.selectbox("Classe", options=list(CLASSES.keys()),
                                      format_func=lambda x: CLASSES[x])
        with c2:
            quantidade  = st.number_input("Quantidade",   min_value=0.0, step=1.0,    value=1.0)
            preco_medio = st.number_input("Preço médio",  min_value=0.0, step=0.01,   value=0.0)

        if st.button("Adicionar", use_container_width=True):
            if ticker and preco_medio > 0:
                carteira.adicionar(Ativo(
                    ticker=ticker, nome=nome or ticker,
                    classe=classe, quantidade=quantidade,
                    preco_medio=preco_medio,
                ))
                carteira.salvar_json()
                st.success(f"✅ {ticker} adicionado!")
                st.rerun()
            else:
                st.error("Preencha ticker e preço médio.")

    if not carteira.ativos:
        st.info("Nenhum ativo cadastrado ainda. Adicione acima para começar.")
        st.stop()

    # ── Atualizar preços ─────────────────────────────────────────────────────
    col_btn, col_del = st.columns([4, 1])
    with col_btn:
        if st.button("🔄 Atualizar preços de mercado", use_container_width=True):
            with st.spinner("Buscando preços..."):
                precos = get_batch_prices([a.ticker for a in carteira.ativos])
                for ticker, preco in precos.items():
                    if preco:
                        carteira.atualizar_preco(ticker, preco)
                carteira.salvar_json()
            st.success("Preços atualizados!")
            st.rerun()
    with col_del:
        if st.button("🗑️ Limpar carteira", use_container_width=True):
            st.session_state.carteira = Carteira()
            Carteira().salvar_json()
            st.rerun()

    # ── Métricas resumo ──────────────────────────────────────────────────────
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Investido",   f"R$ {carteira.valor_total_investido:,.2f}")
    m2.metric("📈 Valor Atual", f"R$ {carteira.valor_total_atual:,.2f}")
    m3.metric("P&L (R$)",
              f"R$ {carteira.pl_total_reais:+,.2f}",
              delta=f"{carteira.pl_total_pct:+.2f}%")
    m4.metric("Ativos", len(carteira.ativos))

    # ── Tabela ───────────────────────────────────────────────────────────────
    st.divider()
    df = carteira.para_dataframe()
    st.dataframe(
        df.style.format({
            "Preço Médio":    "R$ {:.2f}",
            "Preço Atual":    lambda v: f"R$ {v:.2f}" if v else "—",
            "Investido (R$)": "R$ {:,.2f}",
            "Atual (R$)":     "R$ {:,.2f}",
            "P&L (R$)":       "R$ {:+,.2f}",
            "P&L (%)":        "{:+.2f}%",
            "% Carteira":     "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # ── Remover ativo ────────────────────────────────────────────────────────
    with st.expander("🗑️ Remover ativo"):
        ticker_rem = st.selectbox("Selecione", [a.ticker for a in carteira.ativos])
        if st.button("Remover", type="secondary"):
            carteira.remover(ticker_rem)
            carteira.salvar_json()
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — SIMULADOR
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "🔮 Simulador":
    st.header("Simulador de Cenários")

    if not carteira.ativos:
        st.warning("Cadastre ativos na página Carteira primeiro.")
        st.stop()

    # ── Input do cenário ─────────────────────────────────────────────────────
    st.subheader("Descreva o cenário")
    exemplos = [
        "e se o dólar subir 20%?",
        "e se o Fed cortar juros em 1 ponto?",
        "e se houver uma crise global?",
        "e se o petróleo desabar 30%?",
    ]
    col_ex = st.columns(len(exemplos))
    cenario_texto = st.session_state.get("cenario_texto", "")
    for i, ex in enumerate(exemplos):
        if col_ex[i].button(ex, use_container_width=True):
            st.session_state.cenario_texto = ex
            st.rerun()

    cenario_texto = st.text_area(
        "Cenário",
        value=st.session_state.get("cenario_texto", ""),
        placeholder="Ex: e se a Selic subir 2 pontos e o dólar cair 10%?",
        label_visibility="collapsed",
        height=80,
    )

    if st.button("🚀 Simular", type="primary", use_container_width=True):
        if not cenario_texto.strip():
            st.error("Digite um cenário.")
            st.stop()

        # 1. Extrai variáveis macro
        with st.spinner("🤖 Interpretando cenário..."):
            choque, resumo = extrair_choque(cenario_texto)

        # Mostra o que foi extraído
        st.info(f"**Interpretação:** {resumo}")
        choque_nao_zero = {k: v for k, v in choque.items() if v != 0}
        if choque_nao_zero:
            cols = st.columns(len(choque_nao_zero))
            from macro_model import VARIAVEIS_MACRO
            for i, (k, v) in enumerate(choque_nao_zero.items()):
                cols[i].metric(VARIAVEIS_MACRO[k], f"{v:+.1f}%")

        # 2. Roda simulação
        with st.spinner("⚙️ Rodando Monte Carlo (10.000 cenários)..."):
            resultado = simular_carteira(carteira, choque)

        # 3. Métricas principais
        st.divider()
        st.subheader("Resultados")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Valor Atual",     f"R$ {resultado.valor_base:,.2f}")
        r2.metric("Pessimista (P10)", f"R$ {resultado.valor_p10:,.2f}",
                  delta=f"{resultado.retorno_p10_pct:+.1f}%")
        r3.metric("Mediano (P50)",    f"R$ {resultado.valor_p50:,.2f}",
                  delta=f"{resultado.retorno_p50_pct:+.1f}%")
        r4.metric("Otimista (P90)",   f"R$ {resultado.valor_p90:,.2f}",
                  delta=f"{resultado.retorno_p90_pct:+.1f}%")

        # 4. Histograma
        st.divider()
        col_hist, col_tab = st.columns([3, 2])

        with col_hist:
            st.subheader("Distribuição dos cenários")
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=resultado.distribuicao,
                nbinsx=80,
                marker_color="#4f8ef7",
                opacity=0.8,
                name="Simulações",
            ))
            for val, label, cor in [
                (resultado.valor_p10, "P10", "red"),
                (resultado.valor_p50, "P50", "yellow"),
                (resultado.valor_p90, "P90", "green"),
            ]:
                fig.add_vline(x=val, line_color=cor, line_dash="dash",
                              annotation_text=label, annotation_position="top")
            fig.add_vline(x=resultado.valor_base, line_color="white",
                          line_dash="solid", annotation_text="Atual")
            fig.update_layout(
                xaxis_title="Valor da carteira (R$)",
                yaxis_title="Frequência",
                template="plotly_dark",
                showlegend=False,
                margin=dict(t=20, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

        # 5. Tabela de impacto por ativo
        with col_tab:
            st.subheader("Impacto por ativo")
            df_imp = impacto_por_ativo(carteira, choque)
            df_imp = df_imp.sort_values("Impacto (R$)")
            st.dataframe(
                df_imp.style.format({
                    "Valor Atual (R$)": "R$ {:,.2f}",
                    "Impacto (%)":      "{:+.2f}%",
                    "Impacto (R$)":     "R$ {:+,.2f}",
                }).background_gradient(subset=["Impacto (R$)"], cmap="RdYlGn"),
                use_container_width=True,
                hide_index=True,
            )

        # 6. Narrativa do agente (streaming)
        st.divider()
        st.subheader("🤖 Análise do assessor")
        tabela_ativos = carteira.para_dataframe()[
            ["Ticker", "Classe", "Atual (R$)", "% Carteira"]
        ].to_string(index=False)

        with st.chat_message("assistant"):
            st.write_stream(narrar_resultado_stream(
                cenario_texto, resumo, resultado, tabela_ativos
            ))

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — ANÁLISE
# ═══════════════════════════════════════════════════════════════════════════════

elif pagina == "📈 Análise":
    st.header("Análise da Carteira")

    if not carteira.ativos:
        st.warning("Cadastre ativos na página Carteira primeiro.")
        st.stop()

    col_pie, col_bar = st.columns(2)

    # ── Pizza: alocação por classe ───────────────────────────────────────────
    with col_pie:
        st.subheader("Alocação por classe")
        aloc = carteira.alocacao_por_classe()
        fig_pie = px.pie(
            names=[CLASSES.get(k, k) for k in aloc],
            values=list(aloc.values()),
            hole=0.4,
            template="plotly_dark",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(t=20))
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Barras: peso de cada ativo ───────────────────────────────────────────
    with col_bar:
        st.subheader("Peso por ativo")
        df = carteira.para_dataframe().sort_values("% Carteira", ascending=True)
        fig_bar = go.Figure(go.Bar(
            x=df["% Carteira"],
            y=df["Ticker"],
            orientation="h",
            marker_color="#4f8ef7",
        ))
        fig_bar.update_layout(
            xaxis_title="%",
            template="plotly_dark",
            margin=dict(t=20, l=60),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Tabela completa ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("Visão detalhada")
    st.dataframe(carteira.para_dataframe(), use_container_width=True, hide_index=True)