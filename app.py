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
# 2. LOGOTIPO OFICIAL DA YATTÓ NA BARRA LATERAL (ACIMA DA NAVEGAÇÃO)
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
# 3. TABELA DE REFERÊNCIA EXPANDIDA DE CNAES E ATIVIDADES
# ==============================================================================
MAPEAMENTO_CNAE_ATIVIDADES = {
    "4930-2/01": ("Transportador não perigoso", "Transporte rodoviário de cargas não perigosas"),
    "4930-2/02": ("Transportador não perigoso", "Transporte rodoviário de cargas não perigosas (intermunicipal/interestadual)"),
    "4930-2/03": ("Transportador perigoso", "Transporte rodoviário de produtos e resíduos perigosos"),
    "3811-4/00": ("Coletor de resíduos", "Coleta de resíduos não perigosos"),
    "3812-2/00": ("Coletor de resíduos perigosos", "Coleta de resíduos perigosos"),
    "3821-1/00": ("Destinador não perigoso", "Tratamento e disposição de resíduos não perigosos"),
    "3822-0/00": ("Destinador perigoso", "Tratamento e disposição de resíduos perigosos"),
    "3832-7/00": ("Reciclador de plástico", "Recuperação de materiais plásticos"),
    "3831-9/01": ("Reciclador de metais", "Recuperação de sucatas de alumínio"),
    "3831-9/99": ("Reciclador de metais", "Recuperação de materiais metálicos diversos"),
    "3839-4/99": ("Reciclador de outros materiais", "Recuperação de materiais não especificados"),
    "3839-4/01": ("Compostagem", "Usinas de compostagem / tratamento orgânico"),
    "3900-5/00": ("Descontaminador / Gestão", "Descontaminação e serviços especializados de gestão de resíduos"),
    "4687-7/01": ("Comercializador de resíduos", "Comércio atacadista de resíduos de papel e papelão"),
    "4687-7/02": ("Comercializador de resíduos", "Comércio atacadista de resíduos plásticos"),
    "4687-7/03": ("Comercializador de resíduos", "Comércio atacadista de resíduos metálicos e sucatas"),
    "5211-7/01": ("Armazenador", "Armazéns gerais - emissão de warrant"),
    "5211-7/99": ("Armazenador", "Depósitos de mercadorias para terceiros / guarda de materiais"),
    "5250-8/03": ("Operador logístico", "Agenciamento de cargas"),
    "5250-8/04": ("Operador logístico", "Organização logística do transporte de carga"),
    "5250-8/05": ("Operador logístico", "Operador de transporte multimodal - OTM"),
    "5212-5/00": ("Apoio logístico", "Carga e descarga de mercadorias"),
    "5229-0/99": ("Apoio logístico", "Outras atividades auxiliares dos transportes terrestres"),
    "3701-1/00": ("Serviço ambiental", "Esgotamento sanitário e serviços relacionados"),
    "3600-6/01": ("Serviço ambiental", "Captação, tratamento e distribuição de água"),
    "3600-6/02": ("Serviço ambiental", "Distribuição de água por caminhões")
}

# DOCUMENTOS EXIGIDOS POR TIPO DE ATIVIDADE CONFIRMADA
CHECKLIST_POR_ATIVIDADE = {
    "Transportador não perigoso": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "RNTRC ANTT", "Carteira Nacional de Habilitação (CNH)", "Licenciamento do Veículo (CRLV)"],
    "Transportador perigoso": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Certificado de Regularidade - CTF IBAMA", "AATIPP", "Licença ou Certificado Ambiental Estadual", "RNTRC ANTT", "Seguro Ambiental de Carga / PAE", "Amostragem de Treinamento MOPP", "Licenciamento do Veículo (CRLV)"],
    "Coletor de resíduos": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Dispensa ou Licença Ambiental"],
    "Coletor de resíduos perigosos": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Certificado de Regularidade - CTF IBAMA", "Licença ou Certificado Ambiental Estadual", "Seguro Ambiental de Carga / PAE"],
    "Destinador não perigoso": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Dispensa ou Licença Ambiental", "AVCB/CLCB", "Certificado de Regularidade - CTF IBAMA"],
    "Destinador perigoso": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Licença Ambiental para Perigosos", "AVCB/CLCB", "Certificado de Regularidade - CTF IBAMA", "Relatório de Passivo Ambiental / Infração Ambiental"],
    "Reciclador de plástico": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Dispensa ou Licença Ambiental", "AVCB/CLCB", "Certificado de Regularidade - CTF IBAMA"],
    "Reciclador de metais": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Dispensa ou Licença Ambiental", "AVCB/CLCB", "Certificado de Regularidade - CTF IBAMA"],
    "Reciclador de outros materiais": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Dispensa ou Licença Ambiental", "AVCB/CLCB"],
    "Compostagem": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Licença Ambiental de Operação"],
    "Descontaminador / Gestão": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Licença Ambiental", "Certificado de Regularidade - CTF IBAMA"],
    "Comercializador de resíduos": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento"],
    "Armazenador": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "AVCB/CLCB", "Dispensa ou Licença Ambiental"],
    "Operador logístico": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Licença Sanitária", "AVCB/CLCB", "Dispensa ou Licença Ambiental", "Certificado de Regularidade - CTF IBAMA", "CND Federal", "CND Estadual", "CND Municipal", "Certidão Negativa de Débitos Trabalhistas (CNDT)", "Certificado de Regularidade do FGTS", "PGR – Plano de Gerenciamento de Riscos", "PCMSO – Programa de Controle Médico de Saúde Ocupacional"],
    "Apoio logístico": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento"],
    "Serviço ambiental": ["Cartão CNPJ", "Inscrição Estadual Ativa", "Alvará de Funcionamento", "Licença Ambiental"]
}

# REQUISITOS ADICIONAIS POR NATUREZA JURÍDICA
DOCS_POR_NATUREZA = {
    "Cooperativa / Associação": ["Estatuto Social", "Última Ata de Eleição"],
    "Empresa PJ (LTDA, SA, MEI)": [],
    "Transportador PF (Autônomo)": ["Termo LGPD", "Comprovante de Residência"]
}

TODOS_DOCUMENTOS_POSSIVEIS = sorted(list(set(
    doc
    for lista in CHECKLIST_POR_ATIVIDADE.values()
    for doc in lista
) | set(["Estatuto Social", "Última Ata de Eleição", "Termo LGPD", "Comprovante de Residência"])))

# ==============================================================================
# 4. EXTRAÇÃO DE DADOS DOS DOCUMENTOS (PDF / ZIP)
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
    """Extrai CNAEs no formato 0000-0/00 ou 00.00-0-00"""
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
    palavras_chave = ["validade", "válido até", "valido ate", "vencimento", "expira em", "expira"]

    for linha in linhas:
        linha_lower = linha.lower()
        if any(p in linha_lower for p in palavras_chave):
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
# 5. ETAPA 1: IDENTIFICAÇÃO AUTOMÁTICA DE CNAES E POSSÍVEIS ENQUADRAMENTOS
# ==============================================================================

def identificar_enquadramentos_cnae(cnaes_encontrados):
    enquadramentos_detectados = {}
    
    for cnae in cnaes_encontrados:
        if cnae in MAPEAMENTO_CNAE_ATIVIDADES:
            categoria, desc = MAPEAMENTO_CNAE_ATIVIDADES[cnae]
            if categoria not in enquadramentos_detectados:
                enquadramentos_detectados[categoria] = []
            enquadramentos_detectados[categoria].append(f"{cnae} ({desc})")
            
    return enquadramentos_detectados

# ==============================================================================
# 6. INTERFACE STREAMLIT (FLUXO EM 3 ETAPAS)
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
        '<div class="sub-header">Classificação automatizada por CNPJ/CNAE e validação de compliance | Yattó</div>',
        unsafe_allow_html=True,
    )

    modo_analise = st.radio(
        "Escopo da Análise:",
        [
            "Análise Completa / Homologação de Operação",
            "Análise Pontual (Documento Avulso)"
        ],
        horizontal=True
    )

    st.markdown("---")

    col_files, col_process = st.columns([1.2, 1.8])

    with col_files:
        st.subheader("1. Identificação Automática (Upload)")
        razao_social = st.text_input("Razão Social / Identificação do Fornecedor:", placeholder="Ex: Operador Logístico Sp Ltda")
        arquivos = st.file_uploader(
            "Anexe os documentos do parceiro (.PDF ou .ZIP):",
            type=["pdf", "zip"],
            accept_multiple_files=True
        )

        btn_processar_etapa1 = st.button("🔍 Mapear CNPJ, CNAEs e Documentos")

    # Inicializar estado da sessão para armazenar resultados do lote
    if "resultado_leitura" not in st.session_state:
        st.session_state.resultado_leitura = None

    if btn_processar_etapa1:
        if not arquivos:
            st.warning("Por favor, faça o upload dos arquivos para análise.")
        else:
            with st.spinner("Lendo arquivos, extraindo CNPJs e classificando CNAEs..."):
                lista_pdfs = processar_arquivos_upload(arquivos)
                
                texto_total = ""
                cnpjs_encontrados = []
                cnaes_encontrados = []
                datas_vencimento = []

                for nome_pdf, pdf_bytes in lista_pdfs:
                    texto = extrair_texto_pdf(pdf_bytes)
                    texto_total += f"\n--- {nome_pdf} ---\n" + texto
                    cnpjs_encontrados.extend(extrair_cnpjs(texto))
                    cnaes_encontrados.extend(extrair_cnaes_completos(texto))
                    datas_vencimento.extend(extrair_datas_validade(texto))

                cnpjs_unicos = list(set(cnpjs_encontrados))
                cnaes_unicos = list(set(cnaes_encontrados))
                enquadramentos = identificar_enquadramentos_cnae(cnaes_unicos)

                st.session_state.resultado_leitura = {
                    "lista_pdfs": lista_pdfs,
                    "texto_total": texto_total,
                    "cnpjs": cnpjs_unicos,
                    "cnaes": cnaes_unicos,
                    "enquadramentos": enquadramentos,
                    "datas_vencimento": datas_vencimento
                }

    with col_process:
        st.subheader("2. Confirmação do Enquadramento e Validação")

        if st.session_state.resultado_leitura:
            dados = st.session_state.resultado_leitura
            
            st.info(f"**CNPJ(s) Mapeado(s):** {', '.join(dados['cnpjs']) if dados['cnpjs'] else 'Nenhum formato padrão extraído'}")
            st.write(f"**CNAEs Identificados:** {', '.join(dados['cnaes']) if dados['cnaes'] else 'Nenhum CNAE explícito localizado no texto'}")

            st.markdown("#### ☑️ Enquadramentos Suportados pelos CNAEs Encontrados:")
            if dados['enquadramentos']:
                for cat_detectada, lista_detalhes in dados['enquadramentos'].items():
                    st.success(f"✓ **{cat_detectada}:** {'; '.join(lista_detalhes)}")
            else:
                st.warning("⚠️ Não foi possível determinar automaticamente a atividade pelo CNAE. Selecione manualmente abaixo.")

            st.markdown("---")
            st.markdown("#### Confirmar Dados da Operação para Homologação:")
            
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                # Seleciona a atividade efetivamente realizada para a operação
                opcoes_atividades_possoveisc = list(CHECKLIST_POR_ATIVIDADE.keys())
                
                # Pre-seleciona a primeira atividade detectada pelos CNAEs se houver
                index_default = 0
                if dados['enquadramentos']:
                    primeira_det = list(dados['enquadramentos'].keys())[0]
                    if primeira_det in opcoes_atividades_possoveisc:
                        index_default = opcoes_atividades_possoveisc.index(primeira_det)

                atividade_confirmada = st.selectbox(
                    "Atividade Efetiva na Operação:",
                    opcoes_atividades_possoveisc,
                    index=index_default
                )

            with col_sel2:
                # Característica do Fornecedor / Natureza Jurídica
                natureza_confirmada = st.selectbox(
                    "Característica / Natureza Jurídica:",
                    list(DOCS_POR_NATUREZA.keys())
                )

            doc_especifico_selecionado = None
            if modo_analise == "Análise Pontual (Documento Avulso)":
                doc_especifico_selecionado = st.selectbox(
                    "Escolha o documento a ser verificado pontualmente:",
                    TODOS_DOCUMENTOS_POSSIVEIS
                )

            btn_executar_homologacao = st.button("🚀 Emitir Parecer de Compliance")

            if btn_executar_homologacao:
                st.markdown("---")
                st.markdown("### 3. Parecer Final de Compliance Documental")

                if modo_analise == "Análise Pontual (Documento Avulso)":
                    checklist_exigido = [doc_especifico_selecionado]
                else:
                    checklist_base = CHECKLIST_POR_ATIVIDADE.get(atividade_confirmada, [])
                    checklist_natureza = DOCS_POR_NATUREZA.get(natureza_confirmada, [])
                    checklist_exigido = list(set(checklist_base + checklist_natureza))

                # Verificação de presença documental no texto extraído
                docs_validados = []
                texto_busca = dados['texto_total'].lower()

                for doc in checklist_exigido:
                    termo = doc.lower().split()[0]
                    if termo in texto_busca:
                        docs_validados.append(doc)

                docs_pendentes = [d for d in checklist_exigido if d not in docs_validados]

                hoje = datetime.now()
                datas_vencidas = [d for d in dados['datas_vencimento'] if d < hoje]

                pct_conclusao = (len(docs_validados) / len(checklist_exigido) * 100) if checklist_exigido else 0

                # Status Final
                if datas_vencidas:
                    status_final = "🔴 REPROVADO (DOCUMENTO VENCIDO DETECTADO)"
                    css_status = "status-rejected"
                elif pct_conclusao == 100:
                    status_final = "🟢 HOMOLOGADO / EM CONFORMIDADE"
                    css_status = "status-approved"
                    st.balloons()
                elif pct_conclusao > 0:
                    status_final = f"🟡 HOMOLOGAÇÃO PARCIAL ({round(pct_conclusao, 1)}% Concluído)"
                    css_status = "status-partial"
                else:
                    status_final = "🔴 AGUARDANDO DOCUMENTAÇÃO"
                    css_status = "status-rejected"

                st.markdown(f'<div class="card-status {css_status}">STATUS: {status_final}</div>', unsafe_allow_html=True)

                if modo_analise != "Análise Pontual (Documento Avulso)":
                    st.progress(pct_conclusao / 100)

                if datas_vencidas:
                    str_venc = [d.strftime("%d/%m/%Y") for d in datas_vencidas]
                    st.error(f"⚠️ Documento(s) com data de validade vencida identificados: {', '.join(str_venc)}")

                col_val, col_pend = st.columns(2)
                with col_val:
                    st.markdown("#### ✅ Documentos Validados")
                    if docs_validados:
                        for d in docs_validados:
                            st.write(f"✓ {d}")
                    else:
                        st.write("*Nenhum documento do checklist localizado.*")

                with col_pend:
                    st.markdown("#### ⏳ Documentos Pendentes")
                    if docs_pendentes:
                        for d in docs_pendentes:
                            st.write(f"○ {d}")
                    else:
                        st.write("🎉 *Nenhuma pendência documental!*")

                st.markdown("---")
                st.markdown("### ✉️ Resposta Pronta para Comunicação")
                texto_email = (
                    f"Prezados,\n\nRealizamos a análise documental referente a {razao_social or 'Parceiro'}.\n\n"
                    f"ENQUADRAMENTO OPERACIONAL: {atividade_confirmada} ({natureza_confirmada})\n"
                    f"STATUS DA HOMOLOGAÇÃO: {status_final}\n\n"
                    f"DOCUMENTOS VALIDADOS ({len(docs_validados)}):\n"
                    + "\n".join([f"- {d}" for d in docs_validados])
                    + f"\n\nDOCUMENTOS PENDENTES PARA CONCLUIR O CADASTRO ({len(docs_pendentes)}):\n"
                    + "\n".join([f"- {d}" for d in docs_pendentes])
                    + "\n\nFicamos no aguardo das pendências para liberação operacional.\n\nAtenciosamente,\nEquipe de Compliance Yattó"
                )
                st.text_area("Copie o texto para envio ao fornecedor:", texto_email, height=180)

        else:
            st.info("👈 Faça o upload dos arquivos ao lado e clique em 'Mapear CNPJ, CNAEs e Documentos' para iniciar a homologação automatizada.")

elif menu == "Matriz de Requisitos Yattó":
    st.title("Matriz Geral de Requisitos por Atividade Operacional")
    st.write("Consulte as exigências documentais específicas para cada escopo de atuação:")

    for ativ, docs in CHECKLIST_POR_ATIVIDADE.items():
        with st.expander(f"📌 {ativ}"):
            st.write("**Documentos Exigidos para a Atividade:**", ", ".join(docs))

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
