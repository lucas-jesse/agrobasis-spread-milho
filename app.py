import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="AgroBasis | Spread Milho B3",
    layout="wide"
)

SHEET_ID = "1uGrRfOg2W9ICx58eKgwCjJ-bCWZ3l_y7bLbt1CA3mAE"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

MESES = {
    "jan": "CCMF",
    "mar": "CCMH",
    "mai": "CCMK",
    "jul": "CCMN",
    "set": "CCMU",
    "nov": "CCMX",
}

NOMES_MESES = {
    "jan": "janeiro",
    "mar": "março",
    "mai": "maio",
    "jul": "julho",
    "set": "setembro",
    "nov": "novembro",
}

MESES_NUM = {
    "jan": 1,
    "mar": 3,
    "mai": 5,
    "jul": 7,
    "set": 9,
    "nov": 11,
}

ORDEM_MESES = list(MESES.keys())

st.markdown("""
<meta name="google" content="notranslate">
<style>
.block-container {
    padding-top: 0.8rem;
    padding-bottom: 2rem;
    max-width: 1450px;
}
[data-testid="stSidebar"] {
    background-color: #f3f4f6;
}

/* ---------- CABEÇALHO (discreto, sem cor de fundo) ---------- */
.page-header {
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid #e2e8f0;
}
.page-header-title {
    font-size: 26px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 4px;
}
.page-header-subtitle {
    font-size: 14.5px;
    color: #64748b;
}
.page-header-meta {
    margin-top: 8px;
    font-size: 13.5px;
    color: #475569;
}
.page-header-meta b { color: #0f172a; }

/* ---------- KPIs discretos (grid CSS responsivo, não compete com o gráfico) ---------- */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 10px;
    margin-bottom: 20px;
}
.kpi-card {
    background: #f8fafc;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid #e5e7eb;
    border-left: 3px solid #cbd5e1;
}
.kpi-card.is-positive { border-left-color: #15803d; }
.kpi-card.is-negative { border-left-color: #dc2626; }
.kpi-label {
    font-size: 11.5px;
    color: #6b7280;
    margin-bottom: 4px;
    line-height: 1.3;
}
.kpi-value {
    font-size: 19px;
    font-weight: 700;
    color: #111827;
}
.kpi-value.is-positive { color: #15803d; }
.kpi-value.is-negative { color: #dc2626; }

.section-title {
    font-size: 22px;
    font-weight: 800;
    margin-top: 12px;
    margin-bottom: 6px;
    color: #111827;
}
.section-subtitle {
    color: #6b7280;
    font-size: 14.5px;
    margin-bottom: 14px;
}
.reading-box {
    background: #f8fafc;
    border-left: 4px solid #14532d;
    padding: 16px 20px;
    border-radius: 10px;
    font-size: 15.5px;
    color: #1f2937;
    margin-top: 16px;
    line-height: 1.6;
}
.small-note {
    color: #6b7280;
    font-size: 13px;
}
.notranslate {
    unicode-bidi: isolate;
}

/* ---------- RESPONSIVO / MOBILE ---------- */
@media (max-width: 768px) {
    .block-container { padding-top: 0.5rem; padding-left: 0.9rem; padding-right: 0.9rem; }
    .page-header-title { font-size: 21px; }
    .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .kpi-value { font-size: 17px; }
    .section-title { font-size: 19px; }
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 45% !important;
        flex: 1 1 45% !important;
    }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=600)
def carregar_dados():
    try:
        df = pd.read_csv(URL)
    except Exception:
        return None

    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Data"])
    df = df.sort_values("Data")

    for col in df.columns:
        if col != "Data":
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .replace("nan", None)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def br_num(valor):
    if valor is None or pd.isna(valor):
        return "-"
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_variacao(serie, dias):
    serie = serie.dropna()
    if len(serie) <= dias:
        return None
    return serie.iloc[-1] - serie.iloc[-dias - 1]


def codigo_contrato(mes, ano):
    return f"{MESES[mes]}{str(ano)[-2:]}"


def nome_visual(mes, ano):
    return f"{NOMES_MESES[mes].capitalize()}/{str(ano)[-2:]}"


def chave_cronologica(mes, ano):
    return (int(ano), MESES_NUM[mes])


def ordenar_pernas(mes_1, ano_1, mes_2, ano_2):
    """Sempre define o spread como contrato mais curto - contrato mais longo."""
    perna_a = {"mes": mes_1, "ano": int(ano_1)}
    perna_b = {"mes": mes_2, "ano": int(ano_2)}

    if chave_cronologica(mes_1, ano_1) <= chave_cronologica(mes_2, ano_2):
        curto, longo = perna_a, perna_b
    else:
        curto, longo = perna_b, perna_a

    curto["codigo"] = codigo_contrato(curto["mes"], curto["ano"])
    longo["codigo"] = codigo_contrato(longo["mes"], longo["ano"])
    return curto, longo


def estimar_data_vencimento(mes, ano):
    # Aproximação prática para a visualização futura.
    # O objetivo aqui é apenas estender a média/ano anterior até a região de vencimento.
    return pd.Timestamp(year=int(ano), month=MESES_NUM[mes], day=15)


def montar_spread(df_base, c_curto, c_longo):
    temp = df_base[["Data", c_curto, c_longo]].dropna().copy()
    # Regra central do dashboard: spread = contrato mais curto - contrato mais longo
    temp["Spread"] = temp[c_curto] - temp[c_longo]
    temp["DiaAno"] = temp["Data"].dt.dayofyear
    temp["Ano"] = temp["Data"].dt.year
    return temp


def montar_historico_equivalente(df_base, curto, longo, anos_ref):
    """
    Exemplo selecionado: nov/26 x jan/27.
    Como a regra é curto - longo, o histórico equivalente de 5 anos será:
    nov/25 - jan/26, nov/24 - jan/25, nov/23 - jan/24, etc.
    """
    offset_anos = longo["ano"] - curto["ano"]
    series = []

    for ano_base_curto in range(curto["ano"] - anos_ref, curto["ano"]):
        ano_base_longo = ano_base_curto + offset_anos
        c_curto_hist = codigo_contrato(curto["mes"], ano_base_curto)
        c_longo_hist = codigo_contrato(longo["mes"], ano_base_longo)

        if c_curto_hist in df_base.columns and c_longo_hist in df_base.columns:
            temp = montar_spread(df_base, c_curto_hist, c_longo_hist)
            temp["AnoBase"] = ano_base_curto
            temp["Spread_equivalente"] = f"{c_curto_hist} - {c_longo_hist}"
            series.append(temp[["Data", "DiaAno", "AnoBase", "Spread", "Spread_equivalente"]])

    if not series:
        return pd.DataFrame(columns=["Data", "DiaAno", "AnoBase", "Spread", "Spread_equivalente"])

    return pd.concat(series, ignore_index=True)


def estatistica_historica(dados_atual, hist):
    dados = dados_atual.copy()

    if hist.empty:
        dados["Média histórica"] = None
        dados["Desvio histórico"] = None
        dados["+1 desvio"] = None
        dados["-1 desvio"] = None
        dados["+2 desvios"] = None
        dados["-2 desvios"] = None
        return dados

    media_por_dia = hist.groupby("DiaAno")["Spread"].mean()
    desvio_por_dia = hist.groupby("DiaAno")["Spread"].std().fillna(0)

    dados["Média histórica"] = dados["DiaAno"].map(media_por_dia)
    dados["Desvio histórico"] = dados["DiaAno"].map(desvio_por_dia)
    dados["+1 desvio"] = dados["Média histórica"] + dados["Desvio histórico"]
    dados["-1 desvio"] = dados["Média histórica"] - dados["Desvio histórico"]
    dados["+2 desvios"] = dados["Média histórica"] + 2 * dados["Desvio histórico"]
    dados["-2 desvios"] = dados["Média histórica"] - 2 * dados["Desvio histórico"]
    return dados


def montar_linhas_historicas_para_grafico(dados, hist, curto, longo, mostrar_futuro, suavizar_media, janela_suavizacao):
    """Cria série de média histórica, bandas e ano anterior, podendo estender no futuro."""
    if hist.empty:
        return pd.DataFrame(columns=["Data", "DiaAno", "Média histórica", "Desvio histórico", "+1 desvio", "-1 desvio", "+2 desvios", "-2 desvios", "Ano anterior"])

    data_inicio = dados["Data"].min()
    data_fim_atual = dados["Data"].max()

    # Regra correta para projeção:
    # o spread deixa de existir quando vence o contrato mais curto.
    # Portanto, média histórica e ano anterior só devem ser projetados
    # até o vencimento do contrato curto, não até o contrato longo.
    data_venc_curto = estimar_data_vencimento(curto["mes"], curto["ano"])

    if mostrar_futuro and data_venc_curto > data_fim_atual:
        data_fim = data_venc_curto
    else:
        data_fim = data_fim_atual

    calendario = pd.DataFrame({"Data": pd.date_range(data_inicio, data_fim, freq="D")})
    calendario["DiaAno"] = calendario["Data"].dt.dayofyear

    media_por_dia = hist.groupby("DiaAno")["Spread"].mean()
    desvio_por_dia = hist.groupby("DiaAno")["Spread"].std().fillna(0)

    calendario["Média histórica"] = calendario["DiaAno"].map(media_por_dia)

    if suavizar_media:
        calendario["Média histórica"] = calendario["Média histórica"].rolling(
            janela_suavizacao,
            min_periods=1
        ).mean()

    calendario["Desvio histórico"] = calendario["DiaAno"].map(desvio_por_dia)
    calendario["+1 desvio"] = calendario["Média histórica"] + calendario["Desvio histórico"]
    calendario["-1 desvio"] = calendario["Média histórica"] - calendario["Desvio histórico"]
    calendario["+2 desvios"] = calendario["Média histórica"] + 2 * calendario["Desvio histórico"]
    calendario["-2 desvios"] = calendario["Média histórica"] - 2 * calendario["Desvio histórico"]

    # Ano anterior: último spread equivalente disponível antes do ano selecionado
    ano_anterior_base = curto["ano"] - 1
    hist_ano_anterior = hist[hist["AnoBase"] == ano_anterior_base]
    if not hist_ano_anterior.empty:
        serie_ano_anterior = hist_ano_anterior.groupby("DiaAno")["Spread"].mean()
        calendario["Ano anterior"] = calendario["DiaAno"].map(serie_ano_anterior)

        # Suavização fixa do ano anterior para reduzir ruído visual.
        # A linha fica mais útil como referência comparativa, sem virar "serrote".
        calendario["Ano anterior"] = (
            calendario["Ano anterior"]
            .rolling(15, min_periods=1)
            .mean()
        )
    else:
        calendario["Ano anterior"] = None

    return calendario


def criar_grafico_principal(
    dados,
    linhas_hist,
    media_movel,
    mostrar_media_movel,
    mostrar_media,
    mostrar_ano_anterior,
    mostrar_1dp,
    mostrar_2dp,
    anos_ref,
    titulo_grafico
):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dados["Data"],
        y=dados["Spread"],
        mode="lines",
        name="Valor atual do spread",
        line=dict(width=3.2, color="#1d4ed8", shape="spline", smoothing=0.35)
    ))

    if mostrar_media_movel and "Média móvel" in dados.columns:
        fig.add_trace(go.Scatter(
            x=dados["Data"],
            y=dados["Média móvel"],
            mode="lines",
            name=f"Média móvel {media_movel} dias",
            line=dict(width=2.3, color="#f97316", shape="spline", smoothing=0.6)
        ))

    data_ultima_atual = dados["Data"].max()

    if mostrar_media and not linhas_hist.empty:
        media_passado = linhas_hist[linhas_hist["Data"] <= data_ultima_atual]
        media_futuro = linhas_hist[linhas_hist["Data"] > data_ultima_atual]

        fig.add_trace(go.Scatter(
            x=media_passado["Data"],
            y=media_passado["Média histórica"],
            mode="lines",
            name=f"Média histórica ({anos_ref} anos)",
            line=dict(width=4, color="#14532d", shape="spline", smoothing=0.7)
        ))

        if not media_futuro.empty:
            fig.add_trace(go.Scatter(
                x=media_futuro["Data"],
                y=media_futuro["Média histórica"],
                mode="lines",
                name=f"Projeção média histórica ({anos_ref} anos)",
                line=dict(width=4, color="#14532d", dash="dash", shape="spline", smoothing=0.7)
            ))

    if mostrar_ano_anterior and not linhas_hist.empty and "Ano anterior" in linhas_hist.columns:
        ano_ant_passado = linhas_hist[linhas_hist["Data"] <= data_ultima_atual]
        ano_ant_futuro = linhas_hist[linhas_hist["Data"] > data_ultima_atual]

        fig.add_trace(go.Scatter(
            x=ano_ant_passado["Data"],
            y=ano_ant_passado["Ano anterior"],
            mode="lines",
            name="Ano anterior",
            line=dict(width=2.4, color="#94a3b8", shape="spline", smoothing=0.85)
        ))

        if not ano_ant_futuro.empty:
            fig.add_trace(go.Scatter(
                x=ano_ant_futuro["Data"],
                y=ano_ant_futuro["Ano anterior"],
                mode="lines",
                name="Projeção ano anterior",
                line=dict(width=2.4, color="#94a3b8", dash="dash", shape="spline", smoothing=0.85)
            ))

    if mostrar_1dp and not linhas_hist.empty:
        fig.add_trace(go.Scatter(
            x=linhas_hist["Data"], y=linhas_hist["+1 desvio"], mode="lines", name="+1 desvio",
            line=dict(dash="dot", width=1, color="#a855f7")
        ))
        fig.add_trace(go.Scatter(
            x=linhas_hist["Data"], y=linhas_hist["-1 desvio"], mode="lines", name="-1 desvio",
            line=dict(dash="dot", width=1, color="#fb923c")
        ))

    if mostrar_2dp and not linhas_hist.empty:
        fig.add_trace(go.Scatter(
            x=linhas_hist["Data"], y=linhas_hist["+2 desvios"], mode="lines", name="+2 desvios",
            line=dict(dash="dot", width=1, color="#06b6d4")
        ))
        fig.add_trace(go.Scatter(
            x=linhas_hist["Data"], y=linhas_hist["-2 desvios"], mode="lines", name="-2 desvios",
            line=dict(dash="dot", width=1, color="#ec4899")
        ))

    fig.add_annotation(
        text="AgroBasis",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.50,
        showarrow=False,
        font=dict(size=76, color="rgba(20, 83, 45, 0.055)"),
        textangle=-25,
        xanchor="center",
        yanchor="middle"
    )

    fig.update_layout(
        height=620,
        template="plotly_white",
        hovermode="x unified",
        title=dict(
            text=titulo_grafico,
            x=0.01,
            y=0.98,
            xanchor="left",
            yanchor="top",
            font=dict(size=24, color="#111827")
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.01,
            font=dict(size=13),
            title_text=""
        ),
        yaxis_title="Spread R$/saca",
        xaxis_title="Data",
        margin=dict(l=20, r=20, t=105, b=20)
    )
    return fig


def criar_grafico_comparativo_anual(hist, dados_atual):
    fig = go.Figure()

    cores = ["#ef4444", "#16a34a", "#2563eb", "#9333ea", "#f59e0b", "#64748b"]
    anos = sorted(hist["AnoBase"].unique()) if not hist.empty else []

    for idx, ano in enumerate(anos):
        temp = hist[hist["AnoBase"] == ano].sort_values("DiaAno")
        fig.add_trace(go.Scatter(
            x=temp["DiaAno"],
            y=temp["Spread"],
            mode="lines",
            name=str(ano),
            line=dict(width=2.5, color=cores[idx % len(cores)])
        ))

    atual = dados_atual.sort_values("DiaAno")
    fig.add_trace(go.Scatter(
        x=atual["DiaAno"],
        y=atual["Spread"],
        mode="lines",
        name="Ano atual",
        line=dict(width=4, color="#020617")
    ))

    fig.update_layout(
        height=620,
        template="plotly_white",
        hovermode="x unified",
        title=dict(
            text="Comparativo anual do spread",
            x=0.01,
            y=0.98,
            xanchor="left",
            yanchor="top",
            font=dict(size=24, color="#111827")
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.01,
            font=dict(size=13),
            title_text="Anos"
        ),
        yaxis_title="Spread R$/saca",
        xaxis_title="Dia do ano",
        margin=dict(l=20, r=20, t=105, b=20)
    )
    return fig


# ==============================
# Carregamento de dados + filtros (corpo principal)
# ==============================

df = carregar_dados()

if df is None or df.empty:
    st.error(
        "Não foi possível carregar os dados agora. Tente novamente em instantes. "
        "Se o problema persistir, contate o suporte AgroBasis."
    )
    st.stop()

anos_disponiveis = sorted(
    list(
        set(
            int(col[-2:]) + 2000
            for col in df.columns
            if col.startswith("CCM") and len(col) == 6
        )
    )
)

st.markdown('<div class="section-title" style="margin-top:0;">Spread Milho B3</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-subtitle">Monitoramento da estrutura a termo dos contratos futuros de milho na B3. '
    'Regra de cálculo: <b>contrato mais curto − contrato mais longo</b>.</div>',
    unsafe_allow_html=True
)

col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    mes_1 = st.selectbox(
        "Mês do 1º contrato",
        ORDEM_MESES,
        index=3,
        format_func=lambda x: NOMES_MESES[x]
    )

with col_f2:
    ano_1 = st.selectbox(
        "Ano do 1º contrato",
        anos_disponiveis,
        index=max(0, len(anos_disponiveis) - 2)
    )

with col_f3:
    mes_2 = st.selectbox(
        "Mês do 2º contrato",
        ORDEM_MESES,
        index=0,
        format_func=lambda x: NOMES_MESES[x]
    )

with col_f4:
    ano_2 = st.selectbox(
        "Ano do 2º contrato",
        anos_disponiveis,
        index=max(0, len(anos_disponiveis) - 1)
    )

with st.expander("⚙️ Configurações avançadas do gráfico"):
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        mostrar_media_movel = st.checkbox("Mostrar média móvel", value=False)
        media_movel = st.slider(
            "Janela da média móvel (dias)",
            min_value=5,
            max_value=120,
            value=20,
            step=5,
            disabled=not mostrar_media_movel
        )
        anos_ref = st.slider(
            "Histórico da média (anos)",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
            help="Quantidade de anos históricos equivalentes usados para média, desvio e Z-Score."
        )

    with col_a2:
        suavizar_media_historica = st.checkbox(
            "Suavizar média histórica",
            value=True,
            help="Aplica média móvel sobre a linha da média histórica para reduzir ruídos visuais."
        )
        janela_suavizacao_media = st.slider(
            "Suavização da média histórica (dias)",
            min_value=3,
            max_value=60,
            value=15,
            step=3,
            disabled=not suavizar_media_historica
        )

    st.markdown("**Itens do gráfico**")
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        mostrar_media = st.checkbox("Média histórica", value=True)
        mostrar_1dp = st.checkbox("Bandas ±1 desvio", value=False)
    with col_i2:
        mostrar_ano_anterior = st.checkbox("Ano anterior", value=True)
        mostrar_2dp = st.checkbox("Bandas ±2 desvios", value=False)
    with col_i3:
        mostrar_futuro = st.checkbox(
            "Projetar até o vencimento",
            value=True,
            help="Mostra a média histórica e o ano anterior para datas futuras, enquanto o contrato atual ainda não venceu."
        )

st.divider()


# ==============================
# Cálculos
# ==============================

curto, longo = ordenar_pernas(mes_1, ano_1, mes_2, ano_2)
contrato_curto = curto["codigo"]
contrato_longo = longo["codigo"]
nome_spread = f"{contrato_curto} - {contrato_longo}"

if contrato_curto not in df.columns or contrato_longo not in df.columns:
    st.error(f"Contratos não encontrados na base: {contrato_curto} ou {contrato_longo}")
    st.stop()

dados = montar_spread(df, contrato_curto, contrato_longo)

if dados.empty:
    st.warning("Não há dados suficientes para esse spread.")
    st.stop()

dados["Média móvel"] = dados["Spread"].rolling(media_movel).mean()
hist = montar_historico_equivalente(df, curto, longo, anos_ref)
dados = estatistica_historica(dados, hist)
linhas_hist = montar_linhas_historicas_para_grafico(
    dados=dados,
    hist=hist,
    curto=curto,
    longo=longo,
    mostrar_futuro=mostrar_futuro,
    suavizar_media=suavizar_media_historica,
    janela_suavizacao=janela_suavizacao_media
)

spread_atual = dados["Spread"].iloc[-1]
ultima_data_dt = dados["Data"].max()

# Busca a média/desvio histórico exatamente na data atual exibida no gráfico.
# Isso evita Z-Score zerado quando há projeção/suavização ou quando a última linha válida
# da média histórica não coincide com o último dado do spread.
media_hist_atual = None
desvio_hist_atual = None
if not linhas_hist.empty:
    linha_ref = linhas_hist[linhas_hist["Data"] == ultima_data_dt]
    if not linha_ref.empty:
        media_hist_atual = linha_ref["Média histórica"].iloc[-1]
        desvio_hist_atual = linha_ref["Desvio histórico"].iloc[-1]

# Fallback: caso o desvio do mesmo dia seja nulo/indisponível, usa o desvio geral
# da amostra histórica equivalente para não deixar o Z-Score sem informação.
historico_spreads = hist["Spread"].dropna()
if (desvio_hist_atual is None or pd.isna(desvio_hist_atual) or desvio_hist_atual == 0) and len(historico_spreads) > 1:
    desvio_hist_atual = historico_spreads.std()

if media_hist_atual is not None and not pd.isna(media_hist_atual) and desvio_hist_atual not in [None, 0] and not pd.isna(desvio_hist_atual):
    z_score = (spread_atual - media_hist_atual) / desvio_hist_atual
else:
    z_score = None

var_7d = calcular_variacao(dados["Spread"], 7)
var_30d = calcular_variacao(dados["Spread"], 30)
diff_media = spread_atual - media_hist_atual if media_hist_atual is not None and not pd.isna(media_hist_atual) else None
ultima_data = ultima_data_dt.strftime("%d/%m/%Y")

spread_nome_visual = f"{nome_visual(curto['mes'], curto['ano'])} x {nome_visual(longo['mes'], longo['ano'])}"
titulo_grafico = f"Spread entre os contratos de milho {nome_visual(curto['mes'], curto['ano']).lower()} e {nome_visual(longo['mes'], longo['ano']).lower()} na B3"

# ==============================
# Header (discreto, sem bloco colorido)
# ==============================

st.markdown(f"""
<div class="page-header">
    <div class="page-header-title">Spread Milho B3</div>
    <div class="page-header-subtitle">Monitoramento da estrutura a termo dos contratos futuros de milho na B3</div>
    <div class="page-header-meta">
        <b>{spread_nome_visual}</b> &nbsp;·&nbsp; <b>{nome_spread}</b> &nbsp;·&nbsp;
        Última atualização: <b>{ultima_data}</b>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================
# KPIs — grid único, discreto, não compete com o gráfico
# ==============================

z_txt = "-" if z_score is None or pd.isna(z_score) else f"{z_score:.2f}"


def _classe(valor):
    if valor is None or pd.isna(valor):
        return ""
    return "is-positive" if valor >= 0 else "is-negative"


kpis = [
    ("Spread atual", f"{br_num(spread_atual)} R$/saca", ""),
    (f"Vs. média histórica ({anos_ref}a)", f"{br_num(diff_media)} R$/saca", _classe(diff_media)),
    ("Z-Score", z_txt, _classe(z_score)),
    ("Variação 7 dias", f"{br_num(var_7d)} R$/saca", _classe(var_7d)),
    ("Variação 30 dias", f"{br_num(var_30d)} R$/saca", _classe(var_30d)),
]

kpi_html = "".join(
    f"""<div class="kpi-card {classe}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {classe}">{valor}</div>
    </div>"""
    for label, valor, classe in kpis
)

st.markdown(f'<div class="kpi-grid">{kpi_html}</div>', unsafe_allow_html=True)

# ==============================
# Abas: Spread ao vivo | Sazonalidade
# ==============================

tab_live, tab_sazonal = st.tabs(["📈 Spread ao vivo", "📊 Sazonalidade"])

with tab_live:
    st.markdown(
        f'<div class="section-subtitle">Spread calculado como <b>contrato mais curto - contrato mais longo</b>. '
        f'Média histórica, desvios e Z-Score usam spreads equivalentes dos últimos {anos_ref} anos.</div>',
        unsafe_allow_html=True
    )
    fig = criar_grafico_principal(
        dados=dados,
        linhas_hist=linhas_hist,
        media_movel=media_movel,
        mostrar_media_movel=mostrar_media_movel,
        mostrar_media=mostrar_media,
        mostrar_ano_anterior=mostrar_ano_anterior,
        mostrar_1dp=mostrar_1dp,
        mostrar_2dp=mostrar_2dp,
        anos_ref=anos_ref,
        titulo_grafico=titulo_grafico
    )
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    # ---------- Leitura automática ----------
    if z_score is None or pd.isna(z_score):
        leitura = "Ainda não há histórico suficiente para classificar estatisticamente este spread."
    elif z_score >= 1.5:
        leitura = "O spread está em região historicamente elevada frente aos spreads históricos equivalentes. Pela regra curto - longo, isso indica maior prêmio relativo no contrato curto frente ao contrato longo."
    elif z_score <= -1.5:
        leitura = "O spread está em região historicamente baixa frente aos spreads históricos equivalentes. Pela regra curto - longo, isso indica menor prêmio relativo no contrato curto frente ao contrato longo."
    else:
        leitura = "O spread está próximo da faixa normal histórica dos spreads equivalentes, sem distorção estatística extrema no momento."

    media_txt = br_num(media_hist_atual)

    st.markdown(f"""
    <div class="reading-box">
        <b>Leitura AgroBasis:</b><br><br>
        O <span class="notranslate" translate="no">spread</span> <b>{spread_nome_visual}</b> ({nome_spread}) está em <b>{br_num(spread_atual)} R$/saca</b>.
        A média histórica de <b>{anos_ref} anos</b> para o mesmo momento do ano está em
        <b>{media_txt} R$/saca</b>.
        O Z-Score atual é <b>{z_txt}</b>.<br><br>
        {leitura}
    </div>
    """, unsafe_allow_html=True)

with tab_sazonal:
    st.markdown(
        '<div class="section-subtitle">Comparação do spread atual contra os mesmos spreads equivalentes '
        'dos anos anteriores, alinhados pelo dia do ano — evidencia se o comportamento atual está dentro '
        'ou fora do padrão sazonal histórico.</div>',
        unsafe_allow_html=True
    )
    if hist.empty:
        st.info("Não há histórico equivalente suficiente para montar a comparação sazonal deste spread.")
    else:
        fig_sazonal = criar_grafico_comparativo_anual(hist, dados)
        st.plotly_chart(fig_sazonal, use_container_width=True, config={"displaylogo": False})
