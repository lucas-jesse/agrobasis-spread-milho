"""Exporta o histórico diário dos contratos de milho B3 (CCM) para JSON público.

Lê a planilha "Historico Spread Milho" (a mesma que o app Streamlit usa, via
exportação CSV pública) e grava dados/ccm_historico.json num formato colunar
enxuto, consumido pelo dashboard em HTML do site:

{
  "atualizado_em": "08/11/2026 18:40",
  "fonte": "B3 via TradingView",
  "datas": ["2020-01-02", ...],
  "contratos": {"CCMF21": [62.5, null, ...], ...}
}
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

SHEET_ID = "1uGrRfOg2W9ICx58eKgwCjJ-bCWZ3l_y7bLbt1CA3mAE"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
DESTINO = Path("dados/ccm_historico.json")


def carregar():
    df = pd.read_csv(URL)
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Data"]).sort_values("Data").drop_duplicates("Data", keep="last")
    cols = [c for c in df.columns if str(c).startswith("CCM") and len(str(c)) == 6]
    for c in cols:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    return df[["Data"] + cols]


def main():
    df = carregar()
    contratos = {}
    for c in df.columns[1:]:
        serie = df[c].round(2)
        if serie.notna().sum() == 0:
            continue
        contratos[c] = [None if pd.isna(v) else float(v) for v in serie]
    saida = {
        "atualizado_em": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M"),
        "fonte": "B3 via TradingView",
        "datas": df["Data"].dt.strftime("%Y-%m-%d").tolist(),
        "contratos": contratos,
    }
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(saida['datas'])} datas, {len(contratos)} contratos, {DESTINO.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
