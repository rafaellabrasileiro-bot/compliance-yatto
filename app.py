import re
from datetime import datetime
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA & ESTILO VISUAL YATTÓ COM IMAGEM DE FUNDO
# ==============================================================================
st.set_page_config(
    page_title="Central de Compliance | Yattó",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Aplicação da Imagem de Fundo (fundo.png do GitHub) */
    .stApp {
        background: url("app/static/fundo.png") no-repeat center center fixed;
        background-size: cover;
    }

    /* Regra de apoio para busca direta no repositório */
    [data-testid="stAppViewContainer"] {
        background: url("fundo.png") no-repeat center center fixed;
        background-size: cover;
    }
    
    /* Transparência e leiturabilidade dos blocos sobre o fundo */
    div[data-testid="stSidebar"] {
        background-color: rgba(244, 246, 248, 0.92);
        border-right: 2px solid #009BDB;
    }

    .stMainBlockContainer {
        background-color: rgba(255, 255, 255, 0.90);
        border-radius: 12px;
        padding: 25px;
        margin-top: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }
    
    /* Cabeçalhos */
    .main-header { font-size: 26px; font-weight: bold; color: #009BDB; margin-bottom: 5px; }
    .sub-header { font-size: 14px; color: #87868A; margin-bottom: 25px; }
    
    /* Estilização dos Botões */
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
    
    /* Cartões de Status */
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

    /* Personalização da Barra de Progresso */
    .stProgress > div > div > div > div {
        background-color: #93BA1F;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. MATRIZ INTEGRADA DE REQUISITOS (INCLUINDO CARGILL / ÓLEO)
# ==============================================================================
REQUISITOS = {
    "Operador Logístico de Óleo (Cargill)": {
        "obrigatorios_base": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "Certificado de Regularidade IBAMA - CTF/APP",
            "Plano de Atendimento a Emergências (PAE)",
            "Licença Sanitária",
        ],
        "fiscais_cnd": [
            "Certidão Negativa de Débitos Trabalhistas",
            "CND Federal",
            "CND Estadual",
            "CND Municipal",
            "Certificado de Regularidade do FGTS",
        ],
        "sst_seguranca": [
            "AVCB ou CLCB",
            "PGR - Plano de Gerenciamento de Riscos",
            "PCMSO - Programa de Controle Médico de Saúde Ocupacional",
            "Ficha de Entrega de EPI’s / ASOs",
            "Certificado de Treinamento (NR01, NR06 e/ou NR12)",
        ],
        "especificos_operacao": [
            "Relatório de Inspeção de Caldeiras",
            "Certificado de Treinamento de Segurança na Operação de Caldeiras (NR 13)",
            "Certificado de Destinação Final da Borra Orgânica",
            "Certificado de Destinação do PET para Reciclagem",
            "Nota Fiscal de Venda do Óleo",
            "Comprovante de Medidas Preventivas e Corretivas de Controle de Pragas",
        ],
    },
    "Cooperativa": {
        "obrigatorios_base": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "Estatuto",
            "Última Ata de Eleição",
        ],
        "fiscais_cnd": [
            "CND Trabalhista",
            "CND Federal",
            "CND Estadual",
            "CND Municipal",
        ],
        "sst_seguranca": ["AVCB ou CLCB"],
        "especificos_operacao": ["Certificado de Regularidade IBAMA - CTF/APP"],
    },
    "Destinador": {
        "obrigatorios_base": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
        ],
        "fiscais_cnd": ["CND Federal", "CND Estadual", "CND Municipal"],
        "sst_seguranca": ["AVCB ou CLCB"],
        "especificos_operacao": [
            "Certificado de Regularidade IBAMA - CTF/APP",
            "ISO 14001",
            "ISO 9001",
        ],
    },
    "Transportador PJ": {
        "obrigatorios_base": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "RNTRC ANTT",
        ],
        "fiscais_cnd": ["CND Federal"],
        "sst_seguranca": ["CNH", "CRLV"],
        "especificos_operacao": ["Termo LGPD"],
    },
    "Transportador PF": {
        "obrigatorios_base": ["CNH", "CRLV", "RNTRC ANTT", "Termo LGPD"],
        "fiscais_cnd": [],
        "sst_seguranca": [],
        "especificos_operacao": ["Comprovante de Residência"],
    },
    "Transportador (Resíduos Perigosos)": {
        "obrigatorios_base": [
            "Cartão CNPJ",
            "Inscrição Estadual Ativa",
            "Alvará de Funcionamento",
            "Certificado de Regularidade IBAMA - CTF/APP",
            "AATIPP",
            "Licença Ambiental Estadual",
            "RNTRC ANTT",
            "Seguro Ambiental / PAE",
        ],
        "fiscais_cnd": ["CND Federal"],
        "sst_seguranca": ["CNH com MOPP", "CRLV"],
        "especificos_operacao": [
            "ISO 14001",
            "Ficha de Emergência",
            "Relatório Passivo Ambiental",
        ],
    },
}

# ==============================================================================
# 3. LEITURA DE PDFS & EXTRAÇÃO DE DADOS
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

def extrair_cnpjs(texto):
    padrao = r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"
    return list(set(re.findall(padrao, texto)))

def extrair_datas(texto):
    padrao = r"\b\d{2}/\d{2}/\d{4}\b"
    datas_str = re.findall(padrao, texto)
    datas_validas = []
    hoje = datetime.now()

    for d in datas_str:
        try:
            dt = datetime.strptime(d, "%d/%m/%Y")
            if dt.year >= hoje.year - 1 and dt.year <= hoje.year + 10:
                datas_validas.append(dt)
        except ValueError:
            continue
    return datas_validas

# ==============================================================================
# 4. MOTOR DE ANÁLISE DE COMPLIANCE
# ==============================================================================

def analisar_documentos(categoria, arquivos_uploaded, selecionados_manuais):
    reqs = REQUISITOS.get(categoria, {})

    todos_obrigatorios = (
        reqs.get("obrigatorios_base", [])
        + reqs.get("fiscais_cnd", [])
        + reqs.get("sst_seguranca", [])
    )
    especificos = reqs.get("especificos_operacao", [])
    total_exigido = list(set(todos_obrigatorios + especificos))

    docs_encontrados = list(selecionados_manuais)
    cnpjs_encontrados = []
    datas_vencimento = []
    relatorio_erros = []

    if arquivos_uploaded:
        for uploaded_file in arquivos_uploaded:
            nome = uploaded_file.name
            texto = extrair_texto_pdf(uploaded_file.read())

            cnpjs_encontrados.extend(extrair_cnpjs(texto))
            datas_vencimento.extend(extrair_datas(texto))

            texto_busca = (nome + " " + texto).lower()
            for doc in total_exigido:
                termo = doc.lower().split()[0]
                if termo in texto_busca and doc not in docs_encontrados:
                    docs_encontrados.append(doc)

    cnpjs_unicos = list(set(cnpjs_encontrados))
    if len(cnpjs_unicos) > 1:
        relatorio_erros.append(
            f"⚠️ Divergência de CNPJs nos PDFs: {', '.join(cnpjs_unicos)}"
        )

    hoje = datetime.now()
    datas_vencidas = [d for d in datas_vencimento if d < hoje]
    datas_proximas = [
        d for d in datas_vencimento if 0 <= (d - hoje).days <= 30
    ]

    if datas_vencidas:
        str_venc = [d.strftime("%d/%m/%Y") for d in datas_vencidas]
        relatorio_erros.append(f"❌ Documento(s) com data VENCIDA: {', '.join(str_venc)}")

    if datas_proximas:
        str_prox = [d.strftime("%d/%m/%Y") for d in datas_proximas]
        relatorio_erros.append(
            f"⚠️ Documento(s) a vencer nos próximos 30 dias: {', '.join(str_prox)}"
        )

    entregues = [d for d in total_exigido if d in docs_encontrados]
    pendentes = [d for d in total_exigido if d not in docs_encontrados]

    pct_conclusao = (
        (len(entregues) / len(total_exigido) * 100) if total_exigido else 0
    )

    if datas_vencidas:
        status_final = "REPROVADO (DOC VENCIDO)"
    elif pct_conclusao == 100 and not relatorio_erros:
        status_final = "HOMOLOGADO / APROVADO"
    elif pct_conclusao > 0:
        status_final = "EM HOMOLOGAÇÃO PARCIAL"
    else:
        status_final = "AGUARDANDO DOCUMENTAÇÃO"

    return {
        "status": status_final,
        "progresso": round(pct_conclusao, 1),
        "cnpjs": cnpjs_unicos,
        "entregues": entregues,
        "pendentes": pendentes,
        "erros": relatorio_erros,
    }

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
        '<div class="main-header">Central de Análises de Compliance</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">Validação automatizada e acompanhamento de homologações parciais | Yattó</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.1, 1.9])

    with col_left:
        st.subheader("1. Dados do Parceiro")
        razao_social = st.text_input(
            "Razão Social / Nome", placeholder="Ex: Operador Logístico Óleo Sp"
        )
        categoria = st.selectbox("Categoria do Fornecedor", list(REQUISITOS.keys()))

        st.subheader("2. Anexo dos PDFs")
        arquivos = st.file_uploader(
            "Upload dos arquivos em PDF:", type=["pdf"], accept_multiple_files=True
        )

        st.subheader("3. Checklist Manual (Opcional)")
        st.caption("Marque os documentos que você já conferiu manualmente:")

        reqs_cat = REQUISITOS[categoria]
        todos_docs = list(
            set(
                reqs_cat.get("obrigatorios_base", [])
                + reqs_cat.get("fiscais_cnd", [])
                + reqs_cat.get("sst_seguranca", [])
                + reqs_cat.get("especificos_operacao", [])
            )
        )

        docs_manuais = []
        for doc in todos_docs:
            if st.checkbox(doc, key=f"chk_{doc}"):
                docs_manuais.append(doc)

        btn_analisar = st.button("🔍 Executar Análise de Compliance")

    with col_right:
        st.subheader("Parecer do Análise de Compliance")

        if btn_analisar:
            if not razao_social:
                st.warning(
                    "Por favor, insira a Razão Social do fornecedor para prosseguir."
                )
            else:
                with st.spinner("Analisando PDFs e cruzando requisitos..."):
                    res = analisar_documentos(categoria, arquivos, docs_manuais)

                st.write(f"**Fornecedor:** {razao_social}")
                st.write(f"**Categoria:** {categoria}")

                status = res["status"]
                if "APROVADO" in status:
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

                st.progress(res["progresso"] / 100)

                if res["erros"]:
                    st.markdown("### ⚠️ Inconformidades Detectadas")
                    for err in res["erros"]:
                        st.error(err)

                if res["cnpjs"]:
                    st.info(f"**CNPJ(s) Identificados nos PDFs:** {', '.join(res['cnpjs'])}")

                c_ent, c_pend = st.columns(2)

                with c_ent:
                    st.markdown("#### ✅ Documentos Entregues")
                    if res["entregues"]:
                        for d in res["entregues"]:
                            st.write(f"✓ {d}")
                    else:
                        st.write("*Nenhum documento identificado ainda.*")

                with c_pend:
                    st.markdown("#### ⏳ Documentos Pendentes")
                    if res["pendentes"]:
                        for d in res["pendentes"]:
                            st.write(f"○ {d}")
                    else:
                        st.write("🎉 *Nenhuma pendência documental!*")

                st.markdown("---")
                st.markdown("### ✉️ Resposta Pronta para Envio")
                texto_email = (
                    f"Prezados,\n\nRecebemos a documentação de compliance de {razao_social}.\n\n"
                    f"STATUS DA HOMOLOGAÇÃO: {res['status']} ({res['progresso']}% concluído)\n\n"
                    f"DOCUMENTOS RECEBIDOS ({len(res['entregues'])}):\n"
                    + "\n".join([f"- {d}" for d in res["entregues"]])
                    + f"\n\nPENDÊNCIAS PARA CONCLUIR A HOMOLOGAÇÃO ({len(res['pendentes'])}):\n"
                    + "\n".join([f"- {d}" for d in res["pendentes"]])
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
        with st.expander(f"📌 {cat}"):
            st.write(
                "**Geral & Licenciamento:**",
                ", ".join(reqs.get("obrigatorios_base", [])),
            )
            st.write(
                "**Certidões & Fiscais:**", ", ".join(reqs.get("fiscais_cnd", []))
            )
            st.write(
                "**SST / Segurança do Trabalho:**",
                ", ".join(reqs.get("sst_seguranca", [])),
            )
            st.write(
                "**Específicos / Operação:**",
                ", ".join(reqs.get("especificos_operacao", [])),
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
