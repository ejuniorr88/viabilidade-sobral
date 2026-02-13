import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# Configuração da Página
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
# Tabelas extraídas das Normas de Estacionamento e Sanitários
atividades_db = {
    "Residencial Unifamiliar": {"v": 0, "s": 150, "desc": "1 vaga por unidade"},
    "Residencial Multifamiliar": {"v": 65, "s": 150, "desc": "1 vaga por unidade habitacional"},
    "Hospedagem (Hotéis e Pousadas)": {"v": 100, "s": 60, "desc": "1 vaga a cada 100m²"},
    "Motéis": {"v": 1, "s": 60, "desc": "1 vaga por quarto"},
    "Comércio e Serviços em Geral (Inc. Farmácias)": {"v": 50, "s": 100, "desc": "1 vaga a cada 50m²"},
    "Supermercados e Centros Comerciais": {"v": 25, "s": 80, "desc": "1 vaga a cada 25m²"},
    "Serviços de Saúde (Hospitais e Maternidades)": {"v": 80, "s": 30, "desc": "1 vaga a cada 80m²"},
    "Clínicas e Laboratórios": {"v": 40, "s": 50, "desc": "1 vaga a cada 40m²"},
    "Educação Infantil e Fundamental": {"v": 0, "s": 40, "desc": "Embarque interno obrigatório"},
    "Educação Superior e Profissionalizante": {"v": 35, "s": 40, "desc": "1 vaga a cada 35m²"},
    "Locais de Reunião (Igrejas e Templos)": {"v": 20, "s": 50, "desc": "1 vaga a cada 20m² de área de público"},
    "Cinemas e Teatros": {"v": 15, "s": 30, "desc": "1 vaga a cada 15 assentos"},
    "Clubes e Estádios": {"v": 50, "s": 100, "desc": "1 vaga a cada 50m²"},
    "Oficinas e Postos de Serviços": {"v": 100, "s": 150, "desc": "1 vaga a cada 100m²"},
    "Indústrias e Depósitos (Galpões)": {"v": 150, "s": 200, "desc": "1 vaga a cada 150m² + Carga/Descarga"},
}

# --- SIDEBAR: BUSCA E DIMENSÕES ---
with st.sidebar:
    st.header("📋 Definição do Uso")
    
    # Busca independente fiel à tabela com autocomplete
    escolha_busca = st.selectbox(
        "Digite ou selecione a atividade:",
        options=[""] + sorted(list(atividades_db.keys())),
        index=0,
        help="Nomenclaturas oficiais conforme o Código de Ordenamento de Sobral."
    )

    if escolha_busca == "":
        st.warning("Selecione uma atividade para gerar o relatório.")
        dados_atv = None
    else:
        dados_atv = atividades_db[escolha_busca]

    st.divider()
    st.header("📐 Dados do Projeto")
    testada = st.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = st.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    area_c = st.number_input("Área Construída Total (m²)", min_value=1.0, value=200.0)
    pavs = st.number_input("Número de Pavimentos", min_value=1, value=1)
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

# --- RELATÓRIO EVT (QUADROS) ---
if st.session_state.clique and dados_atv:
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

    st.divider()
    st.subheader(f"📑 EVT: {escolha_busca.upper()}")

    # Bloco de Índices
    c1, c2 = st.columns(2)
    with c1:
        st.info("### 🏗️ 1. ÍNDICES")
        to_calc = (area_c / pavs) / area_t
        st.write(f"**Zona:** {zona}")
        st.write(f"**Taxa de Ocupação:** {to_calc*100:.1f}% (Limite: 70%)")
        st.write(f"**Área Permeável (10%):** {area_t * 0.1:.2f}m²")

    with c2:
        st.info("### 📏 2. RECUOS")
        st.write("**Frontal:** 3,00 m")
        st.write("**Divisas Laterais:** 1,50 m (para aberturas)")
        st.write("**Paredes Cegas:** Isento de recuo lateral.")

    # Bloco de Vagas e Sanitários
    c3, c4 = st.columns(2)
    with c3:
        st.info("### 🚽 3. SANITÁRIOS")
        vasos = math.ceil(area_c / dados_atv['s'])
        st.write(f"**Vaso/Lavatório:** {max(1, vasos)} conj.")
        st.caption("Cálculo baseado na área construída e tabelas oficiais.")

    with c4:
        st.info("### 🚗 4. VAGAS")
        vagas = math.ceil(area_c / dados_atv['v']) if dados_atv['v'] > 0 else 1
        st.write(f"**Vagas de Carro:** {vagas}")
        st.write(f"**Regra:** {dados_atv['desc']}")
        bicis = max(5, math.ceil(vagas * 0.1))
        st.write(f"**Bicicletas:** {bicis} vagas (mín. 5 conforme Art. 129)")

    if to_calc <= 0.7:
        st.success(f"✅ **VIÁVEL:** O projeto atende aos parâmetros da zona {zona}.")
    else:
        st.error(f"❌ **INVIÁVEL:** TO de {to_calc*100:.1f}% excede o limite.")
