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

# --- BANCO DE DADOS (SOBRAL LC 90/91) ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "t": "Residencial"},
    "Prédio (Multifamiliar)": {"v": 65, "s": 150, "t": "Residencial"},
    "Comércio e Serviços (Inc. Farmácias)": {"v": 50, "s": 100, "t": "Comercial"},
    "Farmácia": {"v": 50, "s": 100, "t": "Comercial"},
    "Depósito / Galpão": {"v": 150, "s": 200, "t": "Comercial"},
    "Supermercado": {"v": 25, "s": 80, "t": "Comercial"},
    "Clínica Médica / Consultório": {"v": 40, "s": 50, "t": "Saúde"},
    "Hospital / Maternidade": {"v": 80, "s": 30, "t": "Saúde"},
    "Faculdade / Superior": {"v": 35, "s": 40, "t": "Educação"},
    "Escola (Fund./Médio)": {"v": 100, "s": 40, "t": "Educação"}
}

# --- SIDEBAR: DADOS E BUSCA ---
with st.sidebar:
    st.header("📋 1. Configurar Uso")
    cat = st.selectbox("Categoria:", ["Residencial", "Comercial", "Saúde/Educação"])
    
    if cat == "Residencial": sub = ["Casa Individual (Unifamiliar)", "Prédio (Multifamiliar)"]
    elif cat == "Comercial": sub = ["Comércio e Serviços (Inc. Farmácias)", "Farmácia", "Depósito / Galpão", "Supermercado"]
    else: sub = ["Clínica Médica / Consultório", "Hospital / Maternidade", "Faculdade / Superior", "Escola (Fund./Médio)"]
    
    escolha_quadro = st.selectbox("Tipo de uso (Menu):", sub)

    st.markdown("---")
    st.header("🔍 2. Busca Direta")
    escolha_busca = st.selectbox("Ou digite a atividade:", options=[""] + sorted(list(atividades_db.keys())))

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

# --- BOTÃO DE DISPARO ---
st.markdown("---")
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    gerar_evt = st.button("🚀 GERAR ESTUDO DE VIABILIDADE", use_container_width=True)

# --- RELATÓRIO EVT ---
if gerar_evt:
    if not st.session_state.clique:
        st.error("📍 Primeiro, selecione o lote clicando no mapa.")
    else:
        ponto = Point(st.session_state.clique[1], st.session_state.clique[0])
        zona = "Não Identificada"
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

        st.success(f"Análise concluída para {atv_final} na zona {zona}.")
        
        # EXIBIÇÃO EM QUADROS
        c1, c2 = st.columns(2)
        with c1:
            st.info("### 🏗️ 1. ÍNDICES")
            to_calc = (area_c / pavs) / area_t
            st.write(f"**Zona:** {zona}")
            st.write(f"**Taxa de Ocupação:** {to_calc*100:.1f}% (Máx: 70%)")
            st.write(f"**Permeabilidade Mínima (10%):** {area_t * 0.1:.2f}m²")

        with c2:
            st.info("### 📏 2. RECUOS")
            st.write("**Frontal:** 3,00 m")
            st.write("**Laterais:** 1,50 m (com abertura)")
            st.write("**Fundos:** 1,50 m (conforme Art. 107 da LC 90)")
            st.caption("Nota: Paredes cegas podem ser isentas conforme a zona.")

        c3, c4 = st.columns(2)
        with c3:
            st.info("### 🚽 3. SANITÁRIO")
            vasos = math.ceil(area_c / dados_atv['s'])
            st.write(f"**Vasos/Lavatórios:** {max(1, vasos)} conj.")

        with c4:
            st.info("### 🚗 4. VAGAS")
            vagas = math.ceil(area_c / dados_atv['v']) if dados_atv['v'] > 0 else 1
            st.write(f"**Vagas de Carro:** {vagas}")
            bicis = max(5, math.ceil(vagas * 0.1))
            st.write(f"**Bicicletas:** {bicis} vagas")
