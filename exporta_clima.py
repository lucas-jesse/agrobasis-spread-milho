"""Clima e El Niño nas regiões produtoras, para o dashboard "Clima e El Niño" do AgroBasis.

Fontes:
  - ENSO: NOAA Climate Prediction Center (CPC). RONI trimestral (índice oficial de intensidade desde 2026),
    Niño 3.4 semanal, probabilidades oficiais por trimestre e a discussão mensal (status do alerta).
  - Chuva observada: reanálise ERA5/ERA5T do Copernicus (ECMWF), diária, desde 1980, via Open-Meteo;
    os últimos dias, ainda fora da reanálise, vêm da análise do modelo (Open-Meteo forecast, past_days).
  - Previsão: ensemble do ECMWF IFS (51 membros), 15 dias, via Open-Meteo.
  - Produtividade: série histórica da Conab por UF (SerieHistoricaGraos), para medir o efeito do ENSO.

Normais climatológicas: média 1991-2020 do ERA5 no próprio ponto (mesma base usada pelo CPC para as anomalias).
Saídas: dados/clima/clima.json (painel) e dados/clima/enso_produtividade.json (estudo histórico).
"""
import html as htmlmod
import json
import math
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

PASTA = Path("dados/clima"); CACHE = PASTA / "cache"
CPC = "https://www.cpc.ncep.noaa.gov"
UA = {"User-Agent": "Mozilla/5.0 (AgroBasis; agrobasis.com.br)"}
INICIO_HIST = date(1980, 1, 1)

# polos produtores: (id, município, UF, lat, lon, culturas principais)
PONTOS = [
    ("sorriso", "Sorriso", "MT", -12.55, -55.72, "soja e milho 2ª safra"),
    ("primavera", "Primavera do Leste", "MT", -15.56, -54.30, "soja, milho e algodão"),
    ("rioverde", "Rio Verde", "GO", -17.79, -50.92, "soja e milho 2ª safra"),
    ("unai", "Unaí", "MG", -16.36, -46.90, "soja, milho e feijão"),
    ("lem", "Luís Eduardo Magalhães", "BA", -12.09, -45.80, "soja, milho e algodão"),
    ("balsas", "Balsas", "MA", -7.53, -46.04, "soja e milho"),
    ("urucui", "Uruçuí", "PI", -7.23, -44.55, "soja e milho"),
    ("portonacional", "Porto Nacional", "TO", -10.71, -48.42, "soja e milho"),
    ("dourados", "Dourados", "MS", -22.22, -54.81, "soja e milho 2ª safra"),
    ("londrina", "Londrina", "PR", -23.31, -51.16, "soja, milho e trigo"),
    ("cascavel", "Cascavel", "PR", -24.96, -53.46, "soja, milho e trigo"),
    ("pontagrossa", "Ponta Grossa", "PR", -25.09, -50.16, "soja, milho e trigo"),
    ("chapeco", "Chapecó", "SC", -27.10, -52.62, "milho e soja"),
    ("passofundo", "Passo Fundo", "RS", -28.26, -52.41, "soja, milho e trigo"),
    ("santarosa", "Santa Rosa", "RS", -27.87, -54.48, "soja, milho e trigo"),
    ("cruzalta", "Cruz Alta", "RS", -28.64, -53.61, "soja e trigo"),
]
MES_SAFRA = 9  # a temporada de chuvas da safra de verão é contada a partir de 1º de setembro
DIAS_SAFRA = 243  # 1º/set a 30/abr


def get(url, params=None, n=4, timeout=120):
    for i in range(n):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 429:
                raise requests.HTTPError("429")
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == n - 1:
                raise
            print(f"  nova tentativa ({e})"); time.sleep(10 * (i + 1))


# ---------------------------------------------------------------- ENSO (NOAA CPC)
SEAS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]


def roni():
    linhas = get(f"{CPC}/data/indices/RONI.ascii.txt").text.splitlines()
    out = []
    for l in linhas[1:]:
        p = l.split()
        if len(p) == 3 and p[0] in SEAS:
            out.append({"s": p[0], "ano": int(p[1]), "v": float(p[2])})
    return out


def nino34_semanal():
    out = []
    for l in get(f"{CPC}/data/indices/wksst9120.for").text.splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+", l)
        if not m:
            continue
        d = datetime.strptime(m.group(1).title(), "%d%b%Y").date()
        # colunas fixas: Niño 3.4 SSTA nas posições 45 a 48 (o sinal pode colar no SST)
        try:
            v = float(l[45:49])
        except ValueError:
            continue
        out.append((d, v))
    return out


def probabilidades():
    s = get(f"{CPC}/products/analysis_monitoring/enso/roni/probabilities/").text
    t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)))
    t = re.sub(r"\s+", " ", t)
    i = t.find("Season La Niña Neutral El Niño")
    out = []
    for m in re.finditer(r"\b([A-Z]{3}) [A-Z][a-z]{2} [A-Z][a-z]{2} [A-Z][a-z]{2} (\d{1,3}) (\d{1,3}) (\d{1,3})\b", t[i:i + 2000] if i >= 0 else ""):
        out.append({"s": m.group(1), "ln": int(m.group(2)), "n": int(m.group(3)), "en": int(m.group(4))})
    return out


def discussao():
    s = get(f"{CPC}/products/analysis_monitoring/enso_advisory/ensodisc.shtml").text
    t = re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s)))
    status = re.search(r"ENSO Alert System Status:\s*(.+?)\s+Synopsis:", t)
    sin = re.search(r"Synopsis:\s*(.+?)(?:\s{1,3}Compared to| The Niño indices| \[Fig)", t)
    emit = re.search(r"issued by .*? (\d{1,2} [A-Z][a-z]+ 20\d\d)", t)
    prox = re.search(r"next ENSO Diagnostics? Discussion is scheduled for (\d{1,2} [A-Z][a-z]+ 20\d\d)", t)
    def d(x):
        return datetime.strptime(x.group(1), "%d %B %Y").date().isoformat() if x else None
    return {"status_en": status.group(1).strip() if status else None, "sinopse_en": sin.group(1).strip() if sin else None,
            "emitida": d(emit), "proxima": d(prox)}


STATUS_PT = {"El Niño Advisory": "Alerta de El Niño em vigor", "La Niña Advisory": "Alerta de La Niña em vigor",
             "El Niño Watch": "Vigilância de El Niño", "La Niña Watch": "Vigilância de La Niña",
             "Final El Niño Advisory": "Fim do El Niño", "Final La Niña Advisory": "Fim da La Niña", "Not Active": "Neutro (sem alerta)"}


def fase(v):
    return "en_forte" if v >= 1.5 else "en" if v >= 0.5 else "ln" if v <= -0.5 else "neutro"


# ---------------------------------------------------------------- chuva por ponto
def carregar_cache(pid):
    f = CACHE / f"{pid}.json"
    return json.loads(f.read_text()) if f.exists() else {}


def salvar_cache(pid, dias):
    # um ano por linha: diferenças diárias pequenas no git
    anos = {}
    for d, v in sorted(dias.items()):
        anos.setdefault(d[:4], {})[d] = v
    linhas = ",\n".join(f'"{a}":' + json.dumps(anos[a], separators=(",", ":")) for a in sorted(anos))
    (CACHE / f"{pid}.json").write_text("{\n" + linhas + "\n}\n")


def chuva_ponto(pid, lat, lon):
    cache = carregar_cache(pid)
    dias = {d: v for a in cache.values() for d, v in a.items()} if cache else {}
    hoje = date.today()
    ini = INICIO_HIST if not dias else (hoje - timedelta(days=120))
    r = get("https://archive-api.open-meteo.com/v1/archive", {"latitude": lat, "longitude": lon, "start_date": ini.isoformat(),
            "end_date": (hoje - timedelta(days=1)).isoformat(), "daily": "precipitation_sum", "timezone": "America/Sao_Paulo"}, timeout=240).json()
    for d, v in zip(r["daily"]["time"], r["daily"]["precipitation_sum"]):
        if v is not None:
            dias[d] = round(v, 1)
    # dias recentes ainda sem reanálise: análise do modelo
    f = get("https://api.open-meteo.com/v1/forecast", {"latitude": lat, "longitude": lon, "past_days": 10, "forecast_days": 1,
            "daily": "precipitation_sum", "timezone": "America/Sao_Paulo"}).json()
    for d, v in zip(f["daily"]["time"], f["daily"]["precipitation_sum"]):
        if v is not None and d < hoje.isoformat() and d not in dias:
            dias[d] = round(v, 1)
    salvar_cache(pid, dias)
    return dias


def previsao(lat, lon):
    e = get("https://ensemble-api.open-meteo.com/v1/ensemble", {"latitude": lat, "longitude": lon, "daily": "precipitation_sum",
            "forecast_days": 15, "models": "ecmwf_ifs025", "timezone": "America/Sao_Paulo"}).json()["daily"]
    membros = [k for k in e if k.startswith("precipitation_sum")]
    datas = e["time"]
    mat = [[e[k][i] for k in membros if e[k][i] is not None] for i in range(len(datas))]
    tot = [sum(e[k][i] or 0 for i in range(len(datas))) for k in membros]
    t = get("https://api.open-meteo.com/v1/forecast", {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max",
            "forecast_days": 15, "models": "ecmwf_ifs025", "timezone": "America/Sao_Paulo"}).json()["daily"]
    tmax = t.get("temperature_2m_max_ecmwf_ifs025") or t.get("temperature_2m_max") or []

    def q(xs, p):
        xs = sorted(xs)
        if not xs:
            return None
        k = (len(xs) - 1) * p; a = math.floor(k); b = min(a + 1, len(xs) - 1)
        return xs[a] + (xs[b] - xs[a]) * (k - a)
    return {"d": datas, "media": [round(sum(x) / len(x), 1) if x else None for x in mat],
            "p10": [round(q(x, .1), 1) if x else None for x in mat], "p90": [round(q(x, .9), 1) if x else None for x in mat],
            "tot": {"media": round(sum(tot) / len(tot), 1), "p10": round(q(tot, .1), 1), "p90": round(q(tot, .9), 1),
                    "seco": round(sum(1 for x in tot if x < 25) / len(tot) * 100)},
            "tmax": [None if v is None else round(v, 1) for v in tmax][:len(datas)]}


def doy(d):
    """dia do ano em calendário fixo de 365 dias (29/02 vira 28/02)"""
    if d.month == 2 and d.day == 29:
        d = d - timedelta(days=1)
    return date(2001, d.month, d.day).timetuple().tm_yday - 1


def normal_diaria(dias):
    soma = [0.0] * 365; n = [0] * 365
    for s, v in dias.items():
        d = date.fromisoformat(s)
        if 1991 <= d.year <= 2020:
            k = doy(d); soma[k] += v; n[k] += 1
    bruta = [soma[i] / n[i] if n[i] else 0 for i in range(365)]
    # suaviza com janela de 31 dias (circular): a normal de um dia isolado é ruidosa
    return [sum(bruta[(i + j) % 365] for j in range(-15, 16)) / 31 for i in range(365)]


def acumulado(dias, ini, fim):
    out = 0.0; d = ini; faltas = 0
    while d <= fim:
        v = dias.get(d.isoformat())
        if v is None:
            faltas += 1
        else:
            out += v
        d += timedelta(days=1)
    return out, faltas


def normal_periodo(norm, ini, fim):
    out = 0.0; d = ini
    while d <= fim:
        out += norm[doy(d)]; d += timedelta(days=1)
    return out


def curva_safra(dias, ano_ini, n=DIAS_SAFRA):
    """chuva acumulada dia a dia desde 1º/set do ano_ini"""
    out = []; acc = 0.0; d = date(ano_ini, MES_SAFRA, 1)
    for _ in range(n):
        v = dias.get(d.isoformat())
        if v is None:
            break
        acc += v; out.append(round(acc, 1)); d += timedelta(days=1)
    return out


def safra_de(d):
    return d.year if d.month >= MES_SAFRA else d.year - 1


def analisar_ponto(p, dias, norm, fases):
    pid, nome, uf, lat, lon, cult = p
    ultimo = date.fromisoformat(max(dias))
    acc = {}
    for k in (30, 60, 90):
        ini = ultimo - timedelta(days=k - 1)
        obs, _ = acumulado(dias, ini, ultimo)
        acc[f"d{k}"] = [round(obs), round(normal_periodo(norm, ini, ultimo))]
    s0 = safra_de(ultimo); ini = date(s0, MES_SAFRA, 1)
    obs, _ = acumulado(dias, ini, ultimo)
    ant_fim = date(ultimo.year - 1, ultimo.month, min(ultimo.day, 28))
    ant, _ = acumulado(dias, date(s0 - 1, MES_SAFRA, 1), ant_fim)
    acc["safra"] = [round(obs), round(normal_periodo(norm, ini, ultimo)), round(ant)]
    # curvas: normal, safra atual, safra anterior e médias dos anos por fase do ENSO
    normal = []; a = 0.0; d = ini
    for _ in range(DIAS_SAFRA):
        a += norm[doy(d)]; normal.append(round(a, 1)); d += timedelta(days=1)
    comp = {}
    for f in ("en_forte", "en", "ln"):
        cs = [curva_safra(dias, y) for y, fz in fases.items() if fz == f and y < s0]
        cs = [c for c in cs if len(c) == DIAS_SAFRA]
        if cs:
            comp[f] = {"anos": [y for y, fz in fases.items() if fz == f and y < s0 and len(curva_safra(dias, y)) == DIAS_SAFRA],
                       "curva": [round(sum(c[i] for c in cs) / len(cs), 1) for i in range(DIAS_SAFRA)]}
    # anomalia mensal (set a abr) por fase: % da normal 1991-2020
    meses = [9, 10, 11, 12, 1, 2, 3, 4]
    norm_mes = {m: sum(norm[doy(date(2001, m, 1)) + i] for i in range([30, 31, 30, 31, 31, 28, 31, 30][meses.index(m)])) for m in meses}
    enso_mes = {}
    for f in ("en_forte", "en", "ln"):
        anos = [y for y, fz in fases.items() if fz == f and y < s0]
        linha = []
        for m in meses:
            vals = []
            for y in anos:
                yy = y if m >= MES_SAFRA else y + 1
                tot = sum(v for k, v in dias.items() if k.startswith(f"{yy}-{m:02d}-"))
                if any(k.startswith(f"{yy}-{m:02d}-") for k in dias):
                    vals.append(tot)
            linha.append(round((sum(vals) / len(vals) / norm_mes[m] - 1) * 100) if vals and norm_mes[m] > 5 else None)
        enso_mes[f] = linha
    # últimos 13 meses
    mensal = []
    for i in range(12, -1, -1):
        y, m = ultimo.year, ultimo.month - i
        while m <= 0:
            y, m = y - 1, m + 12
        tot = sum(v for k, v in dias.items() if k.startswith(f"{y}-{m:02d}-"))
        dim = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
        fim = min(dim, ultimo.day) if (y, m) == (ultimo.year, ultimo.month) else dim
        nm = normal_periodo(norm, date(y, m, 1), date(y, m, fim))
        mensal.append({"m": f"{y}-{m:02d}", "obs": round(tot), "norm": round(nm), "parcial": (y, m) == (ultimo.year, ultimo.month)})
    return {"id": pid, "nome": nome, "uf": uf, "lat": lat, "lon": lon, "culturas": cult, "ultimo": ultimo.isoformat(),
            "acc": acc, "safra_ini": ini.isoformat(),
            "curva": {"atual": curva_safra(dias, s0), "anterior": curva_safra(dias, s0 - 1), "normal": normal, "fases": comp},
            "enso_mes": enso_mes, "mensal": mensal}


# ---------------------------------------------------------------- produtividade x ENSO (Conab)
def produtividade(rn):
    import exporta_conab as ec
    serie = ec.ler_txt(ec.baixar(f"{ec.PORTAL}/SerieHistoricaGraos.txt"))
    djf = {r["ano"]: r["v"] for r in rn if r["s"] == "DJF"}
    aso = {r["ano"]: r["v"] for r in rn if r["s"] == "ASO"}
    culturas = {"soja": ("SOJA", None, "Soja"), "milho1": ("MILHO", "1ª SAFRA", "Milho 1ª safra"),
                "milho2": ("MILHO", "2ª SAFRA", "Milho 2ª safra"), "trigo": ("TRIGO", None, "Trigo")}
    UFS = ["MT", "PR", "RS", "GO", "MS", "MG", "BA", "SP", "SC", "TO", "MA", "PI"]
    out = {"metodo": "Desvio da produtividade em relação à tendência quadrática 1990/91 em diante, por UF; fase do ENSO pelo RONI de dezembro a fevereiro da safra (trigo: agosto a outubro do ano da colheita).", "culturas": {}}
    for slug, (prod, filtro, nome) in culturas.items():
        acc = ec.agrega(serie, prod, filtro, "ano_agricola")
        res = {"nome": nome, "ufs": {}}
        for uf in ["BR"] + UFS:
            pts = []
            anos = sorted({k[0] for k in acc}, key=lambda s: int(s[:4]))
            for a in anos:
                y = int(a[:4])
                if y < 1990:
                    continue
                if uf == "BR":
                    ar = sum(v[0] for k, v in acc.items() if k[0] == a); pr = sum(v[1] for k, v in acc.items() if k[0] == a)
                else:
                    ar, pr = acc.get((a, uf), [0, 0])
                if ar < 20:  # menos de 20 mil ha: produtividade ruidosa demais
                    continue
                ind = (aso.get(y + 1) if slug == "trigo" else djf.get(y + 1))
                if ind is None:
                    continue
                pts.append((a, y, pr / ar * 1000, ind))
            if len(pts) < 15:
                continue
            # tendência quadrática por mínimos quadrados
            xs = [p[1] - 2000 for p in pts]; ys = [p[2] for p in pts]
            n = len(xs); sx = [sum(x ** k for x in xs) for k in range(5)]; sy = [sum(y * x ** k for x, y in zip(xs, ys)) for k in range(3)]
            A = [[sx[i + j] for j in range(3)] + [sy[i]] for i in range(3)]
            for i in range(3):
                piv = A[i][i]
                A[i] = [v / piv for v in A[i]]
                for j in range(3):
                    if j != i:
                        f = A[j][i]; A[j] = [vj - f * vi for vj, vi in zip(A[j], A[i])]
            c = [A[i][3] for i in range(3)]
            lst = []
            for (a, y, pr, ind), x in zip(pts, xs):
                tend = c[0] + c[1] * x + c[2] * x * x
                lst.append({"safra": a, "prod": round(pr), "tend": round(tend), "desvio": round((pr / tend - 1) * 100, 1), "roni": ind, "fase": fase(ind)})
            med = {}
            for f in ("en_forte", "en", "neutro", "ln"):
                v = [x["desvio"] for x in lst if x["fase"] == f]
                med[f] = {"media": round(sum(v) / len(v), 1) if v else None, "n": len(v),
                          "pior": min(v) if v else None, "melhor": max(v) if v else None}
            res["ufs"][uf] = {"fases": med, "safras": lst}
        out["culturas"][slug] = res
    return out


def main():
    PASTA.mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
    rn = roni(); sem = nino34_semanal(); prob = probabilidades(); disc = discussao()
    djf = {r["ano"]: r["v"] for r in rn if r["s"] == "DJF"}
    fases = {y - 1: fase(v) for y, v in djf.items()}  # safra que começa em set/(y-1) tem o DJF de y
    # Niño 3.4 semanal: últimos 2 anos e os grandes El Niños para comparação, alinhados pela semana do ano
    ult = sem[-1][0]
    comp = {}
    for ano in (1997, 2015, 2023, ult.year):
        comp[str(ano)] = [[(d - date(ano, 1, 1)).days, v] for d, v in sem if date(ano, 1, 1) <= d < date(ano + 1, 7, 1)]
    enso = {"status_en": disc["status_en"], "status": STATUS_PT.get(disc["status_en"] or "", disc["status_en"]),
            "sinopse_en": disc["sinopse_en"], "emitida": disc["emitida"], "proxima": disc["proxima"],
            "roni": [[r["s"], r["ano"], r["v"]] for r in rn], "prob": prob,
            "nino34": {"ultimo": [ult.isoformat(), sem[-1][1]], "comparacao": comp,
                       "recente": [[d.isoformat(), v] for d, v in sem[-104:]]}}
    pontos = []
    for p in PONTOS:
        print(p[1], p[2])
        dias = chuva_ponto(p[0], p[3], p[4]); time.sleep(1.5)
        norm = normal_diaria(dias)
        a = analisar_ponto(p, dias, norm, fases)
        a["prev"] = previsao(p[3], p[4]); time.sleep(1.5)
        ini = date.fromisoformat(a["prev"]["d"][0]); fim = date.fromisoformat(a["prev"]["d"][-1])
        a["prev"]["tot"]["normal"] = round(normal_periodo(norm, ini, fim))
        a["prev"]["normal_dia"] = [round(norm[doy(date.fromisoformat(d))], 1) for d in a["prev"]["d"]]
        pontos.append(a)
        print(f"  safra {a['acc']['safra']} | 30d {a['acc']['d30']} | prev 15d {a['prev']['tot']}")
    saida = {"atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M"), "enso": enso, "pontos": pontos,
             "fases_safra": {str(k): v for k, v in fases.items() if k >= 1980}}
    (PASTA / "clima.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    # o estudo de produtividade muda pouco: refeito uma vez por semana (segunda) ou se não existir
    est = PASTA / "enso_produtividade.json"
    if not est.exists() or date.today().weekday() == 0:
        est.write_text(json.dumps(produtividade(rn), ensure_ascii=False, separators=(",", ":")))
        print("estudo de produtividade atualizado")


if __name__ == "__main__":
    main()
