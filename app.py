import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# 1. Configuração da Página
st.set_page_config(page_title="Viabilidade Sobral", layout="wide")
st.markdown("<h1 style='text-align: center;'>Viabilidade</h1>", unsafe_allow_html=True)

@st.cache_data
def carregar_dados_kmz():
    try:
        with zipfile.ZipFile('Zoneamento Urbano da Sede.kmz', 'r') as z:
            kml_name = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_name) as f: return ET.fromstring(f.read())
    except: return None

root = carregar_dados_kmz()

# --- BANCO DE DADOS TÉCNICO ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "zonas": ["ZAP", "ZAM", "ZPR", "ZCR", "ZPH"]},
    "Prédio (Multifamiliar)": {"v": 65, "s": 150, "zonas": ["ZAP", "ZAM", "ZCR"]},
    "Loja / Comércio": {"v": 50, "s": 100, "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Farmácia": {"v": 50, "s": 100, "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Depósito / Galpão": {"v": 150, "s": 200, "zonas": ["ZAP", "ZAM", "ZDE", "ZIND"]},
    "Supermercado": {"v": 25, "s": 80, "zonas": ["ZAP", "ZAM", "ZCR"]},
    "Clínica Médica": {"v": 40, "s": 50, "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Hospital / Maternidade": {"v": 80, "s": 30, "zonas": ["ZAP", "ZAM", "ZCR"]},
    "Escritório": {"v": 60, "s": 70, "zonas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Faculdade / Superior": {"v": 35, "s": 40, "zonas": ["ZAP", "ZAM", "ZCR"]}
}

# --- SIDEBAR: ESTRUTURA FIXA ---
with st.sidebar:
    st.header("📋 1. Escolha por Categoria")
    cat = st.selectbox("Categoria:", ["Residencial", "Comercial", "Saúde/Educação"])
    
    # Mapeamento simples para evitar erros de sintaxe em linhas longas
    subs = {
        "Residencial": ["Casa Individual (Unifamiliar)", "Prédio (Multifamiliar)"],
        "Comercial": ["Loja / Comércio", "Farmácia", "Depósito / Galpão", "Supermercado"],
        "Saúde/Educação": ["Clínica Médica", "Hospital / Maternidade", "Faculdade / Superior"]
    }
    escolha_quadro = st.selectbox("Tipo de uso (Menu):", subs[cat])

    st.markdown("---")
    st.header("🔍 2. Busca por Digitação")
    escolha_busca = st.selectbox("Ou digite o uso:", [""] + sorted(list(atividades_db.keys())))

    atv_final = escolha_busca if escolha_busca != "" else escolha_quadro
    dados_atv = atividades_db[atv_final]

    st.divider()
    st.header("📐 3. Dimensões")
    testada = st.number_input("Testada (m)", value=10.0)
    profundidade = st.number_input("Profundidade (m)", value=30.0)
    area_c = st.number_input("Área Construída (m²)", value=200.0)
    pavs = st.number_input("Pavimentos", min_value=1, value=1)
    area_t = testada * profundidade

# --- MAPA ---
st.subheader("\"lote\"")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite', name='Google Satellite').add_to(m)

if 'clique' not in st.session_state: st.session_state.clique = None
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red")).add_to(m)

out = st_folium(m, width="100%", height=400)
if out and out.get("last_clicked"):
    st.session_state.clique = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    st.rerun()

# --- BOTÕES ---
st.markdown("---")
c_btn1, c_btn2, c_btn3 = st.columns([1, 2, 1])
with c_btn2:
    if st.button("🚀 GERAR ESTUDO DE VIABILIDADE", use_container_width=True):
        if not st.session_state.clique: st.error("📍 Clique no mapa!")
        else:
            ponto = Point(st.session_state.clique[1], st.session_state.clique[0])
            zona = "Desconhecida"
            if root is not None:
                for pm in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
                    poly = pm.find('.//{http://www.opengis.net/kml/2.2}Polygon')
                    if poly is not None:
                        coords_text = poly.find('.//{http://www.opengis.net/kml/2.2}coordinates').text.strip().split()
                        coords = [tuple(map(float, c.split(',')[:2])) for c in coords_text]
                        if Polygon(coords).contains(ponto):
                            zona = pm.find('{http://www.opengis.net/kml/2.2}name').text
                            break

            to_calc = (area_c / pavs) / area_t
            limites = {"ZAP": 0.7, "ZAM": 0.6, "ZCR": 0.8}
            lim_to = limites.get(zona, 0.6)
            permitido = any(z in zona for z in dados_atv["zonas"])

            st.divider()
            st.subheader(f"📑 ESTUDO DE VIABILIDADE: {atv_final.upper()}")
            
            if permitido: st.success(f"✔️ PERMITIDO na zona {zona}.")
            else: st.error(f"❌ NÃO PREVISTO na zona {zona}.")

            

            col1, col2 = st.columns(2)
            with col1:
                st.info("### 🏗️ ÍNDICES")
                st.write(f"**TO:** {to_calc*100:.1f}%")
                st.write(f"**Status:** {'✅ OK' if to_calc <= lim_to else '⚠️ EXCEDE'}")
            with col2:
                st.info("### 📏 RECUOS")
                st.write("**Frontal:** 3m | **Lateral/Fundo:** 1,5m")
            
            col3, col4 = st.columns(2)
            with col3:
                st.info("### 🚽 SANITÁRIO")
                st.write(f"**Mínimo:** {max(1, math.ceil(area_c/dados_atv['s']))} conj.")
            with col4:
                st.info("### 🚗 VAGAS")
                v = max(1, math.ceil(area_c/dados_atv['v']))
                st.write(f"**Carros:** {v} | **Bicicletas:** {max(5, math.ceil(v*0.1))}")

    if st.button("🗑️ LIMPAR PESQUISA", use_container_width=True):
        st.session_state.clique = None
        st.rerun()
