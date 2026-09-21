from datetime import datetime
import re
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA & IDENTIDADE YATTÓ
# ==========================================
st.set_page_config(
    page_title="Central de Compliance | Yattó",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização customizada Yattó
st.markdown(
    """
    <style>
    .main-header { font-size: 26px; font-weight: bold; color: #009bdb; }
    .sub-header { font-size: 14px; color: #87868a; margin-bottom: 20px; }
    .stButton>button { background-color: #009bdb; color: white; border-radius: 6px; font-weight: bold; }
    .stButton>button:hover { background-color: #240085; color: white; }
    .status-approved { background-color: #d4edda; color: #155724; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
    .status-pending { background-color: #fff3cd; color: #856404; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
    .status-rejected { background-color: #f8d7da; color: #721c24; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. DEFINIÇÃO DA MATRIZ DE REQUISITOS YATTÓ
# ==========================================
REQUISITOS = {
    "Cooperativa": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "Estatuto",
            "Última Ata de Eleição",
            "CND Trabalhista",
            "CND Federal/Estadual/Municipal",
        ],
        "opcionais": ["AVCB/CLCB", "CTF IBAMA"],
    },
    "Destinador": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "AVCB/CLCB",
            "CTF IBAMA",
        ],
        "opcionais": ["ISO 14001", "ISO 9001"],
    },
    "Transportador PJ": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual",
            "Alvará de Funcionamento",
            "Dispensa ou Licença Ambiental",
            "RNTRC ANTT",
            "CNH",
            "CRLV",
        ],
        "opcionais": ["Termo LGPD", "ISO 14001"],
    },
    "Transportador PF": {
        "obrigatorios": ["CNH", "CRLV", "RNTRC ANTT", "Termo LGPD"],
        "opcionais": ["Comprovante de Residência"],
    },
    "Transportador (Resíduos Perigosos)": {
        "obrigatorios": [
            "Cartão CNPJ",
            "Inscrição Estadual",
            "Alvará de Funcionamento",
            "CTF IBAMA",
            "AATIPP",
            "Licença Ambiental Estadual",
            "RNTRC ANTT",
            "Seguro Ambiental / PAE",
            "Treinamento MOPP",
            "CRLV",
        ],
        "opcionais": [
            "ISO 14001",
            "ISO 9001",
            "Ficha de Emergência",
            "Relatório Passivo Ambiental",
        ],
    },
}

# ==========================================
# 3. FUNÇÕES DE LEITURA E VALIDAÇÃO DE PDF
# ==========================================


def extrair_texto_pdf(file_bytes):
  """Extrai o texto contido nos arquivos PDF enviados."""
  try:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    texto = ""
    for page in doc:
      texto += page.get_text() + "\n"
    return texto
  except Exception:
    return ""


def extrair_cnpjs(texto):
  """Encontra padrões de CNPJ no texto extraído."""
  padrao = r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"
  cnpjs = re.findall(padrao, texto)
  return list(set(cnpjs))


def extrair_datas(texto):
  """Encontra possíveis datas de validade no PDF (DD/MM/AAAA)."""
  padrao = r"\b\d{2}/\d{2}/\d{4}\b"
  datas_str = re.findall(padrao, texto)
  datas_validas = []
  hoje = datetime.now()

  for d in datas_str:
    try:
      dt = datetime.strptime(d, "%d/%m/%Y")
      # Filtra datas plausíveis de validade
      if dt.year >= hoje.year - 1 and dt.year <= hoje.year + 10:
        datas_validas.append(dt)
    except ValueError:
      continue

  return datas_validas


def analisar_documentos(categoria, arquivos_uploaded):
  """Executa o cruzamento das regras de compliance."""
  reqs = REQUISITOS.get(categoria, {"obrigatorios": [], "opcionais": []})
  documentos_encontrados = {}
  cnpjs_encontrados = []
  datas_vencimento = []
  relatorio_erros = []

  # Leitura de cada PDF enviado
  for uploaded_file in arquivos_uploaded:
    nome_arquivo = uploaded_file.name
    file_bytes = uploaded_file.read()
    texto_pdf = extrair_texto_pdf(file_bytes)

    # Coleta CNPJs e Datas
    cnpjs_encontrados.extend(extrair_cnpjs(texto_pdf))
    datas_vencimento.extend(extrair_datas(texto_pdf))

    # Identificação de tipo de documento por palavras-chave no nome ou conteúdo
    texto_low = (nome_arquivo + " " + texto_pdf).lower()
    for doc_req in reqs["obrigatorios"] + reqs["opcionais"]:
      # Mapeamento simplificado de termos
      termo_chave = doc_req.lower().split()[0]
      if termo_chave in texto_low:
        documentos_encontrados[doc_req] = True

  # 1. Checagem de Documentos Obrigatórios
  docs_faltantes = [
      doc
      for doc in reqs["obrigatorios"]
      if doc not in documentos_encontrados
  ]
  if docs_faltantes:
    relatorio_erros.append(
        f"❌ Documentos Obrigatórios Faltantes: {', '.join(docs_faltantes)}"
    )

  # 2. Checagem de Divergência de CNPJ
  cnpjs_unicos = list(set(cnpjs_encontrados))
  if len(cnpjs_unicos) > 1:
    relatorio_erros.append(
        f"⚠️ Divergência de CNPJ detectada entre arquivos: {', '.join(cnpjs_unicos)}"
    )

  # 3. Checagem de Validade
  hoje = datetime.now()
  datas_vencidas = [d for d in datas_vencimento if d < hoje]
  datas_proximas = [
      d for d in datas_vencimento if 0 <= (d - hoje).days <= 30
  ]

  if datas_vencidas:
    datas_str = [d.strftime("%d/%m/%Y") for d in datas_vencidas]
    relatorio_erros.append(
        f"❌ Documento(s) com data VENCIDA identificada: {', '.join(datas_str)}"
    )

  if datas_proximas:
    datas_str = [d.strftime("%d/%m/%Y") for d in datas_proximas]
    relatorio_erros.append(
        f"⚠️ Documento(s) próximo(s) do vencimento (30 dias):"
        f" {', '.join(datas_str)}"
    )

  # Definir Status Final
  if any("❌" in e for e in relatorio_erros):
    status_final = "REPROVADO"
  elif any("⚠️" in e for e in relatorio_erros) or len(
      documentos_encontrados
  ) < len(reqs["obrigatorios"]):
    status_final = "PENDENTE"
  else:
    status_final = "APROVADO"

  return {
      "status": status_final,
      "cnpjs": cnpjs_unicos,
      "docs_presentes": list(documentos_encontrados.keys()),
      "erros": relatorio_erros,
      "total_arquivos": len(arquivos_uploaded),
  }


# ==========================================
# 4. INTERFACE DO USUÁRIO (STREAMLIT)
# ==========================================

# Sidebar
st.sidebar.image(
    "https://www.yatto.com.br/wp-content/uploads/2021/08/logo-yatto.png",
    width=160,
)
st.sidebar.title("Navegação")
menu = st.sidebar.radio(
    "Ir para:",
    [
        "Nova Análise de Documentos",
        "Matriz de Requisitos (Checklist)",
        "Sobre a Yattó",
    ],
)

if menu == "Nova Análise de Documentos":
  st.markdown(
      '<div class="main-header">Central de Análises de Compliance</div>',
      unsafe_allow_html=True,
  )
  st.markdown(
      '<div class="sub-header">Automação de verificação de documentação para'
      " conformidade com o Decreto 12.688/2025</div>",
      unsafe_allow_html=True,
  )

  col1, col2 = st.columns([1, 2])

  with col1:
    st.subheader("1. Informações do Parceiro")
    razao_social = st.text_input("Razão Social do Fornecedor")
    categoria = st.selectbox("Categoria do Fornecedor", list(REQUISITOS.keys()))

    st.subheader("2. Anexo dos PDFs")
    arquivos = st.file_uploader(
        "Selecione todos os arquivos PDF do fornecedor:",
        type=["pdf"],
        accept_multiple_files=True,
    )

    btn_analisar = st.button("🔍 Executar Verificação Automática")

  with col2:
    st.subheader("3. Resultado da Auditoria")

    if btn_analisar:
      if not razao_social:
        st.warning(
            "Por favor, informe a Razão Social do parceiro antes de analisar."
        )
      elif not arquivos:
        st.warning("Por favor, anexe ao menos um arquivo PDF para análise.")
      else:
        with st.spinner("Lendo PDFs e cruzando regras de compliance..."):
          resultado = analisar_documentos(categoria, arquivos)

        # Exibição do Status
        st.write(f"**Parceiro:** {razao_social}")
        st.write(f"**Categoria:** {categoria}")

        if resultado["status"] == "APROVADO":
          st.success("✅ **STATUS FINAL: APROVADO**")
          st.balloons()
        elif resultado["status"] == "PENDENTE":
          st.warning("⚠️ **STATUS FINAL: PENDENTE / ATENÇÃO**")
        else:
          st.error("❌ **STATUS FINAL: REPROVADO**")

        st.markdown("---")
        st.subheader("Detalhamento da Análise")

        # Exibir CNPJs identificados
        if resultado["cnpjs"]:
          st.info(f"**CNPJ(s) Identificado(s):** {', '.join(resultado['cnpjs'])}")
        else:
          st.write("Nenhum CNPJ formatado encontrado nos PDFs.")

        # Exibir Inconformidades / Alertas
        if resultado["erros"]:
          st.write("**Inconformidades e Observações:**")
          for err in resultado["erros"]:
            st.write(f"- {err}")
        else:
          st.write(
              "✅ Nenhuma inconformidade de validade ou documentação foi"
              " identificada."
          )

        # Download do Relatório
        relatorio_txt = (
            f"PARECER DE COMPLIANCE YATTÓ\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"Parceiro: {razao_social}\nCategoria: {categoria}\nStatus:"
            f" {resultado['status']}\n\nObservações:\n"
            + "\n".join(resultado["erros"])
        )

        st.download_button(
            label="📄 Baixar Parecer Técnico (TXT)",
            data=relatorio_txt,
            file_name=f"Parecer_Compliance_{razao_social.replace(' ', '_')}.txt",
            mime="text/plain",
        )

elif menu == "Matriz de Requisitos (Checklist)":
  st.title("Matriz de Requisitos de Compliance Yattó")
  st.write(
      "Documentos obrigatórios e opcionais exigidos conforme a categoria do"
      " parceiro:"
  )

  for cat, reqs in REQUISITOS.items():
    with st.expander(f"📌 {cat}"):
      col_a, col_b = st.columns(2)
      with col_a:
        st.write("**Obrigatórios:**")
        for doc in reqs["obrigatorios"]:
          st.write(f"• {doc}")
      with col_b:
        st.write("**Opcionais:**")
        for doc in reqs["opcionais"]:
          st.write(f"• {doc}")

elif menu == "Sobre a Yattó":
  st.title("Yattó - Infraestrutura de Economia Circular")
  st.write(
      "A Yattó é a infraestrutura de soluções em economia circular para grandes"
      " empresas, atuando de forma contínua e auditável em resíduos,"
      " embalagens, conteúdo reciclado e governança."
  )
  st.write(
      "Com a PNRS e o **Decreto nº 12.688/2025**, a comprovação de circularidade"
      " exige dados auditáveis e segurança jurídica na homologação de toda a"
      " cadeia de parceiros."
  )
