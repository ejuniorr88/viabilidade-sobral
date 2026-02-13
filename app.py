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

# --- BANCO DE DADOS FIEL ÀS TABELAS OFICIAIS (LC 90/2023) ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "desc": "1 vaga por unidade"},
    "Prédio (Multifamiliar)": {"v": 65, "s": 150, "desc": "1 vaga por unidade"},
    "Comércio e Serviços (Inc. Farmácias)": {"v": 50, "s": 100, "desc": "1 vaga a cada 50m²"},
    "Farmácia": {"v": 50, "s": 100, "desc": "1 vaga a cada 50m²"},
    "Depósito / Galpão": {"v": 150, "s": 200, "desc": "1 vaga a cada 150m²"},
    "Supermercado": {"v": 25, "s": 80, "desc": "1 vaga a cada 25m²"},
    "Clínica Médica / Consultório": {"v": 40, "s": 50, "desc": "1 vaga a cada 40m²"},
    "Hospital / Maternidade": {"v": 80, "s": 30, "desc": "1 vaga a cada 80m²"},
    "Faculdade / Superior": {"v": 35, "s": 40, "desc": "1 vaga a cada 35m²"},
}

# --- SIDEBAR: DADOS E BUSCA ---
with st.sidebar:
    st.header("📋 1. Configurar Uso")
    cat = st.selectbox("Categoria:", ["Residencial", "Comercial", "Saúde/Educação"])
    
    if cat == "Residencial": sub = ["Casa Individual (Unifamiliar)", "Prédio (Multifamiliar)"]
    elif cat == "Comercial": sub = ["Comércio e Serviços (Inc. Farmácias)", "Farmácia", "Depósito / Galpão", "Supermercado"]
    else: sub = ["Clínica Médica / Consultório", "Hospital / Maternidade", "Faculdade / Superior"]
    
    escolha_quadro = st.selectbox("Tipo de uso:", sub)

    st.markdown("---")
    st.header("🔍 2. Busca Rápida")
    escolha_busca = st.selectbox(
        "Ou digite a atividade:",
        options=[""] + sorted(list(atividades_db.keys())),
        index=0
    )

    atv_final = escolha_busca if escolha_busca != "" else escolha_quadro
    dados_atv = atividades_db[atv_final]

    st.divider()
    st.header("📐 3. Dimensões")
    testada = st.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = st.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    area_c = st.number_input("Área Construída (m²)", min_value=1.0, value=200.0)
    pavs = st.number_input("Pavimentos", min_value=1, value=1)
    area_t = testada * profundidade

# --- MAPA ---
st.subheader("\"lote\"")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite', name='Google Satellite').add_to(m)

if 'clique' not in st.session_state: st.session_state.clique = None
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red", icon="home")).add_to(m)

out = st_folium(m, width="100%", height=400)
if out and out.get("last_clicked"):
    pos = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    if st.session_state.clique != pos:
        st.session_state.clique = pos
        st.rerun()

# --- BOTÃO DE PESQUISA ---
st.markdown("---")
btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
with btn_col2:
    botao_gerar = st.button("🚀 GERAR ESTUDO DE VIABILIDADE", use_container_width=True)

# --- PROCESSAMENTO DO RELATÓRIO ---
if botao_gerar:
    if not st.session_state.clique:
        st.error("📍 Por favor, primeiro clique no lote desejado no mapa.")
    else:
        ponto = Point(st.session_state.clique[1], st.session_state.clique[0])
        zona = "ZAP" 
        if root is not None:
            namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
            for pm in root.findall('.//kml:Placemark', namespaces):
                poly = pm.find('.//kml:Polygon', namespaces)
                if poly is not None:
                    coords_text = poly.find('.//kml:coordinates', namespaces).text.strip().split()
                    coords = [tuple(map(float, c.split(',')[:2])) for c in coords_text]
                    if Polygon(coords).contains(ponto):
                        zona = pm.find('kml:name', namespaces).text
                        break

        st.success(f"Relatório gerado com sucesso para a atividade: {atv_final}")
        
        st.subheader(f"📑 EVT: {atv_final.upper()}")
        c1, c2 = st.columns(2)
        with c1:
            st.info("### 🏗️ 1. ÍNDICES")
            to_calc = (area_c / pavs) / area_t
            st.write(f"**Zona:** {zona}")
            st.write(f"**Ocupação:** {to_calc*100:.1f}% (Máx: 70%)")
            st.write(f"**Área Permeável (10%):** {area_t * 0.1:.2f}m²")

        with c2:
            st.info("### 📏 2. RECUOS")
            st.write("**Frontal:** 3,00 m")
            st.write("**Laterais:** Isento (paredes cegas) / 1,50m (aberturas)")

        c3, c4 = st.columns(2)
        with c3:
            st.info("### 🚽 3. SANITÁRIO")
            vasos = math.ceil(area_c / dados_atv['s'])
            st.write(f"**Vasos/Lavatórios:** {max(1, vasos)} conj.")

        with c4:
            st.info("### 🚗 4. VAGAS")
            vagas = math.ceil(area_c / dados_atv['v']) if dados_atv['v'] > 0 else 1
            st.write(f"**Vagas Carro:** {vagas} vaga(s)")
            st.write(f"**Regra:** {dados_atv['desc']}")
else:
    if st.session_state.clique:
        st.info("✅ Lote selecionado. Clique no botão acima para gerar o relatório.")
