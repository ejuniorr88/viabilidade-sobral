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
    profundidade = st.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    area_c = st.number_input("Área Construída Total (m²)", min_value=1.0, value=200.0)
    pavs = st.number_input("Pavimentos", min_value=1, value=1)
    area_t = testada * profundidade

# --- MAPA ---
st.subheader("\"lote\"")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google Satellite', name='Google Satellite').add_to(m)

if 'clique' not in st.session_state: st.session_state.clique = None
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red", icon="home")).add_to(m)

out = st_folium(m, width="100%", height=400)
if out and out.get("last_clicked"):
    pos = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    if st.session_state.clique != pos:
        st.session_state.clique = pos
        st.rerun()

# --- BOTÕES DE CONTROLE ---
st.markdown("---")
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])

with col_btn2:
    gerar_evt = st.button("🚀 GERAR ESTUDO DE VIABILIDADE", use_container_width=True)
    
    if st.button("🗑️ LIMPAR PESQUISA", use_container_width=True):
        st.session_state.clique = None
        st.rerun()

# --- RESULTADO DO EVT ---
if gerar_evt:
    if not st.session_state.clique:
        st.error("📍 Por favor, clique em um lote no mapa primeiro.")
    else:
        ponto = Point(st.session_state.clique[1], st.session_state.clique[0])
        zona_clicada = "Desconhecida"
        if root is not None:
            namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
            for pm in root.findall('.//kml:Placemark', namespaces):
                poly = pm.find('.//kml:Polygon', namespaces)
                if poly is not None:
                    coords_text = poly.find('.//kml:coordinates', namespaces).text.strip().split()
                    coords = [tuple(map(float, c.split(',')[:2])) for c in coords_text]
                    if Polygon(coords).contains(ponto):
                        zona_clicada = pm.find('kml:name', namespaces).text
                        break

        to_calc = (area_c / pavs) / area_t
        ca_calc = area_c / area_t
        limites_zonas = {
            "ZAP": {"TO": 0.70, "CA": 1.0, "TP": 0.10},
            "ZAM": {"TO": 0.60, "CA": 1.0, "TP": 0.1
