import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# 1. Configuração da Página (Sempre no topo)
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

# --- BANCO DE DADOS COMPLETO (SOBRAL LC 90/91) ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 0, "s": 150, "t": "Residencial"},
    "Prédio (Multifamiliar)": {"v": 65, "s": 150, "t": "Residencial"},
    "Loja / Comércio": {"v": 50, "s": 100, "t": "Comercial"},
    "Farmácia": {"v": 50, "s": 100, "t": "Comercial"},
    "Depósito / Galpão": {"v": 150, "s": 200, "t": "Comercial"},
    "Supermercado": {"v": 25, "s": 80, "t": "Comercial"},
    "Restaurante": {"v": 40, "s": 50, "t": "Comercial"},
    "Escritório": {"v": 60, "s": 70, "t": "Serviço"},
    "Academia de Ginástica": {"v": 30, "s": 50, "t": "Serviço"},
    "Oficina Mecânica": {"v": 100, "s": 150, "t": "Serviço"},
    "Clínica Médica": {"v": 40, "s": 50, "t": "Saúde"},
    "Hospital / Maternidade": {"v": 80, "s": 30, "t": "Saúde"},
    "Faculdade / Superior": {"v": 35, "s": 40, "t": "Educação"},
    "Escola (Fund./Médio)": {"v": 100, "s": 40, "t": "Educação"},
    "Hospedagem (Hotel/Pousada)": {"v": 100, "s": 60, "t": "Hospedagem"}
}

# --- SIDEBAR: OS DOIS CAMPOS INDEPENDENTES ---
with st.sidebar:
    st.header("📋 1. Escolha Pré-definida")
    cat = st.selectbox("Selecione a Categoria:", ["Residencial", "Comercial", "Serviço", "Saúde/Educação"])
    
    if cat == "Residencial": sub = ["Casa Individual (Unifamiliar)", "Prédio (Multifamiliar)"]
    elif cat == "Comercial": sub = ["Loja / Comércio", "Farmácia", "Depósito / Galpão", "Supermercado", "Restaurante"]
    elif cat == "Serviço": sub = ["Escritório", "Academia de Ginástica", "Oficina Mecânica"]
    else: sub = ["Clínica Médica", "Hospital / Maternidade", "Faculdade / Superior", "Escola (Fund./Médio)"]
    
    escolha_quadro = st.selectbox("Tipo de uso (Quadro):", sub)

    st.markdown("---")
    
    st.header("🔍 2. Busca por Digitação")
    escolha_busca = st.selectbox(
        "Digite para filtrar:",
        options=[""] + sorted(list(atividades_db.keys())),
        index=0,
        help="Use este campo para buscar qualquer item da tabela rapidamente."
    )

    # Lógica de Independência: Se a busca estiver vazia, usa o quadro. Se algo for digitado, a busca manda.
    atv_final = escolha_busca if escolha_busca != "" else escolha_quadro
    dados = atividades_db[atv_final]

    st.divider()
    st.header("📐 Dimensões do Lote")
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

# --- RELATÓRIO EVT (QUADROS LIMPOS) ---
if st.session_state.clique:
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

    st.divider()
    st.subheader(f"📑 EVT: {atv_final.upper()}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.info("### 🏗️ 1. ÍNDICES")
        to_calc = (area_c / pavs) / area_t
        st.write(f"**Zona:** {zona}")
        st.write(f"**Ocupação:** {to_calc*100:.1f}% (Máx: 70%)")
        st.write(f"**Área Permeável (10%):** {area_t * 0.1:.2f}m²")

    with col_b:
        st.info("### 📏 2. RECUOS")
        st.write("**Frontal:** 3,00 m")
        st.write("**Laterais:** Isento (paredes cegas) / 1,50m (aberturas)")

    col_c, col_d = st.columns(2)
    with col_c:
        st.info("### 🚽 3. SANITÁRIO")
        vasos = math.ceil(area_c / dados['s'])
        st.write(f"**Vasos/Lavatórios:** {max(1, vasos)} conj.")

    with col_d:
        st.info("### 🚗 4. VAGAS")
        vagas = math.ceil(area_c / dados['v']) if dados['v'] > 0 else 1
        st.write(f"**Vagas Carro:** {vagas} vaga(s)")
        st.write(f"**Bicicletas:** {max(5, math.ceil(vagas*0.1))} vagas")

    if to_calc <= 0.7:
        st.success(f"✅ **VIÁVEL:** O projeto atende aos parâmetros da zona {zona}.")
    else:
        st.error("❌ **INVIÁVEL:** A taxa de ocupação ultrapassa o limite permitido.")
else:
    st.info("👈 Use os campos na lateral e clique no lote no mapa.")
