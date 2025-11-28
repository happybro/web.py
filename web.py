# ================ web.py ================
# VERSÃO WEB DO SEU GERENCIADOR - ACESSO PELO CELULAR/INTERNET
# RODA EM PARALELO COM O PROGRAMA PRINCIPAL (gerenciador.py)
# Usa exatamente o mesmo banco de dados!

import streamlit as st
import sqlite3
import os
from datetime import datetime

# === CONFIGURAÇÕES IGUAIS AO SEU PROGRAMA ===
CAMINHO_SERVIDOR = r"\\servidor\dados\Nova Pasta"  # ← MUDE SE FOR DIFERENTE NO SEU CASO
CAMINHO_BANCO = os.path.join(CAMINHO_SERVIDOR, "ordens_servico.db")

CONFIG = {
    "SITUACOES": ["AG DIAGNOSTICO", "EX DIAGNOSTICO", "AG APROVAÇÃO", "AG EXECUÇÃO",
                  "EXECUTANDO SERVIÇOS", "AGUARDANDO PÇ CLIENTE", "AGUARDANDO PÇ INT", "FINALIZADO"],
    "CORES": {"VERDE": "#28a745", "LARANJA": "#fd7e14", "VERMELHO": "#dc3545", "PADRAO": "#444444"}
}

# === FUNÇÕES DO BANCO ===
def conectar():
    if not os.path.exists(CAMINHO_BANCO):
        st.error(f"Banco não encontrado!\nCaminho: {CAMINHO_BANCO}")
        st.stop()
    conn = sqlite3.connect(CAMINHO_BANCO, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def calcular_cor(previsao):
    if not previsao:
        return CONFIG["CORES"]["PADRAO"]
    try:
        dt = datetime.strptime(previsao, "%d/%m/%Y %H:%M")
        minutos = (dt - datetime.now()).total_seconds() / 60
        if minutos > 60: return CONFIG["CORES_ROSA"]["VERDE"]
        if minutos > 30: return CONFIG["CORES"]["LARANJA"]
        return CONFIG["CORES"]["VERMELHO"]
    except:
        return CONFIG["CORES"]["PADRAO"]

# === FUNÇÕES DE ATUALIZAÇÃO ===
def toggle_sai_hoje(numero):
    conn = conectar()
    conn.execute("UPDATE ordens SET sai_hj = NOT sai_hj, data_alteracao = ? WHERE numero_ordem = ?",
                 (datetime.now().strftime("%d/%m/%Y %H:%M"), numero))
    conn.commit()
    conn.close()
    st.success(f"✓ Sai Hoje alterado - OS {numero}")

def mudar_situacao(numero, nova):
    conn = conectar()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    finalizacao = now if nova == "FINALIZADO" else ""
    conn.execute("UPDATE ordens SET situacao = ?, data_finalizacao = ?, data_alteracao = ? WHERE numero_ordem = ?",
                 (nova, finalizacao, now, numero))
    conn.commit()
    conn.close()
    st.success(f"Situação alterada → {nova}")

def cadastrar_nova_os(numero, placa, cliente, obs=""):
    if not all([numero, placa, cliente]):
        st.error("Preencha Número OS, Placa e Cliente!")
        return False
    conn = conectar()
    try:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn.execute("""
            INSERT INTO ordens 
            (numero_ordem, placa, cliente, situacao, data_criacao, observacao, data_alteracao, sai_hj)
            VALUES (?, ?, ?, 'AG DIAGNOSTICO', ?, ?, ?, 0)
        """, (numero, placa.upper(), cliente, now, obs, now))
        conn.commit()
        st.success(f"OS {numero} cadastrada com sucesso!")
        return True
    except sqlite3.IntegrityError:
        st.error("Este número de OS já existe!")
        return False
    finally:
        conn.close()

# === CARREGAR DADOS COM CACHE ===
@st.cache_data(ttl=15, show_spinner="Atualizando ordens...")
def carregar_ordens():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT numero_ordem, placa, cliente, previsao, situacao, observacao, sai_hj
        FROM ordens 
        WHERE situacao != 'FINALIZADO'
        ORDER BY 
            CASE situacao
                WHEN 'AG DIAGNOSTICO' THEN 1
                WHEN 'AG APROVAÇÃO' THEN 2
                WHEN 'AG EXECUÇÃO' THEN 3
                WHEN 'EXECUTANDO SERVIÇOS' THEN 4
                WHEN 'AGUARDANDO PÇ CLIENTE' THEN 5
                WHEN 'AGUARDANDO PÇ INT' THEN 6
                ELSE 99
            END,
            previsao
    """)
    dados = cur.fetchall()
    conn.close()
    return dados

# === INTERFACE WEB ===
st.set_page_config(page_title="Oficina - Pátio", layout="wide", initial_sidebar_state="expanded")
st.title("🚛 Gerenciador de Ordens de Serviço - Versão Web")
st.markdown("**Acompanhe em tempo real pelo celular • Usa o mesmo banco do programa principal**")

# Contador gigante
dados = carregar_ordens()
total = len(dados)
st.markdown(f"### **{total}** caminhões no pátio")

# Pesquisa + botão atualizar
col1, col2 = st.columns([4, 1])
with col1:
    busca = st.text_input("🔍 Pesquisar (OS / Placa / Cliente)", "")
with col2:
    if st.button("Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if busca:
    dados = [d for d in dados if busca.upper() in " ".join(map(str, d)).upper()]

# Exibir por situação
for situacao in CONFIG["SITUACOES"][:-1]:
    ordens = [d for d in dados if d[4] == situacao]
    if ordens:
        st.markdown(f"### ═══ {situacao} ═══")
        for row in ordens:
            num, placa, cliente, prev, sit, obs, sai = row
            cor = calcular_cor(prev)
            sai_texto = "🚛 SAI HOJE" if sai else "Espera"

            with st.container():
                c1, c2, c3, c4 = st.columns([1.3, 4, 2.5, 2])
                with c1:
                    if st.button(sai_texto, key=f"sai_{num}", use_container_width=True):
                        toggle_sai_hoje(num)
                        st.rerun()
                with c2:
                    st.markdown(f"**OS {num}** • **{placa}** • {cliente}")
                    if obs:
                        st.caption(f"📝 {obs}")
                with c3:
                    prev_texto = prev or "Sem previsão"
                    st.markdown(f"**Previsão:** {prev_texto}")
                with c4:
                    nova_sit = st.selectbox("Situação", CONFIG["SITUACOES"], 
                                          index=CONFIG["SITUACOES"].index(sit), 
                                          key=f"sit_{num}")
                    if nova_sit != sit:
                        mudar_situacao(num, nova_sit)
                        st.rerun()

                # Barra colorida da previsão
                st.markdown(f"<div style='background:{cor};height:8px;border-radius:4px;'></div>", 
                           unsafe_allow_html=True)
                st.markdown("---")

# === CADASTRO RÁPIDO ===
st.markdown("### ➕ Cadastrar Nova Ordem de Serviço")
with st.form("nova_os_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    num_os = col1.text_input("Número OS *", placeholder="12345")
    placa = col2.text_input("Placa *", placeholder="ABC-1234")
    cliente = col3.text_input("Cliente *", placeholder="João Silva")
    obs = st.text_area("Observação (opcional)", height=80)
    enviar = st.form_submit_button("🚀 CADASTRAR ORDEM")
    if enviar:
        if cadastrar_nova_os(num_os, placa, cliente, obs):
            st.rerun()

# Rodapé
st.markdown("""
---
JJSOFT26
""")

