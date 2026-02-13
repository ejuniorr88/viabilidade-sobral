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

# Inicialização da Memória (Previne erros de chave inexistente)
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
db = {
    "Casa Individual": {"v": 1, "s": 150, "zs": ["ZAP", "ZAM", "ZPR", "ZCR", "ZPH"]},
    "Prédio Multifamiliar": {"v": 65, "s": 150, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Loja / Comércio": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Farmácia": {"v": 50, "s": 100, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]},
    "Depósito / Galpão": {"v": 150, "s": 200, "zs": ["ZAP", "ZAM", "ZDE", "ZIND"]},
    "Escola Infantil": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escola Fundamental": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escola Médio": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escola Superior": {"v": 35, "s": 40, "zs": ["ZAP", "ZAM", "ZCR"]},
    "Escritório / Serviço": {"v": 60, "s": 70, "zs": ["ZAP", "ZAM", "ZCR", "ZPR"]}
}

# --- SIDEBAR: ESTRUTURA FIXA (CATEGORIA -> BUSCA -> DADOS) ---
with st.sidebar:
    st.header("📋 1. Escolha o Uso")
    cat = st.selectbox("Categoria:", ["Residencial", "Comercial", "Serviço", "Saúde/Educação"])
    subs = {
        "Residencial": ["Casa Individual", "Prédio Multifamiliar"],
        "Comercial": ["Loja / Comércio", "Farmácia", "Depósito / Galpão"],
        "Serviço": ["Escritório / Serviço"],
        "Saúde/Educação": ["Escola Infantil", "Escola Fundamental", "Escola Médio", "Escola Superior"]
    }
    sel_cat = st.selectbox("Opções:", subs[cat])
    
    st.markdown("---")
    st.header("🔍 2. Busca Direta")
    sel_busca = st.selectbox("Ou digite:", [""] + sorted(list(db.keys())))
    
    # Define o uso final priorizando a busca direta
    final_atv = sel_busca if sel_busca != "" else sel_cat
    dados = db[final_atv]
    
    st.divider()
    st.header("📐 3. Dados do Lote")
    t = st.number_input("Testada (m):", value=10.0)
    p = st.number_input("Profundidade (m):", value=30.0)
    esq = st.checkbox("Lote de Esquina")
    area_p = st.number_input("Área Construída (m²):", value=0.0)
    pavs = st.slider("Pavimentos Planejados:", 1, 20, 1)
    area_t = t * p

# --- MAPA ---
st.subheader("📍 Selecione o lote no mapa:")
m = folium.Map(location=[-3.6890, -40.3480], zoom_start=15)
folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite', name='GS').add_to(m)
if st.session_state.clique: 
    folium.Marker(st.session_state.clique, icon=folium.Icon(color="red")).add_to(m)

out = st_folium(m, width="100%", height=400)
if out and out.get("last_clicked"):
    st.session_state.clique = [out["last_clicked"]["lat"], out["last_clicked"]["lng"]]
    st.rerun()

# --- BOTÕES ---
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 GERAR ESTUDO DE VIABILIDADE", use_container_width=True):
        if not st.session_state.clique: st.error("📍 Clique no mapa!")
        else:
            pt = Point(st.session_state.clique[1], st.session_state.clique[0])
            zona = "Desconhecida"
            if root is not None:
                for pm in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
                    poly = pm.find('.//{http://www.opengis.net/kml/2.2}Polygon')
                    if poly is not None:
                        c_txt = poly.find('.//{http://www.opengis.net/kml/2.2}coordinates').text.strip().split()
                        coords = [tuple(map(float, c.split(',')[:2])) for c in c_txt]
                        if Polygon(coords).contains(pt):
                            zona = pm.find('{http://www.opengis.net/kml/2.2}name').text
                            break
            
            # Limites Sobral (LC 91)
            lims = {"ZAP":{"to":0.7,"ca":1.0,"tp":0.1,"gb":12},"ZAM":{"to":0.6,"ca":1.0,"tp":0.15,"gb":15},"ZCR":{"to":0.8,"ca":2.5,"tp":0.05,"gb":45}}
            l = lims.get(zona, {"to":0.6,"ca":1.0,"tp":0.15,"gb":10})
            
            pot = area_t * l['ca']
            a_estudo = pot if area_p <= 0 else area_p
            modo_txt = "POTENCIAL MÁXIMO" if area_p <= 0 else "ÁREA PRETENDIDA"
            
            st.session_state.relatorio = {
                "atv": final_atv, "zona": zona, "a_t": area_t, "a_max_t": area_t*l['to'],
                "pot": pot, "a_f": a_estudo, "pavs": pavs, "esq": esq, "modo": modo_txt,
                "tp": area_t*l['tp'], "perm": any(z in zona for z in dados["zs"]),
                "dados": dados, "gb": l['gb']
            }

    if st.button("🗑️ LIMPAR TUDO", use_container_width=True):
        st.session_state.clique = None
        st.session_state.relatorio = None
        st.rerun()

# --- RESULTADO EM 4 QUADROS ---
if st.session_state.relatorio:
    r = st.session_state.relatorio
    st.divider()
    
    # Verificação de segurança para evitar KeyError
    titulo_modo = r.get('modo', 'ESTUDO')
    st.subheader(f"📑 VIABILIDADE ({titulo_modo}): {r['atv'].upper()}")
    
    if r['perm']: st.success(f"✔️ Uso permitido na zona {r['zona']}")
    else: st.error(f"❌ Não previsto na zona {r['zona']}")

    q1, q2 = st.columns(2)
    with q1:
        st.info("### 🏗️ POTENCIAL")
        st.write(f"**Área Máx. Permitida:** {r['pot']:.2f} m²")
        st.write(f"**Área do Estudo:** {r['a_f']:.2f} m²")
        st.write(f"**Ocupação Térreo Máx:** {r['a_max_t']:.2f} m²")
    with q2:
        st.info("### 📏 RECUOS E GABARITO")
        f_rec = "3,00m (Frente/Esq)" if r['esq'] else "3,00m (Frente)"
        st.write(f"**Frontal:** {f_rec}")
        st.write("**Lateral / Fundos:** 1,50m")
        st.write(f"**Gabarito Máx (Altura):** {r['gb']} metros")

    

    q3, q4 = st.columns(2)
    with q3:
        st.info("### 🚽 VAGAS E SANITÁRIO")
        v = max(1, math.ceil(r['a_f']/r['dados']['v']))
        st.write(f"**Vagas Est.:** {v}")
        st.write(f"**Sanitários Mín.:** {max(1, math.ceil(r['a_f']/r['dados']['s']))}")
    with q4:
        st.info("### 🏢 PAVIMENTOS")
        rec_pav = math.floor(r['pot']/(r['a_max_t'] if r['a_max_t']>0 else 1))
        st.metric("Sugestão Técnica", f"{rec_pav} pav.")
        st.write(f"No estudo ({r['pavs']} pav.): {r['a_f']/r['pavs']:.2f} m²/andar")
    
    st.caption(f"**Jardim Obrigatório (Permeabilidade):** {r['tp']:.2f} m²")
