# --- BANCO DE DADOS FIEL ÀS TABELAS OFICIAIS (LC 90/2023) ---
atividades_db = {
    "Residencial Unifamiliar": {"v": 0, "s": 150, "label": "1 vaga por unidade"},
    "Residencial Multifamiliar": {"v": 65, "s": 150, "label": "1 vaga por unidade habitacional"},
    "Hospedagem (Hotéis e Pousadas)": {"v": 100, "s": 60, "label": "1 vaga a cada 100m²"},
    "Motéis": {"v": 1, "s": 60, "label": "1 vaga por quarto"},
    "Comércio e Serviços em Geral (Inc. Farmácias)": {"v": 50, "s": 100, "label": "1 vaga a cada 50m²"},
    "Supermercados e Centros Comerciais": {"v": 25, "s": 80, "label": "1 vaga a cada 25m²"},
    "Serviços de Saúde (Hospitais e Maternidades)": {"v": 80, "s": 30, "label": "1 vaga a cada 80m²"},
    "Clínicas e Laboratórios": {"v": 40, "s": 50, "label": "1 vaga a cada 40m²"},
    "Educação Infantil e Fundamental": {"v": 0, "s": 40, "label": "Embarque/Desembarque interno obrigatório"},
    "Educação Superior e Profissionalizante": {"v": 35, "s": 40, "label": "1 vaga a cada 35m²"},
    "Locais de Reunião (Igrejas e Templos)": {"v": 20, "s": 50, "label": "1 vaga a cada 20m² de área de público"},
    "Cinemas e Teatros": {"v": 15, "s": 30, "label": "1 vaga a cada 15 assentos"},
    "Clubes e Estádios": {"v": 50, "s": 100, "label": "1 vaga a cada 50m²"},
    "Oficinas e Postos de Serviços": {"v": 100, "s": 150, "label": "1 vaga a cada 100m²"},
    "Indústrias e Depósitos": {"v": 150, "s": 200, "label": "1 vaga a cada 150m²"},
}

# --- CAMPO DE BUSCA PREDITIVA ---
with st.sidebar:
    st.header("🔍 Busca por Atividade")
    # O selectbox funciona como busca preditiva ao digitar
    atividade_final = st.selectbox(
        "Digite a atividade (Fiel ao Anexo IV):",
        options=sorted(list(atividades_db.keys())),
        help="Nomenclaturas extraídas da Lei Complementar 90/2023."
    )
    dados = atividades_db[atividade_final]
