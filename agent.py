import os
import json
import anthropic
from dotenv import load_dotenv
from macro_model import VARIAVEIS_MACRO
from simulator import ResultadoSimulacao

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-5"


SYSTEM_EXTRAIR = """Você é um analista financeiro especialista em macroeconomia brasileira e global.
Sua tarefa é extrair variáveis macro de um cenário descrito em linguagem natural.

Responda APENAS com um JSON válido, sem nenhum texto adicional, nenhum markdown, sem ```json.
O JSON deve ter exatamente estas chaves (valores em %):
{
  "dolar": 0,
  "juros_br": 0,
  "juros_us": 0,
  "inflacao": 0,
  "petroleo": 0,
  "ibovespa": 0,
  "sp500": 0,
  "resumo_cenario": "frase curta descrevendo o cenário"
}

Regras:
- Valores positivos = alta, negativos = queda
- Se a variável não for mencionada, use 0
- "dólar subir 20%" → dolar: 20
- "Selic cair 2 pontos" → juros_br: -2
- "crise global" → sp500: -15, ibovespa: -10, dolar: 10
- "recessão americana" → sp500: -20, juros_us: -1
- Seja razoável com magnitudes implícitas
"""


SYSTEM_NARRAR = """Você é um assessor de investimentos experiente, comunicativo e objetivo.
Sua missão é narrar o resultado de uma simulação de carteira de investimentos de forma clara,
usando linguagem acessível (sem jargão excessivo), com tom profissional mas humano.

Estruture sua resposta em 3 parágrafos curtos:
1. O que o cenário significa (contexto macro)
2. Impacto na carteira (números principais)
3. Observações e sugestões de atenção

Seja direto, use os números fornecidos, evite disclaimers legais genéricos.
Máximo 200 palavras."""


def extrair_choque(texto_cenario: str) -> dict[str, float]:
    """Usa o LLM para extrair variáveis macro do texto em linguagem natural."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_EXTRAIR,
        messages=[{"role": "user", "content": texto_cenario}],
    )
    raw = resp.content[0].text.strip()
    
    # Limpa markdown se vier mesmo assim
    raw = raw.replace("```json", "").replace("```", "").strip()
    
    data = json.loads(raw)
    
    # Remove a chave de texto, mantém só os números
    choque = {k: float(v) for k, v in data.items() if k in VARIAVEIS_MACRO}
    resumo = data.get("resumo_cenario", texto_cenario[:80])
    
    return choque, resumo


def narrar_resultado(
    cenario_texto: str,
    resumo_cenario: str,
    resultado: ResultadoSimulacao,
    ativos_resumo: str,
) -> str:
    """Usa o LLM para narrar o resultado da simulação."""
    
    choque_str = ", ".join(
        f"{VARIAVEIS_MACRO.get(k, k)}: {'+' if v > 0 else ''}{v:.1f}%"
        for k, v in resultado.choque_aplicado.items()
        if v != 0
    ) or "nenhuma variação significativa"

    prompt = f"""Cenário descrito pelo usuário: "{cenario_texto}"
Interpretação: {resumo_cenario}
Variáveis extraídas: {choque_str}

Carteira atual:
{ativos_resumo}

Resultados da simulação (horizonte 30 dias, 1000 cenários):
- Valor atual da carteira: R$ {resultado.valor_base:,.2f}
- Impacto direto do choque: R$ {resultado.impacto_choque_reais:+,.2f} ({resultado.impacto_choque_pct:+.1f}%)
- Cenário pessimista (P10): R$ {resultado.valor_p10:,.2f} ({resultado.retorno_p10_pct:+.1f}%)
- Cenário mediano (P50): R$ {resultado.valor_p50:,.2f} ({resultado.retorno_p50_pct:+.1f}%)
- Cenário otimista (P90): R$ {resultado.valor_p90:,.2f} ({resultado.retorno_p90_pct:+.1f}%)

Narre este resultado para o investidor."""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM_NARRAR,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()
