import os
import json
import requests
import pandas as pd
import gspread
from io import StringIO
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials

URL = "https://br.tradingview.com/symbols/BMFBOVESPA-CCM1!/contracts/"
NOME_PLANILHA = "Historico Spread Milho"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Data no horário do Brasil
data_hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%y")

resposta = requests.get(URL, headers=headers, timeout=20)
resposta.raise_for_status()

tabelas = pd.read_html(StringIO(resposta.text))
df = tabelas[0].copy()

linha = {"Data": data_hoje}

for _, row in df.iterrows():
    simbolo = str(row["Símbolo"])

    codigo = simbolo[:4]
    ano = simbolo[4:8]
    coluna = f"{codigo}{ano[-2:]}"

    preco = float(row["Preço"]) / 100
    linha[coluna] = preco

print("Linha capturada:")
print(linha)

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

if "GOOGLE_CREDENTIALS" in os.environ:
    credenciais = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(credenciais, scopes=scope)
else:
    creds = Credentials.from_service_account_file("credenciais.json", scopes=scope)

client = gspread.authorize(creds)
planilha = client.open(NOME_PLANILHA)
aba = planilha.sheet1

cabecalho = aba.row_values(1)
nova_linha = [linha.get(coluna, "") for coluna in cabecalho]

datas_existentes = aba.col_values(1)

# Procura a data de hoje na coluna A
numero_linha = None

for i, data in enumerate(datas_existentes, start=1):
    if str(data).strip() == data_hoje:
        numero_linha = i
        break

if numero_linha:
    aba.update(
        range_name=f"A{numero_linha}",
        values=[nova_linha]
    )
    print(f"Data {data_hoje} já existia. Linha atualizada.")
else:
    aba.append_row(nova_linha)
    print(f"Data {data_hoje} não existia. Nova linha gravada.")

# ──────────────────────────────────────────────────────────────────
# A partir daqui, o Sheets (que o dashboard depende) já está
# atualizado com sucesso. Só agora, depois disso, exporta também um
# JSON público e enxuto (só a curva do dia, sem histórico) pra ser
# consumido pelo Simulador de Spread de Milho via fetch() direto no
# navegador do visitante do site. O Google Sheets exige autenticação
# e não é servível publicamente como está; este arquivo é commitado
# no repositório pelo próprio workflow do GitHub Actions e servido
# via raw.githubusercontent.com (preferido a um CDN com cache
# agressivo, já que o dado muda todo dia).
# Fica dentro de um try/except de propósito: se essa parte falhar
# por qualquer motivo, o script termina com sucesso do mesmo jeito,
# porque a parte que o dashboard depende (Sheets) já rodou antes e
# está isolada desta.
# ──────────────────────────────────────────────────────────────────
try:
    data_atualizacao = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

    curva_publica = {
        "atualizado_em": data_atualizacao,
        "fonte": "TradingView (BMFBOVESPA-CCM1!)",
        "curva": {k: v for k, v in linha.items() if k != "Data"}
    }

    CAMINHO_JSON = "dados/curva_ccm.json"
    os.makedirs(os.path.dirname(CAMINHO_JSON), exist_ok=True)
    with open(CAMINHO_JSON, "w", encoding="utf-8") as f:
        json.dump(curva_publica, f, ensure_ascii=False, indent=2)

    print(f"JSON público gravado em {CAMINHO_JSON}: {curva_publica}")
except Exception as e:
    print(f"Aviso: não consegui gravar o JSON público da curva (não afeta o Sheets/dashboard). Erro: {e}")a gravada.")
