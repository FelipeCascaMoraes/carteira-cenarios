# analytics.py

import numpy as np
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from portfolio import Carteira
import streamlit as st

PERIODO_DIAS = 365

@st.cache_data(ttl=300, show_spinner=False)
def retorno_acumulado_carteira(carteira: Carteira, days: int = 365) -> pd.Series | None:
    # corpo da função que já existia, sem alteração
    ...

@st.cache_data(ttl=300, show_spinner=False)
def acumulado_benchmarks(days: int = 365) -> pd.DataFrame:
    # corpo da função que já existia, sem alteração
    ...

@st.cache_data(ttl=300, show_spinner=False)
def matriz_correlacao(carteira: Carteira, days: int = 365) -> pd.DataFrame | None:
    # corpo da função que já existia, sem alteração
    ...

PERIODO_DIAS = 365

# ─── Benchmarks ──────────────────────────────────────────────────────────────
def _strip_tz(s: pd.Series) -> pd.Series:
    """Remove fuso horário do índice se existir."""
    if isinstance(s.index, pd.DatetimeIndex) and s.index.tz is not None:
        s = s.copy()
        s.index = s.index.tz_localize(None)
    return s

def _retornos_ibovespa(days: int = PERIODO_DIAS) -> pd.Series:
    start = (datetime.today() - timedelta(days=days+30)).strftime("%Y-%m-%d")
    hist  = yf.Ticker("^BVSP").history(start=start)
    if hist.empty: return pd.Series(dtype=float)
    closes = hist["Close"]
    return _strip_tz(closes.pct_change().dropna().rename("Ibovespa"))

def _retornos_cdi(days: int = PERIODO_DIAS) -> pd.Series:
    """
    Aproxima o CDI diário via ETF CDII11 (Tesouro Selic ETF).
    Fallback: taxa fixa de 10.5% a.a. convertida para diário.
    """
    try:
        start = (datetime.today() - timedelta(days=days+30)).strftime("%Y-%m-%d")
        hist  = yf.Ticker("CDII11.SA").history(start=start)
        if not hist.empty and len(hist) > 20:
            return hist["Close"].pct_change().dropna().rename("CDI")
    except Exception:
        pass
    # Fallback: CDI fixo aprox. 10.5% a.a.
    n = days
    diario = (1 + 0.105) ** (1/252) - 1
    idx = pd.date_range(end=datetime.today(), periods=n, freq="B")
    return pd.Series(diario, index=idx, name="CDI")


def _retornos_ipca(days: int = PERIODO_DIAS) -> pd.Series:
    """
    IPCA mensal via API do Banco Central (série 433).
    Converte para retorno diário aproximado.
    """
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&ultimos=24"
        data = requests.get(url, timeout=10).json()
        valores = [(d["data"], float(d["valor"].replace(",", ".")) / 100) for d in data]
        df = pd.DataFrame(valores, columns=["data", "ipca_mensal"])
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df = df.set_index("data").sort_index()
        # Converte mensal → diário (aproximado)
        df["ipca_diario"] = (1 + df["ipca_mensal"]) ** (1/21) - 1
        # Expande para dias úteis
        idx = pd.date_range(end=datetime.today(), periods=days, freq="B")
        serie = df["ipca_diario"].reindex(idx, method="ffill").dropna()
        return serie.rename("IPCA")
    except Exception:
        # Fallback fixo ~4.5% a.a.
        diario = (1 + 0.045) ** (1/252) - 1
        idx = pd.date_range(end=datetime.today(), periods=days, freq="B")
        return pd.Series(diario, index=idx, name="IPCA")


def get_benchmarks(days: int = PERIODO_DIAS) -> pd.DataFrame:
    """Retorna DataFrame com retornos diários dos 3 benchmarks."""
    ibov = _strip_tz(_retornos_ibovespa(days))
    cdi  = _strip_tz(_retornos_cdi(days))
    ipca = _strip_tz(_retornos_ipca(days))
    df = pd.concat([ibov, cdi, ipca], axis=1).dropna(how="all")
    return df


# ─── Retorno acumulado da carteira ───────────────────────────────────────────

def retorno_acumulado_carteira(carteira: Carteira, days: int = PERIODO_DIAS) -> pd.Series | None:
    """
    Reconstrói o retorno acumulado da carteira usando histórico real de preços.
    Pondera pelo valor atual de cada ativo.
    """
    from market_data import _normalizar_ticker, is_crypto, is_tesouro, COINGECKO_IDS
    import yfinance as yf

    start = (datetime.today() - timedelta(days=days+30)).strftime("%Y-%m-%d")
    total_valor = carteira.valor_total_atual or 1
    series = []

    for ativo in carteira.ativos:
        peso = (ativo.valor_atual / total_valor)
        retornos = None

        if is_tesouro(ativo.ticker):
            # Tesouro: usa retorno fixo estimado (sem histórico de PU disponível)
            diario = (1 + 0.105) ** (1/252) - 1
            idx = pd.date_range(end=datetime.today(), periods=days, freq="B")
            retornos = pd.Series(diario, index=idx)

        elif is_crypto(ativo.ticker):
            from market_data import _retornos_cripto
            arr = _retornos_cripto(ativo.ticker, days)
            if arr is not None:
                idx = pd.date_range(end=datetime.today(), periods=len(arr), freq="B")
                retornos = pd.Series(arr, index=idx[-len(arr):])

        else:
            ticker_yf = _normalizar_ticker(ativo.ticker)
            try:
                hist = yf.Ticker(ticker_yf).history(start=start)
                if not hist.empty:
                    closes = hist["Close"]
                    retornos = _strip_tz(closes.pct_change().dropna())
            except Exception:
                pass

        if retornos is not None and len(retornos) > 0:
            series.append(retornos * peso)

    if not series:
        return None

    # Alinha todos pelo índice comum
    df = pd.concat(series, axis=1).fillna(0)
    retorno_carteira = df.sum(axis=1)

    # Acumulado
    acumulado = (1 + retorno_carteira).cumprod() - 1
    return acumulado.rename("Carteira")


# ─── Acumulado dos benchmarks ────────────────────────────────────────────────

def acumulado_benchmarks(days: int = PERIODO_DIAS) -> pd.DataFrame:
    df = get_benchmarks(days)
    return (1 + df).cumprod() - 1


# ─── Correlação entre ativos ─────────────────────────────────────────────────

def matriz_correlacao(carteira: Carteira, days: int = PERIODO_DIAS) -> pd.DataFrame | None:
    from market_data import _normalizar_ticker, is_crypto, is_tesouro, COINGECKO_IDS
    import yfinance as yf

    if len(carteira.ativos) < 2:
        return None

    start = (datetime.today() - timedelta(days=days+30)).strftime("%Y-%m-%d")
    series = {}

    for ativo in carteira.ativos:
        retornos = None

        if is_tesouro(ativo.ticker):
            continue  # sem histórico de PU

        elif is_crypto(ativo.ticker):
            from market_data import _retornos_cripto
            arr = _retornos_cripto(ativo.ticker, days)
            if arr is not None:
                idx = pd.date_range(end=datetime.today(), periods=len(arr), freq="B")
                retornos = pd.Series(arr, index=idx[-len(arr):])

        else:
            ticker_yf = _normalizar_ticker(ativo.ticker)
            try:
                hist = yf.Ticker(ticker_yf).history(start=start)
                if not hist.empty:
                    retornos = _strip_tz(hist["Close"].pct_change().dropna())
            except Exception:
                pass

        if retornos is not None and len(retornos) > 20:
            series[ativo.ticker] = retornos

    if len(series) < 2:
        return None

    df = pd.DataFrame(series).dropna()
    return df.corr()