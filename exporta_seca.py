"""Seca nos Estados Unidos e no Brasil, para o painel "Clima e El Niño" do AgroBasis.

EUA: U.S. Drought Monitor (National Drought Mitigation Center, USDA e NOAA), mapa semanal publicado às quintas.
     Percentual da área de cada estado em cada categoria (estatística cumulativa: D1 = área em D1 ou pior),
     52 semanas. A área de milho e de soja em seca é a média dos estados ponderada pela produção de cada estado
     na última safra (USDA NASS Quick Stats, chave no secret NASS_API_KEY; sem chave, usa pesos de reserva).
Brasil: mapa mensal oficial do Monitor de Secas (ANA), copiado para o repositório para exibição no painel.
Saídas: dados/clima/seca.json e dados/clima/seca_brasil.jpg.
"""
import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

PASTA = Path("dados/clima")
UA = {"User-Agent": "Mozilla/5.0 (AgroBasis; agrobasis.com.br)", "Accept": "application/json"}
USDM = "https://usdmdataservices.unl.edu/api"
NASS = "https://quickstats.nass.usda.gov/api/api_GET/"
ANA_S3 = "https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/uploads/mapas/"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]

# principais estados produtores de milho e soja (mais de 85% da produção dos EUA)
ESTADOS = {"IA": "Iowa", "IL": "Illinois", "NE": "Nebraska", "MN": "Minnesota", "IN": "Indiana",
           "SD": "Dakota do Sul", "OH": "Ohio", "KS": "Kansas", "ND": "Dakota do Norte", "WI": "Wisconsin",
           "MO": "Missouri", "MI": "Michigan", "AR": "Arkansas", "KY": "Kentucky"}
FIPS = {"IA": "19", "IL": "17", "NE": "31", "MN": "27", "IN": "18", "SD": "46", "OH": "39", "KS": "20",
        "ND": "38", "WI": "55", "MO": "29", "MI": "26", "AR": "05", "KY": "21"}
# pesos de reserva: produção de 2025 em milhões de bushels (USDA NASS), usados se a API não responder
RESERVA = {"milho": {"IA": 2761, "IL": 2343, "NE": 2016, "MN": 1696, "IN": 1069, "SD": 820, "OH": 580,
                     "KS": 935, "ND": 709, "WI": 560, "MO": 673, "MI": 352, "AR": 144, "KY": 237},
           "soja": {"IA": 596, "IL": 639, "NE": 314, "MN": 371, "IN": 323, "SD": 230, "OH": 259,
                    "KS": 196, "ND": 224, "WI": 110, "MO": 277, "MI": 100, "AR": 141, "KY": 75}}


def get(url, params=None, n=4, timeout=90, headers=UA):
    for i in range(n):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == n - 1:
                raise
            print(f"  nova tentativa ({e})"); time.sleep(8 * (i + 1))


def usdm(area, aoi, ini, fim):
    r = get(f"{USDM}/{area}/GetDroughtSeverityStatisticsByAreaPercent",
            {"aoi": aoi, "startdate": f"{ini.month}/{ini.day}/{ini.year}", "enddate": f"{fim.month}/{fim.day}/{fim.year}",
             "statisticsType": "1"})
    linhas = r.json()
    out = []
    for x in linhas:
        out.append({"d": x["mapDate"][:10], "d0": float(x["d0"]), "d1": float(x["d1"]), "d2": float(x["d2"]),
                    "d3": float(x["d3"]), "d4": float(x["d4"])})
    return sorted(out, key=lambda x: x["d"])


def pesos():
    """produção por estado na safra mais recente do NASS"""
    chave = os.environ.get("NASS_API_KEY", "").strip()
    out, fonte = {}, {}
    for cult, com in (("milho", "CORN"), ("soja", "SOYBEANS")):
        dados = None
        if chave:
            for ano in (date.today().year, date.today().year - 1):
                try:
                    p = {"key": chave, "commodity_desc": com, "statisticcat_desc": "PRODUCTION", "unit_desc": "BU",
                         "agg_level_desc": "STATE", "year": str(ano), "reference_period_desc": "YEAR",
                         "source_desc": "SURVEY", "format": "JSON"}
                    if com == "CORN":
                        p["util_practice_desc"] = "GRAIN"
                    rows = get(NASS, p, n=2, timeout=120, headers={"User-Agent": UA["User-Agent"]}).json().get("data", [])
                    v = {}
                    for x in rows:
                        uf = x["state_alpha"]
                        if uf in ESTADOS:
                            try:
                                v[uf] = max(v.get(uf, 0), float(x["Value"].replace(",", "")) / 1e6)
                            except ValueError:
                                pass
                    if len(v) >= 10:
                        dados, fonte[cult] = v, f"USDA NASS, produção de {ano}"
                        break
                except Exception as e:
                    print(f"  NASS {com} {ano}: {e}")
        if not dados:
            dados, fonte[cult] = RESERVA[cult], "USDA NASS, produção de 2025 (valores de reserva)"
        out[cult] = {uf: round(v) for uf, v in dados.items()}
    return out, fonte


def mapa_ana():
    """último mapa mensal publicado pelo Monitor de Secas (o site da ANA usa o mesmo endereço de arquivo)"""
    hoje = date.today()
    for k in range(0, 5):
        m = hoje.month - k; a = hoje.year
        while m < 1:
            m += 12; a -= 1
        n = 12 * (a - 2025) + (m - 10) + 136
        url = f"{ANA_S3}{n}_{MESES[m - 1]}{a}.png"
        try:
            r = requests.get(url, headers={"User-Agent": UA["User-Agent"]}, timeout=60)
            if r.ok and r.content[:4] == b"\x89PNG":
                # versão leve para a web: 1000 px de largura, JPEG
                from io import BytesIO
                from PIL import Image
                im = Image.open(BytesIO(r.content)).convert("RGB")
                im = im.resize((1000, round(im.size[1] * 1000 / im.size[0])), Image.LANCZOS)
                im.save(PASTA / "seca_brasil.jpg", "JPEG", quality=86, optimize=True, progressive=True)
                print(f"  mapa da ANA: {MESES[m - 1]} de {a}")
                return {"mes": m, "ano": a, "rotulo": f"{MESES[m - 1]} de {a}", "origem": url}
        except requests.RequestException as e:
            print(f"  {url}: {e}")
    return None


def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    fim = date.today(); ini = fim - timedelta(days=364)
    estados = {}
    for uf in ESTADOS:
        try:
            estados[uf] = usdm("StateStatistics", FIPS[uf], ini, fim)
            print(f"{uf}: {len(estados[uf])} semanas, D1+ {estados[uf][-1]['d1']}%")
        except Exception as e:
            print(f"{uf}: falhou ({e})")
        time.sleep(1)
    conus = usdm("USStatistics", "conus", ini, fim)
    pw, fonte = pesos()
    datas = sorted(set.intersection(*(set(x["d"] for x in s) for s in estados.values())))
    idx = {uf: {x["d"]: x for x in s} for uf, s in estados.items()}

    def ponderado(cult, cat):
        w = {uf: pw[cult].get(uf, 0) for uf in estados}
        tw = sum(w.values())
        return [round(sum(idx[uf][d][cat] * w[uf] for uf in estados) / tw, 1) for d in datas]

    serie = {"d": datas}
    for cult in ("milho", "soja"):
        for cat in ("d0", "d1", "d2"):
            serie[f"{cult}_{cat}"] = ponderado(cult, cat)
    serie["conus_d1"] = [next((x["d1"] for x in conus if x["d"] == d), None) for d in datas]
    tot = {c: sum(pw[c].values()) for c in pw}
    ufs = []
    for uf, nome in ESTADOS.items():
        if uf not in estados:
            continue
        u = estados[uf][-1]; ant = idx[uf].get(datas[-5]) if len(datas) >= 5 else None
        ufs.append({"uf": uf, "nome": nome, "d0": u["d0"], "d1": u["d1"], "d2": u["d2"], "d3": u["d3"], "d4": u["d4"],
                    "d1_4sem": ant["d1"] if ant else None,
                    "part_milho": round(pw["milho"].get(uf, 0) / tot["milho"] * 100, 1),
                    "part_soja": round(pw["soja"].get(uf, 0) / tot["soja"] * 100, 1)})
    ufs.sort(key=lambda x: -x["part_milho"])
    saida = {"atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "eua": {"mapa": datas[-1], "serie": serie, "estados": ufs, "conus": conus[-1],
                     "pesos_fonte": fonte},
             "brasil": mapa_ana()}
    (PASTA / "seca.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    m = saida["eua"]
    print(f"mapa {m['mapa']}: milho em seca {serie['milho_d1'][-1]}%, soja {serie['soja_d1'][-1]}%, CONUS {conus[-1]['d1']}%")


if __name__ == "__main__":
    main()
