"""Armazenagem de grãos por estado, para o dashboard "Armazenagem de Grãos no Brasil" do AgroBasis.

Fontes oficiais:
  - IBGE, Pesquisa de Estoques (semestral), via API do SIDRA (apisidra.ibge.gov.br):
      tabela 5459: número de estabelecimentos e capacidade útil (t) dos armazéns graneleiros e silos,
                   por UF e por município, desde o 2º semestre de 2007;
      tabela 5470: armazéns convencionais, estruturais e infláveis (m³), por UF;
      tabela 254:  quantidade estocada no último dia do semestre, por produto e tipo de proprietário.
  - Conab, série histórica de produção de grãos por UF (SerieHistoricaGraos), para a relação capacidade/produção.

Saída: dados/armazenagem/armazenagem.json
"""
import json
import time
from collections import defaultdict
from pathlib import Path

import requests

PASTA = Path("dados/armazenagem")
SIDRA = "https://apisidra.ibge.gov.br/values"
UA = {"User-Agent": "Mozilla/5.0 (AgroBasis; agrobasis.com.br)"}
SIGLA = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
         "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
         "51": "MT", "52": "GO", "53": "DF"}
TIPOS = {"114630": "total", "3067": "graneleiro", "3327": "silo"}
PRODUTOS = {"118423": "total", "3047": "soja", "3045": "milho", "3328": "trigo", "3038": "arroz", "3034": "algodao", "33467": "cafe_arabica"}
PROPRIEDADE = {"0": "total", "3029": "governo", "3030": "privada", "3031": "cooperativa", "3032": "mista"}


def sidra(caminho, n=4):
    for i in range(n):
        try:
            r = requests.get(f"{SIDRA}/{caminho}", headers=UA, timeout=180)
            r.raise_for_status()
            d = r.json()
            return d[1:]  # a primeira linha é o cabeçalho
        except (requests.RequestException, ValueError) as e:
            if i == n - 1:
                raise
            print(f"  nova tentativa ({e})"); time.sleep(15 * (i + 1))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None  # "-", "X" (sigilo) e ".." viram vazio


def local(x):
    return "BR" if x["NC"] == "1" else SIGLA.get(x["D1C"], x["D1C"])


def periodo(cod):
    return f"{cod[:4]}-{cod[4:]}"  # 202601 -> 2026-01 (1º semestre)


def capacidade():
    linhas = sidra("t/5459/n1/all/n3/all/v/152,153/p/all/c166/all/c11278/39324")
    cap = defaultdict(lambda: defaultdict(dict))  # local -> tipo -> periodo -> [estab, t]
    for x in linhas:
        t = TIPOS.get(x["D4C"])
        if not t:
            continue
        reg = cap[local(x)][t].setdefault(periodo(x["D3C"]), [None, None])
        reg[0 if x["D2C"] == "152" else 1] = num(x["V"])
    return cap


def convencional():
    linhas = sidra("t/5470/n1/all/n3/all/v/2171,2172/p/all/c11278/39324")
    out = defaultdict(dict)
    for x in linhas:
        reg = out[local(x)].setdefault(periodo(x["D3C"]), [None, None])
        reg[0 if x["D2C"] == "2171" else 1] = num(x["V"])
    return out


def municipios():
    linhas = sidra("t/5459/n6/all/v/153/p/last%201/c166/114630/c11278/39324")
    out = []
    for x in linhas:
        v = num(x["V"])
        if v:
            nome, uf = x["D1N"].rsplit(" - ", 1) if " - " in x["D1N"] else (x["D1N"], "")
            out.append({"cod": x["D1C"], "nome": nome, "uf": uf, "t": v, "p": periodo(x["D3C"])})
    out.sort(key=lambda m: -m["t"])
    return out


def estoques():
    produtos = ",".join(PRODUTOS)
    linhas = sidra(f"t/254/n1/all/n3/all/v/150/p/all/c162/{produtos}/c161/0/c163/0")
    out = defaultdict(lambda: defaultdict(dict))
    for x in linhas:
        p = PRODUTOS.get(x["D5C"])
        if p:
            out[local(x)][p][periodo(x["D3C"])] = num(x["V"])
    time.sleep(3)
    linhas = sidra("t/254/n1/all/v/150/p/all/c162/118423/c161/allxt/c163/0")
    prop = defaultdict(dict)
    for x in linhas:
        k = PROPRIEDADE.get(x["D4C"])
        if k:
            prop[k][periodo(x["D3C"])] = num(x["V"])
    return out, prop


def producao():
    import exporta_conab as ec
    serie = ec.ler_txt(ec.baixar(f"{ec.PORTAL}/SerieHistoricaGraos.txt"))
    h = ec.historico_total(serie)
    out = {"anos": h["anos"][-20:], "BR": h["brasil"]["producao"][-20:]}
    for uf, d in h["ufs"].items():
        out[uf] = d["producao"][-len(out["anos"]):]
    return out


def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    cap = capacidade(); time.sleep(3)
    conv = convencional(); time.sleep(3)
    mun = municipios(); time.sleep(3)
    est, prop = estoques()
    prod = producao()
    periodos = sorted({p for l in cap.values() for t in l.values() for p in t})
    ufs = ["BR"] + sorted(k for k in cap if k != "BR")
    saida = {"fonte": "IBGE, Pesquisa de Estoques (SIDRA 5459, 5470, 254) e Conab", "periodos": periodos, "ultimo": periodos[-1],
             "locais": {}, "municipios": mun[:60], "n_municipios": len(mun), "propriedade": {k: [v.get(p) for p in periodos] for k, v in prop.items()},
             "producao": prod}
    for u in ufs:
        reg = {"cap": {}, "estab": {}, "conv_m3": [conv.get(u, {}).get(p, [None, None])[1] for p in periodos],
               "estoque": {k: [est.get(u, {}).get(k, {}).get(p) for p in periodos] for k in PRODUTOS.values()}}
        for t in TIPOS.values():
            serie = cap.get(u, {}).get(t, {})
            reg["cap"][t] = [serie.get(p, [None, None])[1] for p in periodos]
            reg["estab"][t] = [serie.get(p, [None, None])[0] for p in periodos]
        saida["locais"][u] = reg
    (PASTA / "armazenagem.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    b = saida["locais"]["BR"]
    print("períodos:", periodos[0], "a", periodos[-1], "| BR granel:", b["cap"]["total"][-1], "t | silos:", b["cap"]["silo"][-1],
          "| estoque total:", b["estoque"]["total"][-1], "| municípios:", len(mun), "| maior:", mun[0])


if __name__ == "__main__":
    main()
