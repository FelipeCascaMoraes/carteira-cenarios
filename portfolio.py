# portfolio.py

import json
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Optional

# ─── Classes de ativo ────────────────────────────────────────────────────────

CLASSES = {
    "acao_br":     "Ação BR (B3)",
    "acao_us":     "Ação US (NYSE/NASDAQ)",
    "crypto":      "Criptomoeda",
    "fii":         "Fundo Imobiliário",
    "renda_fixa":  "Renda Fixa",
    "commodities": "Commodities",
}

# ─── Ativo ───────────────────────────────────────────────────────────────────

@dataclass
class Ativo:
    ticker:       str
    nome:         str
    classe:       str
    quantidade:   float
    preco_medio:  float
    preco_atual:  Optional[float] = None

    @property
    def valor_investido(self) -> float:
        return self.quantidade * self.preco_medio

    @property
    def valor_atual(self) -> float:
        p = self.preco_atual if self.preco_atual is not None else self.preco_medio
        return self.quantidade * p

    @property
    def pl_reais(self) -> float:
        return self.valor_atual - self.valor_investido

    @property
    def pl_pct(self) -> float:
        if self.valor_investido == 0:
            return 0.0
        return (self.pl_reais / self.valor_investido) * 100

# ─── Carteira ────────────────────────────────────────────────────────────────

class Carteira:
    def __init__(self):
        self.ativos: list[Ativo] = []

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def adicionar(self, ativo: Ativo):
        self.ativos = [a for a in self.ativos if a.ticker != ativo.ticker]
        self.ativos.append(ativo)

    def remover(self, ticker: str):
        self.ativos = [a for a in self.ativos if a.ticker != ticker]

    def atualizar_preco(self, ticker: str, preco: float):
        for a in self.ativos:
            if a.ticker == ticker:
                a.preco_atual = preco

    # ── Totais ───────────────────────────────────────────────────────────────

    @property
    def valor_total_investido(self) -> float:
        return sum(a.valor_investido for a in self.ativos)

    @property
    def valor_total_atual(self) -> float:
        return sum(a.valor_atual for a in self.ativos)

    @property
    def pl_total_reais(self) -> float:
        return self.valor_total_atual - self.valor_total_investido

    @property
    def pl_total_pct(self) -> float:
        if self.valor_total_investido == 0:
            return 0.0
        return (self.pl_total_reais / self.valor_total_investido) * 100

    # ── Análise ──────────────────────────────────────────────────────────────

    def alocacao_por_classe(self) -> dict[str, float]:
        total = self.valor_total_atual or 1
        result: dict[str, float] = {}
        for a in self.ativos:
            result[a.classe] = result.get(a.classe, 0) + (a.valor_atual / total) * 100
        return result

    def para_dataframe(self) -> pd.DataFrame:
        if not self.ativos:
            return pd.DataFrame()
        total = self.valor_total_atual or 1
        rows = []
        for a in self.ativos:
            rows.append({
                "Ticker":        a.ticker,
                "Nome":          a.nome,
                "Classe":        CLASSES.get(a.classe, a.classe),
                "Qtd":           a.quantidade,
                "Preço Médio":   a.preco_medio,
                "Preço Atual":   a.preco_atual,
                "Investido (R$)": a.valor_investido,
                "Atual (R$)":    a.valor_atual,
                "P&L (R$)":      a.pl_reais,
                "P&L (%)":       a.pl_pct,
                "% Carteira":    (a.valor_atual / total) * 100,
            })
        return pd.DataFrame(rows)

    # ── Persistência ─────────────────────────────────────────────────────────

    def salvar_json(self, caminho: str = "carteira.json"):
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in self.ativos], f, indent=2, ensure_ascii=False)

    @classmethod
    def carregar_json(cls, caminho: str = "carteira.json") -> "Carteira":
        c = cls()
        try:
            with open(caminho, encoding="utf-8") as f:
                for d in json.load(f):
                    c.ativos.append(Ativo(**d))
        except FileNotFoundError:
            pass
        return c