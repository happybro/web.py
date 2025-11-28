# ================ web.py ================
# VERSÃO WEB DO SEU GERENCIADOR - ACESSO PELO CELULAR/INTERNET
# RODA EM PARALELO COM O PROGRAMA PRINCIPAL (gerenciador.py)
# Usa exatamente o mesmo banco de dados!

import streamlit as st
import sqlite3
import os
from datetime import datetime

# === CONFIGURAÇÕES IGUAIS AO SEU PROGRAMA ===
CAMINHO_SERVIDOR = r"\\servidor\dados\Nova Pasta"
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
        if minutos > 60: return CONFIG["CORES"]["VERDE"]
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
    st.success(f"Sai Hoje alterado - OS {numero}")

def mudar_situacao(numero, nova):
    conn = conectar()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    finalizacao = now if nova == "FINALIZADO" else ""
    conn.execute("UPDATE ordens SET situacao = ?, data_finalizacao = ?, data_alteracao = ? WHERE numero_ordem = ?",
                 (nova, finalizacao, now, numero))
    conn.commit()
    conn.close()
    st.success(f"Situação → {nova}")

def cadastrar_nova_os(numero, placa, cliente, obs=""):
    if not all([numero, placa, cliente]):
        st.error("Preencha Número OS, Placa e Cliente!")
        return
    conn = conectar()
    try:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn.execute("""
            INSERT INTO ordens 
            (numero_ordem, placa, cliente, situacao, data_criacao, observacao, data_alteracao, sai_hj)
            VALUES (?, ?, ?, 'AG DIAGNOSTICO', ?, ?, ?, 0)
        """, (numero, placa.upper(), cliente, now, obs, now))
        conn Merrill
        conn.commit()
        st.success(f"OS {numero} cadastrada!")
    except sqlite3.IntegrityError:
        st.error("Este número de OS já existe!")
    finally:
        conn.close()

# === CARREGAR DADOS COM CACHE ===
@st.cache_data(ttl=15, show_spinner="Atualizando...")
def carregar_ordens():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT numero_ordem, placa, cliente, previsao, situacao, observacao, sai_hj
        FROM ordens WHERE situacao != 'FINALIZADO'
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

st.title("Gerenciador de Ordens de Serviço")
st.markdown("**Acompanhe em tempo real pelo celular!**")

# Contador gigante
dados = carregar_ordens()
total = len(dados)
st.markdown(f"### **{total}** caminhões no pátio", unsafe_allow_html=True)

# Pesquisa
busca = st.text_input("Pesquisar (OS, placa, cliente)", "")
if busca:
    dados = [d for d in dados if busca.upper() in " ".join(map(str, d)).upper()]

if st.button("Atualizar Agora"):
    st.cache_data.clear()
    st.rerun()

# Exibir por situação
for situacao in CONFIG["SITUACOES"][:-1]:
    ordens = [d for d in dados if d[4] == situacao]
    if ordens:
        st.markdown(f"### {situacao}")
        for row in ordens:
            num, placa, cliente, prev, sit, obs, sai = row
            cor = calcular_cor(prev)
            sai_texto = "SAI HOJE" if sai else "No pátio"

            with st.container():
                cols = st.columns([1.2, 4, 2.5, 2])
                with cols[0]:
                    if st.button(sai_texto, key=f"sai_{num}", use_container_width=True):
                        toggle_sai_hoje(num)
                        st.rerun()
                with cols[1]:
                    st.markdown(f"**OS {num}** • **{placa}** • {cliente}")
                    if obs:
                        st.caption(obs)
                with cols[2]:
                    prev_texto = prev or "Sem previsão"
                    st.markdown(f"**Previsão:** {prev_texto}")
                with cols[3]:
                    nova_sit = st.selectbox("Situação", CONFIG["SITUACOES"], 
                                          index=CONFIG["SITUACOES"].index(sit), 
                                          key=f"sit_{num}")
                    if nova_sit != sit:
                        mudar_situacao(num, nova_sit)
                        st.rerun()

                # Barra colorida
                st.markdown(f"<div style='background:{cor};height:8px;border-radius:4px;margin:8px 0;'></div>", 
                           unsafe_allow_html=True)

# === CADASTRO RÁPIDO ===
st.markdown("### + Nova Ordem de Serviço")
with st.form("nova_os"):
    c1, c2, c3 = st.columns(3)
    num = c1.text_input("Número OS *")
    placa = c2.text_input("Placa *")
    cliente = c3.text_input("Cliente *")
    obs = st.text_area("Observação")
    enviar = st.form_submit_button("CADASTRAR ORDEM")
    if enviar:
        cadastrar_nova_os(num, placa, cliente, obs)
        st.rerun()

# Rodapé
st.markdown("""
---
JJSOFT26
""")
