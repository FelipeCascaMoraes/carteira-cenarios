"""
risk_metrics.py
────────────────────────────────────────────────────────────
Métricas de risco para a carteira: Sharpe, Sortino, Drawdown,
Volatilidade, Beta vs Ibovespa.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from analytics import retorno_acumulado_carteira, _strip_tz

PERIODO_DIAS = 365
CDI_ANUAL    = 0.105  # fallback ~10.5% a.a.
TRADING_DAYS = 252


def _retornos_diarios_carteira(carteira, days: int = PERIODO_DIAS) -> pd.Series | None:
    """Reconstrói série de retornos diários ponderados da carteira."""
    from market_data import _normalizar_ticker, is_crypto, is_tesouro
    start = (datetime.today() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
    total = carteira.valor_total_atual or 1
    series = []

    for ativo in carteira.ativos:
        peso = ativo.valor_atual / total
        retornos = None

        if is_tesouro(ativo.ticker):
            diario = (1 + CDI_ANUAL) ** (1 / TRADING_DAYS) - 1
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
                    retornos = _strip_tz(hist["Close"].pct_change().dropna())
            except Exception:
                pass

        if retornos is not None and len(retornos) > 0:
            series.append(retornos * peso)

    if not series:
        return None

    df = pd.concat(series, axis=1).fillna(0)
    return df.sum(axis=1)


def _retornos_ibovespa(days: int = PERIODO_DIAS) -> pd.Series | None:
    try:
        start = (datetime.today() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
        hist = yf.Ticker("^BVSP").history(start=start)
        if hist.empty:
            return None
        return _strip_tz(hist["Close"].pct_change().dropna())
    except Exception:
        return None


def calcular_metricas(carteira, days: int = PERIODO_DIAS) -> dict:
    """
    Retorna dict com todas as métricas de risco da carteira.
    """
    retornos = _retornos_diarios_carteira(carteira, days)
    if retornos is None or len(retornos) < 20:
        return {}

    retornos = retornos.dropna()
    rf_diario = (1 + CDI_ANUAL) ** (1 / TRADING_DAYS) - 1  # risk-free diário

    # ── Retorno ───────────────────────────────────────────────────────────────
    retorno_total   = float((1 + retornos).prod() - 1)
    retorno_anual   = float((1 + retorno_total) ** (TRADING_DAYS / len(retornos)) - 1)

    # ── Volatilidade ──────────────────────────────────────────────────────────
    vol_diaria  = float(retornos.std())
    vol_anual   = vol_diaria * np.sqrt(TRADING_DAYS)

    # ── Sharpe ────────────────────────────────────────────────────────────────
    excess      = retornos - rf_diario
    sharpe      = float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS)) if excess.std() > 0 else 0.0

    # ── Sortino (penaliza só retornos negativos) ──────────────────────────────
    downside    = retornos[retornos < rf_diario] - rf_diario
    downside_std = float(np.sqrt((downside ** 2).mean())) if len(downside) > 0 else 0.0
    sortino     = float(excess.mean() / downside_std * np.sqrt(TRADING_DAYS)) if downside_std > 0 else 0.0

    # ── Max Drawdown ──────────────────────────────────────────────────────────
    acum        = (1 + retornos).cumprod()
    rolling_max = acum.cummax()
    drawdown    = (acum - rolling_max) / rolling_max
    max_dd      = float(drawdown.min())
    max_dd_date = drawdown.idxmin()

    # ── Calmar Ratio ─────────────────────────────────────────────────────────
    calmar = float(retorno_anual / abs(max_dd)) if max_dd != 0 else 0.0

    # ── Beta vs Ibovespa ──────────────────────────────────────────────────────
    beta = None
    ibov = _retornos_ibovespa(days)
    if ibov is not None:
        df_joint = pd.concat([retornos, ibov], axis=1).dropna()
        if len(df_joint) > 20:
            df_joint.columns = ["carteira", "ibov"]
            cov   = df_joint.cov().iloc[0, 1]
            var_m = df_joint["ibov"].var()
            beta  = float(cov / var_m) if var_m > 0 else None

    return {
        "retorno_total":   retorno_total,
        "retorno_anual":   retorno_anual,
        "vol_anual":       vol_anual,
        "sharpe":          sharpe,
        "sortino":         sortino,
        "max_drawdown":    max_dd,
        "max_dd_date":     max_dd_date,
        "calmar":          calmar,
        "beta":            beta,
        "n_dias":          len(retornos),
        "serie_retornos":  retornos,
        "serie_drawdown":  drawdown,
        "serie_acum":      acum,
    }


def interpretar_sharpe(s: float) -> tuple[str, str]:
    """Retorna (label, cor) para o Sharpe."""
    if s >= 2.0:   return "Excelente", "#4ade80"
    if s >= 1.0:   return "Bom",       "#a3e635"
    if s >= 0.5:   return "Razoável",  "#fbbf24"
    if s >= 0.0:   return "Fraco",     "#fb923c"
    return "Negativo", "#f87171"


def interpretar_drawdown(dd: float) -> tuple[str, str]:
    """Retorna (label, cor) para o max drawdown."""
    dd_pct = abs(dd) * 100
    if dd_pct < 5:    return "Baixo",    "#4ade80"
    if dd_pct < 15:   return "Moderado", "#fbbf24"
    if dd_pct < 30:   return "Alto",     "#fb923c"
    return "Severo", "#f87171"