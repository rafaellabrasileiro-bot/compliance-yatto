import base64
import io
import re
import zipfile
from datetime import datetime
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA & ESTILO VISUAL YATTÓ
# ==============================================================================
st.set_page_config(
    page_title="Central de Análises Documentais | Yattó",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Estilo de fundo do aplicativo inteiro (Branco Limpo) */
    .stApp {
        background-color: #FFFFFF !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
    }

    /* Barra lateral de Navegação (Sidebar) com FUNDO EXCLUSIVAMENTE BRANCO */
    section[data-testid="stSidebar"], div[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        background-image: none !important;
        border-right: 2px solid #009BDB;
    }

    section[data-testid="stSidebar"] > div:first-child {
        background-color: #FFFFFF !important;
    }

    /* Container do Logotipo Superior na Sidebar */
    .logo-container {
        text-align: center;
        padding: 10px;
        background-color: #FFFFFF;
        border-radius: 8px;
        margin-bottom: 20px;
    }

    .logo-container img {
        max-width: 100%;
        height: auto;
    }

    /* Cartões de verificação com fundo branco e bordas suaves Yattó */
    .stMainBlockContainer {
        background-color: #FFFFFF !important;
        border-radius: 12px;
        padding: 25px;
        margin-top: 15px;
        box-shadow: 0 4px 20px rgba(0, 155, 219, 0.08);
        border: 1px solid rgba(0, 155, 219, 0.2);
    }

    .main-header { font-size: 26px; font-weight: bold; color: #009BDB; margin-bottom: 5px; }
    .sub-header { font-size: 14px; color: #87868A; margin-bottom: 25px; }
    
    /* Botões Yattó */
    .stButton>button { 
        background-color: #009BDB; 
        color: #FFFFFF; 
        border-radius: 6px; 
        font-weight: bold; 
        border: none;
        padding: 8px 16px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { 
        background-color: #240085; 
        color: #FFFFFF; 
    }
    
    .card-status {
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 15px;
    }
    .status-approved { 
        background-color: #93BA1F; 
        color: #FFFFFF; 
        border: 1px solid #93BA1F; 
    }
    .status-partial { 
        background-color: #D1DD00; 
        color: #240085; 
        border: 1px solid #D1DD00; 
    }
    .status-rejected { 
        background-color: #F8D7DA; 
        color: #721C24; 
        border: 1px solid #F5C6CB; 
    }

    .stProgress > div > div > div > div {
        background-color: #93BA1F;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. LOGOTIPO OFICIAL DA YATTÓ NA BARRA LATERAL
# ==============================================================================
st.sidebar.markdown(
    """
    <div class="logo-container">
        <img src="https://yatto.com.br/wp-content/uploads/2025/01/yatto-id-v1.png" alt="Yattó - Economia Circular">
    </div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 3. MATRIZ INTEGRADA DE REQUISITOS, CATEGORIAS E CNAES DETALHADOS
# ==============================================================================
EMOJIS_CATEGORIAS = {
    "Cooperativas": "🤝",
    "Destinador": "📦",
    "Transportador - Pessoa Jurídica": "🚛",
    "Transportador - Pessoa Física": "🚛",
    "Transportador (Resíduos Perigosos)": "☢️",
    "Operador Logístico de Óleo (Cargill)": "🛢️"
}

# Tabela Detalhada de Mapeamento de CNAEs
MAPEAMENTO_CNAE_COMPATIBILIDADE = {
    "4930-2/01": ("Transportador - Pessoa Jurídica", "Transporte rodoviário de cargas não perigosas"),
    "4930-2/02": ("Transportador - Pessoa Jurídica", "Transporte rodoviário de cargas não perigosas (intermunicipal/interestadual)"),
    "4930-2/03": ("Transportador (Resíduos Perigosos)", "Transporte rodoviário de produtos e resíduos perigosos"),
    "3811-4/00": ("Cooperativas", "Coleta de resíduos não perigosos"),
    "3812-2/00": ("Transportador (Resíduos Perigosos)", "Coleta de resíduos perigosos"),
    "3821-1/00": ("Destinador", "Tratamento e disposição de resíduos não perigosos"),
    "3822-0/00": ("Destinador", "Tratamento e disposição de resíduos perigosos"),
    "3832-7/00": ("Destinador", "Recuperação de materiais plásticos"),
    "3831-9/01": ("Destinador", "Recuperação de sucatas de alumínio"),
    "3831-9/99": ("Destinador", "Recuperação de materiais metálicos diversos"),
    "3839-4/99": ("Destinador", "Recuperação de materiais não especificados"),
    "3839-4/01": ("Destinador", "Tratamento/recuperação de resíduos orgânicos"),
    "3900-5/00": ("Destinador", "Descontaminação e serviços de gestão de resíduos"),
    "4687-7/01": ("Cooperativas", "Comércio atacadista de resíduos de papel e papelão"),
    "4687-7/02": ("Cooperativas", "Comércio atacadista de resíduos plásticos"),
    "4687-7/03": ("Cooperativas", "Comércio atacadista de resíduos metálicos e sucatas"),
    "5211-7/01": ("Operador Logístico de Óleo (Cargill)", "Armazéns gerais"),
    "5211-7/99": ("Operador Logístico de Óleo (Cargill)", "Armazenamento/guarda de materiais de terceiros"),
    "5250-8/03": ("Operador Logístico de Óleo (Cargill)", "Agenciamento de cargas"),
    "5250-8/04": ("Operador Logístico de Óleo (Cargill)", "Organização, agenciamento ou operação logística de cargas"),
    "5250-8/05": ("Operador Logístico de Óleo (Cargill)", "Operador de transporte multimodal - OTM")
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
            "Certidão Negativa de Débitos Trabalhistas",
            "CND Federal, Estadual e Municipal"
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
            "RNTRC - Registro Nacional de Transportadores Rodoviários de Cargas",
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
            "RNTRC - Registro Nacional de Transportadores Rodoviários de Cargas",
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
            "AATIPP - Autorização para o Transporte Interestadual de Produtos Perigosos",
            "Licença ou Certificado Ambiental Estadual para Transporte de Produto/Resíduo Perigoso",
            "RNTRC - Registro Nacional de Transportadores Rodoviários de Cargas",
            "Seguro Ambiental de Carga ou Plano de Atendimento a Emergência (PAE)",
            "Amostragem de Treinamento - MOPP",
            "Licenciamento do Veículo (CRLV)"
        ],
        "opcionais": [
            "ISO 14001",
            "ISO 9001",
            "Ficha de Emergência",
            "Relatório de Passivo Ambiental ou Infração Ambiental"
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

# PALAVRAS-CHAVE FLEXÍVEIS PARA DETECÇÃO EM TEXTOS PDF
PALAVRAS_CHAVE_DOCS = {
    "Cartão CNPJ": ["cnpj", "comprovante de inscrição", "receita federal", "situação cadastral"],
    "Comprovante de Inscrição e de Situação Cadastral – CNPJ": ["cnpj", "comprovante de inscrição", "receita federal", "situação cadastral"],
    "Inscrição Estadual Ativa": ["inscrição estadual", "sintegra", "ie ativa", "inscrição no cadastro de contribuintes"],
    "Inscrição Estadual": ["inscrição estadual", "sintegra", "ie ativa", "inscrição no cadastro de contribuintes"],
    "Alvará de Funcionamento": ["alvará", "alvara", "licença de funcionamento", "alvará de licença"],
    "Dispensa ou Licença Ambiental": ["licença ambiental", "licenca ambiental", "cetesb", "ibama", "dispensa de licença", "cadri", "operacao", "instalacao"],
    "Licença Ambiental": ["licença ambiental", "licenca ambiental", "cetesb", "ibama", "dispensa de licença", "cadri"],
    "Licença Sanitária": ["sanitária", "sanitaria", "vigilância sanitária", "visa"],
    "AVCB/CLCB": ["avcb", "clcb", "bombeiros", "corpo de bombeiros", "vistoria"],
    "AVCB ou CLCB": ["avcb", "clcb", "bombeiros", "corpo de bombeiros", "vistoria"],
    "Estatuto": ["estatuto", "estatuto social", "cooperativa"],
    "Última Ata de Eleição": ["ata", "ata de eleição", "eleicao", "assembleia"],
    "Certidão Negativa de Débitos Trabalhistas": ["cndt", "trabalhistas", "justiça do trabalho"],
    "Certidão Negativa de Débitos Trabalhistas – CNDT": ["cndt", "trabalhistas", "justiça do trabalho"],
    "CND Federal, Estadual e Municipal": ["receita federal", "sefaz", "prefeitura", "débitos", "certidão conjunta"],
    "CND Federal": ["receita federal", "débitos relativos a tributos federais", "certidão conjunta"],
    "CND Estadual": ["fazenda estadual", "sefaz", "débitos estaduais"],
    "CND Municipal": ["prefeitura", "débitos municipais", "tributos municipais"],
    "Certificado de Regularidade - CTF IBAMA": ["ctf", "ibama", "certificado de regularidade"],
    "Certificado de Regularidade IBAMA – CTF/APP": ["ctf", "ibama", "certificado de regularidade"],
    "Certificado de Regularidade do Fundo de Garantia por Tempo de Serviço – FGTS": ["fgts", "caixa econômica", "crf"],
    "RNTRC - Registro Nacional de Transportadores Rodoviários de Cargas": ["antt", "rntrc", "transportador rodoviário"],
    "RNTRC ANTT": ["antt", "rntrc", "transportador rodoviário"],
    "Carteira Nacional de Habilitação (CNH)": ["cnh", "carteira nacional de habilitação", "motorista"],
    "Licenciamento do Veículo (CRLV)": ["crlv", "licenciamento", "detran", "veículo"],
    "AATIPP - Autorização para o Transporte Interestadual de Produtos Perigosos": ["aatipp", "produtos perigosos", "autorização"],
    "Licença ou Certificado Ambiental Estadual para Transporte de Produto/Resíduo Perigoso": ["licença ambiental", "transporte de resíduos perigosos", "certificado ambiental"],
    "Seguro Ambiental de Carga ou Plano de Atendimento a Emergência (PAE)": ["pae", "plano de atendimento", "seguro ambiental", "emergência"],
    "Plano de Atendimento a Emergências – PAE": ["pae", "plano de atendimento", "emergências"],
    "Amostragem de Treinamento - MOPP": ["mopp", "produtos perigosos", "treinamento"],
    "ISO 14001": ["14001", "gestão ambiental"],
    "ISO 9001": ["9001", "gestão da qualidade"],
    "Ficha de Emergência": ["ficha de emergência", "emergencia"],
    "Relatório de Passivo Ambiental ou Infração Ambiental": ["passivo ambiental", "infração ambiental", "relatório"],
    "Termo LGPD": ["lgpd", "proteção de dados", "termo"]
}

TODOS_DOCUMENTOS_POSSIVEIS = sorted(list(set(
    doc
    for cat_data in REQUISITOS.values()
    for lista_docs in [cat_data.get("obrigatorios", []), cat_data.get("opcionais", [])]
    for doc in lista_docs
)))

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

def extrair_cnaes_completos(texto):
    padrao = r"\b\d{4}-\d/\d{2}\b|\b\d{2}\.\d{2}-\d-\d{2}\b"
    encontrados = re.findall(padrao, texto)
    cnaes_formatados = []
    for c in encontrados:
        c_clean = re.sub(r"\D", "", c)
        if len(c_clean) == 7:
            cnaes_formatados.append(f"{c_clean[:4]}-{c_clean[4]}/{c_clean[5:]}")
    return list(set(cnaes_formatados))

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

def identificar_enquadramentos_cnae(cnaes_encontrados):
    enquadramentos = {}
    for cnae in cnaes_encontrados:
        if cnae in MAPEAMENTO_CNAE_COMPATIBILIDADE:
            cat, desc = MAPEAMENTO_CNAE_COMPATIBILIDADE[cnae]
            if cat not in enquadramentos:
                enquadramentos[cat] = []
            enquadramentos[cat].append(f"{cnae} - {desc}")
    return enquadramentos

def validar_presenca_documento(nome_doc, texto_acumulado, cnpjs_unicos):
    """
    Verifica se um documento está presente no texto do lote
    usando busca por palavras-chave flexíveis e validação de CNPJ.
    """
    if "CNPJ" in nome_doc and len(cnpjs_unicos) > 0:
        return True

    texto_lower = texto_acumulado.lower()
    chaves = PALAVRAS_CHAVE_DOCS.get(nome_doc, [nome_doc.lower().split()[0]])

    return any(chave in texto_lower for chave in chaves)

# ==============================================================================
# 5. INTERFACE DO USUÁRIO (STREAMLIT)
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
        '<div class="main-header">Central de Análises Documentais</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Identificação automática de CNAE e validação de compliance | Yattó</div>',
        unsafe_allow_html=True,
    )

    if "dados_lote_analise" not in st.session_state:
        st.session_state.dados_lote_analise = None

    col_left, col_right = st.columns([1.1, 1.9])

    with col_left:
        st.subheader("1. Identificação Automática (Upload)")
        
        modo_analise = st.radio(
            "Escopo da verificação:",
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

        razao_social = st.text_input(
            "Razão Social / Nome do Parceiro", placeholder="Ex: Operador Logístico Óleo Sp"
        )

        arquivos = st.file_uploader(
            "Upload dos arquivos (.PDF ou .ZIP):", type=["pdf", "zip"], accept_multiple_files=True
        )

        btn_mapear = st.button("🔍 Mapear CNPJ, CNAEs e Documentos")

    if btn_mapear:
        if not arquivos:
            st.warning("Por favor, faça o upload de pelo menos um arquivo PDF ou ZIP.")
        else:
            with st.spinner("Lendo arquivos, identificando CNPJ e consultando matriz de CNAE..."):
                lista_pdfs = processar_arquivos_upload(arquivos)
                
                texto_acumulado = ""
                cnpjs_encontrados = []
                cnaes_encontrados = []
                datas_vencimento = []

                for nome_pdf, pdf_bytes in lista_pdfs:
                    texto = extrair_texto_pdf(pdf_bytes)
                    texto_acumulado += f"\n--- {nome_pdf} ---\n" + texto
                    cnpjs_encontrados.extend(extrair_cnpjs(texto))
                    cnaes_encontrados.extend(extrair_cnaes_completos(texto))
                    datas_vencimento.extend(extrair_datas_validade(texto))

                cnpjs_unicos = list(set(cnpjs_encontrados))
                cnaes_unicos = list(set(cnaes_encontrados))
                enquadramentos_cnae = identificar_enquadramentos_cnae(cnaes_unicos)

                st.session_state.dados_lote_analise = {
                    "lista_pdfs": lista_pdfs,
                    "texto_acumulado": texto_acumulado,
                    "cnpjs": cnpjs_unicos,
                    "cnaes": cnaes_unicos,
                    "enquadramentos": enquadramentos_cnae,
                    "datas_vencimento": datas_vencimento
                }

    with col_right:
        st.subheader("2. Confirmação do Enquadramento & Parecer Final")

        if st.session_state.dados_lote_analise:
            d = st.session_state.dados_lote_analise

            st.info(f"**CNPJ(s) Identificados:** {', '.join(d['cnpjs']) if d['cnpjs'] else 'Nenhum'}")
            st.write(f"**CNAE(s) Mapeados:** {', '.join(d['cnaes']) if d['cnaes'] else 'Nenhum explícito no texto'}")

            st.markdown("#### ☑️ Possíveis Enquadramentos Identificados pelos CNAEs:")
            if d['enquadramentos']:
                for cat_detectada, lista_det in d['enquadramentos'].items():
                    st.success(f"✓ **{cat_detectada}:** {'; '.join(lista_det)}")
            else:
                st.warning("Nenhum CNAE mapeado automaticamente. Selecione a categoria abaixo para prosseguir.")

            st.markdown("---")
            col_conf1, col_conf2 = st.columns(2)
            
            index_default_cat = 0
            if d['enquadramentos']:
                primeira_cat = list(d['enquadramentos'].keys())[0]
                if primeira_cat in REQUISITOS:
                    index_default_cat = list(REQUISITOS.keys()).index(primeira_cat)

            with col_conf1:
                categoria = st.selectbox("Categoria do Fornecedor na Operação:", list(REQUISITOS.keys()), index=index_default_cat)
            with col_conf2:
                caracteristica_fornecedor = st.selectbox("Característica do Fornecedor:", ["Pessoa Jurídica (Empresa)", "Cooperativa / Associação", "Pessoa Física (Autônomo)"])

            btn_emitir_parecer = st.button("🚀 Executar Análise Final de Compliance")

            if btn_emitir_parecer:
                st.markdown("---")
                reqs = REQUISITOS.get(categoria, {})

                if modo_analise == "Análise Pontual (Documento Avulso)":
                    obrigatorios_exigidos = [doc_especifico_selecionado]
                    opcionais_exigidos = []
                else:
                    obrigatorios_exigidos = reqs.get("obrigatorios", [])
                    opcionais_exigidos = reqs.get("opcionais", [])

                    if caracteristica_fornecedor == "Cooperativa / Associação":
                        if "Estatuto" not in obrigatorios_exigidos: obrigatorios_exigidos.append("Estatuto")
                        if "Última Ata de Eleição" not in obrigatorios_exigidos: obrigatorios_exigidos.append("Última Ata de Eleição")

                docs_encontrados = []
                for doc in set(obrigatorios_exigidos + opcionais_exigidos):
                    if validar_presenca_documento(doc, d['texto_acumulado'], d['cnpjs']):
                        docs_encontrados.append(doc)

                hoje = datetime.now()
                datas_vencidas = [dt for dt in d['datas_vencimento'] if dt < hoje]

                obrig_entregues = [doc for doc in obrigatorios_exigidos if doc in docs_encontrados]
                obrig_pendentes = [doc for doc in obrigatorios_exigidos if doc not in docs_encontrados]
                opc_entregues = [doc for doc in opcionais_exigidos if doc in docs_encontrados]

                pct_conclusao = ((len(obrig_entregues) / len(obrigatorios_exigidos)) * 100) if obrigatorios_exigidos else 0

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
                        css_status = "status-rejected"
                    elif len(obrig_entregues) > 0:
                        status_final = "DOCUMENTO EM CONFORMIDADE (APROVADO)"
                        css_status = "status-approved"
                        st.balloons()
                    else:
                        status_final = "DOCUMENTO NÃO IDENTIFICADO OU INCOMPLETO"
                        css_status = "status-rejected"
                else:
                    if datas_vencidas or pendencias_criticas.get("Grave"):
                        status_final = "REPROVADO / RISCO GRAVE"
                        css_status = "status-rejected"
                    elif pct_conclusao == 100:
                        status_final = "HOMOLOGADO / APROVADO"
                        css_status = "status-approved"
                        st.balloons()
                    elif pct_conclusao > 0:
                        status_final = "EM HOMOLOGAÇÃO PARCIAL"
                        css_status = "status-partial"
                    else:
                        status_final = "AGUARDANDO DOCUMENTAÇÃO"
                        css_status = "status-rejected"

                st.write(f"**Fornecedor:** {razao_social or 'Não informado'}")
                st.write(f"**Categoria:** {categoria}")
                st.markdown(f'<div class="card-status {css_status}">STATUS: {status_final}</div>', unsafe_allow_html=True)

                if modo_analise != "Análise Pontual (Documento Avulso)":
                    st.progress(pct_conclusao / 100)

                if datas_vencidas:
                    str_venc = [dt.strftime("%d/%m/%Y") for dt in datas_vencidas]
                    st.error(f"❌ Documento(s) com data de validade VENCIDA: {', '.join(str_venc)}")

                c_ent, c_pend = st.columns(2)
                with c_ent:
                    st.markdown("#### ✅ Documentos Validados")
                    if obrig_entregues:
                        for doc in obrig_entregues:
                            st.write(f"✓ {doc}")
                    else:
                        st.write("*Nenhum documento obrigatório validado.*")

                    if opc_entregues:
                        st.markdown("#### 🌟 Opcionais Entregues")
                        for doc in opc_entregues:
                            st.write(f"★ {doc}")

                with c_pend:
                    st.markdown("#### ⏳ Documentos Pendentes")
                    if obrig_pendentes:
                        for doc in obrig_pendentes:
                            st.write(f"○ {doc}")
                    else:
                        st.write("🎉 *Nenhuma pendência documental!*")

                if any(pendencias_criticas.values()):
                    st.markdown("---")
                    st.markdown("### 🚦 Avaliação de Criticidade das Pendências")
                    if pendencias_criticas.get("Grave"):
                        st.error(f"**Pendências Graves (Impedimentos):** {', '.join(pendencias_criticas['Grave'])}")
                    if pendencias_criticas.get("Médio"):
                        st.warning(f"**Pendências Médias (Prazo de Adequação):** {', '.join(pendencias_criticas['Médio'])}")
                    if pendencias_criticas.get("Leve"):
                        st.info(f"**Pendências Leves (Cadastro/Administrativo):** {', '.join(pendencias_criticas['Leve'])}")

                st.markdown("---")
                st.markdown("### ✉️ Resposta Pronta para Envio")
                if modo_analise == "Análise Pontual (Documento Avulso)":
                    texto_email = (
                        f"Prezados,\n\nRealizamos a verificação pontual do documento ({doc_especifico_selecionado}) referente a {razao_social or 'Parceiro'}.\n\n"
                        f"STATUS DA VERIFICAÇÃO: {status_final}\n\n"
                        f"Atenciosamente,\nEquipe de Compliance Yattó"
                    )
                else:
                    texto_email = (
                        f"Prezados,\n\nRecebemos a documentação de compliance de {razao_social or 'Parceiro'}.\n\n"
                        f"STATUS DA HOMOLOGAÇÃO: {status_final} ({round(pct_conclusao, 1)}% concluído)\n\n"
                        f"DOCUMENTOS OBRIGATÓRIOS RECEBIDOS ({len(obrig_entregues)}):\n"
                        + "\n".join([f"- {d}" for d in obrig_entregues])
                        + (f"\n\nDOCUMENTOS OPCIONAIS RECEBIDOS:\n" + "\n".join([f"- {d}" for d in opc_entregues]) if opc_entregues else "")
                        + f"\n\nPENDÊNCIAS PARA CONCLUIR A HOMOLOGAÇÃO ({len(obrig_pendentes)}):\n"
                        + "\n".join([f"- {d}" for d in obrig_pendentes])
                        + "\n\nFicamos no aguardo dos itens pendentes para finalização do cadastro.\n\nAtenciosamente,\nEquipe de Compliance Yattó"
                    )
                st.text_area("Copie o texto abaixo para enviar ao parceiro:", texto_email, height=200)

        else:
            st.info("👈 Faça o upload dos arquivos e clique em 'Mapear CNPJ, CNAEs e Documentos' para iniciar a verificação.")

elif menu == "Matriz de Requisitos Yattó":
    st.title("Matriz Geral de Requisitos de Compliance")
    st.write("Consulte as exigências documentais divididas por categoria de fornecedor:")

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
    st.title("Segurança Jurídica")
    st.write(
        "A Yattó atua como infraestrutura de soluções em economia circular oferecendo diagnósticos, inteligência de dados e execução operacional contínua."
    )
    st.write(
        "Com a entrada em vigor do **Decreto nº 12.688/2025**, a exigência regulatória mudou da simples compensação para a **comprovação de circularidade com dados auditáveis**."
    )
    st.write(
        "Garantir a conformidade documental de todos os parceiros, cooperativas, destinadores e operadores logísticos é o pilar que elimina riscos de sanção regulatória, multas e greenwashing."
    )
