"""Exporta o Commitments of Traders (CFTC) para o dashboard Posição dos Fundos (HTML).

Fontes:
  - CFTC, Disaggregated Futures Only (arquivos anuais oficiais, atualizados toda sexta)
  - Stooq: preço de fechamento diário do contrato contínuo, alinhado à terça do relatório
  - CME Group Daily Bulletin, Section 03: open interest por vencimento (produtos CBOT)

Grava em dados/cot/:
  <produto>.json : série semanal completa (desde 2010) por categoria de participante
  resumo.json    : último relatório de todas as commodities, para o quadro geral
"""
import io
import json
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

TZ = ZoneInfo("America/Sao_Paulo")
ANO_INICIAL = 2010
DESTINO = Path("dados/cot")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# slug: (nome, código CFTC, símbolo Stooq, divisor do preço, unidade do preço, seção do bulletin CME, tamanho do contrato)
PRODUTOS = {
    "soja": ("Soja", 5602, "zs.f", 100, "US$/bushel", "SOYBEAN FUT", "5.000 bushels"),
    "milho": ("Milho", 2602, "zc.f", 100, "US$/bushel", "CORN FUT", "5.000 bushels"),
    "farelo": ("Farelo de soja", 26603, "zm.f", 1, "US$/tonelada curta", "SOY MEAL FUT", "100 toneladas curtas"),
    "oleo": ("Óleo de soja", 7601, "zl.f", 100, "US$/libra", "SOY OIL FUT", "60.000 libras"),
    "trigo": ("Trigo Chicago", 1602, "zw.f", 100, "US$/bushel", "WHEAT FUT", "5.000 bushels"),
    "trigo_kansas": ("Trigo Kansas", 1612, "ke.f", 100, "US$/bushel", None, "5.000 bushels"),
    "algodao": ("Algodão", 33661, "ct.f", 100, "US$/libra", None, "50.000 libras"),
}

# categoria: (rótulo, coluna long, coluna short, coluna spread)
CATEGORIAS = {
    "mm": ("Fundos", "m_money_positions_long_all", "m_money_positions_short_all", "m_money_positions_spread_all"),
    "pm": ("Produtores e comerciais", "prod_merc_positions_long_all", "prod_merc_positions_short_all", None),
    "sw": ("Swap dealers", "swap_positions_long_all", "swap__positions_short_all", "swap__positions_spread_all"),
    "or": ("Outros reportáveis", "other_rept_positions_long_all", "other_rept_positions_short_all", "other_rept_positions_spread_all"),
    "nr": ("Pequenos especuladores", "nonrept_positions_long_all", "nonrept_positions_short_all", None),
}
TRADERS = {"mm_l": "traders_m_money_long_all", "mm_s": "traders_m_money_short_all"}


def norm(df):
    df.columns = (df.columns.astype(str).str.strip().str.replace(" ", "_", regex=False)
                  .str.replace("-", "_", regex=False).str.replace("/", "_", regex=False).str.lower())
    return df


def baixar_cftc(ano):
    url = f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{ano}.zip"
    for _ in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content))
            nome = [n for n in z.namelist() if n.lower().endswith((".txt", ".csv"))][0]
            return norm(pd.read_csv(z.open(nome), low_memory=False, encoding="latin1"))
        except Exception as e:  # noqa: BLE001
            err = e
    print("CFTC", ano, "falhou:", err)
    return None


def col(df, *opcoes):
    for o in opcoes:
        if o and o in df.columns:
            return o
    return None


DIAG = []


def precos_stooq(simbolo, divisor):
    try:
        r = requests.get("https://stooq.com/q/d/l/", params={"s": simbolo, "i": "d"}, headers=UA, timeout=60)
        r.raise_for_status()
        if not r.text.startswith("Date"):
            raise ValueError("resposta inesperada: " + r.text[:120].replace("\n", " "))
        p = pd.read_csv(io.StringIO(r.text))
        p["Date"] = pd.to_datetime(p["Date"])
        s = (p.set_index("Date")["Close"] / divisor).sort_index()
        return s[s.index >= f"{ANO_INICIAL}-01-01"]
    except Exception as e:  # noqa: BLE001
        DIAG.append(f"Stooq {simbolo}: {type(e).__name__} {str(e)[:200]}")
        return None


RE_VENC = re.compile(r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{2})$")
MES_EN = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}


def oi_por_vencimento():
    """Open interest por vencimento (mercado inteiro) do Daily Bulletin da CME. Pode falhar por bloqueio."""
    try:
        import pdfplumber
        r = requests.get("https://www.cmegroup.com/daily_bulletin/current/Section03_Agricultural_Futures.pdf",
                         headers={**UA, "Accept": "application/pdf,*/*", "Referer": "https://www.cmegroup.com/market-data/daily-bulletin.html"}, timeout=60)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            DIAG.append(f"CME: resposta não é PDF ({r.headers.get('Content-Type')}): {r.content[:120]!r}")
            return {}
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            texto = "\n".join(pg.extract_text() or "" for pg in pdf.pages)
    except Exception as e:  # noqa: BLE001
        DIAG.append(f"CME: {type(e).__name__} {str(e)[:200]}")
        return {}
    m = re.search(r"(\d{2}/\d{2}/\d{4})", texto[:3000])
    data_bul = m.group(1) if m else None
    out = {}
    linhas = texto.splitlines()
    for slug, cfg in PRODUTOS.items():
        sec = cfg[5]
        if not sec:
            continue
        try:
            ini = next(i for i, l in enumerate(linhas) if l.strip() == sec) + 1
        except StopIteration:
            continue
        regs = []
        for l in linhas[ini:]:
            t = l.strip().split()
            if not t:
                continue
            if t[0].upper() == "TOTAL":
                break
            mm = RE_VENC.match(t[0])
            if not mm:
                break
            i = 5
            if i >= len(t):
                continue
            i += 1 if t[i].upper() == "UNCH" else 2
            if i + 2 >= len(t):
                continue
            try:
                oi = int(t[i + 2].replace(",", ""))
            except ValueError:
                continue
            regs.append({"v": f"{mm.group(1)}{mm.group(2)}", "k": (2000 + int(mm.group(2))) * 12 + MES_EN[mm.group(1)], "oi": oi})
        if regs:
            regs.sort(key=lambda x: x["k"])
            out[slug] = {"data": data_bul, "contratos": [{"v": x["v"], "oi": x["oi"]} for x in regs if x["oi"] > 0]}
    print("CME OI por vencimento:", {k: len(v["contratos"]) for k, v in out.items()})
    return out


def lista(s, casas=0):
    return [None if pd.isna(v) else (int(v) if casas == 0 else round(float(v), casas)) for v in s]


def percentil(serie, valor):
    v = serie.dropna()
    return None if v.empty or valor is None else round(float((v < valor).mean() * 100), 1)


def main():
    anos = range(ANO_INICIAL, datetime.now(TZ).year + 1)
    partes = [d for d in (baixar_cftc(a) for a in anos) if d is not None]
    if not partes:
        raise SystemExit("nenhum arquivo da CFTC")
    bruto = pd.concat(partes, ignore_index=True)
    c_cod = col(bruto, "cftc_contract_market_code")
    bruto["cod"] = pd.to_numeric(bruto[c_cod], errors="coerce")
    # a coluna de data muda de nome/formato entre os anos: usa a primeira que existir em cada linha
    data = pd.Series(pd.NaT, index=bruto.index)
    for c in ("report_date_as_yyyy_mm_dd", "report_date_as_mm_dd_yyyy"):
        if c in bruto.columns:
            data = data.fillna(pd.to_datetime(bruto[c], errors="coerce"))
    for c in ("as_of_date_in_form_yymmdd", "as_of_date_form_yymmdd"):
        if c in bruto.columns:
            data = data.fillna(pd.to_datetime(pd.to_numeric(bruto[c], errors="coerce").astype("Int64").astype(str).str.zfill(6), format="%y%m%d", errors="coerce"))
    bruto["data"] = data
    bruto = bruto.dropna(subset=["data"])
    oi_venc = oi_por_vencimento()
    DESTINO.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    resumo = {"atualizado_em": agora, "produtos": {}}
    for slug, (nome, cod, stq, div, un, _, tam) in PRODUTOS.items():
        d = bruto[bruto["cod"] == cod].sort_values("data").drop_duplicates("data", keep="last")
        if d.empty:
            print("sem dados", slug)
            continue
        out = {"atualizado_em": agora, "produto": nome, "codigo_cftc": cod, "contrato": tam, "unidade_preco": un,
               "mercado": str(d[col(d, "market_and_exchange_names")].iloc[-1]).strip(),
               "datas": d["data"].dt.strftime("%Y-%m-%d").tolist(),
               "oi": lista(pd.to_numeric(d["open_interest_all"], errors="coerce")), "cat": {}, "traders": {}}
        for k, (rot, cl, cs, csp) in CATEGORIAS.items():
            cl, cs, csp = col(d, cl), col(d, cs, cs.replace("swap__", "swap_")), col(d, csp, csp.replace("swap__", "swap_") if csp else None)
            out["cat"][k] = {"l": lista(pd.to_numeric(d[cl], errors="coerce")), "s": lista(pd.to_numeric(d[cs], errors="coerce")),
                             "sp": lista(pd.to_numeric(d[csp], errors="coerce")) if csp else None}
        for k, c in TRADERS.items():
            c = col(d, c)
            out["traders"][k] = lista(pd.to_numeric(d[c], errors="coerce")) if c else None
        pr = precos_stooq(stq, div)
        if pr is not None and not pr.empty:
            al = pr.reindex(pd.to_datetime(out["datas"]), method="ffill")
            out["preco"] = lista(al, 4)
        else:
            out["preco"] = None
        if slug in oi_venc:
            out["oi_vencimento"] = oi_venc[slug]
        arq = DESTINO / f"{slug}.json"
        arq.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        # resumo: fundos (managed money)
        mm = out["cat"]["mm"]
        net = pd.Series([None if a is None or b is None else a - b for a, b in zip(mm["l"], mm["s"])], dtype="float")
        dts = pd.to_datetime(out["datas"])
        cinco = net[dts >= dts.max() - pd.DateOffset(years=5)]
        n = float(net.iloc[-1])
        resumo["produtos"][slug] = {
            "nome": nome, "data": out["datas"][-1], "net": int(n),
            "d1": int(n - net.iloc[-2]) if len(net) > 1 else None, "d4": int(n - net.iloc[-5]) if len(net) > 4 else None,
            "pct_oi": round(n / out["oi"][-1] * 100, 1) if out["oi"][-1] else None,
            "pctl5": percentil(cinco, n), "min5": int(cinco.min()), "max5": int(cinco.max()),
            "spark": [int(x) for x in net.tail(26).tolist()],
            "preco": out["preco"][-1] if out["preco"] else None, "unidade_preco": un,
        }
        print(slug, len(out["datas"]), out["datas"][-1], "net MM", int(n), "preço", out["preco"][-1] if out["preco"] else None, f"{arq.stat().st_size/1024:.0f} KB")
    resumo["diagnostico"] = DIAG
    (DESTINO / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
