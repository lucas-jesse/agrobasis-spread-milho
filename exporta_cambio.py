"""Coleta de câmbio e juros para o dashboard Curva do Dólar (HTML).

Grava dados/cambio.json com:
  - dol: contratos futuros de dólar da B3 (R$/US$), por vencimento, com volume e contratos em aberto
  - di1: contratos futuros de DI1 da B3 (taxa % a.a.), por vencimento
  - ptax: série diária da PTAX de venda (Banco Central, SGS 1), últimos 6 anos
  - focus: mediana do Focus para o câmbio de fim de ano (ano corrente e seguintes)
  - selic: meta Selic vigente (SGS 432)
E acrescenta a curva do dia em dados/cambio_curvas.json (histórico de curvas, até 400 pregões),
para comparar a curva de hoje com a de uma semana e um mês atrás.

Fontes: scanner público do TradingView (contratos B3, atraso de 10 a 15 min) e APIs públicas do BCB.
"""
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TZ = ZoneInfo("America/Sao_Paulo")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Origin": "https://br.tradingview.com", "Referer": "https://br.tradingview.com/"}
LETRAS = "FGHJKMNQUVXZ"


def proximos_meses(hoje, n):
    out, a, m = [], hoje.year, hoje.month
    for _ in range(n):
        out.append((a, m))
        m += 1
        if m > 12:
            m, a = 1, a + 1
    return out


def primeiro_dia_util(a, m):
    d = date(a, m, 1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def scanner(tickers, colunas):
    for endpoint in ("brazil", "futures", "global"):
        try:
            dados = []
            for i in range(0, len(tickers), 40):
                r = requests.post(f"https://scanner.tradingview.com/{endpoint}/scan",
                                  json={"symbols": {"tickers": tickers[i:i + 40], "query": {"types": []}}, "columns": colunas},
                                  headers=UA, timeout=25)
                r.raise_for_status()
                dados.extend(r.json().get("data", []) or [])
            if dados:
                return {x["s"]: dict(zip(colunas, x["d"])) for x in dados}
        except Exception as e:  # noqa: BLE001
            print("scanner", endpoint, e)
    return {}


def coletar_dol(hoje):
    meses = proximos_meses(hoje, 40)
    tick = {f"BMFBOVESPA:DOL{LETRAS[m - 1]}{a}": (a, m) for a, m in meses}
    res = scanner(list(tick), ["close", "volume", "open_interest", "change", "update_mode"])
    out = []
    for t, (a, m) in tick.items():
        v = res.get(t)
        if not v or v.get("close") is None:
            continue
        preco = float(v["close"])
        preco = preco / 1000 if preco > 100 else preco  # B3 cota em pontos (R$ por US$ 1.000)
        if not 3 <= preco <= 9:
            continue
        out.append({"contrato": f"DOL{LETRAS[m - 1]}{str(a)[-2:]}", "vencimento": primeiro_dia_util(a, m).isoformat(),
                    "preco": round(preco, 4), "volume": v.get("volume"), "em_aberto": v.get("open_interest"),
                    "var_pct": round(v["change"], 2) if v.get("change") is not None else None})
    return out


def coletar_di1(hoje):
    meses = proximos_meses(hoje, 13)
    # depois do primeiro ano, só os vencimentos de janeiro (os mais líquidos) até 10 anos
    meses += [(a, 1) for a in range(hoje.year + 2, hoje.year + 11) if (a, 1) not in meses]
    tick = {f"BMFBOVESPA:DI1{LETRAS[m - 1]}{a}": (a, m) for a, m in meses}
    res = scanner(list(tick), ["close", "volume", "open_interest"])
    out = []
    for t, (a, m) in tick.items():
        v = res.get(t)
        if not v or v.get("close") is None:
            continue
        taxa = float(v["close"])
        if not 1 <= taxa <= 40:
            continue
        out.append({"contrato": f"DI1{LETRAS[m - 1]}{str(a)[-2:]}", "vencimento": primeiro_dia_util(a, m).isoformat(),
                    "taxa": round(taxa, 3), "volume": v.get("volume"), "em_aberto": v.get("open_interest")})
    return sorted(out, key=lambda x: x["vencimento"])


def bcb_sgs(serie, ini, fim):
    r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados",
                     params={"formato": "json", "dataInicial": ini.strftime("%d/%m/%Y"), "dataFinal": fim.strftime("%d/%m/%Y")},
                     headers={"User-Agent": UA["User-Agent"]}, timeout=40)
    r.raise_for_status()
    return r.json()


def coletar_ptax(hoje):
    out = []
    # a API do SGS limita consultas diárias a 10 anos; 6 anos em dois blocos por segurança
    for ini, fim in ((hoje - timedelta(days=6 * 365), hoje - timedelta(days=3 * 365)), (hoje - timedelta(days=3 * 365) + timedelta(days=1), hoje)):
        for x in bcb_sgs(1, ini, fim):
            d = datetime.strptime(x["data"], "%d/%m/%Y").date().isoformat()
            out.append([d, round(float(x["valor"]), 4)])
    out = sorted({d: v for d, v in out}.items())
    return {"datas": [d for d, _ in out], "valores": [v for _, v in out]}


def coletar_focus(hoje):
    url = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
    r = requests.get(url, params={"$top": "60", "$filter": "Indicador eq 'Câmbio'", "$orderby": "Data desc", "$format": "json",
                                  "$select": "Data,DataReferencia,Mediana,baseCalculo"},
                     headers={"User-Agent": UA["User-Agent"]}, timeout=40)
    r.raise_for_status()
    v = [x for x in r.json()["value"] if str(x.get("baseCalculo")) == "0"]
    if not v:
        return None
    ult = max(x["Data"] for x in v)
    anos = sorted({int(x["DataReferencia"]) for x in v if x["Data"] == ult and int(x["DataReferencia"]) <= hoje.year + 3})
    return {"data": ult, "fim_de_ano": {str(a): next(x["Mediana"] for x in v if x["Data"] == ult and int(x["DataReferencia"]) == a) for a in anos}}


def coletar_selic():
    x = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1", params={"formato": "json"},
                     headers={"User-Agent": UA["User-Agent"]}, timeout=30).json()[-1]
    return {"meta_aa": float(x["valor"])}


def tentar(nome, fn, *a):
    for i in range(3):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            print(f"falha {nome} ({i + 1}/3): {type(e).__name__}: {e}"[:300])
            time.sleep(3 + 4 * i)
    return None


def main():
    agora = datetime.now(TZ)
    hoje = agora.date()
    arq = Path("dados/cambio.json")
    antigo = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    novo = {
        "atualizado_em": agora.strftime("%d/%m/%Y %H:%M"),
        "fonte": "B3 via TradingView (atraso de 10 a 15 min) · Banco Central (PTAX, Focus, Selic)",
        "dol": tentar("dol", coletar_dol, hoje),
        "di1": tentar("di1", coletar_di1, hoje),
        "ptax": tentar("ptax", coletar_ptax, hoje),
        "focus": tentar("focus", coletar_focus, hoje),
        "selic": tentar("selic", coletar_selic),
    }
    # se uma fonte falhar, mantém o último dado bom dela
    for k in ("dol", "di1", "ptax", "focus", "selic"):
        if not novo[k] and antigo.get(k):
            novo[k] = antigo[k]
            novo.setdefault("avisos", []).append(f"{k}: mantido o último dado disponível")
    if not novo["dol"]:
        raise SystemExit("sem curva de dólar futuro")
    arq.parent.mkdir(exist_ok=True)
    arq.write_text(json.dumps(novo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # histórico de curvas: uma por dia (a última coleta do dia prevalece)
    hist_p = Path("dados/cambio_curvas.json")
    hist = json.loads(hist_p.read_text(encoding="utf-8")) if hist_p.exists() else {}
    hist[hoje.isoformat()] = {"dol": {x["contrato"]: x["preco"] for x in novo["dol"]},
                              "di1": {x["contrato"]: x["taxa"] for x in (novo["di1"] or [])},
                              "ptax": novo["ptax"]["valores"][-1] if novo.get("ptax") else None}
    hist = dict(sorted(hist.items())[-400:])
    hist_p.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({k: (v if k not in ("ptax",) else {"n": len(v["datas"]), "ult": v["datas"][-1]} if v else None) for k, v in novo.items()}, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
