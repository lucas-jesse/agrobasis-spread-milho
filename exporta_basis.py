"""Exporta o basis da soja e do milho para os dashboards HTML do site.

Lê as planilhas do Google Drive que o Lucas atualiza (com a mesma credencial
de serviço do spread) e grava JSON compactos em dados/basis/:

  soja.json  : planilha "fechamento_usd_bushel" (CBOT ZS em US$/bu, PTAX e
               físico por praça em R$/sc). Basis em cents/bu, com a mesma
               regra de contrato de referência do app Streamlit:
               basis = físico (R$/sc ÷ PTAX × 27,2155/60 × 100) − CBOT ref.
  milho.json : aba "basis_diario" da planilha "Preço milho Fisico", gerada
               pelo pipeline do repositório agrobasis-basis-milho
               (físico manual + Conab semanal × CCM B3). Basis em R$/sc.

Os números só mudam quando a planilha muda; o atualizado_em é preservado
quando não há novidade, para não gerar commit vazio.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

TZ = ZoneInfo("America/Sao_Paulo")
DESTINO = Path("dados/basis")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

SOJA_SHEET_ID = "1nj__9QGMMXR3L8L0PaP6wnPYxztDgtu0T9cKWg2jjOY"
SOJA_ABA = "fechamento_usd_bushel"
MILHO_PLANILHA = "Preço milho Fisico"
MILHO_ABA = "basis_diario"
KG_BUSHEL_SOJA = 27.2155


def cliente():
    import gspread
    from google.oauth2.service_account import Credentials
    info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    print("conta de serviço:", info.get("client_email"))
    return gspread.authorize(Credentials.from_service_account_info(info, scopes=SCOPES))


def num(v):
    if v is None:
        return np.nan
    if isinstance(v, (int, float, np.number)):
        return float(v)
    t = str(v).strip().replace("R$", "").replace("US$", "").replace(" ", "")
    if t == "" or t.lower() in ("nan", "none", "#n/a", "#value!", "#ref!", "-"):
        return np.nan
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return np.nan


def aba_df(ws):
    v = ws.get_all_values()
    if len(v) < 2:
        return pd.DataFrame()
    return pd.DataFrame(v[1:], columns=[str(c).strip() for c in v[0]]).replace("", np.nan).dropna(how="all")


def contrato_ref_soja(d):
    """Mesma regra do app Streamlit do Basis Soja."""
    m, a = d.month, d.year
    if m == 12:
        return f"ZSF{str(a + 1)[-2:]}"
    tab = {1: "H", 2: "H", 3: "K", 4: "K", 5: "N", 6: "N", 7: "Q", 8: "U", 9: "X", 10: "X"}
    if m in tab:
        return f"ZS{tab[m]}{str(a)[-2:]}"
    return f"ZSF{str(a + 1)[-2:]}"


def r(x, c=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), c)


def exportar_soja(cli):
    df = aba_df(cli.open_by_key(SOJA_SHEET_ID).worksheet(SOJA_ABA))
    if "date" not in df.columns and "Data" in df.columns:
        df = df.rename(columns={"Data": "date"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="last")
    for c in df.columns:
        if c != "date":
            df[c] = df[c].map(num)
    contratos = [c for c in df.columns if re.match(r"^ZS[FHKNQUX]\d{2}$", str(c))]
    pracas = [c for c in df.columns if c not in ["date", "PTAX"] + contratos and df[c].notna().any()]
    datas, ptax, ref, cbot = [], [], [], []
    por = {p: {"fisico": [], "basis": []} for p in pracas}
    for _, row in df.iterrows():
        px = row.get("PTAX")
        cref = contrato_ref_soja(row["date"])
        cb = row.get(cref) if cref in df.columns else np.nan
        if pd.isna(px) or px <= 0 or pd.isna(cb) or cb <= 0:
            continue
        datas.append(row["date"].strftime("%Y-%m-%d"))
        ptax.append(r(px, 4)); ref.append(cref); cbot.append(r(cb * 100, 2))
        for p in pracas:
            f = row.get(p)
            if pd.isna(f) or f <= 0:
                por[p]["fisico"].append(None); por[p]["basis"].append(None)
            else:
                fis_c = f / px * (KG_BUSHEL_SOJA / 60) * 100
                por[p]["fisico"].append(r(f, 2)); por[p]["basis"].append(r(fis_c - cb * 100, 1))
    return {"fonte": "Planilha AgroBasis (físico) · CBOT · PTAX/BCB", "unidade_basis": "cents/bushel",
            "datas": datas, "ptax": ptax, "contrato_ref": ref, "cbot_ref_cents": cbot, "pracas": por}


def exportar_milho(cli):
    df = aba_df(cli.open(MILHO_PLANILHA).worksheet(MILHO_ABA))
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    for c in ["Preco_Fisico", "Preco_B3", "Basis"]:
        df[c] = df[c].map(num)
    df = df.dropna(subset=["Data", "Cidade", "Basis"]).sort_values("Data")
    pracas = {}
    for cid, g in df.groupby("Cidade"):
        g = g.drop_duplicates("Data", keep="last")
        pracas[cid] = {
            "datas": g["Data"].dt.strftime("%Y-%m-%d").tolist(),
            "fisico": [r(v) for v in g["Preco_Fisico"]],
            "b3": [r(v) for v in g["Preco_B3"]],
            "basis": [r(v) for v in g["Basis"]],
            "contrato": g["Contrato_Ref"].astype(str).tolist(),
            "fonte": g["Fonte"].astype(str).str[0].tolist() if "Fonte" in g else None,  # M = manual, C = Conab
        }
    return {"fonte": "Planilha AgroBasis (físico) · Conab · B3", "unidade_basis": "R$/saca", "pracas": pracas}


def gravar(nome, dados):
    DESTINO.mkdir(parents=True, exist_ok=True)
    arq = DESTINO / f"{nome}.json"
    agora = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    dados = {"atualizado_em": agora, **dados}
    if arq.exists():
        antigo = json.loads(arq.read_text(encoding="utf-8"))
        if {k: v for k, v in antigo.items() if k != "atualizado_em"} == {k: v for k, v in dados.items() if k != "atualizado_em"}:
            print(nome, "sem mudança")
            return
    arq.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(nome, f"{arq.stat().st_size / 1024:.0f} KB gravado")


def main():
    cli = cliente()
    erros = 0
    for nome, fn in (("soja", exportar_soja), ("milho", exportar_milho)):
        try:
            gravar(nome, fn(cli))
        except Exception as e:  # noqa: BLE001
            erros += 1
            print(f"ERRO {nome}: {type(e).__name__}: {e}")
    sys.exit(1 if erros == 2 else 0)


if __name__ == "__main__":
    main()
