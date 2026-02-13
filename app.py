
import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Viabilidade Sobral", layout="wide")
st.title("🏗️ Consultor de Viabilidade Sobral")

@st.cache_data
def carregar_dados_kmz():
    try:
        with zipfile.ZipFile('Zoneamento Urbano da Sede.kmz', 'r') as z:
            kml_name = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_name) as f:
                return ET.fromstring(f.read())
    except: return None

root = carregar_dados_kmz()

# Entradas de área
st.subheader("1. Áreas do Projeto")
c1, c2 = st.columns(2)
area_t = c1.number_input("Área do Terreno (m²)", value=300.0)
area_p = c2.number_input("Área de Construção (m²)", value=150.0)

st.divider()

# Mapa de Satélite focado em Sobral
st.subheader("2. Clique no Lote em Sobral")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', name='Google Satellite').add_to(m)

if 'clique' not in st.session_state: st.session_state.clique = None
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red", icon="home")).add_to(m)

out = st_folium(m, width="100%", height=500)

if out and out.get("last_clicked"):
    pos = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    if st.session_state.clique != pos:
        st.session_state.clique = pos
        st.rerun()

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
    
    st.markdown(f"### Zona Detectada: **{zona}**")
    
    # Regras Sobral: ZAP (70%), ZAM (60%), ZCR (80%)
    regras = {"ZAP": 0.70, "ZAM": 0.60, "ZCR": 0.80}
    if zona in regras:
        to = area_p / area_t
        if to <= regras[zona]:
            st.success(f"✅ VIÁVEL! TO: {to*100:.1f}% (Limite: {regras[zona]*100}%)")
        else:
            st.error(f"❌ ILEGAL! TO: {to*100:.1f}% (Excede o limite de {regras[zona]*100}%)")
