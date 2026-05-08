"""
auth.py
────────────────────────────────────────────────────────────
Autenticação via Supabase Auth — email + senha.
"""

from __future__ import annotations
import streamlit as st
from database import get_supabase


def get_user():
    return st.session_state.get("user", None)

def is_logged_in() -> bool:
    return get_user() is not None

def get_user_id() -> str | None:
    user = get_user()
    return user.user.id if user else None

def fazer_login(email: str, senha: str) -> tuple[bool, str]:
    try:
        sb = get_supabase()
        res = sb.auth.sign_in_with_password({"email": email, "password": senha})
        st.session_state.user = res
        return True, "ok"
    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "Email ou senha incorretos."
        return False, f"Erro: {msg}"

def fazer_cadastro(email: str, senha: str) -> tuple[bool, str]:
    try:
        sb = get_supabase()
        res = sb.auth.sign_up({"email": email, "password": senha})
        if res.user:
            st.session_state.user = res
            return True, "ok"
        return False, "Não foi possível criar a conta."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg:
            return False, "Este email já está cadastrado."
        return False, f"Erro: {msg}"

def fazer_logout():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    for key in ["user", "carteira", "historico_chat", "historico_simulacoes", "benchmarks_cache"]:
        st.session_state.pop(key, None)

def mostrar_tela_login():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif !important; }
.stApp { background: #0f172a !important; }
section[data-testid="stSidebar"] { display: none; }
header { display: none !important; }
[data-testid="stRadio"] label { color: #94a3b8 !important; font-size: 0.85rem; }
[data-testid="stRadio"] label:has(input:checked) { color: #e2e8f0 !important; }
[data-testid="stTextInput"] input {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
    font-family: 'DM Mono', monospace !important;
    padding: 0.65rem 1rem !important;
    font-size: 0.9rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #475569 !important;
    box-shadow: none !important;
}

                /* Esconde o "Press Enter to Apply" */
[data-testid="InputInstructions"] { display: none !important; }

/* Card maior */

[data-testid="stWidgetLabel"] p { color: #64748b !important; font-size: 0.75rem !important; letter-spacing: 0.06em; text-transform: uppercase; }
.stButton > button {
    background: #3b82f6 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 0.65rem !important;
    letter-spacing: 0.03em;
    transition: background 0.2s, transform 0.1s;
    font-family: 'Syne', sans-serif !important;
}
.stButton > button:hover { background: #2563eb !important; transform: translateY(-1px); }
[data-testid="stAlert"] { border-radius: 10px !important; }
p, span, label { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

    # Logo + título centralizado
    st.markdown("""
<div style="
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 0 2rem;
    gap: 0.5rem;
">
    <svg width="56" height="56" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="56" height="56" rx="16" fill="#1e293b"/>
        <rect x="1" y="1" width="54" height="54" rx="15" stroke="#334155" stroke-width="1"/>
        <polyline points="10,38 20,26 28,32 36,18 46,24"
                  fill="none" stroke="#3b82f6" stroke-width="2.5"
                  stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="46" cy="24" r="3" fill="#4ade80"/>
        <circle cx="10" cy="38" r="2.5" fill="#3b82f6" opacity="0.5"/>
    </svg>
    <div style="font-family:'Syne',sans-serif; font-size:1.6rem; font-weight:800; color:#e2e8f0; letter-spacing:-0.02em; margin-top:0.5rem;">
        Carteira
    </div>
    <div style="font-family:'DM Mono',monospace; font-size:0.72rem; color:#475569; letter-spacing:0.12em; text-transform:uppercase;">
        Monte Carlo · IA · Macro
    </div>
</div>
""", unsafe_allow_html=True)

    # Card de login
    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("""
<div style="
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 2rem 1.75rem 1.75rem;
    margin-bottom: 1rem;
">
""", unsafe_allow_html=True)

        aba = st.radio("", ["Entrar", "Criar conta"], horizontal=True,
                       label_visibility="collapsed", key="login_aba")
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        email = st.text_input("Email", placeholder="seu@email.com", key="login_email")
        senha = st.text_input("Senha", type="password", placeholder="••••••••", key="login_senha")

        if aba == "Entrar":
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Entrar →", use_container_width=True):
                if not email or not senha:
                    st.error("Preencha email e senha.")
                else:
                    with st.spinner(""):
                        ok, msg = fazer_login(email, senha)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            senha2 = st.text_input("Confirmar senha", type="password",
                                   placeholder="••••••••", key="login_senha2")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Criar conta →", use_container_width=True):
                if not email or not senha:
                    st.error("Preencha todos os campos.")
                elif senha != senha2:
                    st.error("As senhas não coincidem.")
                elif len(senha) < 6:
                    st.error("Senha precisa ter pelo menos 6 caracteres.")
                else:
                    with st.spinner(""):
                        ok, msg = fazer_cadastro(email, senha)
                    if ok:
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div style="text-align:center; font-family:'DM Mono',monospace; font-size:0.7rem; color:#334155; margin-top:0.5rem;">
    Seus dados são privados e criptografados
</div>
""", unsafe_allow_html=True)