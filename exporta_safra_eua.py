"""
Exporta Condição e Progresso das Lavouras dos EUA (USDA NASS Crop Progress) para o dashboard HTML.

Fonte: API Quick Stats do USDA NASS (https://quickstats.nass.usda.gov/api). Chave no secret NASS_API_KEY.
Nível nacional, semanal, desde 2010. Culturas: milho, soja, trigo de inverno e trigo de primavera.

Saída: dados/safra_eua.json
  culturas.<slug>.condicao[ano] = [[data, muito_ruim, ruim, regular, boa, excelente], ...]
  culturas.<slug>.progresso[etapa][ano] = [[data, pct], ...]
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

URL = "https://quickstats.nass.usda.gov/api/api_GET/"
ANO_INICIAL = 2010
SAIDA = Path("dados/safra_eua.json")

CULTURAS = {
    "milho": {"nome": "Milho", "commodity_desc": "CORN"},
    "soja": {"nome": "Soja", "commodity_desc": "SOYBEANS"},
    "trigo_inverno": {"nome": "Trigo de inverno", "commodity_desc": "WHEAT", "class_desc": "WINTER"},
    "trigo_primavera": {"nome": "Trigo de primavera", "commodity_desc": "WHEAT", "class_desc": "SPRING, (EXCL DURUM)"},
}
# etapas do Crop Progress traduzidas (o que não estiver aqui é ignorado)
ETAPAS = {
    "PCT PLANTED": "Plantio", "PCT EMERGED": "Emergência", "PCT SILKING": "Embonecamento",
    "PCT DOUGH": "Grão pastoso", "PCT DENTED": "Grão dentado", "PCT MATURE": "Maturação",
    "PCT HARVESTED": "Colheita", "PCT BLOOMING": "Floração", "PCT SETTING PODS": "Formação de vagens",
    "PCT DROPPING LEAVES": "Queda de folhas", "PCT HEADED": "Espigamento", "PCT COLORING": "Maturação",
    "PCT JOINTING": "Elongação",
}
CONDICAO = ["PCT VERY POOR", "PCT POOR", "PCT FAIR", "PCT GOOD", "PCT EXCELLENT"]


def consultar(chave: str, params: dict) -> list[dict]:
    base = {"key": chave, "source_desc": "SURVEY", "agg_level_desc": "NATIONAL", "freq_desc": "WEEKLY",
            "year__GE": str(ANO_INICIAL), "format": "JSON"}
    base.update(params)
    for tentativa in range(5):
        try:
            r = requests.get(URL, params=base, timeout=120)
            if r.status_code == 200:
                return r.json().get("data", [])
            if r.status_code == 400 and "exceeds" not in r.text:
                print("  sem dados:", params, r.text[:120])
                return []
            print(f"  HTTP {r.status_code} (tentativa {tentativa + 1}):", r.text[:150])
        except requests.RequestException as e:
            print(f"  erro (tentativa {tentativa + 1}):", e)
        time.sleep(10 * (tentativa + 1))
    raise RuntimeError(f"falha na consulta {params}")


def valor(v) -> float | None:
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None  # "(D)", "(NA)" etc.


def main():
    chave = os.environ.get("NASS_API_KEY", "").strip()
    if not chave:
        sys.exit("NASS_API_KEY não configurada")
    saida = {"fonte": "USDA NASS Crop Progress (Quick Stats)", "culturas": {}}
    ultima = ""
    for slug, cfg in CULTURAS.items():
        filtro = {k: v for k, v in cfg.items() if k != "nome"}
        print(slug)
        # condição: [data] -> {categoria: pct}
        cond = defaultdict(dict)
        for r in consultar(chave, {**filtro, "statisticcat_desc": "CONDITION"}):
            u, d, v = r.get("unit_desc"), r.get("week_ending"), valor(r.get("Value"))
            if u in CONDICAO and d and v is not None:
                cond[d][u] = v
        condicao = defaultdict(list)
        for d in sorted(cond):
            x = cond[d]
            if all(c in x for c in CONDICAO):
                condicao[d[:4]].append([d] + [x[c] for c in CONDICAO])
                ultima = max(ultima, d)
        time.sleep(2)
        # progresso
        prog = defaultdict(lambda: defaultdict(dict))
        for r in consultar(chave, {**filtro, "statisticcat_desc": "PROGRESS"}):
            u, d, v = r.get("unit_desc"), r.get("week_ending"), valor(r.get("Value"))
            etapa = ETAPAS.get(u)
            if not etapa or not d or v is None:
                continue
            # milho: ignora "silagem" e outras utilizações; mantém o total (GRAIN ou ALL)
            util = r.get("util_practice_desc") or "ALL UTILIZATION PRACTICES"
            if util not in ("ALL UTILIZATION PRACTICES", "GRAIN"):
                continue
            prog[etapa][d[:4]][d] = v
            ultima = max(ultima, d)
        progresso = {e: {a: [[d, prog[e][a][d]] for d in sorted(prog[e][a])] for a in sorted(prog[e])} for e in prog}
        saida["culturas"][slug] = {"nome": cfg["nome"], "condicao": dict(condicao), "progresso": progresso}
        print(f"  condição: {sum(len(v) for v in condicao.values())} semanas · etapas: {list(progresso)}")
        time.sleep(2)

    if not ultima:
        sys.exit("nenhum dado retornado; arquivo não alterado")
    saida["ultima_semana"] = ultima
    corpo = json.dumps(saida, ensure_ascii=False, separators=(",", ":"))
    if SAIDA.exists():
        velho = json.loads(SAIDA.read_text())
        at = velho.pop("atualizado_em", None)
        if json.dumps(velho, ensure_ascii=False, separators=(",", ":")) == corpo:
            print("sem mudança")
            return
    saida["atualizado_em"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    print("gravado", SAIDA, "última semana", ultima)


if __name__ == "__main__":
    main()
