from dataclasses import dataclass

@dataclass
class Sensibilidades:
    dolar: float; juros_br: float; juros_us: float
    inflacao: float; petroleo: float; ibovespa: float; sp500: float

SENSIBILIDADES: dict[str, Sensibilidades] = {
    "acao_br":     Sensibilidades(dolar=0.30,  juros_br=-0.60, juros_us=-0.20, inflacao=-0.30, petroleo=0.15,  ibovespa=1.00, sp500=0.40),
    "acao_us":     Sensibilidades(dolar=0.00,  juros_br=0.00,  juros_us=-0.50, inflacao=-0.20, petroleo=0.05,  ibovespa=0.25, sp500=1.00),
    "crypto":      Sensibilidades(dolar=0.40,  juros_br=-0.20, juros_us=-0.80, inflacao=0.20,  petroleo=0.10,  ibovespa=0.15, sp500=0.55),
    "fii":         Sensibilidades(dolar=0.05,  juros_br=-1.20, juros_us=-0.20, inflacao=0.50,  petroleo=0.00,  ibovespa=0.45, sp500=0.10),
    "renda_fixa":  Sensibilidades(dolar=0.00,  juros_br=0.70,  juros_us=0.00,  inflacao=0.50,  petroleo=0.00,  ibovespa=0.00, sp500=0.00),
    # Tesouro: diferenciado por subtipo via nome do ticker
    "tesouro":     Sensibilidades(dolar=0.00,  juros_br=-0.80, juros_us=-0.10, inflacao=0.60,  petroleo=0.00,  ibovespa=0.05, sp500=0.00),
    "commodities": Sensibilidades(dolar=0.70,  juros_br=-0.10, juros_us=-0.35, inflacao=0.45,  petroleo=0.75,  ibovespa=0.20, sp500=0.20),
}

# Sensibilidades específicas por tipo de Tesouro
TESOURO_SENSIBILIDADES: dict[str, Sensibilidades] = {
    # Selic: sobe com juros altos
    "SELIC":      Sensibilidades(dolar=0.00, juros_br=0.90,  juros_us=0.00, inflacao=0.30,  petroleo=0.00, ibovespa=0.00, sp500=0.00),
    # IPCA+: protege inflação mas sofre com juros subindo (marcação a mercado)
    "IPCA":       Sensibilidades(dolar=0.00, juros_br=-0.70, juros_us=-0.10, inflacao=0.80, petroleo=0.00, ibovespa=0.05, sp500=0.00),
    # Prefixado: o mais sensível a juros
    "PREFIXADO":  Sensibilidades(dolar=0.00, juros_br=-1.20, juros_us=-0.15, inflacao=-0.30, petroleo=0.00, ibovespa=0.05, sp500=0.00),
}

VARIAVEIS_MACRO = {
    "dolar":    "Dólar (USDBRL)",
    "juros_br": "Juros Brasil (Selic)",
    "juros_us": "Juros EUA (Fed)",
    "inflacao": "Inflação (IPCA)",
    "petroleo": "Petróleo (WTI)",
    "ibovespa": "Ibovespa",
    "sp500":    "S&P 500",
}

def aplicar_choque(classe: str, choque: dict[str, float], ticker: str = "") -> float:
    # Para tesouro, usa sensibilidade específica pelo prefixo do ticker
    if classe == "tesouro" and ticker:
        t = ticker.upper()
        for prefixo, sens in TESOURO_SENSIBILIDADES.items():
            if t.startswith(prefixo):
                s = sens
                break
        else:
            s = SENSIBILIDADES["tesouro"]
    else:
        s = SENSIBILIDADES.get(classe, SENSIBILIDADES["acao_br"])

    return (
        s.dolar    * choque.get("dolar",    0) / 100 +
        s.juros_br * choque.get("juros_br", 0) / 100 +
        s.juros_us * choque.get("juros_us", 0) / 100 +
        s.inflacao * choque.get("inflacao", 0) / 100 +
        s.petroleo * choque.get("petroleo", 0) / 100 +
        s.ibovespa * choque.get("ibovespa", 0) / 100 +
        s.sp500    * choque.get("sp500",    0) / 100
    )
