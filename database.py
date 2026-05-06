"""
database.py
────────────────────────────────────────────────────────────
Camada de persistência via Supabase (PostgreSQL).
Dados filtrados por user_id — cada usuário vê só sua carteira.
"""

from __future__ import annotations
import streamlit as st
from supabase import create_client, Client
from portfolio import Carteira, Ativo


# ─── Conexão ─────────────────────────────────────────────────────────────────

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def _uid() -> str | None:
    """Retorna o user_id do usuário logado."""
    user = st.session_state.get("user", None)
    if user is None:
        return None
    try:
        return user.user.id
    except Exception:
        return None


# ─── CRUD ────────────────────────────────────────────────────────────────────

def carregar_carteira() -> Carteira:
    """Carrega ativos do usuário logado."""
    uid = _uid()
    if not uid:
        return Carteira()
    try:
        sb = get_supabase()
        res = sb.table("ativos").select("*").eq("user_id", uid).execute()
        carteira = Carteira()
        for row in res.data:
            carteira.ativos.append(Ativo(
                ticker      = row["ticker"],
                nome        = row["nome"],
                classe      = row["classe"],
                quantidade  = float(row["quantidade"]),
                preco_medio = float(row["preco_medio"]),
                preco_atual = float(row["preco_atual"]) if row["preco_atual"] else None,
            ))
        return carteira
    except Exception as e:
        st.warning(f"Erro ao carregar carteira: {e}")
        return Carteira()


def salvar_ativo(ativo: Ativo) -> bool:
    """Insere ou atualiza um ativo do usuário logado."""
    uid = _uid()
    if not uid:
        return False
    try:
        sb = get_supabase()
        sb.table("ativos").upsert({
            "ticker":      ativo.ticker,
            "nome":        ativo.nome,
            "classe":      ativo.classe,
            "quantidade":  ativo.quantidade,
            "preco_medio": ativo.preco_medio,
            "preco_atual": ativo.preco_atual,
            "user_id":     uid,
        }, on_conflict="ticker,user_id").execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {ativo.ticker}: {e}")
        return False


def remover_ativo(ticker: str) -> bool:
    """Remove um ativo do usuário logado."""
    uid = _uid()
    if not uid:
        return False
    try:
        sb = get_supabase()
        sb.table("ativos").delete().eq("ticker", ticker).eq("user_id", uid).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao remover {ticker}: {e}")
        return False


def salvar_carteira(carteira: Carteira) -> bool:
    """Salva todos os ativos do usuário logado."""
    uid = _uid()
    if not uid:
        return False
    try:
        sb = get_supabase()
        rows = [{
            "ticker":      a.ticker,
            "nome":        a.nome,
            "classe":      a.classe,
            "quantidade":  a.quantidade,
            "preco_medio": a.preco_medio,
            "preco_atual": a.preco_atual,
            "user_id":     uid,
        } for a in carteira.ativos]
        if rows:
            sb.table("ativos").upsert(rows, on_conflict="ticker,user_id").execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar carteira: {e}")
        return False


def limpar_carteira() -> bool:
    """Remove todos os ativos do usuário logado."""
    uid = _uid()
    if not uid:
        return False
    try:
        sb = get_supabase()
        sb.table("ativos").delete().eq("user_id", uid).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao limpar carteira: {e}")
        return False