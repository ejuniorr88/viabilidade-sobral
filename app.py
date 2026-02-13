import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

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
    except: return None

root = carregar_dados_kmz()

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("📋 Dados do Projeto")
    tipo_uso = st.selectbox("Tipo de Uso", 
                            ["Residencial Unifamiliar", "Residencial Multifamiliar", 
                             "Comercial (Depósito/Galpão)", "Comércio Varejista", "Serviço"])
    
    col1, col2 = st.columns(2)
    testada = col1.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = col2.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    
    area_terreno = testada * profundidade
    area_const_total = st.number_input("Área Construída Estimada (m²)", min_value=1.0, value=210.0)
    num_pavimentos = st.number_input("Número de Pavimentos", min_value=1, value=1)
    
    st.info(f"Área do Terreno: {area_terreno:.2f} m²")

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

# --- RELATÓRIO EVT ---
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

    # Lógica de Parâmetros de Sobral
    db_regras = {
        "ZAP": {"TO": 0.70, "CA": 1.0, "CAMax": 4.0, "TP": 0.10},
        "ZAM": {"TO": 0.60, "CA": 1.0, "CAMax": 3.0, "TP": 0.15},
        "ZCR": {"TO": 0.80, "CA": 1.0, "CAMax": 5.0, "TP": 0.05}
    }
    r = db_regras.get(zona, {"TO": 0.60, "CA": 1.0, "CAMax": 2.0, "TP": 0.15})

    st.divider()
    st.subheader(f"📑 ESTUDO DE VIABILIDADE TÉCNICA (EVT) - {tipo_uso.upper()}")
    
    st.markdown(f"""
    **DADOS DO LOTE:** **Zona:** {zona}  
    **Terreno:** {area_terreno:.2f}m² ({testada:.2f}m x {profundidade:.2f}m)  
    **Uso:** {tipo_uso}
    """)

    col_evt1, col_evt2 = st.columns(2)

    with col_evt1:
        st.markdown("### 1. ÍNDICES URBANÍSTICOS")
        to_calc = (area_const_total / num_pavimentos) / area_terreno
        proj_max = area_terreno * r['TO']
        st.write(f"**Taxa de Ocupação (TO):** {r['TO']*100}%")
        st.write(f"**Projeção Máxima no Solo:** {proj_max:.2f}m²")
        
        ca_calc = area_const_total / area_terreno
        st.write(f"**C.A. Básico:** {r['CA']}")
        st.write(f"**Área Construída Gratuita:** {area_terreno * r['CA']:.2f}m²")
        st.write(f"**Taxa de Permeabilidade (TP):** {r['TP']*100}% ({area_terreno * r['TP']:.2f}m²)")

    with col_evt2:
        st.markdown("### 2. RECUOS OBRIGATÓRIOS")
        st.write("**Frontal:** 3,00 m (Uso permitido para estacionamento descoberto)")
        st.write("**Laterais e Fundos:** Isento se paredes cegas. Se houver aberturas: 1,50 m.")

    st.markdown("---")
    c_san, c_vagas = st.columns(2)

    with c_san:
        st.markdown("### 3. DIMENSIONAMENTO SANITÁRIO")
        if area_const_total <= 150:
            st.write("- Até 150 m²: 01 Vaso + 01 Lavatório (Unissex/PCD)")
        else:
            st.write("- Acima de 150 m²: 02 Vasos + 02 Lavatórios (M/F)")
        st.write("- Copa/Cozinha: Obrigatório 01 pia para funcionários.")

    with c_vagas:
        st.markdown("### 4. ESTACIONAMENTO E CARGA")
        if "Comercial" in tipo_uso:
            vagas = math.ceil(area_const_total / 100)
            st.write(f"**Vagas de Veículos:** {vagas} vaga(s)")
            st.write("**Carga e Descarga:** Obrigatório pátio interno para caminhões.")
        else:
            st.write(f"**Vagas de Veículos:** 01 vaga por unidade.")

    st.markdown("---")
    # CONCLUSÃO
    if to_calc <= r['TO']:
        st.success(f"✅ **CONCLUSÃO:** O projeto é **VIÁVEL**, respeitando a TO de {r['TO']*100}%.")
    else:
        st.error(f"❌ **CONCLUSÃO:** **INVIÁVEL**. A ocupação de {to_calc*100:.1f}% excede o limite.")

    st.info(f"**Dica de Projeto:** Como o terreno tem {area_terreno}m², a melhor estratégia é concentrar a construção respeitando o recuo frontal de 3m para vagas e garantir a área de permeabilidade de {area_terreno*r['TP']}m² nos fundos ou pátios laterais.")
    st.caption("Recomenda-se confirmação junto ao órgão municipal competente.")

else:
    st.info("👈 Insira os dados e clique no mapa para gerar o EVT.")
