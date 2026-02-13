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

# --- BANCO DE DATOS DE ATIVIDADES (SOBRAL - LC 90/91) ---
# Organizado para o sistema de busca inteligente
atividades_db = {
    "Academia de Ginástica": {"fator_vaga": 30, "tipo": "Serviço", "sanit": "M/F + PCD"},
    "Autoescola / Cursos Livres": {"fator_vaga": 50, "tipo": "Educação", "sanit": "1 conj."},
    "Casa Individual (Unifamiliar)": {"fator_vaga": 0, "tipo": "Residencial", "sanit": "1 conj."},
    "Clínica Médica / Consultório": {"fator_vaga": 40, "tipo": "Saúde", "sanit": "1 conj. por 50m²"},
    "Creche / Escola Infantil": {"fator_vaga": 0, "tipo": "Educação", "sanit": "Proporcional"},
    "Depósito / Galpão Logístico": {"fator_vaga": 150, "tipo": "Comercial", "sanit": "Tabela 2"},
    "Escritório Administrativo": {"fator_vaga": 60, "tipo": "Serviço", "sanit": "1 conj. por 70m²"},
    "Faculdade / Ensino Superior": {"fator_vaga": 35, "tipo": "Educação", "sanit": "Proporcional"},
    "Hospital com Internação": {"fator_vaga": 80, "tipo": "Saúde", "sanit": "Normas Anvisa"},
    "Hotel / Pousada": {"fator_vaga": 100, "tipo": "Hospedagem", "sanit": "1 por quarto"},
    "Loja de Varejo / Comércio": {"fator_vaga": 50, "tipo": "Comercial", "sanit": "1 conj. por 100m²"},
    "Oficina Mecânica": {"fator_vaga": 100, "tipo": "Serviço", "sanit": "M/F"},
    "Prédio de Apartamentos (Multifamiliar)": {"fator_vaga": 0, "tipo": "Residencial", "sanit": "1 por unidade"},
    "Restaurante / Lanchonete": {"fator_vaga": 40, "tipo": "Comercial", "sanit": "M/F + PCD"},
    "Supermercado": {"fator_vaga": 25, "tipo": "Comercial", "sanit": "M/F + PCD"}
}

# --- SIDEBAR COM BUSCA INTELIGENTE ---
with st.sidebar:
    st.header("🔍 O que deseja construir?")
    
    # O st.selectbox já funciona como busca conforme digita (Autocomplete)
    escolha = st.selectbox(
        "Digite ou selecione a atividade:",
        options=[""] + sorted(list(atividades_db.keys())),
        format_func=lambda x: "🔎 Buscar atividade..." if x == "" else x
    )
    
    if escolha == "":
        st.info("Aguardando seleção de atividade...")
        dados_atv = None
    else:
        dados_atv = atividades_db[escolha]
        st.success(f"Atividade: {dados_atv['tipo']}")

    st.divider()
    st.header("📐 Dimensões")
    col1, col2 = st.columns(2)
    testada = col1.number_input("Testada (m)", min_value=1.0, value=10.0)
    profundidade = col2.number_input("Profundidade (m)", min_value=1.0, value=30.0)
    
    area_terreno = testada * profundidade
    area_const_total = st.number_input("Área Construída Total (m²)", min_value=1.0, value=200.0)
    num_pavimentos = st.number_input("Pavimentos", min_value=1, value=1)

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
if st.session_state.clique and escolha != "":
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

    # Parâmetros Reais extraídos das Leis 90/91
    regras_zonas = {
        "ZAP": {"TO": 0.70, "CA": 1.0, "TP": 0.10},
        "ZAM": {"TO": 0.60, "CA": 1.0, "TP": 0.15},
        "ZCR": {"TO": 0.80, "CA": 1.0, "TP": 0.05}
    }
    r = regras_zonas.get(zona, {"TO": 0.60, "CA": 1.0, "TP": 0.15})

    st.divider()
    st.subheader(f"📑 ESTUDO DE VIABILIDADE TÉCNICA - {escolha.upper()}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Índices", "📏 Recuos", "🚽 Sanitário", "🚗 Vagas"])
    
    with tab1:
        to_calc = (area_const_total / num_pavimentos) / area_terreno
        st.write(f"**Zona:** {zona}")
        st.metric("Taxa de Ocupação", f"{to_calc*100:.1f}%", f"Limite: {r['TO']*100}%")
        st.write(f"**Área de Permeabilidade Mínima (TP):** {area_terreno * r['TP']:.2f}m²")

    with tab2:
        st.write("**Recuos (LC 90 Art. 107):**")
        st.write("- **Frontal:** 3,00m")
        st.write("- **Laterais:** Isento para paredes cegas.")

    with tab3:
        st.write(f"**Exigência:** {dados_atv['sanit']}")
        if area_const_total > 150:
            st.warning("Obrigatório sanitário acessível (PCD) e separação por sexo.")

    with tab4:
        # Cálculo de Vagas de Automóvel (LC 90 Anexo IV)
        if dados_atv['fator_vaga'] > 0:
            vagas = math.ceil(area_const_total / dados_atv['fator_vaga'])
        else:
            vagas = 1 # Mínimo para unifamiliar
        
        st.write(f"**Vagas de Automóveis:** {vagas} vaga(s)")
        # Regra de Bicicletas (Art. 129 LC 90)
        bicis = max(5, math.ceil(vagas * 0.1))
        st.write(f"- **Vagas de Bicicletas:** {bicis} (Mínimo de 5 ou 10% das de carro)")

    st.markdown("---")
    if to_calc <= r['TO']:
        st.success("✅ PROJETO VIÁVEL")
    else:
        st.error(f"❌ INVIÁVEL (Excede a TO de {r['TO']*100}%)")

elif st.session_state.clique and escolha == "":
    st.error("⚠️ Atividade não encontrada. Por favor, selecione uma opção válida na busca lateral.")
