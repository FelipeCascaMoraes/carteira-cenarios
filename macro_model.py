# macro_model.py

from dataclasses import dataclass

# ─── Estrutura ───────────────────────────────────────────────────────────────

@dataclass
class Sensibilidades:
    dolar:    float   # impacto de +1% no USDBRL
    juros_br: float   # impacto de +1pp na Selic
    juros_us: float   # impacto de +1pp no Fed Funds
    inflacao: float   # impacto de +1pp no IPCA
    petroleo: float   # impacto de +1% no WTI
    ibovespa: float   # correlação com Ibov
    sp500:    float   # correlação com S&P500

# ─── Tabela de sensibilidades ────────────────────────────────────────────────
#
# Leitura: se dolar=0.30, uma alta de 10% no dólar → +3% no ativo
# Valores negativos = relação inversa

SENSIBILIDADES: dict[str, Sensibilidades] = {

    "acao_br": Sensibilidades(
        dolar=0.30,     # exportadoras ganham, mas é misto no Ibov
        juros_br=-0.60, # juro alto comprime valuation (P/L)
        juros_us=-0.20, # fuga de capital de emergentes
        inflacao=-0.30, # erosão de margens operacionais
        petroleo=0.15,  # Petrobras é ~10% do Ibov
        ibovespa=1.00,
        sp500=0.40,
    ),

    "acao_us": Sensibilidades(
        dolar=0.00,     # preço em USD — neutro em moeda local
        juros_br=0.00,
        juros_us=-0.50, # alta de juros comprime múltiplos (especialmente growth)
        inflacao=-0.20,
        petroleo=0.05,
        ibovespa=0.25,
        sp500=1.00,
    ),

    "crypto": Sensibilidades(
        dolar=0.40,     # em BRL sobe junto com dólar
        juros_br=-0.20,
        juros_us=-0.80, # crypto é o ativo mais sensível a liquidez global
        inflacao=0.20,  # narrativa de reserva de valor
        petroleo=0.10,
        ibovespa=0.15,
        sp500=0.55,     # correlação com risk-on aumentou pós-2020
    ),

    "fii": Sensibilidades(
        dolar=0.05,
        juros_br=-1.20, # FII compete diretamente com renda fixa
        juros_us=-0.20,
        inflacao=0.50,  # contratos atrelados a IPCA/IGP-M protegem
        petroleo=0.00,
        ibovespa=0.45,
        sp500=0.10,
    ),

    "renda_fixa": Sensibilidades(
        dolar=0.00,
        juros_br=0.70,  # pós-fixado ganha; prefixado perde em marcação a mercado
        juros_us=0.00,
        inflacao=0.50,  # IPCA+ protege; prefixado perde
        petroleo=0.00,
        ibovespa=0.00,
        sp500=0.00,
    ),

    "commodities": Sensibilidades(
        dolar=0.70,     # cotadas em USD → sobe direto com dólar
        juros_br=-0.10,
        juros_us=-0.35, # dólar forte pressiona commodities em USD
        inflacao=0.45,  # commodities são causa e efeito de inflação
        petroleo=0.75,  # correlação alta (energia puxa o índice)
        ibovespa=0.20,
        sp500=0.20,
    ),
}

# ─── Nomes amigáveis (usados na UI e no agente) ───────────────────────────────

VARIAVEIS_MACRO = {
    "dolar":    "Dólar (USDBRL)",
    "juros_br": "Juros Brasil (Selic)",
    "juros_us": "Juros EUA (Fed)",
    "inflacao": "Inflação (IPCA)",
    "petroleo": "Petróleo (WTI)",
    "ibovespa": "Ibovespa",
    "sp500":    "S&P 500",
}

# ─── Função principal ────────────────────────────────────────────────────────

def aplicar_choque(classe: str, choque: dict[str, float]) -> float:
    """
    Retorna o retorno esperado (decimal) para uma classe de ativo
    dado um dicionário de choques macro em %.

    Exemplo:
        aplicar_choque("acao_br", {"dolar": 20}) → 0.06  (+6%)
    """
    s = SENSIBILIDADES.get(classe, SENSIBILIDADES["acao_br"])
    retorno = 0.0
    retorno += s.dolar    * choque.get("dolar",    0) / 100
    retorno += s.juros_br * choque.get("juros_br", 0) / 100
    retorno += s.juros_us * choque.get("juros_us", 0) / 100
    retorno += s.inflacao * choque.get("inflacao", 0) / 100
    retorno += s.petroleo * choque.get("petroleo", 0) / 100
    retorno += s.ibovespa * choque.get("ibovespa", 0) / 100
    retorno += s.sp500    * choque.get("sp500",    0) / 100
    return retorno