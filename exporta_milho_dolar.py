"""Painel "Milho B3 x Dólar": valor relativo entre o milho da B3 e o câmbio.

Lê os dados que o repositório já mantém e grava dados/milho_dolar.json:
  - dados/ccm_historico.json  : ajustes diários de todos os contratos de milho B3 (CCM)
  - dados/cambio.json         : PTAX diária, curva do dólar futuro (DOL) e DI1
  - CBOT:ZC1! (TradingView)   : milho em Chicago, para o prêmio implícito da B3 (opcional)

Contrato de referência da B3 (mesma regra dos outros painéis):
  jan/fev = H, mar/abr = K, mai/jun = N, jul/ago = U, set/out = X, nov/dez = F do ano seguinte.
Todas as variações usam o MESMO contrato no início e no fim da janela, para não misturar rolagens.
"""
import json
import math
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
BRT = ZoneInfo("America/Sao_Paulo")
SACA_BU = 60 / 25.4012          # bushels de milho por saca de 60 kg
CCM_SACAS = 450                 # tamanho do contrato de milho B3
WDO_USD = 10_000                # mini dólar
JANELA = 21                     # pregões no "descolamento de 1 mês"
LIMIAR_Z = -1.5                 # episódios do histórico do sinal


def ler(rel):
    return json.loads((RAIZ / rel).read_text(encoding="utf-8"))


def ref_ccm(d):
    m, a = d.month, d.year
    letra = {1: "H", 2: "H", 3: "K", 4: "K", 5: "N", 6: "N", 7: "U", 8: "U", 9: "X", 10: "X", 11: "F", 12: "F"}[m]
    if m >= 11:
        a += 1
    return f"CCM{letra}{str(a)[-2:]}"


def r(x, c=2):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else round(float(x), c)


def zc_chicago():
    """Fechamentos diários do milho CBOT (contínuo do 1º vencimento), em US$/bu. Falha sem quebrar o painel."""
    try:
        from tv_historico import historico
        s = historico("CBOT:ZC1!", "D", 2000)
        s.index = pd.to_datetime(s.index).normalize()
        return (s / 100.0).rename("zc")
    except Exception as e:  # rede, protocolo ou símbolo
        print("aviso: sem CBOT ZC", e)
        return None


def main():
    h = ler("dados/ccm_historico.json")
    cam = ler("dados/cambio.json")
    datas = pd.to_datetime(h["datas"])
    C = pd.DataFrame({k: v for k, v in h["contratos"].items()}, index=datas, dtype=float)
    ptax = pd.Series(cam["ptax"]["valores"], index=pd.to_datetime(cam["ptax"]["datas"]), dtype=float)

    base = pd.DataFrame(index=datas)
    base["ptax"] = ptax.reindex(datas)
    base = base[base["ptax"].notna()]
    base["ref"] = [ref_ccm(d) for d in base.index]
    base = base[base["ref"].isin(C.columns)]
    pos = {d: i for i, d in enumerate(C.index)}
    base["b3"] = [C.at[d, k] for d, k in zip(base.index, base["ref"])]
    base = base[base["b3"].notna()]
    base["b3_usd"] = base["b3"] / base["ptax"]

    # retornos diários encadeados (mesmo contrato nas duas pontas) e descolamento de 21 pregões
    idx = list(base.index)
    rb, ru, gap, gap63 = [], [], [], []
    for j, d in enumerate(idx):
        k = base.at[d, "ref"]
        i = pos[d]

        def lag(n):
            if i - n < 0:
                return None
            d0 = C.index[i - n]
            v0 = C.at[d0, k]
            p0 = ptax.get(d0)
            return (v0, p0) if pd.notna(v0) and p0 is not None and pd.notna(p0) else None

        v, p = base.at[d, "b3"], base.at[d, "ptax"]
        l1, l21, l63 = lag(1), lag(JANELA), lag(63)
        rb.append(math.log(v / l1[0]) if l1 else np.nan)
        ru.append(math.log(p / l1[1]) if l1 else np.nan)
        gap.append(math.log(v / l21[0]) - math.log(p / l21[1]) if l21 else np.nan)
        gap63.append(math.log(v / l63[0]) - math.log(p / l63[1]) if l63 else np.nan)
    base["rb"], base["ru"], base["gap"], base["gap63"] = rb, ru, gap, gap63

    g = base["gap"].dropna()
    mu, sd = g.mean(), g.std()
    base["z"] = (base["gap"] - mu) / sd

    # correlação e beta móveis (semanal, 26 semanas)
    sem = base[["rb", "ru"]].dropna().resample("W-FRI").sum()
    corr26 = sem["rb"].rolling(26).corr(sem["ru"])
    beta26 = sem["rb"].rolling(26).cov(sem["ru"]) / sem["ru"].rolling(26).var()
    corr_tot = sem["rb"].corr(sem["ru"])
    beta52 = (sem["rb"].tail(52).cov(sem["ru"].tail(52)) / sem["ru"].tail(52).var())

    # histórico do sinal: dias em que o descolamento de 1 mês cruzou z <= LIMIAR_Z
    eps, ult = [], None
    for j, d in enumerate(idx):
        z = base.at[d, "z"]
        if pd.isna(z) or z > LIMIAR_Z:
            continue
        if ult is not None and j - ult < JANELA:
            continue
        ult = j
        k = base.at[d, "ref"]
        fw = {}
        for n in (21, 42):
            if j + n < len(idx):  # retornos encadeados: troca para o contrato seguinte se o atual vencer
                sb, su = base["rb"].iloc[j + 1:j + n + 1].sum(), base["ru"].iloc[j + 1:j + n + 1].sum()
                fw[n] = (sb - su, sb, su)
        eps.append({"data": d.strftime("%Y-%m-%d"), "contrato": k, "z": r(z), "gap": r(base.at[d, "gap"] * 100, 1),
                    "f21": r(fw[21][0] * 100, 1) if 21 in fw else None, "f21_milho": r(fw[21][1] * 100, 1) if 21 in fw else None,
                    "f21_dolar": r(fw[21][2] * 100, 1) if 21 in fw else None,
                    "f42": r(fw[42][0] * 100, 1) if 42 in fw else None})
    f21 = [e["f21"] for e in eps if e["f21"] is not None]
    f42 = [e["f42"] for e in eps if e["f42"] is not None]

    # sazonal: contrato janeiro em US$/sc, de agosto até o vencimento, ano a ano
    sazonal = {}
    for k in sorted(c for c in C.columns if c.startswith("CCMF")):
        ano = 2000 + int(k[-2:])
        s = C[k].dropna()
        s = s[(s.index >= f"{ano - 1}-08-01") & (s.index <= f"{ano}-01-20")]
        px = ptax.reindex(s.index)
        s = (s / px).dropna()
        if len(s) > 20:
            sazonal[str(ano)] = [[d.strftime("%m-%d") if d.year == ano - 1 else "13-" + d.strftime("%d"), r(v)] for d, v in s.items()]

    # prêmio implícito da B3 sobre Chicago
    zc = zc_chicago()
    if zc is not None:
        base["zc_usd_sc"] = zc.reindex(base.index).ffill(limit=3) * SACA_BU
        base["premio"] = base["b3_usd"] - base["zc_usd_sc"]

    # curva do dólar e carrego
    dol = [x for x in cam.get("dol", []) if x.get("preco")]
    dol.sort(key=lambda x: x["vencimento"])
    ult_d = base.index[-1]
    p_ult = float(base["ptax"].iloc[-1])
    carrego = None
    if len(dol) >= 2:
        a, b = dol[0], dol[1]
        dias = (date.fromisoformat(b["vencimento"]) - date.fromisoformat(a["vencimento"])).days
        carrego = {"de": a["contrato"], "para": b["contrato"], "pct_mes": r((b["preco"] / a["preco"] - 1) * 100 * 30 / dias, 2)}

    # contratos de milho em aberto (último ajuste)
    ultimo = C.iloc[-1]
    abertos = [{"contrato": k, "preco": r(v)} for k, v in ultimo.items() if pd.notna(v)]
    ordem = "FGHJKMNQUVXZ"
    abertos.sort(key=lambda x: (int(x["contrato"][-2:]), ordem.index(x["contrato"][3])))

    def pct(s, v):
        s = s.dropna()
        return r((s < v).mean() * 100, 0) if len(s) else None

    usd = base["b3_usd"]
    hoje = base.iloc[-1]
    um_ano = usd[usd.index >= ult_d - pd.Timedelta(days=365)]
    out = {
        "atualizado_em": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"),
        "referencia": ult_d.strftime("%Y-%m-%d"),
        "fontes": "B3 (ajustes do milho CCM e dólar futuro), Banco Central (PTAX) e CME via TradingView (milho CBOT)",
        "constantes": {"sacas_ccm": CCM_SACAS, "usd_wdo": WDO_USD, "bu_por_saca": round(SACA_BU, 5), "janela": JANELA, "limiar_z": LIMIAR_Z},
        "hoje": {
            "contrato": hoje["ref"], "b3": r(hoje["b3"]), "ptax": r(hoje["ptax"], 4), "b3_usd": r(hoje["b3_usd"]),
            "gap": r(hoje["gap"] * 100, 1), "gap63": r(hoje["gap63"] * 100, 1), "z": r(hoje["z"]),
            "pct_gap": pct(base["gap"], hoje["gap"]),
            "pct_usd_tudo": pct(usd, hoje["b3_usd"]), "pct_usd_1a": pct(um_ano, hoje["b3_usd"]),
            "min_usd_1a": r(um_ano.min()), "max_usd_1a": r(um_ano.max()),
            "corr26": r(corr26.dropna().iloc[-1]) if corr26.notna().any() else None,
            "beta26": r(beta26.dropna().iloc[-1]) if beta26.notna().any() else None,
            "beta52": r(beta52), "corr_total": r(corr_tot),
            "premio": r(hoje.get("premio")) if "premio" in base else None,
            "pct_premio": pct(base["premio"], hoje["premio"]) if "premio" in base and pd.notna(hoje.get("premio")) else None,
            "zc": r(hoje["zc_usd_sc"] / SACA_BU) if "zc_usd_sc" in base and pd.notna(hoje.get("zc_usd_sc")) else None,
        },
        "serie": {
            "datas": [d.strftime("%Y-%m-%d") for d in base.index],
            "b3": [r(x) for x in base["b3"]], "ptax": [r(x, 4) for x in base["ptax"]],
            "b3_usd": [r(x) for x in base["b3_usd"]], "contrato": list(base["ref"]),
            "gap": [r(x * 100, 1) for x in base["gap"]], "gap63": [r(x * 100, 1) for x in base["gap63"]],
            "premio": [r(x) for x in base["premio"]] if "premio" in base else None,
        },
        "correlacao": {"datas": [d.strftime("%Y-%m-%d") for d in corr26.dropna().index],
                       "corr": [r(x) for x in corr26.dropna()], "beta": [r(x) for x in beta26.reindex(corr26.dropna().index)]},
        "sazonal": sazonal,
        "sinal": {"episodios": eps, "n21": len(f21), "acerto21": r(np.mean([x > 0 for x in f21]) * 100, 0) if f21 else None,
                  "media21": r(np.mean(f21), 1) if f21 else None, "mediana21": r(np.median(f21), 1) if f21 else None,
                  "n42": len(f42), "acerto42": r(np.mean([x > 0 for x in f42]) * 100, 0) if f42 else None, "media42": r(np.mean(f42), 1) if f42 else None},
        "dolar_futuro": dol[:4], "carrego": carrego, "milho_abertos": abertos[:6],
    }
    (RAIZ / "dados/milho_dolar.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("ok", out["referencia"], out["hoje"], out["sinal"]["n21"], out["sinal"]["acerto21"], out["sinal"]["media21"])


if __name__ == "__main__":
    main()
