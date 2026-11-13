"""Relação de troca grãos x fertilizantes, para o dashboard "Relação de Troca" do AgroBasis.

Fontes oficiais:
  - Fertilizantes: preço médio de importação CIF (US$/t) e volume importado, por NCM, mês a mês.
    Comex Stat (MDIC/SECEX), API https://api-comexstat.mdic.gov.br/general.
  - Grãos: indicadores diários do Cepea/Esalq em R$ e US$ por saca (soja Paranaguá, milho Esalq/B3)
    e por tonelada (trigo Paraná), baixados das séries públicas do Cepea e convertidos em médias mensais.
  - Câmbio: PTAX média mensal de venda (Banco Central, SGS 3698).

Relação de troca = preço CIF do fertilizante (US$/t) ÷ preço do grão (US$/saca de 60 kg) no mesmo mês:
quantas sacas pagam uma tonelada do adubo no porto. Saída: dados/troca/troca.json.
"""
import json
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import requests
from python_calamine import CalamineWorkbook
from io import BytesIO

PASTA = Path("dados/troca")
INICIO = "2010-01"
COMEX = "https://api-comexstat.mdic.gov.br/general"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

FERTS = {  # slug: (nome, nome curto, NCMs somados, nutriente principal)
    "ureia": ("Ureia", "Ureia", ["31021010"], "Nitrogênio, 45% N"),
    "kcl": ("Cloreto de potássio (KCl)", "KCl", ["31042090", "31042010"], "Potássio, 60% K2O"),
    "map": ("Fosfato monoamônico (MAP)", "MAP", ["31054000"], "Fósforo e nitrogênio, 11-52-00"),
    "sam": ("Sulfato de amônio", "Sulfato de amônio", ["31022100"], "Nitrogênio e enxofre, 21% N"),
    "ssp": ("Superfosfato simples (SSP)", "Superfosfato", ["31031900"], "Fósforo, cerca de 18% P2O5"),
}
GRAOS = {  # slug: (nome, praça, url da série Cepea, kg por unidade cotada)
    "soja": ("Soja", "Paranaguá (PR)", "https://www.cepea.org.br/br/indicador/series/soja.aspx?id=92", 60),
    "milho": ("Milho", "Campinas (SP), Esalq/B3", "https://www.cepea.org.br/br/indicador/series/milho.aspx?id=77", 60),
    "trigo": ("Trigo", "Paraná", "https://www.cepea.org.br/br/indicador/series/trigo.aspx?id=178", 1000),
}


def tentar(fn, *a, n=4, **k):
    for i in range(n):
        try:
            return fn(*a, **k)
        except Exception as e:  # rede instável: espera e tenta de novo
            if i == n - 1:
                raise
            print(f"  nova tentativa ({e})"); time.sleep(8 * (i + 1))


def meses(ini, fim):
    a, m = map(int, ini.split("-")); b, n = map(int, fim.split("-"))
    out = []
    while (a, m) <= (b, n):
        out.append(f"{a}-{m:02d}"); m += 1
        if m > 12:
            a, m = a + 1, 1
    return out


# ---------------------------------------------------------------- Comex Stat
def comex(filtro, valores, detalhe, ate):
    corpo = {"flow": "import", "monthDetail": True, "period": {"from": INICIO, "to": ate},
             "filters": [{"filter": filtro, "values": valores}], "details": [detalhe], "metrics": ["metricKG", "metricCIF"]}
    r = requests.post(COMEX, json=corpo, headers=UA, timeout=180)
    r.raise_for_status()
    return r.json()["data"]["list"]


def fertilizantes(ate):
    todos = sorted({n for f in FERTS.values() for n in f[2]})
    linhas = tentar(comex, "ncm", todos, "ncm", ate)
    por = defaultdict(lambda: [0.0, 0.0])  # (ncm, mês) -> [kg, cif]
    for x in linhas:
        k = (x["coNcm"], f'{x["year"]}-{int(x["monthNumber"]):02d}')
        por[k][0] += float(x["metricKG"]); por[k][1] += float(x["metricCIF"])
    saida = {}
    for slug, (nome, curto, ncms, nutr) in FERTS.items():
        kg = defaultdict(float); cif = defaultdict(float)
        for (n, m), (q, v) in por.items():
            if n in ncms:
                kg[m] += q; cif[m] += v
        saida[slug] = {"kg": dict(kg), "cif": dict(cif)}
    time.sleep(3)
    tot = tentar(comex, "heading", ["3102", "3103", "3104", "3105"], "heading", ate)
    total = defaultdict(float)
    for x in tot:
        total[f'{x["year"]}-{int(x["monthNumber"]):02d}'] += float(x["metricKG"])
    return saida, dict(total)


# ---------------------------------------------------------------- Cepea
def cepea(url):
    r = requests.get(url, headers={**UA, "Referer": "https://www.cepea.org.br/br/indicador/soja.aspx"}, timeout=120)
    r.raise_for_status()
    wb = CalamineWorkbook.from_filelike(BytesIO(r.content))
    linhas = wb.get_sheet_by_name(wb.sheet_names[0]).to_python()
    dias = []
    for x in linhas:
        if len(x) < 3 or not isinstance(x[0], str) or x[0].count("/") != 2:
            continue
        try:
            d = datetime.strptime(x[0].strip(), "%d/%m/%Y").date(); brl = float(x[1]); usd = float(x[2])
        except (ValueError, TypeError):
            continue
        dias.append((d, brl, usd))
    return sorted(dias)


def bcb_ptax():
    r = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.3698/dados?formato=json&dataInicial=01/01/2010", headers=UA, timeout=60)
    r.raise_for_status()
    return {f'{x["data"][6:10]}-{x["data"][3:5]}': float(x["valor"]) for x in r.json()}


def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    hoje = date.today(); ate = f"{hoje.year}-{hoje.month:02d}"
    # o Comex Stat aplica o intervalo de meses a cada ano (até "2026-11" corta todos os dezembros): pede até dezembro
    ferts, total = fertilizantes(f"{hoje.year}-12")
    ultimo_fert = max(m for f in ferts.values() for m, q in f["kg"].items() if q > 0)
    graos = {}
    for slug, (nome, praca, url, kg_un) in GRAOS.items():
        dias = tentar(cepea, url)
        fator = 60 / kg_un  # trigo é cotado por tonelada: converte para saca de 60 kg
        mes = defaultdict(lambda: [0.0, 0.0, 0])
        for d, brl, usd in dias:
            k = f"{d.year}-{d.month:02d}"; mes[k][0] += brl * fator; mes[k][1] += usd * fator; mes[k][2] += 1
        u = dias[-1]
        graos[slug] = {"nome": nome, "praca": praca,
                       "brl": {k: round(v[0] / v[2], 2) for k, v in mes.items()},
                       "usd": {k: round(v[1] / v[2], 3) for k, v in mes.items()},
                       "ultimo": {"d": u[0].isoformat(), "brl": round(u[1] * fator, 2), "usd": round(u[2] * fator, 3)}}
        print(slug, len(dias), "dias; último", u)
        time.sleep(2)
    ptax = tentar(bcb_ptax)
    lista = meses(INICIO, ate)
    saida = {
        "fonte": "Comex Stat (MDIC/SECEX), Cepea/Esalq e Banco Central",
        "meses": lista, "ultimo_fert": ultimo_fert,
        "ptax": [ptax.get(m) for m in lista],
        "import_total_mil_t": [round(total.get(m, 0) / 1e6, 1) for m in lista],
        "fertilizantes": {}, "graos": {},
    }
    for slug, (nome, curto, ncms, nutr) in FERTS.items():
        f = ferts[slug]
        saida["fertilizantes"][slug] = {
            "nome": nome, "curto": curto, "ncm": ncms, "nutriente": nutr,
            "usd_t": [round(f["cif"][m] / f["kg"][m] * 1000, 1) if f["kg"].get(m, 0) > 5e6 else None for m in lista],
            "mil_t": [round(f["kg"].get(m, 0) / 1e6, 1) for m in lista],
        }
    for slug, g in graos.items():
        saida["graos"][slug] = {"nome": g["nome"], "praca": g["praca"], "ultimo": g["ultimo"],
                                "usd_sc": [g["usd"].get(m) for m in lista], "brl_sc": [g["brl"].get(m) for m in lista]}
    (PASTA / "troca.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    i = lista.index(ultimo_fert)
    for s, f in saida["fertilizantes"].items():
        p = f["usd_t"][i]; sj = saida["graos"]["soja"]["usd_sc"][i]
        print(f"{s}: {ultimo_fert} US$ {p}/t | {f['mil_t'][i]} mil t | soja US$ {sj}/sc | {p / sj if p and sj else None:.1f} sc/t")


if __name__ == "__main__":
    main()
