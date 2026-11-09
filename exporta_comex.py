"""
Exporta Comex Stat (MDIC) para os dashboards HTML do AgroBasis.

Fonte: API oficial https://api-comexstat.mdic.gov.br (endpoint /general).
Produtos: complexo soja (grão, farelo, óleo), milho e complexo trigo
(grão, farinha, farelo). Fluxos: exportação e importação.

Estratégia:
  * cache agregado por (fluxo, ano) em dados/comex/cache/ -> anos fechados
    não são consultados de novo; o ano corrente e o anterior são sempre
    reconsultados (o MDIC revisa o mês anterior na divulgação seguinte);
  * meses ainda não publicados ficam como null (nunca zero);
  * gera um JSON compacto por produto + resumo.json para os cards.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://api-comexstat.mdic.gov.br/general"
ANO_INICIAL = 2010
SAIDA = Path("dados/comex")
CACHE = SAIDA / "cache"

# NCM -> slug do produto (mesma tabela mestra do app Streamlit)
NCM = {
    12010010: "soja", 12010090: "soja", 12011000: "soja", 12019000: "soja",
    23040010: "farelo", 23040090: "farelo",
    15071000: "oleo", 15079010: "oleo", 15079011: "oleo", 15079019: "oleo", 15079090: "oleo",
    10051000: "milho", 10059010: "milho", 10059090: "milho",
    10011010: "trigo", 10011090: "trigo", 10019900: "trigo",
    11010010: "farinha_trigo",
    23023010: "farelo_trigo",
}
NOMES = {
    "soja": "Soja em grão", "farelo": "Farelo de soja", "oleo": "Óleo de soja",
    "milho": "Milho", "trigo": "Trigo em grão", "farinha_trigo": "Farinha de trigo",
    "farelo_trigo": "Farelo de trigo",
}
FLUXOS = ("export", "import")
TOP_PAISES = 30
TOP_SERIE_PAIS = 12
ANOS_SERIE_PAIS = 6


def _lista(payload):
    """A API já devolveu lista direta e dict aninhado; normaliza os dois."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        d = payload.get("data")
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            for k in ("list", "rows", "items", "results"):
                if isinstance(d.get(k), list):
                    return d[k]
            for v in d.values():
                if isinstance(v, list):
                    return v
        for v in payload.values():
            if isinstance(v, list):
                return v
    return []


def consultar(fluxo: str, ano: int) -> list[dict]:
    body = {
        "flow": fluxo,
        "monthDetail": True,
        "period": {"from": f"{ano}-01", "to": f"{ano}-12"},
        "filters": [{"filter": "ncm", "values": sorted(NCM)}],
        "details": ["ncm", "country", "state"],
        "metrics": ["metricFOB", "metricKG"],
    }
    espera = [15, 30, 60, 90, 120]
    for i, s in enumerate(espera, 1):
        try:
            r = requests.post(URL, json=body, params={"language": "pt"}, timeout=120)
            if r.status_code == 200:
                return _lista(r.json())
            print(f"  {fluxo} {ano}: HTTP {r.status_code} (tentativa {i})", r.text[:150])
            if r.status_code == 400:
                break
        except requests.RequestException as e:
            print(f"  {fluxo} {ano}: {e} (tentativa {i})")
        time.sleep(s)
    raise RuntimeError(f"falha ao consultar {fluxo} {ano}")


def agregar(registros: list[dict]) -> list[list]:
    """Agrega por produto/mês/país/UF -> [slug, mes, pais, uf, fob, kg]."""
    acc = defaultdict(lambda: [0.0, 0.0])
    for r in registros:
        try:
            ncm = int(r.get("coNcm") or r.get("co_ncm") or r.get("ncmCode"))
        except (TypeError, ValueError):
            continue
        slug = NCM.get(ncm)
        if not slug:
            continue
        mes = int(r.get("monthNumber") or 0)
        if not 1 <= mes <= 12:
            continue
        pais = (r.get("country") or "Não declarado").strip()
        uf = (r.get("state") or "Não declarada").strip()
        a = acc[(slug, mes, pais, uf)]
        a[0] += float(r.get("metricFOB") or 0)
        a[1] += float(r.get("metricKG") or 0)
    return [[k[0], k[1], k[2], k[3], round(v[0]), round(v[1])] for k, v in sorted(acc.items())]


def carregar_ano(fluxo: str, ano: int, forcar: bool) -> list[list] | None:
    arq = CACHE / f"{fluxo}_{ano}.json"
    if arq.exists() and not forcar:
        return json.loads(arq.read_text())
    try:
        linhas = agregar(consultar(fluxo, ano))
    except RuntimeError as e:
        print("  aviso:", e)
        return json.loads(arq.read_text()) if arq.exists() else None
    time.sleep(12)  # a API limita a frequência de chamadas
    if linhas or not arq.exists():
        arq.write_text(json.dumps(linhas, ensure_ascii=False, separators=(",", ":")))
    return linhas


def montar_fluxo(dados: dict[int, list[list]], slug: str) -> dict | None:
    anos = sorted(dados)
    # [ano][mes] -> ton, fob ; [ano][pais] ; [ano][uf] ; [ano][pais][mes]
    ton = {a: [None] * 12 for a in anos}
    fob = {a: [None] * 12 for a in anos}
    pais_ano = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    uf_ano = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    pais_mes = defaultdict(lambda: defaultdict(lambda: [0.0] * 12))
    uf_pais = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # ano/mes -> (uf,pais)
    meses_pub = {}
    for a in anos:
        pub = max((l[1] for l in dados[a]), default=0)  # meses publicados (qualquer produto)
        meses_pub[a] = pub
        for m in range(pub):
            ton[a][m] = 0.0
            fob[a][m] = 0.0
        for s, m, p, u, f, kg in dados[a]:
            if s != slug:
                continue
            t = kg / 1000.0
            ton[a][m - 1] += t
            fob[a][m - 1] += f
            pais_ano[a][p][0] += t
            pais_ano[a][p][1] += f
            uf_ano[a][u][0] += t
            uf_ano[a][u][1] += f
            pais_mes[p][a][m - 1] += t
            uf_pais[(a, m)][u][p] += t
    if not any(v for a in anos for v in ton[a] if v):
        return None

    ultimo_ano = max(a for a in anos if meses_pub[a] > 0)
    ultimo_mes = meses_pub[ultimo_ano]

    def top(d, n):
        itens = sorted(d.items(), key=lambda kv: -kv[1][0])
        out = [[k, round(v[0]), round(v[1])] for k, v in itens[:n] if v[0] > 0]
        resto = itens[n:]
        if resto:
            out.append(["Outros", round(sum(v[0] for _, v in resto)), round(sum(v[1] for _, v in resto))])
        return out

    # YTD por país e UF (mesmo corte do último mês publicado) para comparar com o ano anterior
    def ytd(ano, por):
        acc = defaultdict(lambda: [0.0, 0.0])
        for s, m, p, u, f, kg in dados.get(ano, []):
            if s == slug and m <= ultimo_mes:
                k = p if por == "pais" else u
                acc[k][0] += kg / 1000.0
                acc[k][1] += f
        return acc

    # destinos principais (últimos 12 meses) para séries mensais por país
    ult12 = [(ultimo_ano, m) for m in range(ultimo_mes, 0, -1)] + [(ultimo_ano - 1, m) for m in range(12, ultimo_mes, -1)]
    soma12 = defaultdict(float)
    for a, m in ult12:
        for u, ps in uf_pais.get((a, m), {}).items():
            for p, t in ps.items():
                soma12[p] += t
    principais = [p for p, _ in sorted(soma12.items(), key=lambda kv: -kv[1])[:TOP_SERIE_PAIS]]
    anos_serie = [a for a in anos if a > ultimo_ano - ANOS_SERIE_PAIS]

    # fluxo UF -> país dos últimos 12 meses (sankey)
    links = defaultdict(float)
    for a, m in ult12:
        for u, ps in uf_pais.get((a, m), {}).items():
            for p, t in ps.items():
                links[(u, p)] += t
    tot_uf = defaultdict(float)
    tot_p = defaultdict(float)
    for (u, p), t in links.items():
        tot_uf[u] += t
        tot_p[p] += t
    top_uf = [u for u, _ in sorted(tot_uf.items(), key=lambda kv: -kv[1])[:8]]
    top_p = [p for p, _ in sorted(tot_p.items(), key=lambda kv: -kv[1])[:10]]
    sk = defaultdict(float)
    for (u, p), t in links.items():
        sk[(u if u in top_uf else "Outras UFs", p if p in top_p else "Outros destinos")] += t
    sankey = [[u, p, round(t)] for (u, p), t in sorted(sk.items(), key=lambda kv: -kv[1]) if t >= 1]

    r1 = lambda v: None if v is None else round(v)
    return {
        "anos": anos,
        "ultimo": {"ano": ultimo_ano, "mes": ultimo_mes},
        "ton": {str(a): [r1(v) for v in ton[a]] for a in anos},
        "fob": {str(a): [r1(v) for v in fob[a]] for a in anos},
        "paises": {str(a): top(pais_ano[a], TOP_PAISES) for a in anos},
        "estados": {str(a): top(uf_ano[a], 27) for a in anos},
        "paises_ytd": {str(a): top(ytd(a, "pais"), TOP_PAISES) for a in (ultimo_ano, ultimo_ano - 1)},
        "estados_ytd": {str(a): top(ytd(a, "uf"), 27) for a in (ultimo_ano, ultimo_ano - 1)},
        "pais_mensal": {p: {str(a): [round(v) for v in pais_mes[p][a]] for a in anos_serie} for p in principais},
        "sankey": sankey,
    }


def main():
    forcar_tudo = os.environ.get("COMEX_FORCAR_TUDO") == "1"
    CACHE.mkdir(parents=True, exist_ok=True)
    hoje = datetime.now(timezone.utc)
    anos = list(range(ANO_INICIAL, hoje.year + 1))
    brutos = {}
    for fluxo in FLUXOS:
        brutos[fluxo] = {}
        for ano in anos:
            forcar = forcar_tudo or ano >= hoje.year - 1
            print(f"{fluxo} {ano}{' (consulta)' if forcar or not (CACHE / f'{fluxo}_{ano}.json').exists() else ''}")
            linhas = carregar_ano(fluxo, ano, forcar)
            if linhas:
                brutos[fluxo][ano] = linhas
    if not brutos["export"]:
        sys.exit("sem dados de exportação; nada gravado")

    resumo = {}
    for slug, nome in NOMES.items():
        saida = {"produto": nome, "slug": slug, "fonte": "Comex Stat / MDIC"}
        for fluxo in FLUXOS:
            saida[fluxo] = montar_fluxo(brutos[fluxo], slug) if brutos[fluxo] else None
        anterior = SAIDA / f"{slug}.json"
        corpo = json.dumps({k: v for k, v in saida.items()}, ensure_ascii=False, separators=(",", ":"))
        manter = None
        if anterior.exists():
            velho = json.loads(anterior.read_text())
            velho_at = velho.pop("atualizado_em", None)
            if json.dumps(velho, ensure_ascii=False, separators=(",", ":")) == corpo:
                manter = velho_at
        saida["atualizado_em"] = manter or hoje.strftime("%Y-%m-%dT%H:%M:%SZ")
        anterior.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))

        for fluxo in FLUXOS:
            f = saida[fluxo]
            if not f:
                continue
            a, m = f["ultimo"]["ano"], f["ultimo"]["mes"]
            cur = f["ton"].get(str(a), [None] * 12)
            prev = f["ton"].get(str(a - 1), [None] * 12)
            ytd = sum(v or 0 for v in cur[:m])
            ytd0 = sum(v or 0 for v in prev[:m])
            resumo.setdefault(slug, {"produto": nome})[fluxo] = {
                "ano": a, "mes": m, "ytd_ton": round(ytd), "ytd_ton_ant": round(ytd0),
                "var_ytd": round((ytd / ytd0 - 1) * 100, 1) if ytd0 else None,
                "mes_ton": cur[m - 1], "mes_ton_ant": prev[m - 1],
            }
        print(slug, "ok")
    (SAIDA / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
