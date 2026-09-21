import base64
import io
import re
import zipfile
from datetime import datetime
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA & ESTILO VISUAL YATTÓ COM IMAGEM DE FUNDO EMBUTIDA
# ==============================================================================
st.set_page_config(
    page_title="Central de Compliance | Yattó",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKGROUND_B64 = """iVBORw0KGgoAAAANSUhEUgAAA8YAAAHRCAYAAACo3aDLAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAP+lSURBVHhe7N0HWBRH3wfwX/pSpSsgNkBQUBAVGxZsWRNLIjY0/mKMUYstUWPUaGJLL/42Y4s1GqPGXhDFXhBsqChFUR4sCNL7s7s3x1044O6O0f+/3/P8/e21+m3szszN3fA8"""

st.markdown(
    f"""
    <style>
    .stApp {{
        background: url("data:image/png;base64,{BACKGROUND_B64}") no-repeat center center fixed;
        background-size: cover;
    }}

    [data-testid="stAppViewContainer"] {{
        background: url("data:image/png;base64,{BACKGROUND_B64}") no-repeat center center fixed;
        background-size: cover;
    }}
    
    div[data-testid="stSidebar"] {{
        background-color: rgba(244, 246, 248, 0.88);
        border-right: 2px solid #009BDB;
    }}

    .stMainBlockContainer {{
        background-color: rgba(255, 255, 255, 0.90);
        border-radius: 12px;
        padding: 25px;
        margin-top: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }}
    
    .main-header {{ font-size: 26px; font-weight: bold; color: #009BDB; margin-bottom: 5px; }}
    .sub-header {{ font-size: 14px; color: #87868A; margin-bottom: 25px; }}
    
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

TODOS_DOCUMENTOS_POSSIVEIS = sorted(list(set(
    doc
    for cat_data in REQUISITOS.values()
    for lista_docs in cat_data.values()
    for doc in lista_docs
)))

# ==============================================================================
# 3. LEITURA DE PDFS, ZIPS & EXTRAÇÃO DE DADOS
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
    """Extrai os arquivos do upload, descompactando arquivos .ZIP se houver."""
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

def analisar_documentos(categoria, lista_pdfs, modo_analise, doc_especifico_selecionado):
    reqs = REQUISITOS.get(categoria, {})

    if modo_analise == "Análise Pontual (Documento Avulso)":
        total_exigido = [doc_especifico_selecionado]
    else:
        todos_obrigatorios = (
            reqs.get("obrigatorios_base", [])
            + reqs.get("fiscais_cnd", [])
            + reqs.get("sst_seguranca", [])
        )
        especificos = reqs.get("especificos_operacao", [])
        total_exigido = list(set(todos_obrigatorios + especificos))

    docs_encontrados = []
    cnpjs_encontrados = []
    datas_vencimento = []
    relatorio_erros = []

    for nome_pdf, pdf_bytes in lista_pdfs:
        texto = extrair_texto_pdf(pdf_bytes)

        cnpjs_encontrados.extend(extrair_cnpjs(texto))
        datas_vencimento.extend(extrair_datas(texto))

        texto_busca = (nome_pdf + " " + texto).lower()
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

    if datas_vencidas:
        str_venc = [d.strftime("%d/%m/%Y") for d in datas_vencidas]
        relatorio_erros.append(f"❌ Documento(s) com data VENCIDA: {', '.join(str_venc)}")

    entregues = [d for d in total_exigido if d in docs_encontrados]
    pendentes = [d for d in total_exigido if d not in docs_encontrados]

    pct_conclusao = (
        (len(entregues) / len(total_exigido) * 100) if total_exigido else 0
    )

    if modo_analise == "Análise Pontual (Documento Avulso)":
        if datas_vencidas:
            status_final = "DOCUMENTO REPROVADO (VENCIDO)"
        elif len(entregues) > 0 and not relatorio_erros:
            status_final = "DOCUMENTO EM CONFORMIDADE (APROVADO)"
        else:
            status_final = "DOCUMENTO NÃO IDENTIFICADO OU INCOMPLETO"
    else:
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
                            categoria, lista_pdfs, modo_analise, doc_especifico_selecionado
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

                        if res["erros"]:
                            st.markdown("### ⚠️ Inconformidades Detectadas")
                            for err in res["erros"]:
                                st.error(err)

                        if res["cnpjs"]:
                            st.info(f"**CNPJ(s) Identificados nos PDFs:** {', '.join(res['cnpjs'])}")

                        c_ent, c_pend = st.columns(2)

                        with c_ent:
                            st.markdown("#### ✅ Documentos Validados")
                            if res["entregues"]:
                                for d in res["entregues"]:
                                    st.write(f"✓ {d}")
                            else:
                                st.write("*Nenhum documento validado ainda.*")

                        with c_pend:
                            st.markdown("#### ⏳ Documentos Pendentes")
                            if res["pendentes"]:
                                for d in res["pendentes"]:
                                    st.write(f"○ {d}")
                            else:
                                st.write("🎉 *Nenhuma pendência para esta análise!*")

                        st.markdown("---")
                        st.markdown("### ✉️ Resposta Pronta para Envio")
                        if modo_analise == "Análise Pontual (Documento Avulso)":
                            texto_email = (
                                f"Prezados,\n\nRealizamos a verificação pontual do documento ({doc_especifico_selecionado}) referente a {razao_social}.\n\n"
                                f"STATUS DA VERIFICAÇÃO: {res['status']}\n\n"
                                f"Atenciosamente,\nEquipe de Compliance Yattó"
                            )
                        else:
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
