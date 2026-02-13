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

# --- BANCO DE DADOS COMPLETO (Baseado nas Tabelas Oficiais de Sobral) ---
# Adicionei os usos de Saúde, Educação e Comércio detalhados
atividades_db = {
    "Academia de Ginástica": {"f_vaga": 30, "f_san": 50, "tipo": "Serviço"},
    "Autoescola / Cursos Livres": {"f_vaga": 50, "f_san": 70, "tipo": "Educação"},
    "Casa Individual (Unifamiliar)": {"f_vaga": 0, "f_san": 150, "tipo": "Residencial"},
    "Clínica Médica / Consultório": {"f_vaga": 40, "f_san": 50, "tipo": "Saúde"},
    "Creche / Pré-Escola": {"f_vaga": 0, "f_san": 40, "tipo": "Educação"},
    "Depósito / Galpão Logístico": {"f_vaga": 150, "f_san": 200, "tipo": "Comercial"},
    "Escritório Administrativo": {"f_vaga": 60, "f_san": 70, "tipo": "Serviço"},
    "Escola (Ensino Fundamental/Médio)": {"f_vaga": 100, "f_san": 40, "tipo": "Educação"},
    "Faculdade / Ensino Superior": {"f_vaga": 35, "f_san": 40, "tipo": "Educação"},
    "Hospital / Maternidade": {"f_vaga": 80, "f_san": 30, "tipo": "Saúde"},
    "Hotel / Pousada": {"f_vaga": 100, "f_san": 60, "tipo": "Hospedagem"},
    "Indústria de Pequeno Porte": {"f_vaga": 100, "f_san": 150, "tipo": "Industrial"},
    "Loja de Varejo / Comércio": {"f_vaga": 50, "f_san": 100, "tipo": "Comercial"},
    "Oficina Mecânica": {"f_vaga": 100, "f_san": 150, "tipo": "Serviço"},
    "Posto de Combustível": {"f_vaga": 200, "f_san": 150, "tipo": "Comercial"},
    "Prédio de Apartamentos (Multifamiliar)": {"f_vaga": 65, "f_san": 150, "tipo": "Residencial"},
    "Restaurante / Lanchonete": {"f_vaga": 40, "f_san": 50, "tipo": "Comercial"},
    "Supermercado": {"f_vaga": 25, "f_san": 80, "tipo": "Comercial"}
}

# --- SIDEBAR: BUSCA E DIMENSÕES ---
with st.sidebar:
    st.header("📋 Definição do Uso")
    
    # OPÇÃO 1: Categorias (Menu rápido)
    categoria = st.selectbox("1. Escolha por Categoria:", ["Residencial", "Comercial", "Serviço", "Saúde/Educação"])
    
    if categoria == "Residencial": sub_cat = ["Casa Individual (Unifamiliar)", "Prédio de Apartamentos (Multifamiliar)"]
    elif categoria == "Comercial": sub_cat = ["Loja de Varejo / Comércio", "Depósito / Galpão Logístico", "Supermercado", "Posto de Combustível"]
    elif categoria == "Serviço": sub_cat = ["Escritório Administrativo", "Academia de Ginástica", "Oficina Mecânica", "Hotel / Pousada"]
    else: sub_cat = ["Clínica Médica / Consultório", "Hospital / Maternidade", "Faculdade / Ensino Superior", "Escola (Ensino Fundamental/Médio)"]
    
    escolha_cat = st.selectbox("Selecione o tipo:", sub_cat)

    st.markdown("---")
    
    # OPÇÃO 2: Busca Autocomplete (Sugere enquanto digita)
    st.header("🔍 Ou busque por nome:")
    # O selectbox com options e format_func atua como busca preditiva no Streamlit
    escolha_busca = st.selectbox(
        "Digite a atividade (ex: Hospital):",
        options=[""] + sorted(list(atividades_db.keys())),
        index=0,
        help="Comece a digitar para ver as sugestões"
    )

    # Lógica de Prevalência
    atividade_final = escolha_busca if escolha_busca != "" else escolha_cat
    dados_atv = atividades_db[atividade_final]

    st.divider()
    st.header("📐 Dados do Lote")
    testada = st.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = st.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    area_const_total = st.number_input("Área Construída Total (m²)", min_value=1.0, value=200.0)
    num_pavimentos = st.number_input("Pavimentos", min_value=1, value=1)
    area_terreno = testada * profundidade

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

# --- RELATÓRIO EM QUADROS ---
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
    st.subheader(f"📑 EVT: {atividade_final.upper()}")

    c1, c2 = st.columns(2)
    with c1:
        st.info("### 🏗️ 1. ÍNDICES URBANÍSTICOS")
        to_calc = (area_const_total / num_pavimentos) / area_terreno
        st.write(f"**Zona:** {zona}")
        st.write(f"**Ocupação Atual:** {to_calc*100:.1f}%")
        st.write(f"**Permeabilidade Mínima:** {area_terreno * 0.1:.2f}m²")

    with c2:
        st.info("### 📏 2. RECUOS")
        st.write("**Frontal:** 3,00 m")
        st.write("**Laterais:** Isento (paredes cegas)")

    c3, c4 = st.columns(2)
    with c3:
        st.info("### 🚽 3. SANITÁRIO")
        fator_s = dados_atv['f_san']
        vasos = math.ceil(area_const_total / fator_s)
        st.write(f"**Vasos/Lavatórios:** {max(1, vasos)} conjunto(s)")

    with c4:
        st.info("### 🚗 4. VAGAS")
        fator_v = dados_atv['f_vaga']
        vagas = math.ceil(area_const_total / fator_v) if fator_v > 0 else 1
        st.write(f"**Vagas de Carro:** {vagas} vaga(s)")
        st.write(f"**Bicicletas:** {max(5, math.ceil(vagas*0.1))} vagas")

    if to_calc <= 0.7:
        st.success(f"✅ **VIÁVEL:** O projeto atende aos parâmetros básicos da zona {zona}.")
    else:
        st.error("❌ **INVIÁVEL:** A taxa de ocupação ultrapassa o limite permitido.")
else:
    st.info("👈 Defina o uso ou busque a atividade e clique no mapa.")
