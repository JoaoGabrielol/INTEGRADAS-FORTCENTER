import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
from unidecode import unidecode
from dateutil.relativedelta import relativedelta

def padronizar_nome(nome):
    if pd.isnull(nome):
        return "NÃO INFORMADO"
    nome = str(nome).upper()
    nome = unidecode(nome)
    nome = nome.strip()
    nome = ' '.join(nome.split())
    return nome

def padronizar_e_limpar(df):
    for col in ["USUÁRIO", "TÉCNICO"]:
        if col in df.columns:
            df[col] = df[col].fillna("Não informado").apply(padronizar_nome)

    for col in ["PEÇAS", "M.O", "VALOR R$"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Aplica o filtro apenas se a coluna existir
    condicoes = []
    if "PEÇAS" in df.columns:
        condicoes.append(df["PEÇAS"].notnull() & (df["PEÇAS"] > 0))
    if "M.O" in df.columns:
        condicoes.append(df["M.O"].notnull() & (df["M.O"] > 0))
    if "VALOR R$" in df.columns:
        condicoes.append(df["VALOR R$"].notnull() & (df["VALOR R$"] > 0))

    if condicoes:
        filtro_final = condicoes[0]
        for cond in condicoes[1:]:
            filtro_final |= cond
        df = df[filtro_final]

    if "DATA" in df.columns:
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

    obrigatorios = [col for col in ["DATA", "USUÁRIO", "VALOR R$"] if col in df.columns]
    df = df.dropna(subset=obrigatorios)

    return df

def filtrar_dados(df, periodo):
    hoje = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    df = df.copy()
    data_inicio = None
    data_fim = None

    if periodo == "Semana Atual":
        data_inicio = hoje - timedelta(days=hoje.weekday())
        data_fim = hoje
    elif periodo == "Semana Passada":
        data_inicio = hoje - timedelta(days=hoje.weekday() + 7)
        data_fim = data_inicio + timedelta(days=6)
    elif periodo == "Mês Atual":
        data_inicio = hoje.replace(day=1)
        data_fim = hoje
    elif periodo == "Mês Passado":
        primeiro_dia_mes_passado = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        ultimo_dia_mes_passado = hoje.replace(day=1) - timedelta(days=1)
        data_inicio = primeiro_dia_mes_passado
        data_fim = ultimo_dia_mes_passado
    elif periodo == "Últimos 3 Meses":
        data_inicio = (hoje - relativedelta(months=3)).replace(day=1)
        data_fim = hoje
    elif periodo == "Últimos 6 Meses":
        data_inicio = (hoje - relativedelta(months=6)).replace(day=1)
        data_fim = hoje
    elif periodo == "Ano Atual":
        data_inicio = hoje.replace(month=1, day=1)
        data_fim = hoje
    elif periodo == "Ano Passado":
        data_inicio = hoje.replace(year=hoje.year - 1, month=1, day=1)
        data_fim = hoje.replace(year=hoje.year - 1, month=12, day=31)
    elif periodo == "Tempo Todo":
        return df, None, None
    else:
        return df, None, None
    
    if data_inicio and data_fim:
        df_filtrado = df[(df["DATA"] >= data_inicio) & (df["DATA"] <= data_fim)]
        return df_filtrado, data_inicio, data_fim
    else:
        return df, None, None

def exibir_grafico_comparativo(df_receita_filtrado, df_despesa_filtrado):
    df_comparativo = pd.DataFrame({
        "Receita": df_receita_filtrado.groupby("Ano-Mês")["VALOR R$"].sum(),
        "Despesa": df_despesa_filtrado.groupby("Ano-Mês")["VALOR R$"].sum()
    })
    df_comparativo["Faturamento"] = df_comparativo["Receita"] - df_comparativo["Despesa"]
    fig_comparativo = px.bar(df_comparativo, x=df_comparativo.index, y=["Receita", "Despesa", "Faturamento"], barmode="stack", title="Comparativo Receita x Despesa")
    st.plotly_chart(fig_comparativo)
