import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# 1. Configuração da Página
st.set_page_config(page_title="Viabilidade Sobral", layout="wide")
st.markdown("<h1 style='text-align: center;'>Viabilidade</h1>", unsafe_allow_html=True)

# Memória do App
if 'clique' not in st.session_state: st.session_state.clique = None
if 'relatorio' not in st.session_state: st.session_state.relatorio = None

@st.cache_data
def carregar_dados_kmz():
    try:
        with zipfile.ZipFile('Zoneamento Urbano da Sede.kmz', 'r') as z:
            kml_name = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_name) as f: return ET.fromstring(f.read())
    except: return None

root = carregar_dados_kmz()

# --- BANCO DE DADOS TÉCNICO ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "zs": ["ZAP", "ZAM", "ZPR", "ZCR", "ZPH"]},
    "Prédio (Multifamiliar)": {"v": 65, "s": 150, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Loja / Comércio": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Farmácia": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Depósito / Galpão": {"v": 150, "s": 200, "zs": ["ZAP", "ZAM", "ZDE", "ZIND"]},
    "Supermercado": {"v": 25, "s": 80, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Clínica Médica": {"v": 40, "s": 50, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Hospital / Maternidade": {"v": 80, "s": 30, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escritório": {"v": 60, "s": 70, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Faculdade / Superior": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]}
}

# --- SIDEBAR: ESTRUTURA FIXA ---
with st.sidebar:
    st.header("📋 1. Escolha por Categoria")
    cat = st.selectbox("Categoria:", ["Residencial", "Comercial", "Saúde/Educação"])
    subs = {
        "Residencial": ["Casa Individual (Unifamiliar)", "Prédio (Multifamiliar)"],
        "Comercial": ["Loja / Comércio", "Farmácia", "Depósito / Galpão
