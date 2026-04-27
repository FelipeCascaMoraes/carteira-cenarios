# stress_test.py

from dataclasses import dataclass
import pandas as pd
import numpy as np
from simulator import simular_carteira, ResultadoSimulacao
from portfolio import Carteira

@dataclass
class CenarioHistorico:
    nome:      str
    periodo:   str
    descricao: str
    choque:    dict[str, float]

CENARIOS_HISTORICOS: list[CenarioHistorico] = [
    CenarioHistorico(
        nome="Crise Global 2008",
        periodo="Set–Out 2008",
        descricao="Quebra do Lehman Brothers, colapso do crédito global",
        choque=dict(ibovespa=-50, sp500=-40, dolar=40, petroleo=-55, juros_us=-1),
    ),
    CenarioHistorico(
        nome="Crise Dilma 2015",
        periodo="2015",
        descricao="Recessão, fiscal deteriorado, rebaixamento para grau especulativo",
        choque=dict(ibovespa=-13, dolar=50, juros_br=3, inflacao=3, petroleo=-35),
    ),
    CenarioHistorico(
        nome="Impeachment 2016",
        periodo="Maio 2016",
        descricao="Efeito positivo: esperança de ajuste fiscal e reformas",
        choque=dict(ibovespa=15, dolar=-8, juros_br=-0.5),
    ),
    CenarioHistorico(
        nome="Covid-19 2020",
        periodo="Mar 2020",
        descricao="Pandemia global, lockdowns, colapso do petróleo",
        choque=dict(ibovespa=-40, sp500=-35, dolar=30, petroleo=-65, juros_us=-1.5),
    ),
    CenarioHistorico(
        nome="Eleições 2022",
        periodo="Out–Nov 2022",
        descricao="Resultado eleitoral acirrado, incerteza fiscal inicial",
        choque=dict(ibovespa=-5, dolar=8, juros_br=0.5),
    ),
    CenarioHistorico(
        nome="Crise Fiscal 2024",
        periodo="Nov–Dez 2024",
        descricao="Anúncio de corte de gastos frustrou mercado, dólar disparou",
        choque=dict(dolar=10, juros_br=2, ibovespa=-5, inflacao=1),
    ),
]


def rodar_todos(carteira: Carteira) -> pd.DataFrame:
    """Roda todos os cenários históricos e retorna tabela comparativa."""
    rows = []
    resultados = []

    for c in CENARIOS_HISTORICOS:
        res = simular_carteira(carteira, c.choque)
        resultados.append(res)
        rows.append({
            "Cenário":        c.nome,
            "Período":        c.periodo,
            "Choque direto":  res.impacto_choque_pct,
            "P10 (%)":        res.retorno_p10_pct,
            "P50 (%)":        res.retorno_p50_pct,
            "P90 (%)":        res.retorno_p90_pct,
            "P10 (R$)":       res.valor_p10,
            "P50 (R$)":       res.valor_p50,
            "P90 (R$)":       res.valor_p90,
            "Impacto (R$)":   res.impacto_choque_real,
        })

    return pd.DataFrame(rows), resultados