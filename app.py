import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

st.set_page_config(page_title="Viabilidade Sobral", layout="wide")
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

# --- SIDEBAR: CATEGORIAS FACILITADAS ---
with st.sidebar:
    st.header("📋 O que você deseja construir?")
    
    # Primeiro nível de escolha: Linguagem simples
    categoria = st.selectbox("Escolha uma categoria:", [
        "Residencial (Casas e Prédios)", 
        "Comércio e Lojas", 
        "Logística e Indústria (Galpões)",
        "Saúde e Clínicas",
        "Educação e Escolas",
        "Serviços e Escritórios"
    ])

    # Segundo nível: Subgrupos baseados na LC 90 e 91
    sub_uso = ""
    if categoria == "Residencial (Casas e Prédios)":
        sub_uso = st.selectbox("Tipo de moradia:", ["Casa Individual (Unifamiliar)", "Prédio/Apartamentos (Multifamiliar)"])
    
    elif categoria == "Comércio e Lojas":
        sub_uso = st.selectbox("Tipo de comércio:", ["Loja de Rua/Varejo", "Supermercado", "Centro Comercial/Mall"])
    
    elif categoria == "Logística e Indústria (Galpões)":
        sub_uso = st.selectbox("Tipo de instalação:", ["Galpão de Armazenamento/Depósito", "Indústria de Pequeno Porte", "Oficina Mecânica"])
    
    elif categoria == "Saúde e Clínicas":
        sub_uso = st.selectbox("Tipo de serviço de saúde:", ["Consultório Médico", "Clínica com Exames", "Hospital/Pronto Socorro"])
    
    elif categoria == "Educação e Escolas":
        sub_uso = st.selectbox("Nível de ensino:", ["Cursos Livres (Idiomas/Autoescola)", "Escola Infantil/Fundamental", "Faculdade/Universidade"])
    
    elif categoria == "Serviços e Escritórios":
        sub_uso = st.selectbox("Tipo de serviço:", ["Escritório em Geral", "Academia", "Salão de Beleza/Estética"])

    st.divider()
    st.header("📐 Dimensões do Lote")
    col1, col2 = st.columns(2)
    testada = col1.number_input("Largura (Testada)", min_value=1.0, value=10.0)
    profundidade = col2.number_input("Profundidade", min_value=1.0, value=30.0)
    
    area_terreno = testada * profundidade
    area_const_total = st.number_input("Área Construída Total (m²)", min_value=1.0, value=200.0)
    num_pavimentos = st.number_input("Quantos andares?", min_value=1, value=1)
    
    st.info(f"Área Total do Lote: {area_terreno:.2f} m²")

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
    # Lógica de extração de Zona (KMZ)
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

    # Parâmetros simplificados Sobral
    db_regras = {
        "ZAP": {"TO": 0.70, "CA": 1.0, "TP": 0.10},
        "ZAM": {"TO": 0.60, "CA": 1.0, "TP": 0.15},
        "ZCR": {"TO": 0.80, "CA": 1.0, "TP": 0.05}
    }
    r = db_regras.get(zona, {"TO": 0.60, "CA": 1.0, "TP": 0.15})

    st.divider()
    st.subheader(f"📑 EVT - {sub_uso.upper()}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Índices", "📏 Recuos", "🚽 Sanitário", "🚗 Vagas"])
    
    with tab1:
        to_calc = (area_const_total / num_pavimentos) / area_terreno
        st.write(f"**Zona:** {zona}")
        st.write(f"**Projeção Máxima Permitida:** {area_terreno * r['TO']:.2f}m²")
        st.write(f"**Área de Permeabilidade Mínima:** {area_terreno * r['TP']:.2f}m²")

    with tab2:
        st.write("**Afastamentos Obrigatórios (LC 90):**")
        st.write("- **Frontal:** 3,00m (Uso para vagas descobertas permitido)")
        st.write("- **Laterais/Fundos:** Isento para paredes cegas; 1,50m para aberturas.")

    with tab3:
        if area_const_total <= 150:
            st.write("✅ 01 Vaso + 01 Lavatório (Unissex/PCD)")
        else:
            st.write("✅ 02 Vasos + 02 Lavatórios (Masculino/Feminino)")

    with tab4:
        # Lógica de Vagas Dinâmica (Base Anexo IV - LC 90)
        if "Galpão" in sub_uso:
            vagas = math.ceil(area_const_total / 150)
            st.write(f"**Vagas de Veículos:** {vagas} vaga(s)")
            st.warning("⚠️ Obrigatório pátio interno para Carga e Descarga.")
        elif "Loja" in sub_uso or "Escritório" in sub_uso:
            vagas = math.ceil(area_const_total / 50)
            st.write(f"**Vagas de Veículos:** {vagas} vaga(s)")
        elif "Faculdade" in sub_uso:
            vagas = math.ceil(area_const_total / 35)
            st.write(f"**Vagas de Veículos:** {vagas} vaga(s)")
        else:
            vagas = 1
            st.write(f"**Vagas de Veículos:** {vagas} vaga(s)")

    st.markdown("---")
    # CONCLUSÃO AUTOMÁTICA
    if to_calc <= r['TO']:
        st.success("✅ PROJETO VIÁVEL")
    else:
        st.error(f"❌ INVIÁVEL (TO calculada: {to_calc*100:.1f}% | Máxima: {r['TO']*100}%)")

else:
    st.info("👈 Selecione o que deseja construir na esquerda e clique no lote no mapa.")
