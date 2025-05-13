import streamlit as st
import pandas as pd
import environ
import plotly.express as px
from components.dados_receita import autenticar_msal as auth_receita, processar_arquivos as proc_receita
from components.dados_despesas import autenticar_msal as auth_despesa, processar_arquivos as proc_despesa
from components.utils_receita import padronizar_e_limpar as limpar_receita, filtrar_dados as filtrar_receita
from components.utils_despesas import padronizar_e_limpar as limpar_despesa, filtrar_dados as filtrar_despesa
from components.utils_despesas import exibir_grafico_comparativo  

env = environ.Env()
environ.Env().read_env()
drive_id = env("drive_id")

arquivos_receita = [
    {"nome": "Recebimentos_Caixa.xlsx", "caminho": "/Recebimentos%20Caixa%20(1).xlsx", "aba": "ENTRADAS", "linhas_pular": 4},
    {"nome": "P._conta_2025.xlsx", "caminho": "/P.conta%202025.xlsx", "aba": "Prestação", "linhas_pular": 5},
    {"nome": "Venda_Balcao.xlsx", "caminho": "/Venda%20Balc%C3%A3o.xlsx", "aba": None, "linhas_pular": 0}
]
token_receita = auth_receita()
headers_receita = {"Authorization": f"Bearer {token_receita}", "Content-Type": "application/json"}
df_receita = proc_receita(arquivos_receita, drive_id, headers_receita)

df_venda_balcao = pd.read_excel("Venda_Balcao.xlsx", header=0, usecols=['Dt. Neg.', 'Vlr. Nota'])
df_venda_balcao.rename(columns={'Dt. Neg.': 'DATA', 'Vlr. Nota': 'VALOR R$'}, inplace=True)
df_venda_balcao["ORIGEM"] = "Venda_Balcao"
df_receita["ORIGEM"] = "Outras Planilhas"
df_receitas_unificado = pd.concat([df_receita, df_venda_balcao], ignore_index=True)

df_receitas_unificado = limpar_receita(df_receitas_unificado)

arquivos_despesa = [
    {"nome": "Recebimentos_Caixa.xlsx", "caminho": "/Recebimentos%20Caixa%20(1).xlsx", "aba": "LANÇAMENTO DESPESAS", "linhas_pular": 3},
    {"nome": "PLANILHA_DE_CUSTO.xlsx", "caminho": "/PLANILHA%20DE%20CUSTO%202025.xlsx", "aba": "LANÇAMENTO DESPESAS", "linhas_pular": 3}
]
token_despesa = auth_despesa()
headers_despesa = {"Authorization": f"Bearer {token_despesa}", "Content-Type": "application/json"}
df_despesa = proc_despesa(arquivos_despesa, drive_id, headers_despesa)
df_despesa = limpar_despesa(df_despesa)

st.set_page_config(layout="wide", page_title="Dashboard Financeiro Completo", page_icon="💰")
st.title("Dashboard Financeiro - Receita x Despesa")

opcoes_periodo = [
    "Semana Atual", "Semana Passada", "Mês Atual", "Mês Passado",
    "Últimos 3 Meses", "Últimos 6 Meses",
    "Ano Atual", "Ano Passado", "Tempo Todo"
]
periodo_selecionado = st.sidebar.selectbox("Selecione o Período:", opcoes_periodo)

df_receita_filtrado, inicio_periodo, fim_periodo = filtrar_receita(df_receitas_unificado, periodo_selecionado)
df_despesa_filtrado, _, _ = filtrar_despesa(df_despesa, periodo_selecionado)

if inicio_periodo and fim_periodo:
    st.write(f"**Período selecionado:** {inicio_periodo.strftime('%d/%m/%Y')} a {fim_periodo.strftime('%d/%m/%Y')}")

receita_total = df_receita_filtrado["VALOR R$"].sum()
despesa_total = df_despesa_filtrado["VALOR R$"].sum()
ebtida = receita_total - despesa_total  
rentabilidade = (ebtida / receita_total) * 100 if receita_total > 0 else 0

# LUCRO BRUTO DE PEÇAS
fornecedores_despesas = df_despesa_filtrado[df_despesa_filtrado['GRUPO DESPESAS'] == 'FORNECEDORES']['VALOR R$'].sum()
pecas_receitas = df_receita_filtrado['PEÇAS'].sum()

lucro_pecas = pecas_receitas - fornecedores_despesas

# LUCRO BRUTO DE MÃO DE OBRA
usuarios_selecionados = [
    "EDVAN", "RIBAMAR", "SANDRO ROBERTO","THIAGO MARQUES", "NETO", 
    "DIEGO SOUSA", "SANDRO LUIS", "ADELSON", "ARTHUR", "CLAUDIO"
]

tecnicos_off = ["ROBERTO", "DIEGO HENRIQUE"]

df_despesa_filtrado_usuarios = df_despesa_filtrado[df_despesa_filtrado["USUÁRIO"].isin(usuarios_selecionados)]
df_receita_ativos = df_receita_filtrado[~df_receita_filtrado["TÉCNICO"].isin(tecnicos_off)]

mo_receitas = df_receita_ativos["M.O"].sum()   
tecnico_despesas = df_despesa_filtrado_usuarios["VALOR R$"].sum() 

lucro_bruto_mo = mo_receitas - tecnico_despesas

col1, col2, col3,  = st.columns(3) 
col1.metric("Receita Total", f"R$ {receita_total:,.2f}")
col2.metric("Despesa Total", f"R$ {despesa_total:,.2f}")
col3.metric("📈 Lucro Líquido", f"R$ {ebtida:,.2f}")
col1.metric("📊 Rentabilidade", f"{rentabilidade:.2f} %")
col2.metric("Lucro Bruto de Peças", f"R$ {lucro_pecas:,.2f}")
col3.metric("Lucro Bruto de Mão de Obra", f"R$ {lucro_bruto_mo:,.2f}")

st.divider()

#LUCRO BRUTO DE TÉCNICOS
mapeamento_tecnicos = {
    "JOSE ARTHUR": "ARTHUR"  
}

df_receita_filtrado["TÉCNICO"] = df_receita_filtrado["TÉCNICO"].replace(mapeamento_tecnicos)

tecnicos = ["EDVAN", "RIBAMAR", "SANDRO ROBERTO",
            "THIAGO MARQUES", "NETO", "DIEGO SOUSA", "SANDRO LUIS", "ADELSON", 
            "ARTHUR", "CLAUDIO"]

# Criar uma lista para armazenar as informações de lucro por técnico
dados_tecnicos = []

for tecnico in tecnicos:
    mo_receitas_tecnico = df_receita_filtrado[df_receita_filtrado["TÉCNICO"] == tecnico]["M.O"].sum()

    despesas_tecnico = df_despesa_filtrado[df_despesa_filtrado["USUÁRIO"] == tecnico]["VALOR R$"].sum()

    lucro_tecnico = mo_receitas_tecnico - despesas_tecnico

    dados_tecnicos.append({
        "Técnico": tecnico,
        "Receitas de M.O (R$)": f"R$ {mo_receitas_tecnico:,.2f}",
        "Despesas (R$)": f"R$ {despesas_tecnico:,.2f}",
        "Lucro (R$)": f"R$ {lucro_tecnico:,.2f}"
    })

df_lucros_tecnicos = pd.DataFrame(dados_tecnicos)
df_lucros_tecnicos = df_lucros_tecnicos.sort_values(by="Lucro (R$)", ascending=False)
df_lucros_tecnicos.reset_index(drop=True, inplace=True)

st.write("### Lucro por Técnico")
st.dataframe(df_lucros_tecnicos) 

st.markdown("## 🔗 Acessar Dashboards Individuais")
st.markdown("Visualize separadamente os painéis de receitas e despesas:")

col1, col2 = st.columns(2)

botao_style = """
    <style>
    .botao-link {
        background-color: #2d5576;
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        transition: 0.3s;
        width: 100%;
    }
    .botao-link:hover {
        background-color: #1e3b54;
        cursor: pointer;
    }
    </style>
"""

# Exibir o estilo
st.markdown(botao_style, unsafe_allow_html=True)

with col1:
    st.markdown(
        """
        <a href="https://receitas-fortcenter.streamlit.app/" target="_blank">
            <div class="botao-link">📊 Dashboard de Receitas</div>
        </a>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        """
        <a href="https://despesas-fortcenter.streamlit.app/" target="_blank">
            <div class="botao-link">💸 Dashboard de Despesas</div>
        </a>
        """,
        unsafe_allow_html=True
    )
    
st.divider()

if periodo_selecionado in ["Ano Atual", "Últimos 6 Meses", "Últimos 3 Meses"]:
    st.markdown("## Comparativos Receita x Despesa")

    df_receita_filtrado["Ano-Mês"] = df_receita_filtrado["DATA"].dt.to_period("M")
    df_despesa_filtrado["Ano-Mês"] = df_despesa_filtrado["DATA"].dt.to_period("M")

    grafico_comparativo = pd.DataFrame({
        "Receita": df_receita_filtrado.groupby("Ano-Mês")["VALOR R$"].sum(),
        "Despesa": df_despesa_filtrado.groupby("Ano-Mês")["VALOR R$"].sum()
    }).fillna(0)

    grafico_comparativo["Faturamento"] = grafico_comparativo["Receita"] - grafico_comparativo["Despesa"]
    grafico_comparativo.index = grafico_comparativo.index.astype(str)

    fig = px.line(
        grafico_comparativo.reset_index().melt(
            id_vars="Ano-Mês", 
            var_name="Categoria", 
            value_name="Valor"),
        x="Ano-Mês", y="Valor", 
        color="Categoria", 
        markers=True,
        title="Comparativo Receita x Despesa"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

with st.expander("Ver Dados Detalhados de Receitas"):
    colunas_para_remover = ["OPERAÇÃO", "N° OS", "ORIGEM"]
    df_receita_filtrado = df_receita_filtrado.drop(
        columns=[col for col in colunas_para_remover if col in df_receita_filtrado.columns]
    )

    df_receita_filtrado = df_receita_filtrado.replace(["", "None", None], "Não informado").fillna("Não informado")
    df_receita_filtrado["DATA"] = df_receita_filtrado["DATA"].dt.strftime("%d/%m/%Y")
    df_receita_filtrado.reset_index(drop=True, inplace=True)
    df_receita_filtrado.index += 1

    for col in ["VALOR R$", "PEÇAS", "M.O"]:
        if col in df_receita_filtrado.columns:
            df_receita_filtrado[col] = pd.to_numeric(df_receita_filtrado[col], errors="coerce")
            df_receita_filtrado[col] = df_receita_filtrado[col].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                if pd.notnull(x) else "Não informado"
            )

    st.dataframe(df_receita_filtrado)

with st.expander("Ver Dados Detalhados de Despesas"):
    df_despesa_filtrado["DATA"] = df_despesa_filtrado["DATA"].dt.strftime("%d/%m/%Y")
    df_despesa_filtrado.reset_index(drop=True, inplace=True)
    df_despesa_filtrado.index += 1
    df_despesa_filtrado["VALOR R$"] = df_despesa_filtrado["VALOR R$"].apply(
    lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
)
    
    st.dataframe(df_despesa_filtrado)

    # Comparativo Receita x Despesa
if periodo_selecionado in ["Ano Atual", "Últimos 6 Meses", "Últimos 3 Meses"]:
    exibir_grafico_comparativo(df_receita_filtrado, df_despesa_filtrado)
