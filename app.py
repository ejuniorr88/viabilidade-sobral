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
    except Exception: return None

root = carregar_dados_kmz()

# --- BANCO DE DADOS TÉCNICO (SOBRAL LC 90/91) ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "cat": "R1", "zonas_permitidas": ["ZAP", "ZAM", "ZPR", "ZCR", "ZPH"]},
    "Prédio (Multifamiliar)": {"v": 65, "s": 150, "cat": "R3", "zonas_permitidas": ["ZAP", "ZAM", "ZCR"]},
    "Farmácia": {"v": 50, "s": 100, "cat": "C1", "zonas_permitidas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Depósito / Galpão": {"v": 150, "s": 200, "cat": "S3", "zonas_permitidas": ["ZAP", "ZAM", "ZDE", "ZIND"]},
    "Supermercado": {"v": 25, "s": 80, "cat": "C2", "zonas_permitidas": ["ZAP", "ZAM", "ZCR"]},
    "Clínica Médica": {"v": 40, "s": 50, "cat": "S2", "zonas_permitidas": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Escritório": {"v": 60, "s": 70, "cat": "S1", "zonas_permitidas": ["ZAP", "ZAM", "ZCR", "ZPR"]}
}

with st.sidebar:
    st.header("📋 Configuração do Estudo")
    busca = st.selectbox("Escolha ou digite a Atividade:", options=[""] + sorted(list(atividades_db.keys())))
    
    st.divider()
    testada = st.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = st.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    area_c = st.number_input("Área Construída Total (m²)", min_value=1.0, value=210.0)
    pavs = st.number_input("Pavimentos", min_value=1, value=1)
    area_t = testada * profundidade
    st.info(f"Área do Terreno: {area_t} m²")

# --- MAPA ---
st.subheader("\"lote\"")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite', name='Google Satellite').add_to(m)

if 'clique' not in st.session_state: st.session_state.clique = None
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red", icon="home")).add_to(m)

out = st_folium(m, width="100%", height=400)
if out and out.get("last_clicked"):
    st.session_state.clique = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    st.rerun()

st.markdown("---")
if st.button("🚀 GERAR ESTUDO DE VIABILIDADE", use_container_width=True):
    if not st.session_state.clique or busca == "":
        st.error("⚠️ Selecione a atividade na lateral e clique em um lote no mapa.")
    else:
        # Identificação da Zona
        ponto = Point(st.session_state.clique[1], st.session_state.clique[0])
        zona_clicada = "Desconhecida"
        if root is not None:
            namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
            for pm in root.findall('.//kml:Placemark', namespaces):
                poly = pm.find('.//kml:Polygon', namespaces)
                if poly is not None:
                    coords_text = poly.find('.//kml:coordinates', namespaces).text.strip().split()
                    coords = [tuple(map(float, c.split(',')[:2])) for c in coords_text]
                    if Polygon(coords).contains(ponto):
                        zona_clicada = pm.find('kml:name', namespaces).text
                        break

        dados = atividades_db[busca]
        
        # --- CÁLCULOS ---
        to_calc = (area_c / pavs) / area_t
        ca_calc = area_c / area_t
        
        # Parâmetros da Zona (Exemplo Sobral)
        limites = {"ZAP": {"TO": 0.7, "CA": 1.0}, "ZAM": {"TO": 0.6, "CA": 1.0}, "ZCR": {"TO": 0.8, "CA": 1.0}}
        lim = limites.get(zona_clicada, {"TO": 0.6, "CA": 1.0})

        st.subheader(f"📑 ESTUDO DE VIABILIDADE: {busca.upper()}")
        
        # 1. Admissibilidade
        permitido = any(z in zona_clicada for z in dados["zonas_permitidas"])
        if permitido:
            st.success(f"✔️ O uso **{busca}** é PERMITIDO na zona **{zona_clicada}**.")
        else:
            st.error(f"❌ O uso **{busca}** NÃO é previsto para a zona **{zona_clicada}**.")

        # 2. Quadros de Índices
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("### 🏗️ ÍNDICES URBANÍSTICOS")
            st.write(f"**Taxa de Ocupação:** {to_calc*100:.1f}%")
            if to_calc <= lim["TO"]: st.write("✅ Dentro do limite (70%)")
            else: st.write(f"⚠️ **ULTRAPASSOU O LIMITE** ({lim['TO']*100}%)")
            
            st.write(f"**C.A. Básico:** {ca_calc:.2f}")
            if ca_calc <= lim["CA"]: st.write("✅ Dentro do limite (1.0)")
            else: st.write("⚠️ **EXCEDE C.A. BÁSICO** (Requer Outorga Onerosa)")

        with c2:
            st.info("### 📏 AFASTAMENTOS")
            st.write("**Frontal:** 3,00m")
            st.write("**Lateral:** 1,50m (com aberturas)")
            st.write("**Fundos:** 1,50m")

        c3, c4 = st.columns(2)
        with c3:
            st.info("### 🚽 SANITÁRIO")
            vasos = math.ceil(area_c / dados['s'])
            st.write(f"**Necessário:** {max(1, vasos)} conjunto(s)")

        with c4:
            st.info("### 🚗 VAGAS")
            vagas = math.ceil(area_c / dados['v']) if dados['v'] > 0 else 1
            st.write(f"**Vagas Carro:** {vagas} vaga(s)")
            st.write(f"**Bicicletas:** {max(5, math.ceil(vagas*0.1))} vagas")

        st.divider()
        # CONCLUSÃO FINAL
        if permitido and to_calc <= lim["TO"]:
            st.success("🏁 **CONCLUSÃO: PROJETO VIÁVEL.** Atende aos índices e ao zoneamento.")
        else:
            st.error("🏁 **CONCLUSÃO: PROJETO INVIÁVEL.** Verifique os erros acima.")
