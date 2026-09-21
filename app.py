import base64
import io
import re
import zipfile
from datetime import datetime
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA & ESTILO VISUAL INSPIRADO NO SITE YATTÓ
# ==============================================================================
st.set_page_config(
    page_title="Central de Compliance | Yattó",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Imagem de Fundo embutida em Base64 (estilo institucional yatto.com.br)
BACKGROUND_B64 = """iVBORw0KGgoAAAANSUhEUgAAA8YAAAHRCAYAAACo3aDLAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAP+lSURBVHhe7N0HWBRH3wfwX/pSpSsgNkBQUBAVGxZsWRNLIjY0/mKMUYstUWPUaGJLL/42Y4s1GqPGXhDFXhBsqChFUR4sCNL7s7s3x1044O6O0f+/3/P8/e21+m3szszN3fA8"""

st.markdown(
    f"""
    <style>
    /* Estilo de fundo inspirado no site institucional yatto.com.br */
    .stApp {{
        background: url("data:image/png;base64,{BACKGROUND_B64}") no-repeat center center fixed;
        background-size: cover;
    }}

    [data-testid="stAppViewContainer"] {{
        background: url("data:image/png;base64,{BACKGROUND_B64}") no-repeat center center fixed;
        background-size: cover;
    }}
    
    /* Barra lateral estilizada */
    div[data-testid="stSidebar"] {{
        background-color: rgba(244, 246, 248, 0.92);
        border-right: 2px solid #009BDB;
    }}

    /* Container do Logotipo na Sidebar */
    .logo-container {{
        text-align: center;
        padding: 15px 10px;
        background-color: #FFFFFF;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }}

    /* Cartões principais */
    .stMainBlockContainer {{
        background-color: rgba(255, 255, 255, 0.92);
        border-radius: 12px;
        padding: 25px;
        margin-top: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }}
    
    .main-header {{ font-size: 26px; font-weight: bold; color: #009BDB; margin-bottom: 5px; }}
    .sub-header {{ font-size: 14px; color: #87868A; margin-bottom: 25px; }}
    
    /* Botões Yattó */
    .stButton>button {{ 
        background-color: #009BDB; 
        color: #FFFFFF; 
        border-radius: 6px; 
        font-weight: bold; 
        border: none;
        padding: 8px 16px;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{ 
        background-color: #240085; 
        color: #FFFFFF; 
    }}
    
    .card-status {{
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 15px;
    }}
    .status-approved {{ 
        background-color: #93BA1F; 
        color: #FFFFFF; 
        border: 1px solid #93BA1F; 
    }}
    .status-partial {{ 
        background-color: #D1DD00; 
        color: #240085; 
        border: 1px solid #D1DD00; 
    }}
    .status-rejected {{ 
        background-color: #F8D7DA; 
        color: #721C24; 
        border: 1px solid #F5C6CB; 
    }}

    .stProgress > div > div > div > div {{
        background-color: #93BA1F;
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. LOGOTIPO DA YATTÓ NA BARRA LATERAL (ACIMA DA NAVEGAÇÃO)
# ==============================================================================
st.sidebar.markdown(
    """
    <div class="logo-container">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 140" width="100%">
            <defs>
                <linearGradient id="yattoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#009BDB" />
                    <stop offset="100%" stop-color="#93BA1F" />
                </linearGradient>
            </defs>
            <g fill="none" stroke-width="8" stroke-linecap="round">
                <!-- y -->
                <path d="M 40,35 L 70,85 C 60,115 45,125 30,125" stroke="#009BDB" />
                <path d="M 70,35 L 55,60" stroke="#009BDB" />
                <!-- a -->
                <path d="M 125,50 C 105,50 95,65 95,75 C 95,88 108,98 122,98 C 135,98 142,88 142,75 L 142,98" stroke="#009BDB" />
                <!-- t1 -->
                <path d="M 160,25 L 160,98" stroke="#009BDB" />
                <path d="M 148,42 L 175,42" stroke="#009BDB" />
                <!-- t2 -->
                <path d="M 195,25 L 195,98" stroke="#009BDB" />
                <path d="M 183,42 L 210,42" stroke="#009BDB" />
                <!-- o + Folha -->
                <path d="M 270,70 C 270,88 255,99 238,99 C 220,99 208,85 208,70 C 208,52 222,42 238,42 C 255,42 270,55 270,70 Z" stroke="url(#yattoGrad)" />
                <path d="M 262,45 C 275,25 292,20 292,20 C 292,20 290,40 272,52 Z" fill="#93BA1F" stroke="#93BA1F" stroke-width="2" />
            </g>
            <!-- Tagline -->
            <text x="310" y="52" font-family="'Work Sans', sans-serif" font-size="28" fill="#009BDB" font-weight="300">economia</text>
            <text x="310" y="82" font-family="'Work Sans', sans-serif" font-size="28" fill="#009BDB" font-weight="300">circular</text>
        </svg>
    </div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 3. MATRIZ INTEGRADA DE REQUISITOS E FAMÍLIAS DE CNAE
# ==============================================================================
EMOJIS_CATEGORIAS = {
    "Cooperativas": "🤝",
    "Destinador": "📦",
    "Transportador - Pessoa Jurídica": "🚛",
    "Transportador - Pessoa Física": "🚛",
    "Transportador (Resíduos Perigosos)": "☢️",
    "Operador Logístico de Óleo (Cargill)": "🛢️"
}

FAMILIAS_CNAE = {
    "COLETA_RECURSOS": ["3811", "3812"],
    "RECUPERACAO_MATERIAIS": ["3831", "3832", "3839"],
    "TRATAMENTO_DISPOSICAO": ["3821", "3822"],
    "COMERCIO_SUCATAS": ["4687"],
    "TRANSPORTE_CARGAS": ["4930"],
    "ARMAZENAGEM_LOGISTICA": ["5211", "5212", "5229", "5250"],
    "INDUSTRIA_TRANSFORMACAO": ["2221", "2222", "2223", "2229", "2013", "2019"]
}

REQUISITOS = {
    "Cooperativas": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "Estatuto",
            "Última Ata de Eleição",
            "Certidão Negativa de Débitos Trabalhistas (CNDT)",
            "CND Federal",
            "CND Estadual",
            "CND Municipal"
        ],
        "opcionais": [
            "AVCB/CLCB",
            "Certificado de Regularidade - CTF IBAMA"
        ],
        "criticidade": {}
    },
    "Destinador": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "AVCB/CLCB",
            "Certificado de Regularidade - CTF IBAMA"
        ],
        "opcionais": [
            "ISO 14001",
            "ISO 9001"
        ],
        "criticidade": {}
    },
    "Transportador - Pessoa Jurídica": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "RNTRC ANTT",
            "Carteira Nacional de Habilitação (CNH)",
            "Licenciamento do Veículo (CRLV)"
        ],
        "opcionais": [],
        "criticidade": {}
    },
    "Transportador - Pessoa Física": {
        "obrigatorios": [
            "Carteira Nacional de Habilitação (CNH)",
            "Licenciamento do Veículo (CRLV)",
            "RNTRC ANTT",
            "Termo LGPD"
        ],
        "opcionais": [],
        "criticidade": {}
    },
    "Transportador (Resíduos Perigosos)": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Certificado de Regularidade - CTF IBAMA",
            "AATIPP",
            "Licença ou Certificado Ambiental Estadual",
            "RNTRC ANTT",
            "Seguro Ambiental de Carga / PAE",
            "Amostragem de Treinamento MOPP",
            "Licenciamento do Veículo (CRLV)"
        ],
        "opcionais": [
            "ISO 14001",
            "ISO 9001",
            "Ficha de Emergência",
            "Relatório de Passivo Ambiental / Infração Ambiental"
        ],
        "criticidade": {}
    },
    "Operador Logístico de Óleo (Cargill)": {
        "obrigatorios": [
            "Alvará de Funcionamento",
            "Licença Sanitária",
            "AVCB ou CLCB",
            "Licença Ambiental",
            "Comprovante de Inscrição e de Situação Cadastral – CNPJ",
            "Inscrição Estadual",
            "Certificado de Regularidade IBAMA – CTF/APP",
            "CND Federal",
            "CND Estadual",
            "CND Municipal",
            "Certidão Negativa de Débitos Trabalhistas – CNDT",
            "Certificado de Regularidade do Fundo de Garantia por Tempo de Serviço – FGTS",
            "PGR – Plano de Gerenciamento de Riscos",
            "PCMSO – Programa de Controle Médico de Saúde Ocupacional",
            "Ficha de Entrega de EPI’s",
            "Atestados de Saúde Ocupacional – ASO",
            "Relatório de Inspeção de Caldeiras",
            "Certificado de Treinamento de Segurança na Operação de Caldeiras – NR 13",
            "Certificado de Destinação Final da Borra Orgânica",
            "Plano de Atendimento a Emergências – PAE"
        ],
        "opcionais": [
            "Nota Fiscal de Venda do Óleo",
            "Certificado de Destinação do PET para Reciclagem",
            "Comprovante de Medidas Preventivas e Corretivas de Controle de Pragas",
            "Certificado de Treinamento – NR01, NR06 e/ou NR12"
        ],
        "criticidade": {
            "🔴 Grave": [
                "Alvará de Funcionamento",
                "Licença Sanitária",
                "AVCB ou CLCB",
                "Licença Ambiental",
                "Comprovante de Inscrição e de Situação Cadastral – CNPJ",
                "Inscrição Estadual",
                "Certificado de Regularidade IBAMA – CTF/APP"
            ],
            "🟡 Médio": [
                "CND Federal",
                "CND Estadual",
                "CND Municipal",
                "Certidão Negativa de Débitos Trabalhistas – CNDT",
                "Certificado de Regularidade do Fundo de Garantia por Tempo de Serviço – FGTS",
                "PGR – Plano de Gerenciamento de Riscos",
                "PCMSO – Programa de Controle Médico de Saúde Ocupacional",
                "Ficha de Entrega de EPI’s",
                "Atestados de Saúde Ocupacional – ASO",
                "Relatório de Inspeção de Caldeiras",
                "Certificado de Treinamento de Segurança na Operação de Caldeiras – NR 13",
                "Certificado de Destinação Final da Borra Orgânica",
                "Plano de Atendimento a Emergências – PAE"
            ],
            "🟢 Leve": [
                "Nota Fiscal de Venda do Óleo",
                "Certificado de Destinação do PET para Reciclagem",
                "Comprovante de Medidas Preventivas e Corretivas de Controle de Pragas",
                "Certificado de Treinamento – NR01, NR06 e/ou NR12"
            ]
        }
    }
}

TODOS_DOCUMENTOS_POSSIVEIS = sorted(list(set(
    doc
    for cat_data in REQUISITOS.values()
    for lista_docs in [cat_data.get("obrigatorios", []), cat_data.get("opcionais", [])]
    for doc in lista_docs
)))

OPCOES_ATIVIDADES_POR_CATEGORIA = {
    "Cooperativas": [
        "Recepção, Triagem e Comercialização de Recicláveis",
        "Prensagem, Enfardamento e Preparação de Materiais",
        "Coleta de Resíduos Não Perigosos",
        "Armazenamento de Materiais Recicláveis",
        "Transporte Próprio de Resíduos"
    ],
    "Destinador": [
        "Recuperação / Trituração / Moagem / Granulagem de Plásticos",
        "Recuperação de Materiais Metálicos e Outros Resíduos",
        "Tratamento e Disposição Final de Resíduos Não Perigosos",
        "Tratamento e Disposição Final de Resíduos Perigosos",
        "Indústria de Transformação (Fabricação de produtos com matéria reciclada)"
    ],
    "Transportador - Pessoa Jurídica": [
        "Transporte Rodoviário de Cargas em Geral",
        "Coleta e Transporte de Resíduos Não Perigosos",
        "Coleta e Transporte de Resíduos Perigosos"
    ],
    "Transportador - Pessoa Física": [
        "Transporte Autônomo de Cargas"
    ],
    "Transportador (Resíduos Perigosos)": [
        "Transporte Rodoviário de Produtos / Resíduos Perigosos (MOPP)"
    ],
    "Operador Logístico de Óleo (Cargill)": [
        "Armazenamento / Depósito de Mercadorias de Terceiros",
        "Carga, Descarga e Movimentação de Cargas",
        "Organização Logística do Transporte e Agenciamento",
        "Operação Logística Integrada com Transporte Próprio"
    ]
}

# ==============================================================================
# 4. LEITURA DE PDFS, ZIPS & EXTRAÇÃO INTELIGENTE DE DADOS
# ==============================================================================

def extrair_texto_pdf(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        return texto
    except Exception:
        return ""

def processar_arquivos_upload(arquivos_uploaded):
    lista_pdfs = []
    if arquivos_uploaded:
        for file in arquivos_uploaded:
            nome = file.name.lower()
            bytes_content = file.read()
            if nome.endswith(".zip"):
                try:
                    with zipfile.ZipFile(io.BytesIO(bytes_content)) as z:
                        for filename in z.namelist():
                            if filename.lower().endswith(".pdf") and not filename.startswith("__MACOSX"):
                                pdf_bytes = z.read(filename)
                                lista_pdfs.append((filename, pdf_bytes))
                except Exception:
                    pass
            elif nome.endswith(".pdf"):
                lista_pdfs.append((file.name, bytes_content))
    return lista_pdfs

def extrair_cnpjs(texto):
    padrao = r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"
    return list(set(re.findall(padrao, texto)))

def extrair_cnaes(texto):
    padrao = r"\b\d{4}-\d/\d{2}\b|\b\d{2}\.\d{2}-\d-\d{2}\b"
    encontrados = re.findall(padrao, texto)
    cnaes_limpos = []
    for c in encontrados:
        c_clean = re.sub(r"\D", "", c)
        if len(c_clean) >= 4:
            cnaes_limpos.append(c_clean[:4])
    return list(set(cnaes_limpos))

def extrair_datas_validade(texto):
    linhas = texto.split("\n")
    datas_vencimento = []
    
    palavras_chave_validade = ["validade", "válido até", "valido ate", "vencimento", "expira em", "expira"]

    for linha in linhas:
        linha_lower = linha.lower()
        if any(p in linha_lower for p in palavras_chave_validade):
            padrao = r"\b\d{2}/\d{2}/\d{4}\b"
            datas_encontradas = re.findall(padrao, linha)
            for d in datas_encontradas:
                try:
                    dt = datetime.strptime(d, "%d/%m/%Y")
                    datas_vencimento.append(dt)
                except ValueError:
                    continue
    return datas_vencimento

# ==============================================================================
# 5. MOTOR DE ANÁLISE DE COMPLIANCE & AVALIAÇÃO DE CNAE
# ==============================================================================

def avaliar_compatibilidade_cnae(cnaes_encontrados, atividades_selecionadas):
    if not cnaes_encontrados:
        return "🟡 Necessita validação", "Nenhum código CNAE formatado foi extraído automaticamente do Cartão CNPJ. Requer conferência visual."

    familias_encontradas = set(cnaes_encontrados)
    
    cnaes_alvo = set()
    for ativ in atividades_selecionadas:
        if "Coleta" in ativ:
            cnaes_alvo.update(FAMILIAS_CNAE["COLETA_RECURSOS"])
        if "Recuperação" in ativ or "Prensagem" in ativ or "Triagem" in ativ:
            cnaes_alvo.update(FAMILIAS_CNAE["RECUPERACAO_MATERIAIS"])
            cnaes_alvo.update(FAMILIAS_CNAE["COMERCIO_SUCATAS"])
        if "Tratamento" in ativ or "Disposição" in ativ:
            cnaes_alvo.update(FAMILIAS_CNAE["TRATAMENTO_DISPOSICAO"])
        if "Transporte" in ativ:
            cnaes_alvo.update(FAMILIAS_CNAE["TRANSPORTE_CARGAS"])
        if "Armazenamento" in ativ or "Carga" in ativ or "Logística" in ativ:
            cnaes_alvo.update(FAMILIAS_CNAE["ARMAZENAGEM_LOGISTICA"])
        if "Indústria de Transformação" in ativ:
            cnaes_alvo.update(FAMILIAS_CNAE["INDUSTRIA_TRANSFORMACAO"])

    intersecao = familias_encontradas.intersection(cnaes_alvo)

    if intersecao:
        return "🟢 Compatível", f"Foram identificados CNAEs ({', '.join(intersecao)}) diretamente compatíveis com as atividades operacionais declaradas."
    elif familias_encontradas.intersection(set(FAMILIAS_CNAE["INDUSTRIA_TRANSFORMACAO"])):
        return "🟡 Necessita validação", "Identificado CNAE de Indústria de Transformação. Requer validação conjunta com a Licença Ambiental."
    else:
        return "🟡 Necessita validação", f"Os CNAEs identificados no texto do CNPJ ({', '.join(familias_encontradas)}) não apresentaram correspondência automática exata com o escopo selecionado. Requer verificação visual do Cartão CNPJ."

def analisar_documentos(categoria, lista_pdfs, modo_analise, doc_especifico_selecionado, atividades_selecionadas):
    reqs = REQUISITOS.get(categoria, {})

    if modo_analise == "Análise Pontual (Documento Avulso)":
        obrigatorios_exigidos = [doc_especifico_selecionado]
        opcionais_exigidos = []
    else:
        obrigatorios_exigidos = reqs.get("obrigatorios", [])
        opcionais_exigidos = reqs.get("opcionais", [])

    total_exigido = list(set(obrigatorios_exigidos + opcionais_exigidos))

    docs_encontrados = []
    cnpjs_encontrados = []
    cnaes_encontrados = []
    datas_vencimento = []
    relatorio_erros = []

    for nome_pdf, pdf_bytes in lista_pdfs:
        texto = extrair_texto_pdf(pdf_bytes)

        cnpjs_encontrados.extend(extrair_cnpjs(texto))
        cnaes_encontrados.extend(extrair_cnaes(texto))
        datas_vencimento.extend(extrair_datas_validade(texto))

        texto_busca = (nome_pdf + " " + texto).lower()
        for doc in total_exigido:
            termo = doc.lower().split()[0]
            if termo in texto_busca and doc not in docs_encontrados:
                docs_encontrados.append(doc)

    cnpjs_unicos = list(set(cnpjs_encontrados))
    cnaes_unicos = list(set(cnaes_encontrados))

    status_cnae, parecer_cnae = avaliar_compatibilidade_cnae(cnaes_unicos, atividades_selecionadas)

    hoje = datetime.now()
    datas_vencidas = [d for d in datas_vencimento if d < hoje]

    if datas_vencidas:
        str_venc = [d.strftime("%d/%m/%Y") for d in datas_vencidas]
        relatorio_erros.append(f"❌ Documento(s) com data de validade VENCIDA: {', '.join(str_venc)}")

    obrig_entregues = [d for d in obrigatorios_exigidos if d in docs_encontrados]
    obrig_pendentes = [d for d in obrigatorios_exigidos if d not in docs_encontrados]
    opc_entregues = [d for d in opcionais_exigidos if d in docs_encontrados]

    pct_conclusao = (
        (len(obrig_entregues) / len(obrigatorios_exigidos) * 100) if obrigatorios_exigidos else 0
    )

    matriz_crit = reqs.get("criticidade", {})
    pendencias_criticas = {"Grave": [], "Médio": [], "Leve": []}
    if matriz_crit and obrig_pendentes:
        for p in obrig_pendentes:
            if p in matriz_crit.get("🔴 Grave", []):
                pendencias_criticas["Grave"].append(p)
            elif p in matriz_crit.get("🟡 Médio", []):
                pendencias_criticas["Médio"].append(p)
            elif p in matriz_crit.get("🟢 Leve", []):
                pendencias_criticas["Leve"].append(p)

    if modo_analise == "Análise Pontual (Documento Avulso)":
        if datas_vencidas:
            status_final = "DOCUMENTO REPROVADO (VENCIDO)"
        elif len(obrig_entregues) > 0:
            status_final = "DOCUMENTO EM CONFORMIDADE (APROVADO)"
        else:
            status_final = "DOCUMENTO NÃO IDENTIFICADO OU INCOMPLETO"
    else:
        if datas_vencidas or pendencias_criticas.get("Grave"):
            status_final = "REPROVADO / RISCO GRAVE"
        elif pct_conclusao == 100 and not relatorio_erros and "Compatível" in status_cnae:
            status_final = "HOMOLOGADO / APROVADO"
        elif pct_conclusao > 0:
            status_final = "EM HOMOLOGAÇÃO PARCIAL"
        else:
            status_final = "AGUARDANDO DOCUMENTAÇÃO"

    return {
        "status": status_final,
        "progresso": round(pct_conclusao, 1),
        "cnpjs": cnpjs_unicos,
        "cnaes": cnaes_unicos,
        "status_cnae": status_cnae,
        "parecer_cnae": parecer_cnae,
        "obrig_entregues": obrig_entregues,
        "obrig_pendentes": obrig_pendentes,
        "opc_entregues": opc_entregues,
        "pendencias_criticas": pendencias_criticas,
        "erros": relatorio_erros,
    }

# ==============================================================================
# 6. INTERFACE DO USUÁRIO (STREAMLIT)
# ==============================================================================

st.sidebar.title("Navegação")
menu = st.sidebar.radio(
    "Ir para:",
    [
        "Central de Análises",
        "Matriz de Requisitos Yattó",
        "Sobre o Decreto 12.688/2025",
    ],
)

if menu == "Central de Análises":
    st.markdown(
        '<div class="main-header">Central de Análises de Compliance</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Validação automatizada de parceiros e documentos avulsos | Yattó</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.1, 1.9])

    with col_left:
        st.subheader("1. Tipo de Verificação")
        modo_analise = st.radio(
            "Selecione o escopo da verificação:",
            [
                "Análise Completa / Homologação (Vários documentos)",
                "Análise Pontual (Documento Avulso)",
            ],
        )

        doc_especifico_selecionado = None
        if modo_analise == "Análise Pontual (Documento Avulso)":
            doc_especifico_selecionado = st.selectbox(
                "Escolha o documento a ser verificado:",
                TODOS_DOCUMENTOS_POSSIVEIS
            )

        st.subheader("2. Dados do Parceiro")
        razao_social = st.text_input(
            "Razão Social / Nome", placeholder="Ex: Operador Logístico Óleo Sp"
        )
        categoria = st.selectbox("Categoria do Fornecedor", list(REQUISITOS.keys()))

        atividades_opcoes = OPCOES_ATIVIDADES_POR_CATEGORIA.get(categoria, [])
        atividades_selecionadas = st.multiselect(
            "Atividade(s) efetivamente realizada(s) na operação:",
            atividades_opcoes,
            default=[atividades_opcoes[0]] if atividades_opcoes else []
        )

        st.subheader("3. Anexo dos Arquivos (.PDF ou .ZIP)")
        arquivos = st.file_uploader(
            "Upload dos arquivos (PDFs ou pasta ZIP):", type=["pdf", "zip"], accept_multiple_files=True
        )

        btn_analisar = st.button("🔍 Executar Análise de Compliance")

    with col_right:
        st.subheader("Parecer da Análise de Compliance")

        if btn_analisar:
            if not razao_social:
                st.warning(
                    "Por favor, insira a Razão Social do fornecedor para prosseguir."
                )
            elif not arquivos:
                st.warning(
                    "Por favor, faça o upload de pelo menos um arquivo PDF ou ZIP para analisar."
                )
            else:
                with st.spinner("Processando arquivos (PDF/ZIP) e analisando requisitos..."):
                    lista_pdfs = processar_arquivos_upload(arquivos)
                    
                    if not lista_pdfs:
                        st.error("Nenhum arquivo PDF válido foi encontrado no envio ou dentro do arquivo ZIP.")
                    else:
                        res = analisar_documentos(
                            categoria, lista_pdfs, modo_analise, doc_especifico_selecionado, atividades_selecionadas
                        )

                        st.write(f"**Fornecedor:** {razao_social}")
                        st.write(f"**Categoria:** {categoria}")
                        st.write(f"**PDFs Analisados:** {len(lista_pdfs)} arquivo(s)")
                        if modo_analise == "Análise Pontual (Documento Avulso)":
                            st.write(f"**Documento Alvo:** {doc_especifico_selecionado}")

                        status = res["status"]
                        if "APROVADO" in status or "CONFORMIDADE" in status:
                            st.markdown(
                                f'<div class="card-status status-approved">🟢 STATUS: {status}</div>',
                                unsafe_allow_html=True,
                            )
                            st.balloons()
                        elif "PARCIAL" in status:
                            st.markdown(
                                f'<div class="card-status status-partial">🟡 STATUS: {status} ({res["progresso"]}% Completo)</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div class="card-status status-rejected">🔴 STATUS: {status}</div>',
                                unsafe_allow_html=True,
                            )

                        if modo_analise != "Análise Pontual (Documento Avulso)":
                            st.progress(res["progresso"] / 100)

                        st.markdown("---")
                        st.markdown("### 🏢 Análise de CNPJ & Compatibilidade de CNAE")
                        st.write(f"**Resultado:** {res['status_cnae']}")
                        st.info(res['parecer_cnae'])

                        if res["erros"]:
                            st.markdown("### ⚠️ Inconformidades Detectadas")
                            for err in res["erros"]:
                                st.error(err)

                        if res["cnpjs"]:
                            st.caption(f"CNPJ(s) Mapeados nos PDFs: {', '.join(res['cnpjs'])}")

                        c_ent, c_pend = st.columns(2)

                        with c_ent:
                            st.markdown("#### ✅ Documentos Validados")
                            if res["obrig_entregues"]:
                                for d in res["obrig_entregues"]:
                                    st.write(f"✓ {d}")
                            else:
                                st.write("*Nenhum documento obrigatório validado.*")

                            if res["opc_entregues"]:
                                st.markdown("#### 🌟 Opcionais Entregues")
                                for d in res["opc_entregues"]:
                                    st.write(f"★ {d}")

                        with c_pend:
                            st.markdown("#### ⏳ Documentos Pendentes")
                            if res["obrig_pendentes"]:
                                for d in res["obrig_pendentes"]:
                                    st.write(f"○ {d}")
                            else:
                                st.write("🎉 *Nenhuma pendência documental!*")

                        crit = res.get("pendencias_criticas", {})
                        if any(crit.values()):
                            st.markdown("---")
                            st.markdown("### 🚦 Avaliação de Criticidade das Pendências")
                            if crit.get("Grave"):
                                st.error(f"**Pendências Graves (Impedimentos):** {', '.join(crit['Grave'])}")
                            if crit.get("Médio"):
                                st.warning(f"**Pendências Médias (Prazo de Adequação):** {', '.join(crit['Médio'])}")
                            if crit.get("Leve"):
                                st.info(f"**Pendências Leves (Cadastro/Administrativo):** {', '.join(crit['Leve'])}")

                        st.markdown("---")
                        st.markdown("### ✉️ Resposta Pronta para Envio")
                        if modo_analise == "Análise Pontual (Documento Avulso)":
                            texto_email = (
                                f"Prezados,\n\nRealizamos a verificação pontual do documento ({doc_especifico_selecionado}) referente a {razao_social}.\n\n"
                                f"STATUS DA VERIFICAÇÃO: {res['status']}\n\n"
                                f"PARECER CNPJ/CNAE: {res['status_cnae']} - {res['parecer_cnae']}\n\n"
                                f"Atenciosamente,\nEquipe de Compliance Yattó"
                            )
                        else:
                            texto_email = (
                                f"Prezados,\n\nRecebemos a documentação de compliance de {razao_social}.\n\n"
                                f"STATUS DA HOMOLOGAÇÃO: {res['status']} ({res['progresso']}% concluído)\n\n"
                                f"PARECER DA ANÁLISE DE CNAE: {res['status_cnae']}\n\n"
                                f"DOCUMENTOS OBRIGATÓRIOS RECEBIDOS ({len(res['obrig_entregues'])}):\n"
                                + "\n".join([f"- {d}" for d in res["obrig_entregues"]])
                                + (f"\n\nDOCUMENTOS OPCIONAIS RECEBIDOS:\n" + "\n".join([f"- {d}" for d in res["opc_entregues"]]) if res["opc_entregues"] else "")
                                + f"\n\nPENDÊNCIAS PARA CONCLUIR A HOMOLOGAÇÃO ({len(res['obrig_pendentes'])}):\n"
                                + "\n".join([f"- {d}" for d in res["obrig_pendentes"]])
                                + "\n\nFicamos no aguardo dos itens pendentes para finalização do cadastro.\n\nAtenciosamente,\nEquipe de Compliance Yattó"
                            )
                        st.text_area(
                            "Copie o texto abaixo para enviar ao parceiro:",
                            texto_email,
                            height=200,
                        )

elif menu == "Matriz de Requisitos Yattó":
    st.title("Matriz Geral de Requisitos de Compliance")
    st.write("Consulte as exigências documentais divididas por categoria:")

    for cat, reqs in REQUISITOS.items():
        emoji = EMOJIS_CATEGORIAS.get(cat, "")
        titulo_expander = f"{emoji} {cat}" if emoji else cat
        with st.expander(titulo_expander):
            if reqs.get("criticidade"):
                st.markdown("**Níveis de Criticidade de Risco:**")
                for nivel, docs in reqs["criticidade"].items():
                    st.write(f"- **{nivel}:** {', '.join(docs)}")
            else:
                st.write(
                    "**Documentos Obrigatórios:**",
                    ", ".join(reqs.get("obrigatorios", [])) if reqs.get("obrigatorios") else "Nenhum"
                )
                if reqs.get("opcionais"):
                    st.write(
                        "**Documentos Opcionais:**",
                        ", ".join(reqs.get("opcionais", []))
                    )

elif menu == "Sobre o Decreto 12.688/2025":
    st.title("Segurança Jurídica & Decreto nº 12.688/2025")
    st.write(
        "A Yattó atua como infraestrutura de soluções em economia circular oferecendo diagnósticos, inteligência de dados e execução operacional contínua."
    )
    st.write(
        "Com a entrada em vigor do **Decreto nº 12.688/2025**, a exigência regulatória mudou da simples compensação para a **comprovação de circularidade com dados auditáveis**."
    )
    st.write(
        "Garantir a conformidade documental de todos os parceiros, cooperativas, destinadores e operadores logísticos é o pilar que elimina riscos de sanção regulatória, multas e greenwashing."
    )
