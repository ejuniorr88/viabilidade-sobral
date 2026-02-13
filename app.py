import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# 1. Configuração da Página
st.set_page_config(page_title="Viabilidade Sobral", layout="wide")
st.markdown("<h1 style='text-align: center;'>Viabilidade Urbana</h1>", unsafe_allow_html=True)

if 'clique' not in st.session_state: st.session_state.clique = None
if 'relatorio' not in st.session_state: st.session_state.relatorio = None

@st.cache_data
def carregar_dados_kmz():
    try:
        with zipfile.ZipFile('Zoneamento Urbano da Sede.kmz', 'r') as z:
            kml_name = [f for f in z.namelist() if f.endswith('.kml')][0]
            with z.open(kml_name) as f: return ET.fromstring(f.read())
    except: return None

root = carregar_dados_kmz()

# --- BANCO DE DADOS ATUALIZADO ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "zs": ["ZAP", "ZAM", "ZPR", "ZCR", "ZPH"]},
    "Prédio de Apartamentos (Multifamiliar)": {"v": 65, "s": 150, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Loja / Comércio Varejista": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Farmácia": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Depósito / Galpão": {"v": 150, "s": 200, "zs": ["ZAP", "ZAM", "ZDE", "ZIND"]},
    "Escola - Educação Infantil": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escola - Ensino Fundamental": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escola - Ensino Médio": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escola - Ensino Superior / Faculdade": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escritório / Prestação de Serviço": {"v": 60, "s": 70, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]}
}

# --- SIDEBAR: ESTRUTURA FIXA ---
with st.sidebar:
    st.header("📋 1. Escolha o Uso")
    cat = st.selectbox("Selecione por Categoria:", ["Residencial", "Comercial", "Serviço", "Saúde/Educação"])
    subs = {
        "Residencial": ["Casa Individual (Unifamiliar)", "Prédio de Apartamentos (Multifamiliar)"],
        "Comercial": ["Loja / Comércio Varejista", "Farmácia", "Depósito / Galpão"],
        "Serviço": ["Escritório / Prestação de Serviço"],
        "Saúde/Educação": ["Escola - Educação Infantil", "Escola - Ensino Fundamental", "Escola - Ensino Médio", "Escola - Ensino Superior / Faculdade"]
    }
    escolha_cat = st.selectbox("Opções na categoria:", subs[cat])
    
    st.markdown("---")
    st.header("🔍 2. Busca Direta")
    escolha_busca = st.selectbox("Ou digite para pesquisar:", [""] + sorted(list(atividades_db.keys())))
    
    atv_final = escolha_busca if escolha_busca != "" else escolha_cat
    dados_atv = atividades_db[atv_final]
    
    st.divider()
    st.header("📐 3. Dimensões do Lote")
    testada = st.number_input("Testada / Frente (m):", value=10.0)
    profundidade = st.number_input("Profundidade (m):", value=30.0)
    esquina = st.checkbox("Lote de Esquina")
    pavs_input = st.slider("Simulação de Pavimentos:", 1, 15, 1)
    area_terreno = testada * profundidade

# --- MAPA ---
st.subheader("📍 Selecione o lote no mapa:")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite', name='Google Satellite').add_to(m)
if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red")).add_to(m)

out = st_folium(m, width="100%", height=400)
if out and out.get("last_clicked"):
    novo = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    if novo != st.session_state.clique:
        st.session_state.clique = novo
        st.rerun()

# --- BOTÕES ---
st.markdown("---")
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.button("🚀 GERAR ESTUDO DE VIABILIDADE", use_container_width=True):
        if not st.session_state.clique: st.error("📍 Clique no mapa!")
        else:
            ponto = Point(st.session_state.clique[1], st.session_state.clique[0])
            zona = "Desconhecida"
            if root is not None:
                for pm in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
                    poly = pm.find('.//{http://www.opengis.net/kml/2.2}Polygon')
                    if poly is not None:
                        c_txt = poly.find('.//{http://www.opengis.net/kml/2.2}coordinates').text.strip().split()
                        coords = [tuple(map(float, c.split(',')[:2])) for c in c_txt]
                        if Polygon(coords).contains(ponto):
                            zona = pm.find('{http://www.opengis.net/kml/2.2}name').text
                            break
            
            # Limites por Zona (Conforme LC 91)
            lims = {
                "ZAP": {"to": 0.7, "ca": 1.0, "tp": 0.1, "gab": 12},
                "ZAM": {"to": 0.6, "ca": 1.0, "tp": 0.15, "gab": 15},
                "ZCR": {"to": 0.8, "ca": 2.5, "tp": 0.05, "gab": 45}
            }
            l = lims.get(zona, {"to": 0.6, "ca": 1.0, "tp": 0.15, "gab": 10})
            
            a_max_t = area_terreno * l['to']
            a_total_p = area_terreno * l['ca']
            
            # Recomendação de Pavimentos (Potencial Construtivo / Área máxima de projeção)
            pavs_recomendados = math.floor(l['ca'] / l['to']) if l['to'] > 0 else 1

            st.session_state.relatorio = {
                "atv": atv_final, "zona": zona, "a_t": area_terreno, "a_max_t": a_max_t,
                "a_total": a_total_p, "a_pav": min(a_max_t, a_total_p/pavs_input), 
                "pavs_in": pavs_input, "pavs_rec": pavs_recomendados, "esquina": esquina,
                "tp": area_terreno * l['tp'], "perm": any(z in zona for z in dados_atv["zs"]),
                "dados": dados_atv, "gab": l['gab']
            }

    if st.button("🗑️ LIMPAR TUDO", use_container_width=True):
        st.session_state.clique, st.session_state.relatorio = None, None
        st.rerun()

# --- RESULTADO EM 4 QUADROS ---
if st.session_state.relatorio:
    r = st.session_state.relatorio
    st.divider()
    st.subheader(f"📑 ESTUDO DE VIABILIDADE: {r['atv'].upper()}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("### 🏗️ ÍNDICES E POTENCIAL")
        st.write(f"**Área Máx. Térreo:** {r['a_max_t']:.2f} m²")
        st.write(f"**Potencial Construtivo (CA 1.0):** {r['a_total']:.2f} m²")
        st.write(f"**Gabarito Máximo:** {r['gab']} metros")
        st.write(f"**Área Permeável:** {r['tp']:.2f} m²")
    with col2:
        st.info("### 📏 RECUOS (AFASTAMENTOS)")
        f = "3,00m (Frente e Lateral Esquina)" if r['esquina'] else "3,00m (Frente)"
        st.write(f"**Frontal:** {f}")
        st.write("**Lateral:** 1,50m (c/ aberturas)")
        st.write("**Fundos:** 1,50m (c/ aberturas)")

    

    col3, col4 = st.columns(2)
    with col3:
        st.info("### 🚽 VAGAS E SANITÁRIO")
        v = max(1, math.ceil(r['a_total']/r['dados']['v']))
        st.write(f"**Vagas Estimadas:** {v}")
        st.write(f"**Sanitários Mínimos:** {max(1, math.ceil(r['a_total']/r['dados']['s']))}")
    with col4:
        st.info(f"### 🏢 RECOMENDAÇÃO TÉCNICA")
        st.metric("Sugestão de Pavimentos", f"{r['pavs_rec']} andares")
        st.write(f"Simulação atual ({r['pavs_in']} pav.): **{r['a_pav']:.2f} m²** por andar.")
