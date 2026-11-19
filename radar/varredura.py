"""Radar AgroBasis: varredura automática de todos os dados dos painéis.

Sem IA e sem regra escrita caso a caso. Para cada série:
  - percentil nos últimos 5 anos (e na mesma época do ano, nas séries com sazonalidade),
  - variação em 1 e 4 semanas, máximas e mínimas de 52 semanas.
Para cada par de preços (todas as combinações):
  - a razão entre os dois, seu percentil em 5 anos e o que aconteceu nas vezes
    anteriores em que ela esteve tão esticada (teste histórico de reversão),
  - a correlação dos últimos 6 meses contra a de 3 anos (quebra de correlação).

Saída: dados/radar/sinais.json (lido pela página Radar e pela leitura diária).
"""
from __future__ import annotations

import itertools
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDA = DADOS / "radar" / "sinais.json"
HIST = DADOS / "radar" / "placar.json"
HORIZ_PLACAR = {"4s": 28, "13s": 91}  # dias corridos
BRT = ZoneInfo("America/Sao_Paulo")

ANOS_REF = 5            # janela do percentil
EXTREMO = 10            # percentil <= 10 ou >= 90 vira destaque (séries)
EXTREMO_PAR = 15        # nas relações entre preços, que são poucas, o corte é 15/85
HORIZ_SEM = 13          # horizonte do teste histórico de reversão (semanas)
CORR_CURTA, CORR_LONGA = 26, 156  # semanas
QUEBRA_CORR = 0.6       # diferença mínima entre as correlações para apontar quebra


# --------------------------------------------------------------------------- leitura
def _j(rel: str):
    p = DADOS / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _serie(datas, valores) -> pd.Series:
    s = pd.Series(valores, index=pd.to_datetime(datas), dtype="float64")
    return s[~s.index.duplicated(keep="last")].dropna().sort_index()


SERIES: dict[str, dict] = {}   # id -> {"s": Series, nome, unidade, painel, tipo, sazonal, casas}


def add(sid, s, nome, unidade, painel, tipo="preco", sazonal=False, casas=2):
    if s is None or len(s) < 60:
        return
    SERIES[sid] = dict(s=s, nome=nome, unidade=unidade, painel=painel, tipo=tipo, sazonal=sazonal, casas=casas)


def carregar():
    # Chicago (semanal, desde 2010)
    p = _j("cot/precos.json") or {}
    cbot = {"soja": ("Soja em Chicago", "US$/bu"), "milho": ("Milho em Chicago", "US$/bu"),
            "trigo": ("Trigo em Chicago", "US$/bu"), "farelo": ("Farelo em Chicago", "US$/t curta"),
            "oleo": ("Óleo de soja em Chicago", "US$/lb")}
    for k, (nome, un) in cbot.items():
        if k in p:
            add(f"cbot_{k}", _serie(list(p[k]), list(p[k].values())), nome, un, "/dashboards/posicao-fundos-cftc/",
                casas=3 if k == "oleo" else 2)

    # Fundos (gestores de recursos, posição líquida em contratos)
    for k, nome in [("soja", "soja"), ("milho", "milho"), ("trigo", "trigo"), ("farelo", "farelo"), ("oleo", "óleo de soja")]:
        d = _j(f"cot/{k}.json")
        if d:
            mm = d["cat"]["mm"]
            liq = [(a - b) if a is not None and b is not None else None for a, b in zip(mm["l"], mm["s"])]
            add(f"fundos_{k}", _serie(d["datas"], liq), f"Posição dos fundos em {nome}", "contratos",
                "/dashboards/posicao-fundos-cftc/", tipo="posicao", casas=0)

    # Câmbio
    c = _j("cambio.json")
    if c and c.get("ptax"):
        add("dolar", _serie(c["ptax"]["datas"], c["ptax"]["valores"]), "Dólar (PTAX)", "R$/US$",
            "/dashboards/curva-do-dolar/", casas=4)

    # Milho B3 e milho B3 em dólar
    md = (_j("milho_dolar.json") or {}).get("serie")
    if md:
        add("milho_b3", _serie(md["datas"], md["b3"]), "Milho B3 (1º vencimento)", "R$/sc", "/dashboards/milho-b3-x-dolar/")
        add("milho_b3_usd", _serie(md["datas"], md["b3_usd"]), "Milho B3 em dólar", "US$/sc", "/dashboards/milho-b3-x-dolar/")
        add("premio_b3_cbot", _serie(md["datas"], md["premio"]), "Prêmio do milho B3 sobre Chicago", "US$/sc",
            "/dashboards/milho-b3-x-dolar/", tipo="spread")

    # Carrego da curva do milho B3: 2º menos 1º vencimento em aberto
    h = _j("ccm_historico.json")
    if h:
        datas, C = h["datas"], h["contratos"]
        meses = "FGHJKMNQUVXZ"
        venc = sorted(C, key=lambda t: (int(t[-2:]), meses.index(t[3])))
        car = []
        for i, d in enumerate(datas):
            vivos = [t for t in venc if C[t][i] is not None]
            car.append(C[vivos[1]][i] - C[vivos[0]][i] if len(vivos) >= 2 else None)
        add("carrego_ccm", _serie(datas, car), "Carrego do milho B3 (2º menos 1º vencimento)", "R$/sc",
            "/dashboards/spread-milho-b3/", tipo="spread", sazonal=True)

    # Basis (planilha) e basis de balcão, por praça
    for arq, prod, un, painel, rot in [
        ("basis/soja.json", "soja", "c/bu", "/dashboards/basis-soja-brasil/", "Basis da soja"),
        ("basis/milho.json", "milho", "R$/sc", "/dashboards/basis-milho-brasil/", "Basis do milho"),
        ("basis/balcao_soja.json", "soja", "c/bu", "/dashboards/basis-balcao-soja/", "Basis de balcão da soja"),
        ("basis/balcao_milho.json", "milho", "R$/sc", "/dashboards/basis-balcao-milho/", "Basis de balcão do milho"),
    ]:
        d = _j(arq)
        if not d:
            continue
        tag = "balcao_" if "balcao" in arq else ""
        for praca, v in d["pracas"].items():
            s = _serie(d["datas"], v["basis"])
            sid = f"basis_{tag}{prod}_{praca}".replace(" ", "_").lower()
            add(sid, s, f"{rot} em {praca}", un, painel, tipo="basis", sazonal=True, casas=1)

    # Séries derivadas que valem como preço próprio
    if all(k in SERIES for k in ("cbot_soja", "cbot_farelo", "cbot_oleo")):
        df = pd.concat([SERIES[k]["s"] for k in ("cbot_soja", "cbot_farelo", "cbot_oleo")], axis=1).dropna()
        df.columns = ["s", "f", "o"]
        oleo, farelo = df["o"] * 100 * 0.11, df["f"] * 0.022
        add("margem_esmagamento", oleo + farelo - df["s"], "Margem de esmagamento em Chicago", "US$/bu",
            "/dashboards/posicao-fundos-cftc/", tipo="spread")
        add("peso_oleo", 100 * oleo / (oleo + farelo), "Peso do óleo no valor do esmagamento", "%",
            "/dashboards/posicao-fundos-cftc/", tipo="spread", casas=1)
    if "cbot_soja" in SERIES and "dolar" in SERIES:
        sj = SERIES["cbot_soja"]["s"]
        dl = SERIES["dolar"]["s"].reindex(sj.index, method="ffill")
        add("soja_reais", (sj * 2.20462 * dl).dropna(), "Soja Chicago em reais", "R$/sc", "/dashboards/termometro-de-venda/")


# --------------------------------------------------------------------------- estatística
def semanal(s: pd.Series) -> pd.Series:
    return s.resample("W-FRI").last().dropna()


def percentil(v, ref) -> float:
    ref = np.asarray(ref, dtype=float)
    ref = ref[~np.isnan(ref)]
    return float(100 * (ref < v).mean()) if len(ref) else math.nan


def stats_serie(sid, m) -> dict | None:
    s = m["s"]
    fim = s.index[-1]
    ult = float(s.iloc[-1])
    ref = s[s.index > fim - pd.DateOffset(years=ANOS_REF)]
    if len(ref) < 40:
        return None
    w = semanal(s)
    o = dict(id=sid, nome=m["nome"], unidade=m["unidade"], painel=m["painel"], tipo=m["tipo"], casas=m["casas"],
             data=fim.strftime("%Y-%m-%d"), valor=round(ult, 4),
             pct_5a=round(percentil(ult, ref.values), 1))
    if len(w) >= 6:
        o["var_1s"] = round(ult - float(w.iloc[-2]), 4)
        o["var_4s"] = round(ult - float(w.iloc[-5]), 4)
        d4 = (w - w.shift(4)).dropna()
        d4h = d4[d4.index > fim - pd.DateOffset(years=10)]
        if len(d4h) >= 100:
            o["pct_var_4s"] = round(percentil(o["var_4s"], d4h.values[:-1]), 1)
            maior = d4h.iloc[:-6]  # fora as semanas que se sobrepõem ao movimento atual
            ref_dir = maior[maior <= o["var_4s"]] if o["var_4s"] < 0 else maior[maior >= o["var_4s"]]
            o["var_4s_recorde_desde"] = (ref_dir.index[-1].strftime("%m/%Y") if len(ref_dir)
                                         else ("pelo menos 10 anos" if d4.index[0] < d4h.index[0]
                                               else f"o início da série ({d4h.index[0].strftime('%m/%Y')})"))
    a52 = s[s.index > fim - pd.DateOffset(weeks=52)]
    o["max_52s"] = bool(ult >= a52.max())
    o["min_52s"] = bool(ult <= a52.min())
    if m["sazonal"]:
        # mesma época do ano (±21 dias) nos anos anteriores
        doy = fim.dayofyear
        hist = ref[ref.index.year < fim.year]
        dd = np.abs(hist.index.dayofyear - doy)
        epoca = hist[np.minimum(dd, 365 - dd) <= 21]
        if len(epoca) >= 8:
            o["pct_epoca"] = round(percentil(ult, epoca.values), 1)
            o["media_epoca"] = round(float(epoca.mean()), 4)
    return o


def reversao(r: pd.Series, alto: bool, nivel: float) -> dict | None:
    """Teste histórico: episódios em que a razão (semanal, log) passou do percentil atual
    (percentil móvel de 5 anos) e o que aconteceu HORIZ_SEM semanas depois."""
    if len(r) < 260 + HORIZ_SEM:
        return None
    vals = r.values
    eps, fora = [], True
    for i in range(260, len(r) - HORIZ_SEM):
        p = percentil(vals[i], vals[i - 260:i])
        cond = p >= nivel if alto else p <= nivel
        if cond and fora:
            fut = vals[i + HORIZ_SEM] - vals[i]
            eps.append(fut)
            fora = False
        elif not cond:
            fora = True
    if len(eps) < 4:
        return None
    eps = np.array(eps)
    voltou = (eps < 0) if alto else (eps > 0)
    return dict(n=int(len(eps)), acerto=round(100 * voltou.mean()), mov_medio_pct=round(100 * (math.exp(eps.mean()) - 1), 1))


# Razões com sentido econômico (mesma unidade ou relação de troca clássica)
PARES_RAZAO = [
    ("cbot_soja", "cbot_milho", "Relação soja/milho em Chicago"),
    ("cbot_soja", "cbot_trigo", "Relação soja/trigo em Chicago"),
    ("cbot_trigo", "cbot_milho", "Relação trigo/milho em Chicago"),
    ("soja_reais", "milho_b3", "Relação soja em reais/milho B3"),
]
# Pares só para acompanhar a correlação (unidades diferentes)
PARES_CORR = [
    ("dolar", "cbot_soja", "dólar e soja em Chicago"),
    ("dolar", "milho_b3", "dólar e milho B3"),
    ("cbot_milho", "milho_b3", "milho em Chicago e milho B3"),
    ("cbot_soja", "cbot_milho", "soja e milho em Chicago"),
    ("cbot_oleo", "cbot_soja", "óleo e soja em Chicago"),
]


def _par_df(a, b):
    df = pd.concat([semanal(SERIES[a]["s"]), semanal(SERIES[b]["s"])], axis=1, keys=[a, b], sort=True).dropna()
    return df[(df > 0).all(axis=1)]


def stats_pares() -> list[dict]:
    out = []
    for a, b, nome in PARES_RAZAO:
        if a not in SERIES or b not in SERIES:
            continue
        df = _par_df(a, b)
        if len(df) < 120:
            continue
        r = np.log(df[a] / df[b])
        fim = r.index[-1]
        ref = r[r.index > fim - pd.DateOffset(years=ANOS_REF)]
        pct = percentil(r.iloc[-1], ref.values)
        o = dict(tipo="razao", a=a, b=b, nome=nome, data=fim.strftime("%Y-%m-%d"),
                 valor=round(float(math.exp(r.iloc[-1])), 4), media_5a=round(float(np.exp(ref).mean()), 4),
                 pct_5a=round(pct, 1), desde=r.index[0].strftime("%Y"))
        if pct >= 100 - EXTREMO_PAR or pct <= EXTREMO_PAR:
            o["teste"] = reversao(r, pct >= 50, pct)
        out.append(o)
    for a, b, nome in PARES_CORR:
        if a not in SERIES or b not in SERIES:
            continue
        ret = np.log(_par_df(a, b)).diff().dropna()
        if len(ret) < CORR_LONGA:
            continue
        c_curta = float(ret[a].iloc[-CORR_CURTA:].corr(ret[b].iloc[-CORR_CURTA:]))
        c_longa = float(ret[a].iloc[-CORR_LONGA:].corr(ret[b].iloc[-CORR_LONGA:]))
        out.append(dict(tipo="correlacao", a=a, b=b, nome=nome, data=ret.index[-1].strftime("%Y-%m-%d"),
                        corr_6m=round(c_curta, 2), corr_3a=round(c_longa, 2),
                        quebra_corr=bool(abs(c_curta - c_longa) >= QUEBRA_CORR)))
    return out


# --------------------------------------------------------------------------- texto
def fmt(v, casas=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def frase_serie(o) -> tuple[float, str]:
    """Intensidade (0 a 50) e frase pronta."""
    casas = o["casas"]
    base = f"{o['nome']}: {fmt(o['valor'], casas)} {o['unidade']}"
    partes, intens = [], 0.0
    pe = o.get("pct_epoca")
    if pe is not None and (pe <= EXTREMO or pe >= 100 - EXTREMO):
        partes.append(f"percentil {fmt(pe, 0)} para esta época do ano nos últimos 5 anos (média da época {fmt(o['media_epoca'], casas)})")
        intens = max(intens, abs(pe - 50))
    p5 = o["pct_5a"]
    if p5 <= EXTREMO or p5 >= 100 - EXTREMO:
        partes.append(f"percentil {fmt(p5, 0)} em 5 anos")
        intens = max(intens, abs(p5 - 50))
    pv = o.get("pct_var_4s")
    if pv is not None and (pv <= 2 or pv >= 98) and o["tipo"] in ("preco", "posicao", "spread"):
        sinal = "+" if o["var_4s"] > 0 else ""
        partes.append(f"variação de {sinal}{fmt(o['var_4s'], casas)} em 4 semanas, " + ("o maior movimento em " + o["var_4s_recorde_desde"] if o["var_4s_recorde_desde"].startswith("pelo") else "movimento tão forte não acontecia desde " + o["var_4s_recorde_desde"]) + "")
        intens = max(intens, 45)
    if o["max_52s"]:
        partes.append("máxima de 52 semanas")
        intens = max(intens, 42)
    if o["min_52s"]:
        partes.append("mínima de 52 semanas")
        intens = max(intens, 42)
    if not partes:
        return 0.0, ""
    return intens, base + ", " + "; ".join(partes) + "."


def frase_par(o) -> tuple[float, str]:
    if o["tipo"] == "correlacao":
        if not o["quebra_corr"]:
            return 0.0, ""
        return 35.0, (f"A correlação entre {o['nome']} mudou: {fmt(o['corr_6m'], 2)} nos últimos 6 meses, "
                      f"contra {fmt(o['corr_3a'], 2)} em 3 anos.")
    p = o["pct_5a"]
    if EXTREMO_PAR < p < 100 - EXTREMO_PAR:
        return 0.0, ""
    lado = "alta" if p >= 50 else "baixa"
    t = (f"{o['nome']} em {fmt(o['valor'], 2)}, percentil {fmt(p, 0)} em 5 anos (média {fmt(o['media_5a'], 2)}), "
         f"esticada para {lado}.")
    te, intens = o.get("teste"), abs(p - 50)
    if te and te["n"] >= 6:
        t += (f" Nas {te['n']} vezes anteriores desde {o['desde']} em que chegou a esse extremo, voltou em "
              f"{te['acerto']}% dos casos nas {HORIZ_SEM} semanas seguintes (movimento médio da relação: {fmt(te['mov_medio_pct'], 1)}%).")
        intens += 5 if te["acerto"] >= 65 else 0
    return intens, t


def agrupar_basis(series) -> list[dict]:
    """Uma linha por painel de basis, com as praças em extremo para a época."""
    grupos = {}
    for o in series:
        if o["tipo"] != "basis":
            continue
        pe = o.get("pct_epoca", o["pct_5a"])
        if EXTREMO < pe < 100 - EXTREMO:
            continue
        grupos.setdefault(o["painel"], []).append((pe, o))
    out = []
    for painel, itens in grupos.items():
        fracos = sorted([x for x in itens if x[0] <= EXTREMO], key=lambda x: x[0])
        fortes = sorted([x for x in itens if x[0] >= 100 - EXTREMO], key=lambda x: -x[0])
        rot = itens[0][1]["nome"].split(" em ")[0]
        for lista, adj in ((fracos, "fraco"), (fortes, "forte")):
            if not lista:
                continue
            un = lista[0][1]["unidade"]
            ex = "; ".join(f"{o['nome'].split(' em ', 1)[1]} {fmt(o['valor'], 1)} (média da época {fmt(o.get('media_epoca'), 1)})"
                           for _, o in lista[:4])
            n = len(lista)
            texto = (f"{rot} {adj} para a época em {n} {'praça' if n == 1 else 'praças'}, em {un}: {ex}"
                     + (f" e mais {n - 4}" if n > 4 else "") + ".")
            intens = max(abs(pe - 50) for pe, _ in lista) + min(n, 6)
            out.append(dict(tipo="basis", id=painel, painel=painel, data=max(o["data"] for _, o in lista),
                            intensidade=round(intens, 1), texto=texto))
    return out


# --------------------------------------------------------------------------- placar
def valor_em(sid: str, data: pd.Timestamp):
    """Primeiro valor disponível a partir de 'data' (série simples ou razão 'a/b')."""
    if "/" in sid:
        a, b = sid.split("/")
        if a not in SERIES or b not in SERIES:
            return None
        df = _par_df(a, b)
        s = df[a] / df[b]
    else:
        if sid not in SERIES:
            return None
        s = SERIES[sid]["s"]
    s = s[s.index >= data]
    return (s.index[0], float(s.iloc[0])) if len(s) else None


def atualizar_placar(series, pares, hoje: str):
    hist = json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else {"sinais": []}
    sinais = hist["sinais"]
    abertos = {}
    for x in sinais:
        abertos[x["id"]] = x  # o mais recente de cada id

    novos = []
    for o in series:
        if o["tipo"] == "posicao":
            continue
        pe = o.get("pct_epoca")
        p = pe if pe is not None else o["pct_5a"]
        if EXTREMO < p < 100 - EXTREMO:
            continue
        alvo = o.get("media_epoca") if pe is not None else None
        if alvo is None:
            s = SERIES[o["id"]]["s"]
            alvo = float(s[s.index > s.index[-1] - pd.DateOffset(years=ANOS_REF)].median())
        novos.append(dict(id=o["id"], nome=o["nome"], unidade=o["unidade"], casas=o["casas"], data=o["data"],
                          valor=o["valor"], alvo=round(alvo, 4), lado="alto" if p >= 50 else "baixo",
                          percentil=p, regra="extremo para a época" if pe is not None else "extremo em 5 anos"))
    for o in pares:
        if o["tipo"] != "razao" or EXTREMO_PAR < o["pct_5a"] < 100 - EXTREMO_PAR:
            continue
        novos.append(dict(id=f"{o['a']}/{o['b']}", nome=o["nome"], unidade="", casas=2, data=o["data"],
                          valor=o["valor"], alvo=o["media_5a"], lado="alto" if o["pct_5a"] >= 50 else "baixo",
                          percentil=o["pct_5a"], regra="relação esticada em 5 anos"))
    for n in novos:
        ant = abertos.get(n["id"])
        # mesmo sinal ainda em curso (menos de 28 dias e mesmo lado): não registra de novo
        if ant and ant["lado"] == n["lado"] and (pd.Timestamp(n["data"]) - pd.Timestamp(ant["data"])).days < 28:
            continue
        n["registrado_em"] = hoje
        n["resultado"] = {}
        sinais.append(n)

    # avaliação
    for x in sinais:
        for h, dias in HORIZ_PLACAR.items():
            if h in x["resultado"]:
                continue
            v = valor_em(x["id"], pd.Timestamp(x["data"]) + pd.Timedelta(days=dias))
            if not v:
                continue
            d, val = v
            mov = val - x["valor"]
            certo = mov < 0 if x["lado"] == "alto" else mov > 0
            gap = x["alvo"] - x["valor"]
            x["resultado"][h] = dict(data=d.strftime("%Y-%m-%d"), valor=round(val, 4), acertou=bool(certo),
                                     fechou_pct=round(100 * mov / gap, 0) if gap else None)

    resumo = {}
    for h in HORIZ_PLACAR:
        av = [x["resultado"][h]["acertou"] for x in sinais if h in x["resultado"]]
        resumo[h] = dict(avaliados=len(av), acertos=int(sum(av)), taxa=round(100 * sum(av) / len(av)) if av else None)
    hist = dict(atualizado_em=hoje, inicio=sinais[0]["registrado_em"] if sinais else hoje,
                total=len(sinais), resumo=resumo, sinais=sinais)
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    return resumo


# --------------------------------------------------------------------------- principal
def main():
    carregar()
    series = [x for x in (stats_serie(k, m) for k, m in SERIES.items()) if x]
    pares = stats_pares()
    destaques = []
    destaques += agrupar_basis(series)
    for o in series:
        if o["tipo"] == "basis":
            continue
        i, t = frase_serie(o)
        if t:
            destaques.append(dict(tipo="serie", id=o["id"], painel=o["painel"], data=o["data"], intensidade=round(i, 1), texto=t))
    for o in pares:
        i, t = frase_par(o)
        if t:
            destaques.append(dict(tipo=o["tipo"], id=f"{o['a']}/{o['b']}", painel=SERIES[o["a"]]["painel"], data=o["data"], intensidade=round(i, 1), texto=t))
    destaques.sort(key=lambda d: -d["intensidade"])
    agora = datetime.now(BRT)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dict(
        gerado_em=agora.strftime("%Y-%m-%d %H:%M"),
        metodo=dict(anos_ref=ANOS_REF, extremo=EXTREMO, horizonte_semanas=HORIZ_SEM,
                    corr_semanas=[CORR_CURTA, CORR_LONGA], quebra_corr=QUEBRA_CORR),
        n_series=len(series), n_pares=len(pares),
        destaques=destaques, series=series, pares=pares,
    ), ensure_ascii=False, indent=1), encoding="utf-8")
    resumo = atualizar_placar(series, pares, agora.strftime("%Y-%m-%d"))
    print("placar:", resumo)
    print(f"radar: {len(series)} séries, {len(pares)} pares, {len(destaques)} destaques")


if __name__ == "__main__":
    main()
