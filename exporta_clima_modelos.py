"""Previsão de chuva por vários modelos meteorológicos nos polos do painel "Clima e El Niño" do AgroBasis.

Para cada polo, a chuva diária prevista por cada modelo global é a média das mesmas células da grade de 0,25°
usadas no painel (sede + células espalhadas pela área do município). Fonte: Open-Meteo (API de previsão,
um modelo por coluna). Saída: dados/clima/modelos.json.

O que o usuário vê:
  - total de 7 dias de cada modelo, a mediana entre eles (consenso), a faixa do mais seco ao mais úmido
    e quantos modelos preveem chuva acima ou abaixo da normal;
  - total de 15 dias dos modelos que chegam a esse horizonte;
  - grau de concordância: a faixa entre os modelos medida contra a chuva normal do período.
Roda depois de exporta_clima.py, que fornece a normal diária de cada polo (clima.json).
"""
import json
import statistics
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from exporta_clima import PONTOS, _lote

PASTA = Path("dados/clima")
URL = "https://api.open-meteo.com/v1/forecast"
LOTE = 20

# id na Open-Meteo, nome curto, centro de origem
MODELOS = [
    ("ecmwf_ifs025", "ECMWF IFS", "Europa"),
    ("ecmwf_aifs025_single", "ECMWF AIFS (IA)", "Europa"),
    ("gfs_seamless", "GFS", "EUA"),
    ("icon_seamless", "ICON", "Alemanha"),
    ("gem_seamless", "GEM", "Canadá"),
    ("jma_seamless", "JMA", "Japão"),
    ("ukmo_seamless", "UKMO", "Reino Unido"),
]
PARAMS = {"daily": "precipitation_sum", "forecast_days": 16, "timezone": "America/Sao_Paulo",
          "models": ",".join(m[0] for m in MODELOS)}


def media(vals):
    v = [x for x in vals if x is not None]
    return round(sum(v) / len(v), 1) if v else None


def total(serie, n):
    """soma dos n primeiros dias; None se o modelo não cobre todo o período"""
    s = serie[:n]
    if len(s) < n or any(x is None for x in s):
        return None
    return round(sum(s), 1)


def concordancia(vals, normal):
    """faixa entre o modelo mais seco e o mais úmido, comparada à chuva normal do período"""
    if len(vals) < 3:
        return None, None
    faixa = max(vals) - min(vals)
    r = faixa / max(normal or 0, 15)
    return round(r, 2), ("alta" if r < 0.6 else "média" if r < 1.2 else "baixa")


def resumo(series, normal, n):
    tots = {m: total(s, n) for m, s in series.items()}
    validos = {m: v for m, v in tots.items() if v is not None}
    if not validos:
        return None
    vals = list(validos.values())
    med = round(statistics.median(vals), 1)
    r, nivel = concordancia(vals, normal)
    seco = min(validos, key=validos.get); umido = max(validos, key=validos.get)
    return {"tot": tots, "mediana": med, "min": min(vals), "max": max(vals), "n": len(vals),
            "normal": normal, "pct": round(med / normal * 100) if normal else None,
            "acima": sum(1 for v in vals if normal and v > normal * 1.1),
            "abaixo": sum(1 for v in vals if normal and v < normal * 0.9),
            "faixa_rel": r, "concordancia": nivel, "mais_seco": seco, "mais_umido": umido}


def main():
    clima = json.loads((PASTA / "clima.json").read_text())
    normais = {p["id"]: dict(zip(p["prev"]["d"], p["prev"]["normal_dia"])) for p in clima["pontos"]}
    grade = json.loads((PASTA / "grade_municipios.json").read_text())
    cels = {pid: [(lat, lon)] + [tuple(c) for c in (grade.get(pid) or {}).get("celulas", [])]
            for pid, _, _, lat, lon, _ in PONTOS}
    todos = [(pid, c) for pid, cs in cels.items() for c in cs]
    resp = []
    for i in range(0, len(todos), LOTE):
        resp += _lote(URL, [c for _, c in todos[i:i + LOTE]], PARAMS)
        time.sleep(3)
    pontos = {}
    for pid, nome, uf, *_ in PONTOS:
        rs = [resp[k]["daily"] for k, (p, _) in enumerate(todos) if p == pid]
        datas = rs[0]["time"]
        series = {}
        for mid, *_ in MODELOS:
            col = f"precipitation_sum_{mid}"
            s = [media([r.get(col, [None] * len(datas))[i] for r in rs]) for i in range(len(datas))]
            # corta os dias finais sem valor (horizonte do modelo)
            while s and s[-1] is None:
                s.pop()
            if s:
                series[mid] = s
        nd = normais.get(pid, {})
        norm = [nd.get(d) for d in datas]
        n7 = round(sum(x or 0 for x in norm[:7])); n15 = round(sum(x or 0 for x in norm[:15]))
        pontos[pid] = {"nome": nome, "uf": uf, "d": datas[:16], "series": series,
                       "normal_dia": norm[:16],
                       "r7": resumo(series, n7, 7), "r15": resumo(series, n15, 15)}
        r7 = pontos[pid]["r7"]
        print(f"{nome} ({uf}): 7 dias mediana {r7['mediana']} mm, normal {n7}, faixa {r7['min']}-{r7['max']}, "
              f"concordância {r7['concordancia']}, modelos {r7['n']}")
    saida = {"atualizado_em": datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M"),
             "modelos": [{"id": m, "nome": n, "origem": o} for m, n, o in MODELOS],
             "pontos": pontos}
    (PASTA / "modelos.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
