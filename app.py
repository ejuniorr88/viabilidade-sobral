import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import zipfile
import xml.etree.ElementTree as ET
import math

# 1. Configuração da Página
st.set_page_config(page_title="Consultor de Viabilidade Sobral", layout="wide")
st.markdown("<h1 style='text-align: center;'>Consultor de Projetos</h1>", unsafe_allow_html=True)

# Memória de Sessão
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

# --- BANCO DE DADOS TÉCNICO ---
atividades_db = {
    "Casa Individual (Unifamiliar)": {"v": 1, "s": 150, "zs": ["ZAP", "ZAM", "ZPR", "ZCR", "ZPH"]},
    "Prédio de Apartamentos": {"v": 65, "s": 150, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Comércio / Farmácia / Loja": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Galpão / Depósito": {"v": 150, "s": 200, "zs": ["ZAP", "ZAM", "ZDE", "ZIND"]}
}

# --- SIDEBAR: INTERFACE PARA LEIGOS ---
with st.sidebar:
    st.header("🏠 O que você quer fazer?")
    escolha_uso = st.selectbox("Escolha o tipo de projeto:", sorted(list(atividades_db.keys())))
    
    st.divider()
    st.header("📏 Sobre o seu Terreno")
    testada = st.number_input("Largura da frente (Testada em metros):", value=10.0)
    profundidade = st.number_input("Comprimento lateral (metros):", value=30.0)
    esquina = st.checkbox("Meu lote é de esquina")
    
    st.divider()
    st.header("🏢 Quantos andares você imagina?")
    pavimentos_sugeridos = st.slider("Número de pavimentos:", 1, 10, 1)
    
    area_terreno = testada * profundidade
    dados_atv = atividades_db[escolha_uso]

# --- MAPA ---
st.subheader("📍 Clique no seu lote no mapa:")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite', name='Google Satellite').add_to(m)

if st.session_state.clique:
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

out = st_folium(m, width="100%", height=400)
if out and out.get("last_clicked"):
    novo_clique = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    if novo_clique != st.session_state.clique:
        st.session_state.clique = novo_clique
        st.rerun()

# --- BOTÕES ---
st.markdown("---")
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.button("🔍 CALCULAR MEU POTENCIAL CONSTRUTIVO", use_container_width=True):
        if not st.session_state.clique:
            st.error("📍 Por favor, marque o local no mapa primeiro!")
        else:
            # Busca de Zona
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
            
            # Limites por Zona em Sobral
            lims = {
                "ZAP": {"to": 0.7, "ca": 1.0, "tp": 0.1, "gab": "Sob consulta"},
                "ZAM": {"to": 0.6, "ca": 1.0, "tp": 0.15, "gab": "Até 15m"},
                "ZCR": {"to": 0.8, "ca": 2.0, "tp": 0.05, "gab": "Até 30m"}
            }
            l = lims.get(zona, {"to": 0.6, "ca": 1.0, "tp": 0.15, "gab": "Não definido"})
            
            # CÁLCULOS PARA O LEIGO
            area_max_terreo = area_terreno * l['to']
            area_total_permitida = area_terreno * l['ca']
            area_permeavel = area_terreno * l['tp']
            
            # Distribuição por pavimentos
            if pavimentos_sugeridos > 1:
                area_por_pavimento = min(area_max_terreo, area_total_permitida / pavimentos_sugeridos)
            else:
                area_por_pavimento = area_max_terreo

            st.session_state.relatorio = {
                "uso": escolha_uso, "zona": zona, "area_t": area_terreno,
                "a_max_terreo": area_max_terreo, "a_total": area_total_permitida,
                "a_perm": area_permeavel, "pavs": pavimentos_sugeridos,
                "a_pav": area_por_pavimento, "gab": l['gab'], "esquina": esquina,
                "perm": any(z in zona for z in dados_atv["zs"])
            }

    if st.button("🗑️ LIMPAR", use_container_width=True):
        st.session_state.clique = None
        st.session_state.relatorio = None
        st.rerun()

# --- EXIBIÇÃO DO RELATÓRIO AMIGÁVEL ---
if st.session_state.relatorio:
    r = st.session_state.relatorio
    st.divider()
    st.subheader(f"📊 Resultado da Consultoria: {r['uso']}")
    
    if r['perm']:
        st.success(f"O zoneamento **{r['zona']}** permite este tipo de construção!")
    else:
        st.warning(f"Atenção: O uso **{r['uso']}** pode ter restrições na zona **{r['zona']}**.")

    

    c_box1, c_box2 = st.columns(2)
    with c_box1:
        st.info("### 📐 O que você pode construir")
        st.write(f"**Área máxima no térreo:** {r['a_max_terreo']:.2f} m²")
        st.write(f"**Área construída total permitida:** {r['a_total']:.2f} m²")
        st.write(f"**Gabarito (Altura):** {r['gab']}")
    
    with c_box2:
        st.info("### 🌿 Natureza e Recuos")
        st.write(f"**Área de Jardim (Permeabilidade):** {r['a_perm']:.2f} m²")
        st.write(f"**Recuo Frontal:** {'3,00m e 3,00m (Esquina)' if r['esquina'] else '3,00m'}")
        st.write("**Recuos Laterais:** 1,50m (se houver janelas)")

    # Simulação de Pavimentos
    st.info(f"### 🏢 Simulação para {r['pavs']} Pavimento(s)")
    st.metric("Área por Pavimento", f"{r['a_pav']:.2f} m²")
    st.caption("Nota: Se você aumentar o número de andares, a área de cada andar pode diminuir para respeitar o limite total.")
