import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# =============================
# CONFIGURAÇÃO DO BOLSISTA
# =============================
NOME_BOLSISTA = "Andson Andre Ribeiro"
PROGRAMA = ("Mestrado em TECNOLOGIAS DA INTELIGÊNCIA E DESIGN DIGITAL: "
            "PROCESSOS COGNITIVOS E AMBIENTES DIGITAIS - Pontifícia Universidade Católica de São Paulo")
TITULO_PROJETO = "Título do Projeto"
NUM_PROCESSO_CNPQ = "133785/2025-4"
PERIODO_BOLSA = "Jul/2025 a Jun/2027"
# =============================

DB_NAME = "gastos_cnpq.db"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano INTEGER,
            mes TEXT,
            despesa TEXT,
            categoria TEXT,
            valor REAL,
            nota TEXT,
            observacao TEXT
        )
    """)
    conn.commit()
    return conn

def inserir_gasto(conn, ano, mes, despesa, categoria, valor, nota, observacao):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO gastos (ano, mes, despesa, categoria, valor, nota, observacao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ano, mes, despesa, categoria, valor, nota, observacao))
    conn.commit()

def atualizar_gasto(conn, id, ano, mes, despesa, categoria, valor, nota, observacao):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE gastos
        SET ano = ?, mes = ?, despesa = ?, categoria = ?, valor = ?, nota = ?, observacao = ?
        WHERE id = ?
    """, (ano, mes, despesa, categoria, valor, nota, observacao, id))
    conn.commit()

def deletar_gasto(conn, id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM gastos WHERE id = ?", (id,))
    conn.commit()

def ler_gastos(conn):
    df = pd.read_sql_query("SELECT * FROM gastos ORDER BY ano DESC, mes DESC", conn)
    return df

def gerar_pdf(ano, mes, df_mes):
    nome_arquivo = f"Relatorio_Gastos_{ano}_{mes}.pdf"
    c = canvas.Canvas(nome_arquivo, pagesize=A4)
    largura, altura = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, altura - 50, "Relatório de Prestação de Contas - CNPq")
    c.setFont("Helvetica", 10)
    c.drawString(50, altura - 70, f"Bolsista: {NOME_BOLSISTA}")
    c.drawString(50, altura - 85, f"Programa: {PROGRAMA}")
    c.drawString(50, altura - 100, f"Título do Projeto: {TITULO_PROJETO}")
    c.drawString(50, altura - 115, f"Nº Processo: {NUM_PROCESSO_CNPQ}")
    c.drawString(50, altura - 130, f"Período da Bolsa: {PERIODO_BOLSA}")
    c.drawString(50, altura - 145, f"Ano/Mês do Relatório: {ano} / {mes}")
    c.drawString(50, altura - 160, f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    y = altura - 190
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Descrição")
    c.drawString(250, y, "Categoria")
    c.drawString(350, y, "Valor (R$)")
    c.drawString(450, y, "Nota Fiscal")
    y -= 15

    c.setFont("Helvetica", 10)
    total = 0
    for _, row in df_mes.iterrows():
        c.drawString(50, y, str(row["despesa"])[:25])
        c.drawString(250, y, str(row["categoria"]))
        c.drawString(350, y, f"{row['valor']:.2f}")
        c.drawString(450, y, str(row["nota"]))
        total += row["valor"]
        y -= 15
        if y < 50:
            c.showPage()
            y = altura - 50

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"TOTAL GASTO NO MÊS: R$ {total:.2f}")

    y -= 50
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "_________________________________")
    c.drawString(50, y - 12, "Assinatura do Bolsista")

    c.save()
    return nome_arquivo

def gerar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.drop(columns=['id'], errors='ignore').to_excel(writer, index=False, sheet_name='Gastos')
     
    return output.getvalue()

# --- Início da aplicação Streamlit ---

conn = init_db()

st.set_page_config(page_title="Gestão de Gastos - CNPq", layout="centered")
st.title("📊 Gestão de Gastos - CNPq")

# Estado para edição
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

df = ler_gastos(conn)

anos_disponiveis = sorted(df["ano"].unique()) if not df.empty else [2025]

with st.form("form_gasto", clear_on_submit=True):
    if st.session_state.edit_id:
        gasto = df[df["id"] == st.session_state.edit_id].iloc[0]
        ano_default = gasto["ano"]
        mes_default = gasto["mes"]
        despesa_default = gasto["despesa"]
        categoria_default = gasto["categoria"]
        valor_default = gasto["valor"]
        nota_default = gasto["nota"]
        observacao_default = gasto["observacao"]
    else:
        ano_default = anos_disponiveis[-1] if anos_disponiveis else 2025
        mes_default = "Jan"
        despesa_default = ""
        categoria_default = "Material"
        valor_default = 0.0
        nota_default = ""
        observacao_default = ""

    ano = st.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(ano_default) if ano_default in anos_disponiveis else 0)
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    mes = st.selectbox("Mês", meses, index=meses.index(mes_default) if mes_default in meses else 0)
    categorias = ["Material", "Transporte", "Serviço", "Hospedagem", "Alimentação", "Outros"]
    despesa = st.text_input("Despesa realizada", value=despesa_default)
    categoria = st.selectbox("Categoria", categorias, index=categorias.index(categoria_default) if categoria_default in categorias else 0)
    valor = st.number_input("Valor real (R$)", min_value=0.0, step=0.01, value=valor_default)
    nota = st.text_input("Nº Nota Fiscal / Recibo", value=nota_default)
    observacao = st.text_area("Observação", value=observacao_default)

    submit = st.form_submit_button("Salvar gasto")

    if submit:
        if st.session_state.edit_id is None:
            inserir_gasto(conn, ano, mes, despesa, categoria, valor, nota, observacao)
            st.success("✅ Gasto adicionado com sucesso!")
        else:
            atualizar_gasto(conn, st.session_state.edit_id, ano, mes, despesa, categoria, valor, nota, observacao)
            st.success("✅ Gasto atualizado com sucesso!")
            st.session_state.edit_id = None
        st.rerun()


st.subheader("📅 Gastos registrados")
df = ler_gastos(conn)

# Mostrar tabela com botões editar e deletar
for i, row in df.iterrows():
    cols = st.columns([1,1,2,2,1,1,2,2,1])
    cols[0].write(row["id"])
    cols[1].write(row["ano"])
    cols[2].write(row["mes"])
    cols[3].write(row["despesa"])
    cols[4].write(row["categoria"])
    cols[5].write(f"R$ {row['valor']:.2f}")
    cols[6].write(row["nota"])
    cols[7].write(row["observacao"])

    if cols[8].button("Editar", key=f"edit_{row['id']}"):
        st.session_state.edit_id = row["id"]
        st.experimental_rerun()
    if cols[8].button("Deletar", key=f"del_{row['id']}"):
        deletar_gasto(conn, row["id"])
        st.success("🗑️ Gasto deletado!")
        st.experimental_rerun()

# Exportar Excel
if not df.empty:
    excel_bytes = gerar_excel(df)
    st.download_button(
        label="📥 Baixar planilha Excel",
        data=excel_bytes,
        file_name="Planejamento_Gastos_CNPq.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Resumo mensal e geração de PDF
if not df.empty:
    resumo = df.groupby(["ano", "mes"])["valor"].sum().reset_index()
    st.subheader("📌 Resumo mensal")
    st.dataframe(resumo)

    ano_sel = st.selectbox("Ano para relatório PDF", resumo["ano"].unique())
    meses_disponiveis = resumo[resumo["ano"] == ano_sel]["mes"].unique()
    mes_sel = st.selectbox("Mês para relatório PDF", meses_disponiveis)

    if st.button("📄 Gerar PDF do mês selecionado"):
        df_rel = df[(df["ano"] == ano_sel) & (df["mes"] == mes_sel)]
        pdf_file = gerar_pdf(ano_sel, mes_sel, df_rel)
        with open(pdf_file, "rb") as f:
            st.download_button("📥 Baixar Relatório PDF", data=f, file_name=pdf_file, mime="application/pdf")

# Gráficos simples
if not df.empty:
    st.subheader("📊 Gastos por Categoria")
    graf_cat = df.groupby("categoria")["valor"].sum()
    st.bar_chart(graf_cat)

    st.subheader("📈 Gastos por Ano e Mês")
    df["AnoMes"] = df["ano"].astype(str) + "-" + df["mes"]
    graf_ano_mes = df.groupby("AnoMes")["valor"].sum()
    st.bar_chart(graf_ano_mes)


