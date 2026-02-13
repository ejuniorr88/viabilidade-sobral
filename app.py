import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# 1. Configuração da Página
st.set_page_config(page_title="Viabilidade Sobral", layout="wide")

# Título minimalista
st.markdown("<h1 style='text-align: center;'>Viabilidade</h1>", unsafe_allow_html=True)

@st.cache_data
def carregar_dados_kmz():
    try:
        with zipfile.ZipFile('Zoneamento Urbano da Sede.kmz', 'r') as z:
            kml_name = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_name) as f:
                return ET.fromstring(f.read())
    except Exception:
        return None

root = carregar_dados_kmz()

# --- BANCO DE DADOS TÉCNICO FIXO (SOBRAL LC 90/91) ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "cat": "R1", "zonas": ["ZAP", "ZAM", "ZPR", "ZCR", "ZPH"]},
    "Prédio (Multifamiliar)": {"v": 65, "s": 150, "cat": "R3", "zonas": ["ZAP", "ZAM", "ZCR"]},
    "Loja / Comércio": {"v": 50, "s": 100, "cat": "C1", "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Farmácia": {"v": 50, "s": 100, "cat": "C1", "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Depósito / Galpão": {"v": 150, "s": 200, "cat": "S3", "zonas": ["ZAP", "ZAM", "ZDE", "ZIND"]},
    "Supermercado": {"v": 25, "s": 80, "cat": "C2", "zonas": ["ZAP", "ZAM", "ZCR"]},
    "Clínica Médica": {"v": 40, "s": 50, "cat": "S2", "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Hospital / Maternidade": {"v": 80, "s": 30, "cat": "S3", "zonas": ["ZAP", "ZAM", "ZCR"]},
    "Escritório": {"v": 60, "s": 70, "cat": "S1", "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Faculdade / Superior": {"v": 35, "s": 40, "cat": "E3", "zonas": ["ZAP", "ZAM", "ZCR"]}
}

# --- SIDEBAR: ESTRUTURA FIXA ---
with st.sidebar:
    st.header("📋 1. Escolha por Categoria")
    cat = st.selectbox("Selecione a Categoria:", ["Residencial", "Comercial", "Serviço", "Saúde/Educação"])
    
    if cat == "Residencial": sub = ["Casa Individual (Unifamiliar)", "Prédio (Multifamiliar)"]
    elif cat == "Comercial": sub = ["Loja / Comércio", "Farmácia", "Depósito / Galpão", "Supermercado"]
    elif cat == "Serviço": sub = ["Escritório"]
    else: sub = ["Clínica Médica", "Hospital / Maternidade", "Faculdade / Superior"]
    
    escolha_quadro = st.selectbox("Tipo de uso (Menu):", sub)

    st.markdown("---")
    st.header("🔍 2. Busca por Digitação")
    escolha_busca = st.selectbox(
        "Digite para encontrar o uso:",
        options=[""] + sorted(list(atividades_db.keys())),
        index=0
    )

    atv_final = escolha_busca if escolha_busca != "" else escolha_quadro
    dados_atv = atividades_db[atv_final]

    st.divider()
    st.header("📐 3. Dimensões do Lote")
    testada = st.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade =
