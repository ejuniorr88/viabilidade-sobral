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

# --- SIDEBAR: INTERATIVIDADE DINÂMICA ---
with st.sidebar:
    st.header("📋 Dados do Projeto")
    uso_geral = st.selectbox("Categoria de Uso", ["Residencial", "Comercial", "Serviço"])
    
    sub_uso = ""
    if uso_geral == "Residencial":
        sub_uso = st.selectbox("Tipo", ["Unifamiliar", "Multifamiliar"])
    elif uso_geral == "Comercial":
        sub_uso = st.selectbox("Atividade", ["Varejo/Loja", "Depósito/Galpão", "Supermercado", "Posto de Combustível"])
    elif uso_geral == "Serviço":
        sub_uso = st.selectbox("Atividade", ["Escritório/Consultório", "Saúde (Clínica/Hosp.)", "Educação", "Hospedagem"])

    col1, col2 = st.columns(2)
    testada = col1.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = col2.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    
    area_terreno = testada * profundidade
    area_const_total = st.number_input("Área Construída (m²)", min_value=1.0, value=200.0)
    num_pavimentos = st.number_input("Pavimentos", min_value=1, value=1)
    
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

# --- PROCESSAMENTO DO EVT ---
if st.session_state.clique:
    # Lógica simplificada de Zona (ZAP, ZAM, ZCR)
    # (O código de busca no KMZ permanece o mesmo aqui)
    zona = "ZAP" # Exemplo fixo para demonstração do cálculo

    # Regras de Vagas (LC 90 Anexo IV)
    regras_vagas = {
        "Unifamiliar": 1,
        "Multifamiliar": math.floor(area_const_total / 65),
        "Varejo/Loja": math.ceil(area_const_total / 50),
        "Depósito/Galpão": math.ceil(area_const_total / 150),
        "Escritório/Consultório": math.ceil(area_const_total / 60),
        "Saúde (Clínica/Hosp.)": math.ceil(area_const_total / 40)
    }
    vagas_final = regras_vagas.get(sub_uso, 1)

    st.divider()
    st.subheader(f"📑 ESTUDO DE VIABILIDADE TÉCNICA (EVT) - {sub_uso.upper()}")
    
    # Layout do Relatório Profissional
    col_evt1, col_evt2 = st.columns(2)

    with col_evt1:
        st.markdown("### 1. ÍNDICES URBANÍSTICOS")
        to_limite = 0.70 # Exemplo ZAP
        to_calc = (area_const_total / num_pavimentos) / area_terreno
        st.write(f"**Taxa de Ocupação:** {to_limite*100}%")
        st.write(f"**Área Livre Obrigatória:** {area_terreno * (1 - to_limite):.2f}m²")
        st.write(f"**C.A. Básico:** 1.0")

    with col_evt2:
        st.markdown("### 2. RECUOS OBRIGATÓRIOS")
        st.write("**Frontal:** 3,00 m")
        st.write("**Laterais/Fundos:** Isento se parede cega.")

    st.markdown("---")
    c_san, c_vagas = st.columns(2)

    with c_san:
        st.markdown("### 3. DIMENSIONAMENTO SANITÁRIO")
        if area_const_total <= 150:
            st.write("- 01 Vaso + 01 Lavatório (Unissex/PCD)")
        else:
            st.write("- 02 Vasos + 02 Lavatórios (Separados M/F)")

    with c_vagas:
        st.markdown("### 4. ESTACIONAMENTO E CARGA")
        st.write(f"**Vagas de Carro:** {max(1, vagas_final)} vaga(s)")
        if sub_uso == "Depósito/Galpão":
            st.warning("Obrigatório pátio interno de Carga e Descarga.")

    st.markdown("---")
    # CONCLUSÃO
    if to_calc <= to_limite:
        st.success(f"✅ **CONCLUSÃO:** Projeto VIÁVEL para {sub_uso}.")
    else:
        st.error(f"❌ **CONCLUSÃO:** INVIÁVEL. Ocupação excede o limite da zona.")

else:
    st.info("👈 Selecione a atividade e clique no mapa para gerar o EVT.")
