import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

st.set_page_config(page_title="Viabilidade Sobral", layout="wide")

# Título minimalista conforme solicitado
st.markdown("<h1 style='text-align: center;'>Viabilidade</h1>", unsafe_allow_html=True)

@st.cache_data
def carregar_dados_kmz():
    try:
        with zipfile.ZipFile('Zoneamento Urbano da Sede.kmz', 'r') as z:
            kml_name = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_name) as f:
                return ET.fromstring(f.read())
    except: return None

root = carregar_dados_kmz()

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("📋 Dados do Projeto")
    tipo_uso = st.selectbox("Tipo de Uso", ["Residencial Unifamiliar", "Residencial Multifamiliar", "Comércio", "Serviço"])
    
    col_dim1, col_dim2 = st.columns(2)
    testada = col_dim1.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = col_dim2.number_input("Profundidade (m)", min_value=1.0, value=25.0)
    
    area_terreno = testada * profundidade
    area_const_total = st.number_input("Área Construída Total (m²)", min_value=1.0, value=150.0)
    num_pavimentos = st.number_input("Número de Pavimentos", min_value=1, value=1)
    
    st.info(f"Área do Terreno: {area_terreno} m²")

# --- MAPA ---
st.subheader("\"lote\"")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(m)

if 'clique' not in st.session_state: st.session_state.clique = None
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red", icon="home")).add_to(m)

out = st_folium(m, width="100%", height=400)

if out and out.get("last_clicked"):
    pos = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    if st.session_state.clique != pos:
        st.session_state.clique = pos
        st.rerun()

# --- LÓGICA DE CÁLCULO ---
if st.session_state.clique:
    ponto = Point(st.session_state.clique[1], st.session_state.clique[0])
    zona = "Zona não encontrada"
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

    st.divider()
    st.subheader(f"📊 Resultado: {zona}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Índices", "📏 Recuos", "🚽 Sanitário", "🚗 Vagas"])
    
    # Parâmetros oficiais de Sobral (Exemplos para ajuste)
    params = {
        "ZAP": {"TO": 0.7, "CA": 2.0, "TP": 0.15},
        "ZAM": {"TO": 0.6, "CA": 1.5, "TP": 0.20},
        "ZCR": {"TO": 0.8, "CA": 4.0, "TP": 0.10}
    }
    p = params.get(zona, {"TO": 0.5, "CA": 1.0, "TP": 0.15})

    with tab1:
        to_calc = (area_const_total / num_pavimentos) / area_terreno
        ca_calc = area_const_total / area_terreno
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Taxa Ocupação", f"{to_calc*100:.1f}%", f"Limite: {p['TO']*100}%")
        c2.metric("C.A. Atual", f"{ca_calc:.2f}", f"Limite: {p['CA']}")
        c3.metric("Permeabilidade", f"{p['TP']*100}%", "Mínimo")

    with tab2:
        recuo_f = 3.0 if num_pavimentos < 3 else 5.0
        st.write(f"**Recuo Frontal:** {recuo_f}m")
        st.write(f"**Laterais/Fundos:** 1.50m (para até 2 pavimentos)")

    with tab3:
        # Lógica simplificada de sanitários
        vasos = math.ceil(area_const_total / 100) if "Comércio" in tipo_uso else 1
        st.write(f"**Vasos Sanitários:** {vasos} unidade(s)")
        st.write(f"**Lavatórios:** {vasos} unidade(s)")

    with tab4:
        # Lógica de vagas (1 para cada 50m² no comércio, 1 por unidade no residencial)
        vagas = math.ceil(area_const_total / 50) if "Comércio" in tipo_uso else 1
        st.write(f"**Vagas de Estacionamento:** {vagas} vaga(s)")
        st.write(f"**Bicicletário:** {math.ceil(vagas/4)} vaga(s)")

else:
    st.info("👈 Insira os dados na lateral e clique no lote para analisar.")
