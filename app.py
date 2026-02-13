import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# 1. Configuração da Página
st.set_page_config(page_title="Viabilidade Sobral", layout="wide")
st.markdown("<h1 style='text-align: center;'>Viabilidade Urbana</h1>", unsafe_allow_html=True)

# Memória de Sessão para persistência
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
    "Prédio de Apartamentos": {"v": 65, "s": 150, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Loja / Comércio": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Farmácia": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Depósito / Galpão": {"v": 150, "s": 200, "zs": ["ZAP", "ZAM", "ZDE", "ZIND"]},
    "Supermercado": {"v": 25, "s": 80, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Clínica Médica": {"v": 40, "s": 50, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Hospital": {"v": 80, "s": 30, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escritório": {"v": 60, "s": 70, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Faculdade": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]}
}

# --- SIDEBAR: CATEGORIAS E BUSCA ---
with st.sidebar:
    st.header("📋 1. Escolha o Uso")
    cat = st.selectbox("Categoria:", ["Residencial", "Comercial", "Saúde/Educação"])
    subs = {
        "Residencial": ["Casa Individual (Unifamiliar)", "Prédio de Apartamentos"],
        "Comercial": ["Loja / Comércio", "Farmácia", "Depósito / Galpão", "Supermercado"],
        "Saúde/Educação": ["Clínica Médica", "Hospital", "Escritório", "Faculdade"]
    }
    escolha_cat = st.selectbox("Opções:", subs[cat])
    st.markdown("---")
    st.header("🔍 2. Busca Direta")
    escolha_busca = st.selectbox("Pesquisar uso:", [""] + sorted(list(atividades_db.keys())))
    atv_final = escolha_busca if escolha_busca != "" else escolha_cat
    dados_atv = atividades_db[atv_final]
    st.divider()
    st.header("📐 3. Dados do Lote")
    testada = st.number_input("Testada (m):", value=10.0)
    profundidade = st.number_input("Profundidade (m):", value=30.0)
    esquina = st.checkbox("Lote de Esquina")
    pavs = st.slider("Pavimentos:", 1, 12, 1)
    area_t = testada * profundidade

# --- MAPA ---
st.subheader("📍 Selecione o lote no mapa:")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite', name='Google Satellite').add_to(m)
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red")).add_to(m)
