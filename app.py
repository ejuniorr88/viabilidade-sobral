import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Viabilidade Sobral", layout="wide")

# Substituído conforme solicitado
st.markdown("<h1 style='text-align: center;'>Consultor de Viabilidade Sobral \"viabilidade\"</h1>", unsafe_allow_html=True)

@st.cache_data
def carregar_dados_kmz():
    try:
        with zipfile.ZipFile('Zoneamento Urbano da Sede.kmz', 'r') as z:
            kml_name = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_name) as f:
                return ET.fromstring(f.read())
    except: return None

root = carregar_dados_kmz()

# --- FORMULÁRIO DE ENTRADA NA LATERAL ---
with st.sidebar:
    st.header("📋 Dados do Projeto")
    tipo_uso = st.selectbox("Tipo de Uso", ["Residencial Unifamiliar", "Residencial Multifamiliar/Prédio", "Comércio", "Serviço", "Indústria", "Uso Misto"])
    
    col_dim1, col_dim2 = st.columns(2)
    testada = col_dim1.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = col_dim2.number_input("Profundidade (m)", min_value=1.0, value=25.0)
    
    config_lote = st.radio("Configuração do Lote", ["Meio de Quadra", "Esquina"])
    
    area_construida_total = st.number_input("Área Construída Total Estada (m²)", min_value=1.0, value=150.0)
    num_pavimentos = st.number_input("Número de Pavimentos", min_value=1, value=1)
    
    area_terreno = testada * profundidade
    st.info(f"Área do Terreno: {area_terreno} m²")

# --- MAPA ---
# Substituído conforme solicitado
st.subheader("\"lote\"")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(m)

if 'clique' not in st.session_state: st.session_state.clique = None
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red", icon="home")).add_to(m)

out = st_folium(m, width="100%", height=500)

if out and out.get("last_clicked"):
    pos = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    if st.session_state.clique != pos:
        st.session_state.clique = pos
        st.rerun()

# --- RESULTADOS ---
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
    
    with tab1:
        regras = {"ZAP": {"TO": 0.7, "CA": 2.0}, "ZAM": {"TO": 0.6, "CA": 1.5}, "ZCR": {"TO": 0.8, "CA": 3.0}}
        regra = regras.get(zona, {"TO": 0.0, "CA": 0.0})
        to_calc = (area_construida_total / num_pavimentos) / area_terreno
        st.metric("Taxa de Ocupação", f"{to_calc*100:.1f}%", f"Limite: {regra['TO']*100}%")

    with tab2:
        st.write("Afastamentos automáticos em breve...")

    with tab3:
        st.write("Cálculo de aparelhos sanitários em breve...")

    with tab4:
        st.write("Cálculo de vagas em breve...")
else:
    st.info("👈 Preencha os dados e clique no mapa.")
