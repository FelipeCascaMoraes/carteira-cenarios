"""
auth.py
────────────────────────────────────────────────────────────
Autenticação via Supabase Auth — email + senha.
"""

from __future__ import annotations
import streamlit as st
from database import get_supabase


# ─── Estado de sessão ────────────────────────────────────────────────────────

def get_user():
    """Retorna o usuário logado ou None."""
    return st.session_state.get("user", None)


def is_logged_in() -> bool:
    return get_user() is not None


def get_user_id() -> str | None:
    user = get_user()
    return user.user.id if user else None


# ─── Login ───────────────────────────────────────────────────────────────────

def fazer_login(email: str, senha: str) -> tuple[bool, str]:
    try:
        sb = get_supabase()
        res = sb.auth.sign_in_with_password({"email": email, "password": senha})
        st.session_state.user = res
        return True, "Login realizado com sucesso!"
    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "Email ou senha incorretos."
        if "Email not confirmed" in msg:
            return False, "Confirme seu email antes de entrar. Verifique sua caixa de entrada."
        return False, f"Erro ao fazer login: {msg}"

# ─── Cadastro ────────────────────────────────────────────────────────────────

def fazer_cadastro(email: str, senha: str) -> tuple[bool, str]:
    """Cria uma nova conta. Retorna (sucesso, mensagem)."""
    try:
        sb = get_supabase()
        res = sb.auth.sign_up({"email": email, "password": senha})
        if res.user:
            # Loga automaticamente após cadastro
            st.session_state.user = res
            return True, "Conta criada com sucesso!"
        return False, "Não foi possível criar a conta."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg:
            return False, "Este email já está cadastrado."
        return False, f"Erro ao criar conta: {msg}"


# ─── Logout ──────────────────────────────────────────────────────────────────

def fazer_logout():
    """Desloga e limpa o estado da sessão."""
    try:
        sb = get_supabase()
        sb.auth.sign_out()
    except Exception:
        pass
    for key in ["user", "carteira", "historico_chat", "historico_simulacoes", "benchmarks_cache"]:
        st.session_state.pop(key, None)


# ─── Tela de login ───────────────────────────────────────────────────────────

def mostrar_tela_login():
    """Renderiza a tela de login/cadastro. Chame no início do app.py."""

    BG      = "#0f172a"
    SURFACE = "#1e293b"
    BORDER  = "#334155"
    MUTED   = "#64748b"
    TEXT    = "#e2e8f0"

    st.markdown(f"""
    <style>
    .stApp {{ background: {BG}; }}
    .login-container {{
        max-width: 420px;
        margin: 6rem auto 0;
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 2.5rem 2rem;
    }}
    .login-title {{
        color: {TEXT};
        font-size: 1.6rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }}
    .login-sub {{
        color: {MUTED};
        font-size: 0.85rem;
        margin-bottom: 2rem;
    }}
    </style>
    <div class="login-container">
        <div class="login-title">📊 Carteira</div>
        <div class="login-sub">Monte Carlo · IA · Macro</div>
    </div>
    """, unsafe_allow_html=True)

    # Centraliza o formulário
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        aba = st.radio("", ["Entrar", "Criar conta"], horizontal=True, label_visibility="collapsed")
        st.markdown("")

        email = st.text_input("Email", placeholder="seu@email.com", key="login_email")
        senha = st.text_input("Senha", type="password", placeholder="••••••••", key="login_senha")

        if aba == "Entrar":
            if st.button("Entrar", type="primary", use_container_width=True):
                if not email or not senha:
                    st.error("Preencha email e senha.")
                else:
                    with st.spinner("Entrando..."):
                        ok, msg = fazer_login(email, senha)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        else:
            senha2 = st.text_input("Confirmar senha", type="password",
                                   placeholder="••••••••", key="login_senha2")
            if st.button("Criar conta", type="primary", use_container_width=True):
                if not email or not senha:
                    st.error("Preencha todos os campos.")
                elif senha != senha2:
                    st.error("As senhas não coincidem.")
                elif len(senha) < 6:
                    st.error("A senha precisa ter pelo menos 6 caracteres.")
                else:
                    with st.spinner("Criando conta..."):
                        ok, msg = fazer_cadastro(email, senha)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)