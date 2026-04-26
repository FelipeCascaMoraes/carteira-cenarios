# agent.py

import os
import json
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from macro_model import VARIAVEIS_MACRO
from simulator import ResultadoSimulacao

load_dotenv()

MODEL = Gemini(id="gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY"))

# ─── Agente 1: extração de variáveis macro ───────────────────────────────────

agente_extracao = Agent(
    model=MODEL,
    description="Economista especialista em macroeconomia brasileira.",
    instructions=[
        "Dado um cenário em linguagem natural, extraia as variações das variáveis macro.",
        "Responda SOMENTE com JSON válido, sem markdown, sem texto extra.",
        "Formato esperado:",
        '{',
        '  "dolar": 0, "juros_br": 0, "juros_us": 0,',
        '  "inflacao": 0, "petroleo": 0, "ibovespa": 0, "sp500": 0,',
        '  "resumo": "frase curta descrevendo o cenário"',
        '}',
        "Valores em % (positivo = alta, negativo = queda). Se não mencionado, use 0.",
        "Magnitudes implícitas razoáveis:",
        "  'crise global'        → sp500: -20, ibovespa: -15, dolar: 15",
        "  'recessão nos EUA'    → sp500: -25, juros_us: -1, dolar: 10",
        "  'Selic cair 2 pontos' → juros_br: -2",
        "  'dólar subir 20%'     → dolar: 20",
    ],
)


def extrair_choque(texto: str) -> tuple[dict[str, float], str]:
    """Extrai variáveis macro do texto via LLM. Retorna (choque, resumo)."""
    resp = agente_extracao.run(texto)

    raw = resp.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)

    choque = {k: float(v) for k, v in data.items() if k in VARIAVEIS_MACRO}
    resumo = data.get("resumo", texto[:80])

    return choque, resumo


# ─── Agente 2: narrativa do resultado ────────────────────────────────────────

agente_narrador = Agent(
    model=MODEL,
    description="Assessor de investimentos experiente e direto.",
    instructions=[
        "Narre o resultado de uma simulação de carteira em linguagem clara e objetiva.",
        "Estruture em 3 parágrafos curtos:",
        "  1. O que o cenário significa (contexto macro, 2-3 frases)",
        "  2. Impacto na carteira (use os números fornecidos, seja específico)",
        "  3. Pontos de atenção ou ativos mais expostos",
        "Tom: profissional mas acessível. Sem disclaimers legais. Máximo 180 palavras.",
    ],
    stream=True,
)


def _montar_contexto(
    texto_original: str,
    resumo: str,
    resultado: ResultadoSimulacao,
    tabela_ativos: str,
) -> str:
    choque_str = ", ".join(
        f"{VARIAVEIS_MACRO[k]}: {'+' if v > 0 else ''}{v:.1f}%"
        for k, v in resultado.choque_aplicado.items()
        if v != 0
    ) or "nenhuma variação significativa"

    return f"""Cenário do usuário: "{texto_original}"
Interpretação: {resumo}
Variáveis extraídas: {choque_str}

Composição da carteira:
{tabela_ativos}

Resultados da simulação (30 dias, 10.000 cenários):
- Valor atual:              R$ {resultado.valor_base:,.2f}
- Impacto direto do choque: R$ {resultado.impacto_choque_real:+,.2f} ({resultado.impacto_choque_pct:+.1f}%)
- Pessimista  (P10):        R$ {resultado.valor_p10:,.2f} ({resultado.retorno_p10_pct:+.1f}%)
- Mediano     (P50):        R$ {resultado.valor_p50:,.2f} ({resultado.retorno_p50_pct:+.1f}%)
- Otimista    (P90):        R$ {resultado.valor_p90:,.2f} ({resultado.retorno_p90_pct:+.1f}%)"""


def narrar_resultado_stream(
    texto_original: str,
    resumo: str,
    resultado: ResultadoSimulacao,
    tabela_ativos: str,
):
    """Generator de chunks — compatível com st.write_stream()."""
    contexto = _montar_contexto(texto_original, resumo, resultado, tabela_ativos)

    for chunk in agente_narrador.run(contexto):
        # Agno stream retorna RunResponseEvent — extrai o texto
        if chunk.content:
            yield chunk.content