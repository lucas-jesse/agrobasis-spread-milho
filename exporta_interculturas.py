"""Painel "Relação entre culturas": soja, milho e trigo em Chicago (CBOT).

Grava dados/interculturas.json com:
  - serie     : vencimento mais próximo (contínuo 1!) de soja, milho e trigo, diário, para as relações de longo prazo
  - safra     : relação de safra nova ano a ano (soja novembro / milho dezembro; trigo dezembro - milho dezembro)
  - curva     : relação por vencimento (mesmo mês de entrega, ou o par usual), com o histórico recente de cada par
  - hoje      : indicadores com percentis

Fonte: CME Group via TradingView (fechamentos diários, com atraso). Preços em centavos de dólar por bushel.
Relações usadas:
  soja/milho  = preço da soja / preço do milho (por bushel). Referência clássica de rentabilidade relativa
                para o plantio nos EUA: safra nova = soja novembro / milho dezembro do mesmo ano.
  trigo-milho = trigo (SRW, Chicago) menos milho, em US$ por tonelada (trigo 36,744 bu/t; milho 39,368 bu/t).
                Quando o trigo encosta no milho, ele passa a entrar na ração no lugar do milho.
  soja/trigo  = preço da soja / preço do trigo (por bushel).
"""
import json
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from tv_historico import historico

RAIZ = Path(__file__).resolve().parent
BRT = ZoneInfo("America/Sao_Paulo")
BU_T = {"ZS": 36.744, "ZW": 36.744, "ZC": 39.368}
LETRA_MES = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}
MESES = {"ZS": "FHKNQUX", "ZC": "HKNUZ", "ZW": "HKNUZ"}
# pares por vencimento: (soja, milho) e (trigo, milho) no mesmo ano-calendário; soja janeiro com milho março
PARES_SM = [("F", "H"), ("H", "H"), ("K", "K"), ("N", "N"), ("U", "U"), ("X", "Z")]


def r(x, c=3):
    return None if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))) else round(float(x), c)


def pega(simbolo, barras=800, tent=3):
    for i in range(tent):
        try:
            s = historico(simbolo, "D", barras)
            if len(s):
                return s[~s.index.duplicated(keep="last")].astype(float)
        except Exception as e:
            print("falha", simbolo, str(e)[:120])
            time.sleep(2 + 3 * i)
    return None


def venc(cod, letra, ano):
    """Data aproximada do último pregão (dia 14 do mês de entrega) para ordenar e saber se já venceu."""
    return date(ano, LETRA_MES[letra], 14)


def pct(s, v):
    s = pd.Series(s).dropna()
    return r((s < v).mean() * 100, 0) if len(s) and v is not None else None


def main():
    hoje = datetime.now(BRT).date()

    # 1) contínuos (vencimento mais próximo), ~15 anos
    cont = {}
    for c in ("ZS", "ZC", "ZW"):
        cont[c] = pega(f"CBOT:{c}1!", 4000)
        if cont[c] is None:
            raise SystemExit(f"sem contínuo {c}")
    S = pd.DataFrame(cont).dropna()
    S["sm"] = S["ZS"] / S["ZC"]
    S["tm"] = S["ZW"] / 100 * BU_T["ZW"] - S["ZC"] / 100 * BU_T["ZC"]
    S["tmr"] = S["ZW"] / S["ZC"]
    S["st"] = S["ZS"] / S["ZW"]
    ult = S.index[-1]
    print("contínuo", S.index[0].date(), ult.date(), len(S))

    # 2) contratos em aberto (próximos 20 meses) e histórico recente de cada um
    abertos = {}
    for c in ("ZS", "ZC", "ZW"):
        for ano in (hoje.year, hoje.year + 1, hoje.year + 2):
            for l in MESES[c]:
                if venc(c, l, ano) < hoje or (venc(c, l, ano) - hoje).days > 640:
                    continue
                s = pega(f"CBOT:{c}{l}{ano}", 400)
                if s is not None and len(s) > 5:
                    abertos[f"{c}{l}{ano}"] = s
    print("abertos", sorted(abertos))

    curva = []
    for ano in (hoje.year, hoje.year + 1, hoje.year + 2):
        for ls, lc in PARES_SM:
            ks, kc, kw = f"ZS{ls}{ano}", f"ZC{lc}{ano}", f"ZW{lc}{ano}"
            if ks in abertos and kc in abertos:
                d = pd.DataFrame({"s": abertos[ks], "c": abertos[kc]}).dropna()
                w = abertos.get(kw)
                if w is not None:
                    d["w"] = w
                d = d[d.index >= d.index[-1] - pd.Timedelta(days=370)]
                item = {"soja": ks, "milho": kc, "trigo": kw if kw in abertos else None,
                        "rotulo": f"{ls}/{lc} {str(ano)[-2:]}",
                        "s": r(d["s"].iloc[-1], 2), "c": r(d["c"].iloc[-1], 2),
                        "sm": r(d["s"].iloc[-1] / d["c"].iloc[-1]),
                        "d": [x.strftime("%Y-%m-%d") for x in d.index], "smh": [r(x) for x in d["s"] / d["c"]]}
                if "w" in d and d["w"].notna().iloc[-1]:
                    item["w"] = r(d["w"].iloc[-1], 2)
                    item["tm"] = r(d["w"].iloc[-1] / 100 * BU_T["ZW"] - d["c"].iloc[-1] / 100 * BU_T["ZC"], 1)
                    item["st"] = r(d["s"].iloc[-1] / d["w"].iloc[-1])
                    item["tmh"] = [r(a / 100 * BU_T["ZW"] - b / 100 * BU_T["ZC"], 1) if pd.notna(a) else None for a, b in zip(d["w"], d["c"])]
                curva.append(item)
    curva.sort(key=lambda x: venc("ZC", x["milho"][2], int(x["milho"][3:])))

    # 3) safra nova ano a ano: soja novembro / milho dezembro; trigo dezembro - milho dezembro
    safra_sm, safra_tm = {}, {}
    for ano in range(hoje.year - 10, hoje.year + 2):
        ks, kc, kw = f"ZSX{ano}", f"ZCZ{ano}", f"ZWZ{ano}"
        s = abertos.get(ks) if ks in abertos else pega(f"CBOT:{ks}", 800)
        c = abertos.get(kc) if kc in abertos else pega(f"CBOT:{kc}", 800)
        w = abertos.get(kw) if kw in abertos else pega(f"CBOT:{kw}", 800)
        if s is None or c is None:
            print("sem safra", ano)
            continue
        ini, fim = pd.Timestamp(f"{ano - 1}-09-01"), pd.Timestamp(f"{ano}-11-13")
        d = pd.DataFrame({"s": s, "c": c}).dropna()
        d = d[(d.index >= ini) & (d.index <= fim)]
        if len(d) > 20:
            safra_sm[str(ano)] = [[(x - pd.Timestamp(f"{ano}-01-01")).days, r(v)] for x, v in (d["s"] / d["c"]).items()]
        if w is not None:
            e = pd.DataFrame({"w": w, "c": c}).dropna()
            e = e[(e.index >= ini) & (e.index <= pd.Timestamp(f"{ano}-12-13"))]
            if len(e) > 20:
                safra_tm[str(ano)] = [[(x - pd.Timestamp(f"{ano}-01-01")).days, r(v, 1)]
                                      for x, v in (e["w"] / 100 * BU_T["ZW"] - e["c"] / 100 * BU_T["ZC"]).items()]
    print("safra soja/milho", list(safra_sm), "trigo-milho", list(safra_tm))

    # 4) indicadores de hoje
    dez = max([k for k in safra_sm if safra_sm[k] and int(k) >= hoje.year], default=None)
    hj = S.iloc[-1]
    dez_anos = S[S.index >= ult - pd.Timedelta(days=3653)]

    def mesma_epoca(safra, ano_atual):
        """valor de cada ano anterior na mesma data relativa (dias desde 1º de janeiro do ano da safra)"""
        if ano_atual not in safra:
            return [], None
        x0 = safra[ano_atual][-1][0]
        outros = []
        for a, pts in safra.items():
            if a == ano_atual:
                continue
            perto = [p for p in pts if abs(p[0] - x0) <= 5]
            if perto:
                outros.append({"ano": int(a), "v": min(perto, key=lambda p: abs(p[0] - x0))[1]})
        return outros, x0

    out_sm, x_sm = mesma_epoca(safra_sm, dez) if dez else ([], None)
    out_tm, _ = mesma_epoca(safra_tm, dez) if dez and dez in safra_tm else ([], None)
    nova_sm = safra_sm[dez][-1][1] if dez else None
    nova_tm = safra_tm[dez][-1][1] if dez and dez in safra_tm else None

    def resumo(nome, serie, v):
        return {"v": r(v), "pct10": pct(serie, v), "med10": r(np.median(serie.dropna())), "min10": r(serie.min()), "max10": r(serie.max())}

    saida = {
        "atualizado_em": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"),
        "referencia": ult.strftime("%Y-%m-%d"),
        "fonte": "CME Group via TradingView (fechamentos diários)",
        "constantes": {"bu_t_soja_trigo": BU_T["ZS"], "bu_t_milho": BU_T["ZC"]},
        "hoje": {
            "zs": r(hj["ZS"], 2), "zc": r(hj["ZC"], 2), "zw": r(hj["ZW"], 2),
            "sm": resumo("sm", dez_anos["sm"], hj["sm"]), "tm": resumo("tm", dez_anos["tm"], hj["tm"]),
            "tmr": resumo("tmr", dez_anos["tmr"], hj["tmr"]), "st": resumo("st", dez_anos["st"], hj["st"]),
            "safra_ano": int(dez) if dez else None,
            "safra_sm": r(nova_sm), "safra_sm_anteriores": out_sm,
            "safra_sm_media": r(np.mean([o["v"] for o in out_sm])) if out_sm else None,
            "safra_sm_pct": pct([o["v"] for o in out_sm], nova_sm) if out_sm else None,
            "safra_tm": r(nova_tm, 1), "safra_tm_anteriores": out_tm,
            "safra_tm_media": r(np.mean([o["v"] for o in out_tm]), 1) if out_tm else None,
        },
        "serie": {"datas": [d.strftime("%Y-%m-%d") for d in S.index], "zs": [r(x, 2) for x in S["ZS"]],
                  "zc": [r(x, 2) for x in S["ZC"]], "zw": [r(x, 2) for x in S["ZW"]]},
        "safra": {"sm": safra_sm, "tm": safra_tm},
        "curva": curva,
    }
    destino = RAIZ / "dados/interculturas.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("ok", saida["referencia"], json.dumps(saida["hoje"])[:400], f"{destino.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
