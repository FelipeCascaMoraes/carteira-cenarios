# simulator.py

import numpy as np
import pandas as pd
from dataclasses import dataclass
from portfolio import Carteira
from macro_model import aplicar_choque
from market_data import get_historical_returns

# ─── Constantes ──────────────────────────────────────────────────────────────

N_SIMULACOES   = 10_000
HORIZONTE_DIAS = 30

# ─── Volatilidade padrão (fallback sem histórico) ────────────────────────────

VOL_PADRAO: dict[str, float] = {
    "acao_br":     0.018,
    "acao_us":     0.015,
    "crypto":      0.045,
    "fii":         0.012,
    "renda_fixa":  0.002,
    "commodities": 0.020,
}

# ─── Resultado ───────────────────────────────────────────────────────────────

@dataclass
class ResultadoSimulacao:
    valor_base:          float
    valor_p10:           float
    valor_p50:           float
    valor_p90:           float
    retorno_p10_pct:     float
    retorno_p50_pct:     float
    retorno_p90_pct:     float
    impacto_choque_real:   float    # <- sem $ no nome do atributo
    impacto_choque_pct:  float
    distribuicao:        np.ndarray
    choque_aplicado:     dict[str, float]

# ─── Funções internas ────────────────────────────────────────────────────────

def _get_vol(ticker: str, classe: str) -> float:
    retornos = get_historical_returns(ticker)
    if retornos is not None and len(retornos) > 20:
        return float(np.std(retornos))
    return VOL_PADRAO.get(classe, 0.018)


def _pct(valor: float, base: float) -> float:
    if base == 0:
        return 0.0
    return ((valor - base) / base) * 100

# ─── Simulação principal ─────────────────────────────────────────────────────

def simular_carteira(
    carteira: Carteira,
    choque: dict[str, float],
    n_simulacoes: int = N_SIMULACOES,
    horizonte_dias: int = HORIZONTE_DIAS,
) -> ResultadoSimulacao:
    if not carteira.ativos:
        raise ValueError("Carteira vazia.")

    valor_base = carteira.valor_total_atual or carteira.valor_total_investido
    totais = np.zeros(n_simulacoes)
    impacto_choque_total = 0.0

    for ativo in carteira.ativos:
        preco_atual = ativo.preco_atual or ativo.preco_medio
        valor_ativo = ativo.quantidade * preco_atual
        vol = _get_vol(ativo.ticker, ativo.classe)
        retorno_choque = aplicar_choque(ativo.classe, choque)
        drift_diario   = retorno_choque / horizonte_dias

        ruidos = np.random.normal(
            loc=drift_diario,
            scale=vol,
            size=(n_simulacoes, horizonte_dias),
        )
        totais += valor_ativo * np.prod(1 + ruidos, axis=1)
        impacto_choque_total += valor_ativo * retorno_choque

    p10 = float(np.percentile(totais, 10))
    p50 = float(np.percentile(totais, 50))
    p90 = float(np.percentile(totais, 90))

    return ResultadoSimulacao(
        valor_base=valor_base,
        valor_p10=p10,
        valor_p50=p50,
        valor_p90=p90,
        retorno_p10_pct=_pct(p10, valor_base),
        retorno_p50_pct=_pct(p50, valor_base),
        retorno_p90_pct=_pct(p90, valor_base),
        impacto_choque_real=impacto_choque_total,
        impacto_choque_pct=_pct(valor_base + impacto_choque_total, valor_base),
        distribuicao=totais,
        choque_aplicado=choque,
    )

# ─── Impacto por ativo ───────────────────────────────────────────────────────

def impacto_por_ativo(
    carteira: Carteira,
    choque: dict[str, float],
) -> pd.DataFrame:
    rows = []
    for a in carteira.ativos:
        preco_atual = a.preco_atual or a.preco_medio
        valor_atual = a.quantidade * preco_atual
        ret = aplicar_choque(a.classe, choque)
        rows.append({
            "Ticker":           a.ticker,
            "Classe":           a.classe,
            "Valor Atual (R$)": valor_atual,
            "Impacto (%)":      ret * 100,
            "Impacto (R$)":     valor_atual * ret,
        })
    return pd.DataFrame(rows)