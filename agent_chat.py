"""
agent_chat.py
─────────────────────────────────────────────────────────────
Chat interativo com contexto completo da carteira.
Usa Groq (igual ao agent.py) — modelo llama-3.3-70b-versatile.
"""

from __future__ import annotations
import os
from groq import Groq
from dotenv import load_dotenv
from simulator import ResultadoSimulacao
from macro_model import VARIAVEIS_MACRO

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# ─── Prompts ──────────────────────────────────────────────────────────────────

SYSTEM_CHAT = """Você é um assessor de investimentos brasileiro especializado, direto e perspicaz.
Você tem acesso completo à carteira do usuário, histórico de simulações Monte Carlo e dados de mercado.

PERSONALIDADE:
- Fala em português brasileiro, tom profissional mas acessível
- É direto: vai ao ponto, sem rodeios
- Usa números reais da carteira nas respostas
- Quando identifica riscos, aponta claramente
- Dá sugestões práticas de rebalanceamento quando relevante
- Lembra o histórico da conversa e referencia simulações anteriores

FORMATO DAS RESPOSTAS:
- Respostas concisas (3-5 parágrafos no máximo)
- Use **negrito** para números e pontos críticos
- Quando sugerir rebalanceamento, seja específico: "reduzir X de Y% para Z%"
- Termine com uma pergunta ou próximo passo quando fizer sentido

Você NÃO inventa dados. Se não tiver a informação, diz claramente."""

SYSTEM_REBALANCEAMENTO = """Você é um assessor de investimentos brasileiro especializado em gestão de risco e alocação de ativos.
Seja direto, específico e use os dados reais fornecidos.
Máximo 250 palavras. Use **negrito** para tickers e percentuais importantes."""

SYSTEM_NARRAR = """Você é um assessor de investimentos experiente, comunicativo e objetivo.
Narre o resultado de simulação de carteira de forma clara, linguagem acessível, tom profissional mas humano.

Estruture em 3 parágrafos curtos:
1. O que o cenário significa (contexto macro)
2. Impacto na carteira (números principais)
3. Observações e sugestões de atenção

Se houver simulações anteriores para comparar, mencione brevemente.
Seja direto, use os números fornecidos. Máximo 220 palavras."""


# ─── Helpers de contexto ─────────────────────────────────────────────────────

def _formatar_carteira(carteira) -> str:
    if not carteira or not carteira.ativos:
        return "Carteira vazia — nenhum ativo cadastrado."

    total = carteira.valor_total_atual or 1
    linhas = [
        f"CARTEIRA ATUAL (valor total: R$ {carteira.valor_total_atual:,.2f})",
        f"Investido: R$ {carteira.valor_total_investido:,.2f} | "
        f"P&L: R$ {carteira.pl_total_reais:+,.2f} ({carteira.pl_total_pct:+.1f}%)",
        "",
        f"{'Ticker':<12} {'Classe':<16} {'Valor Atual':>14} {'% Cart':>8} {'P&L %':>8}",
        "─" * 62,
    ]
    for a in sorted(carteira.ativos, key=lambda x: -x.valor_atual):
        pct = (a.valor_atual / total) * 100
        linhas.append(
            f"{a.ticker:<12} {a.classe:<16} "
            f"R$ {a.valor_atual:>10,.2f} {pct:>7.1f}% {a.pl_pct:>+7.1f}%"
        )
    aloc = carteira.alocacao_por_classe()
    linhas += ["", "ALOCAÇÃO POR CLASSE:"]
    for classe, pct in sorted(aloc.items(), key=lambda x: -x[1]):
        linhas.append(f"  {classe}: {pct:.1f}%")
    return "\n".join(linhas)


def _formatar_simulacoes(historico: list[dict]) -> str:
    if not historico:
        return "Nenhuma simulação realizada nesta sessão."
    linhas = [f"HISTÓRICO DE SIMULAÇÕES ({len(historico)} cenário(s)):"]
    for i, s in enumerate(historico, 1):
        linhas += [
            f"\n[{i}] Cenário: \"{s['cenario']}\"",
            f"    Interpretação: {s.get('resumo', '—')}",
            f"    P10: {s['p10']:+.1f}% | P50: {s['p50']:+.1f}% | P90: {s['p90']:+.1f}%",
            f"    Impacto direto do choque: {s['impacto']:+.1f}%",
        ]
    return "\n".join(linhas)


def _formatar_benchmarks(benchmarks: dict | None) -> str:
    if not benchmarks:
        return ""
    linhas = ["BENCHMARKS (12 meses acumulado):"]
    for nome, retorno in benchmarks.items():
        linhas.append(f"  {nome}: {retorno:+.1f}%")
    return "\n".join(linhas)


def _construir_contexto(carteira, historico_simulacoes, benchmarks=None) -> str:
    partes = [
        "=" * 60,
        "CONTEXTO DA SESSÃO",
        "=" * 60,
        _formatar_carteira(carteira),
        "",
        _formatar_simulacoes(historico_simulacoes),
    ]
    bench_str = _formatar_benchmarks(benchmarks)
    if bench_str:
        partes += ["", bench_str]
    partes.append("=" * 60)
    return "\n".join(partes)


# ─── Chat com streaming ───────────────────────────────────────────────────────

def chat_stream(
    mensagem: str,
    historico_chat: list[dict],
    carteira,
    historico_simulacoes: list[dict],
    benchmarks: dict | None = None,
):
    """Chat interativo com memória. Compatível com st.write_stream."""
    contexto = _construir_contexto(carteira, historico_simulacoes, benchmarks)
    system_completo = f"{SYSTEM_CHAT}\n\n{contexto}"

    mensagens = [{"role": "system", "content": system_completo}]
    mensagens += historico_chat
    mensagens.append({"role": "user", "content": mensagem})

    with client.chat.completions.create(
        model=MODEL,
        max_tokens=800,
        messages=mensagens,
        stream=True,
    ) as stream:
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text


# ─── Rebalanceamento proativo ─────────────────────────────────────────────────

def sugerir_rebalanceamento_stream(
    carteira,
    historico_simulacoes: list[dict],
    benchmarks: dict | None = None,
):
    """Análise proativa de rebalanceamento. Compatível com st.write_stream."""
    contexto = _construir_contexto(carteira, historico_simulacoes, benchmarks)

    prompt = (
        f"{contexto}\n\n"
        "Com base na carteira e nos cenários simulados acima, faça uma análise de rebalanceamento:\n"
        "1. Identifique os 2-3 maiores riscos de concentração (cite os tickers)\n"
        "2. Aponte quais ativos são mais vulneráveis aos choques já simulados\n"
        "3. Sugira alocações específicas (% alvo por classe ou ticker)\n"
        "4. Priorize a ação mais urgente\n\n"
        "Use os dados reais da carteira. Seja específico com tickers e percentuais."
    )

    with client.chat.completions.create(
        model=MODEL,
        max_tokens=600,
        messages=[
            {"role": "system", "content": SYSTEM_REBALANCEAMENTO},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    ) as stream:
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text


# ─── Narrativa pós-simulação ──────────────────────────────────────────────────

def narrar_resultado_stream(
    cenario_texto: str,
    resumo_cenario: str,
    resultado: ResultadoSimulacao,
    ativos_resumo: str,
    historico_simulacoes: list[dict] | None = None,
):
    """
    Narrativa rica após simulação, com comparação ao histórico se disponível.
    Compatível com st.write_stream e com a assinatura original do agent.py.
    """
    choque_str = ", ".join(
        f"{VARIAVEIS_MACRO.get(k, k)}: {'+' if v > 0 else ''}{v:.1f}%"
        for k, v in resultado.choque_aplicado.items()
        if v != 0
    ) or "nenhuma variação significativa"

    hist_str = ""
    if historico_simulacoes and len(historico_simulacoes) > 1:
        anteriores = historico_simulacoes[:-1][-3:]
        hist_str = "\n\nCENÁRIOS ANTERIORES PARA COMPARAÇÃO:\n"
        for s in anteriores:
            hist_str += (
                f"- \"{s['cenario']}\": "
                f"P50={s['p50']:+.1f}%, impacto={s['impacto']:+.1f}%\n"
            )

    prompt = f"""Cenário descrito pelo usuário: "{cenario_texto}"
Interpretação: {resumo_cenario}
Variáveis extraídas: {choque_str}

Carteira atual:
{ativos_resumo}

Resultados da simulação (horizonte 30 dias, 1000 cenários):
- Valor atual da carteira: R$ {resultado.valor_base:,.2f}
- Impacto direto do choque: R$ {resultado.impacto_choque_real:+,.2f} ({resultado.impacto_choque_pct:+.1f}%)
- Cenário pessimista (P10): R$ {resultado.valor_p10:,.2f} ({resultado.retorno_p10_pct:+.1f}%)
- Cenário mediano (P50): R$ {resultado.valor_p50:,.2f} ({resultado.retorno_p50_pct:+.1f}%)
- Cenário otimista (P90): R$ {resultado.valor_p90:,.2f} ({resultado.retorno_p90_pct:+.1f}%)
{hist_str}
Narre este resultado para o investidor."""

    with client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM_NARRAR},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    ) as stream:
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text