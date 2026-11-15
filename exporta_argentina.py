"""Painel Safra Argentina: gera dados/argentina/argentina.json.

Fontes
  - Secretaría de Agricultura, Ganadería y Pesca (SAGyP), Informe Semanal de Estimaciones Agrícolas (PDF, quintas-feiras):
    avanço de plantio e colheita, estado e umidade das lavouras, produção. Cada informe lido fica em cache
    em dados/argentina/informes/AAAA-MM-DD.json; o histórico desde 2021 dá a média de 5 safras.
  - SAGyP, base de estimativas por departamento (datos.gob.ar, CSV): produtividade por província desde 1990/91.
  - Bolsa de Comercio de Rosario (GEA): estimativa nacional de área, rendimento e produção.
  - USDA PSD (dados/usda/*.json, já coletado pelo AgroBasis).
  - Chuva: ERA5 e ECMWF via Open-Meteo, com as funções do painel Clima.

Uso: python exporta_argentina.py            (atualização normal)
     python exporta_argentina.py --historico (lê todos os informes desde 2021 que ainda não estão em cache)
"""
import csv
import html
import io
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, quote

import requests

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "argentina"))
import sagyp  # noqa: E402

PASTA = RAIZ / "dados/argentina"
CACHE = PASTA / "informes"
UA = {"User-Agent": "Mozilla/5.0 (compatible; AgroBasis; +https://agrobasis.com.br)"}
LISTA = "https://www.magyp.gob.ar/sitio/areas/estimaciones/estimaciones/informes/"
BCR_EST = "https://www.bcr.com.ar/es/mercados/gea/estimaciones-nacionales-de-produccion/estimaciones"
BCR_SEM = "https://www.bcr.com.ar/es/mercados/gea/seguimiento-de-cultivos/informe-semanal-zona-nucleo"
CKAN = "https://datos.gob.ar/api/3/action/package_search"
INICIO_HIST = date(2020, 8, 1)
PRINCIPAIS = ["soja", "milho", "trigo", "girassol"]
# polos de chuva (id, cidade, província, lat, lon, culturas)
POLOS = [
    ("ar_pergamino", "Pergamino", "Buenos Aires", -33.89, -60.57, "soja e milho, zona núcleo"),
    ("ar_casilda", "Casilda", "Santa Fe", -33.04, -61.17, "soja e milho, zona núcleo"),
    ("ar_marcosjuarez", "Marcos Juárez", "Córdoba", -32.70, -62.10, "soja, milho e trigo"),
    ("ar_riocuarto", "Río Cuarto", "Córdoba", -33.12, -64.35, "milho, soja e amendoim"),
    ("ar_rafaela", "Rafaela", "Santa Fe", -31.25, -61.49, "soja, milho e trigo"),
    ("ar_pehuajo", "Pehuajó", "Buenos Aires", -35.81, -61.90, "soja, milho e girassol"),
    ("ar_generalpico", "General Pico", "La Pampa", -35.66, -63.76, "milho, soja e girassol"),
    ("ar_tresarroyos", "Tres Arroyos", "Buenos Aires", -38.38, -60.28, "trigo, cevada e soja"),
    ("ar_charata", "Charata", "Chaco", -27.22, -61.19, "soja, milho e algodão"),
]


def get(url, n=3, **kw):
    for i in range(n):
        try:
            r = requests.get(url, headers=UA, timeout=90, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == n - 1:
                raise
            print("  nova tentativa:", url[:90], e)
            time.sleep(5 * (i + 1))


# ------------------------------------------------------------------ informes semanais SAGyP
def listar(mes=None):
    """[(data, url_pdf)] dos informes semanais de um mês (mes='AAAA-MM'); sem mês, o mês corrente"""
    r = get(LISTA + (f"?mes={mes}" if mes else ""))
    out = []
    for href, txt in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', r.text, flags=re.S | re.I):
        t = html.unescape(re.sub(r"<[^>]+>", " ", txt))
        m = re.search(r"(\d{2})[_/.-](\d{2})[_/.-](\d{4})", t) or re.search(r"(\d{2})[_/.-](\d{2})[_/.-](\d{4})", href)
        if "emanal" not in t + href or not m:
            continue
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        out.append((d, urljoin(LISTA, quote(html.unescape(href), safe="/:%"))))
    return sorted(set(out))


def meses(desde, ate):
    y, m = desde.year, desde.month
    while (y, m) <= (ate.year, ate.month):
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def ler_e_guardar(d, url):
    alvo = CACHE / f"{d.isoformat()}.json"
    if alvo.exists():
        return json.loads(alvo.read_text())
    tmp = PASTA / "_tmp.pdf"
    tmp.write_bytes(get(url).content)
    try:
        r = sagyp.ler_informe(tmp)
    except Exception as e:
        print("  falha ao ler", d, e)
        r = {"data": d.isoformat(), "erro": repr(e)[:200]}
    r["url"] = url
    tmp.unlink(missing_ok=True)
    # no cache só o que o painel usa: delegações ficam só no informe mais recente
    alvo.write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
    return r


def coletar_informes(historico):
    CACHE.mkdir(parents=True, exist_ok=True)
    hoje = date.today()
    ms = list(meses(INICIO_HIST if historico else hoje - timedelta(days=40), hoje))
    novos = 0
    for mes in ms:
        try:
            lst = listar(mes)
        except Exception as e:
            print("  lista falhou", mes, e); continue
        for d, url in lst:
            if not (CACHE / f"{d.isoformat()}.json").exists():
                print("  informe", d)
                ler_e_guardar(d, url); novos += 1
                time.sleep(1.5)
    print("informes novos:", novos)
    return sorted((json.loads(f.read_text()) for f in CACHE.glob("*.json")), key=lambda r: r["data"])


# ------------------------------------------------------------------ histórico de avanço e estado
def safra_de(dia, cult, op):
    """ano de início da safra (2026 = 2026/27). Colheita de soja, milho e girassol cai no ano seguinte."""
    d = date.fromisoformat(dia)
    if op == "colheita" and cult in ("soja", "milho", "girassol", "algodao", "amendoim", "sorgo", "arroz"):
        return d.year - 1 if d.month <= 10 else d.year
    return d.year if d.month >= 7 else d.year - 1


def dia_safra(dia, s0):
    return (date.fromisoformat(dia) - date(s0, 7, 1)).days


def series_avanco(informes):
    """{cult: {op: {safra: {data: pct}}}} com o total do país, combinando as 6 semanas de cada informe"""
    out = {}
    for r in informes:
        for c, ops in (r.get("avanco") or {}).items():
            for op, a in ops.items():
                tp = (a.get("provincias") or {}).get("TOTAL PAIS")
                if not tp or not tp.get("atual"):
                    continue
                for d, v, va in zip(a["semanas"], tp["atual"], tp.get("anterior") or [None] * 6):
                    if v is None:
                        continue
                    s0 = safra_de(d, c, op)
                    out.setdefault(c, {}).setdefault(op, {}).setdefault(s0, {})[d] = v
    return out


def media_safras(ser, s_atual, datas, n=5):
    """média das n safras anteriores nas mesmas datas do calendário (interpolação linear por dia da safra)"""
    res = []
    for d in datas:
        x = dia_safra(d, s_atual)
        vals = []
        for s in range(s_atual - n, s_atual):
            pts = sorted((dia_safra(k, s), v) for k, v in (ser.get(s) or {}).items())
            if len(pts) < 3:
                continue
            if x <= pts[0][0]:
                vals.append(0.0 if pts[0][1] <= 5 else None); continue
            if x >= pts[-1][0]:
                vals.append(pts[-1][1]); continue
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if x0 <= x <= x1:
                    vals.append(y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y0); break
        vals = [v for v in vals if v is not None]
        res.append(round(sum(vals) / len(vals), 1) if len(vals) >= 3 else None)
    return res


def curva(ser, s0):
    pts = sorted((ser.get(s0) or {}).items())
    return [[k, v] for k, v in pts]


def series_estado(informes):
    """{cult: {safra: [[data, MB+B, R+M, seca%]]}}"""
    out = {}
    for r in informes:
        for c, e in (r.get("estado") or {}).items():
            n = e.get("nacional")
            if not n:
                continue
            s0 = safra_de(r["data"], c, "plantio")
            if c in ("soja", "milho", "girassol") and date.fromisoformat(r["data"]).month <= 6:
                s0 = date.fromisoformat(r["data"]).year - 1
            est = n["estado"]
            out.setdefault(c, {}).setdefault(s0, []).append([r["data"], round(est[0] + est[1], 1), round(est[2] + est[3], 1), n["umidade"]["seca"]])
    return out


# ------------------------------------------------------------------ produtividade por província (datos.gob.ar)
def csv_estimativas():
    r = get(CKAN, params={"q": "estimaciones agricolas", "rows": 5}).json()
    for p in r["result"]["results"]:
        for res in p["resources"]:
            if res.get("format", "").upper() == "CSV" and "estimaciones-agricolas" in res["url"]:
                return res["url"]
    raise RuntimeError("CSV de estimativas não encontrado")


def produtividade(fases):
    url = csv_estimativas()
    print("CSV por departamento:", url.rsplit("/", 1)[-1])
    txt = get(url).content.decode("utf-8", errors="replace")
    alvo = {"soja total": "soja", "soja": "soja", "maíz": "milho", "maiz": "milho", "trigo total": "trigo", "trigo": "trigo"}
    agg = {}
    vistos = {}
    for l in csv.DictReader(io.StringIO(txt)):
        c = alvo.get(l["cultivo"].strip().lower())
        if not c:
            continue
        # se existir "soja total", ignora as linhas de 1ª e 2ª para não somar duas vezes
        vistos.setdefault(c, set()).add(l["cultivo"].strip().lower())
        camp = l["campania"]; s0 = int(camp[:4])
        if s0 < 1990:
            continue
        prov = l["provincia"].strip()
        k = (c, l["cultivo"].strip().lower(), prov, s0)
        a = agg.setdefault(k, [0.0, 0.0, 0.0])
        for i, col in enumerate(("superficie_sembrada_ha", "superficie_cosechada_ha", "produccion_tm")):
            try:
                a[i] += float(l[col] or 0)
            except ValueError:
                pass
    prefer = {c: (min(v, key=lambda x: (0 if "total" in x else 1, x))) for c, v in vistos.items()}
    out = {}
    for (c, nome, prov, s0), (sem, col, prod) in agg.items():
        if nome != prefer[c] or col <= 0:
            continue
        for p in (prov, "Argentina"):
            t = out.setdefault(c, {}).setdefault(p, {}).setdefault(s0, [0.0, 0.0])
            t[0] += col; t[1] += prod
    res = {}
    for c, provs in out.items():
        tot_prod = {p: sum(v[1] for s, v in d.items() if s >= max(d) - 4) for p, d in provs.items()}
        top = [p for p in sorted(tot_prod, key=tot_prod.get, reverse=True) if p != "Argentina"][:6]
        res[c] = {}
        for p in ["Argentina"] + top:
            d = provs[p]
            anos = sorted(d)
            rend = [round(d[s][1] / d[s][0] * 10, 1) for s in anos]       # qq/ha
            # tendência quadrática para separar tecnologia de clima
            n = len(anos); xs = [s - anos[0] for s in anos]
            import numpy as np
            co = np.polyfit(xs, rend, 2) if n >= 8 else None
            desv = [round((r / np.polyval(co, x) - 1) * 100, 1) if co is not None else None for r, x in zip(rend, xs)]
            por_fase = {}
            for s, dv in zip(anos, desv):
                f = fases.get(str(s))
                if f and dv is not None:
                    por_fase.setdefault(f, []).append(dv)
            res[c][p] = {"safras": [f"{s}/{str(s + 1)[2:]}" for s in anos], "rend": rend, "desvio": desv,
                         "prod_mil_t": [round(d[s][1] / 1000) for s in anos],
                         "fases": {f: {"media": round(sum(v) / len(v), 1), "n": len(v)} for f, v in por_fase.items()},
                         "fase_safra": [fases.get(str(s)) for s in anos]}
    return {"fonte": url, "culturas": res}


# ------------------------------------------------------------------ Bolsa de Comercio de Rosario
def bcr():
    out = {"estimativas": {}, "mensal": None, "semanal": None}
    try:
        s = get(BCR_EST).text
        for cls, c in (("trigo", "trigo"), ("maiz", "milho"), ("soja", "soja"), ("girasol", "girassol")):
            m = re.search(rf'<table class="bcr-estimaciones {cls}[^"]*">(.*?)</table>', s, flags=re.S)
            if not m:
                continue
            linhas = []
            for camp, a, r_, p in re.findall(r"<td>(\d{4}/\d{4})</td>\s*<td><strong>([\d,.]*)</strong>.*?<td><strong>([\d,.]*)</strong>.*?<td><strong>([\d,.]*)</strong>", m.group(1), flags=re.S):
                f = lambda x: float(x.replace(".", "").replace(",", ".")) if x else None
                linhas.append({"safra": camp, "area_mi_ha": f(a), "rend_qq_ha": f(r_), "prod_mi_t": f(p)})
            out["estimativas"][c] = linhas
        out["mensal"] = titulo_bcr(s, "Informe de Estimación Mensual")
    except Exception as e:
        print("BCR estimativas falhou:", e)
    try:
        out["semanal"] = titulo_bcr(get(BCR_SEM).text, "Resumen del Informe")
    except Exception as e:
        print("BCR semanal falhou:", e)
    return out


def titulo_bcr(s, ancora):
    t = html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)))
    linhas = [x.strip() for x in t.split("\n") if x.strip()]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    pdf = re.search(r'href="(https://www\.bcr\.com\.ar/sites/default/files/[^"]+\.pdf)"', s)
    for i, l in enumerate(linhas):
        m = re.match(r"^-?\s*(\d{1,2}) de (\w+) de (\d{4})$", l)
        if m and m.group(2).capitalize() in meses and i + 1 < len(linhas):
            tit = next((x for x in linhas[i - 3:i] if len(x) > 25 and x not in ("Descargar",) and ancora not in x), None)
            d = date(int(m.group(3)), meses.index(m.group(2).capitalize()) + 1, int(m.group(1)))
            return {"data": d.isoformat(), "titulo": tit, "pdf": pdf.group(1) if pdf else None}
    return None


def historico_bcr(novo):
    f = PASTA / "bcr_historico.json"
    h = json.loads(f.read_text()) if f.exists() else []
    chave = json.dumps(novo["estimativas"], sort_keys=True)
    if novo["estimativas"] and (not h or json.dumps(h[-1]["estimativas"], sort_keys=True) != chave):
        h.append({"data": date.today().isoformat(), "estimativas": novo["estimativas"]})
        f.write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":")))
    return h


# ------------------------------------------------------------------ USDA
def usda():
    out = {}
    for c, arq in (("soja", "soja"), ("milho", "milho"), ("trigo", "trigo")):
        f = RAIZ / f"dados/usda/{arq}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text()); a = d["produtos"]["grao"]["paises"]["AR"]["dados"]; anos = d["anos"]
        out[c] = {"relatorio": d.get("relatorio"), "safras": [f"{y}/{str(y + 1)[2:]}" for y in anos[-6:]],
                  "producao_mil_t": a["producao"][-6:], "area_mil_ha": a["area"][-6:], "rend_t_ha": a["produtividade"][-6:],
                  "exportacao_mil_t": a["exportacao"][-6:]}
    return out


# ------------------------------------------------------------------ chuva nos polos
def chuva():
    import exporta_clima as ec
    clima = json.loads((RAIZ / "dados/clima/clima.json").read_text())
    fases = {int(k): v for k, v in clima["fases_safra"].items()}
    out = []
    for p in POLOS:
        try:
            dias = ec.chuva_ponto(p[0], p[3], p[4])
            norm = ec.normal_diaria(dias)
            a = ec.analisar_ponto(p, dias, norm, fases)
            a["prev"] = ec.previsao(p[3], p[4])
            ini = date.fromisoformat(a["prev"]["d"][0]); fim = date.fromisoformat(a["prev"]["d"][-1])
            a["prev"]["tot"]["normal"] = round(ec.normal_periodo(norm, ini, fim))
            a.pop("enso_mes", None)
            a["curva"].pop("fases", None)
            out.append(a)
            print("  chuva", p[1], a["acc"]["safra"])
        except Exception as e:
            print("  chuva falhou", p[1], e)
        time.sleep(1.5)
    return out, clima["enso"].get("status")


# ------------------------------------------------------------------ montagem
def resumo_atual(r):
    """informe mais recente: avanço com províncias e delegações, estado e produção"""
    av = {}
    for c, ops in (r.get("avanco") or {}).items():
        for op, a in ops.items():
            if "provincias" not in a:
                continue
            provs = []
            for k, p in a["provincias"].items():
                if k == "TOTAL PAIS" or not p.get("area"):
                    continue
                provs.append({"nome": p["nome"], "area": p["area"], "atual": p["atual"][-1] if p.get("atual") else None,
                              "anterior": p["anterior"][-1] if p.get("anterior") else None,
                              "semana": (p["atual"][-1] - p["atual"][-2]) if p.get("atual") and len(p["atual"]) > 1 and None not in p["atual"][-2:] else None})
            provs.sort(key=lambda x: -x["area"])
            av.setdefault(c, {})[op] = {"semanas": a["semanas"], "total": a["provincias"].get("TOTAL PAIS"), "provincias": provs}
    est = {}
    for c, e in (r.get("estado") or {}).items():
        if not e.get("nacional"):
            continue
        # agrega delegações por província, ponderando pela área
        delegs = {}
        for op in ("plantio", "colheita"):
            delegs.update((((r.get("avanco") or {}).get(c) or {}).get(op) or {}).get("delegacoes", {}))
        nomes = {}
        for op in ("plantio", "colheita"):
            for kk, pp in ((((r.get("avanco") or {}).get(c) or {}).get(op) or {}).get("provincias") or {}).items():
                nomes[kk] = pp["nome"]
        pv = {}
        for k, v in e["delegacoes"].items():
            dg = delegs.get(k) or {}
            if not dg.get("area"):
                continue
            nome = dg.get("prov") or "OUTRAS"
            t = pv.setdefault(nome, {"area": 0, "estado": [0, 0, 0, 0], "seca": 0, "excesso": 0})
            t["area"] += dg["area"]
            for i in range(4):
                t["estado"][i] += v["estado"][i] * dg["area"]
            cods = v["umidade"].split("/")
            t["seca"] += dg["area"] * sum(1 for x in cods if x in ("S", "PS", "R")) / len(cods)
            t["excesso"] += dg["area"] * sum(1 for x in cods if x in ("E", "I")) / len(cods)
        provs = [{"nome": nomes.get(k, k.title()), "area": round(t["area"]), "estado": [round(x / t["area"], 1) for x in t["estado"]],
                  "seca": round(t["seca"] / t["area"] * 100), "excesso": round(t["excesso"] / t["area"] * 100)} for k, t in pv.items()]
        provs.sort(key=lambda x: -x["area"])
        est[c] = {"nacional": e["nacional"], "fases": e["fases"], "provincias": provs}
    return {"data": r["data"], "url": r.get("url"), "avanco": av, "estado": est, "producao": r.get("producao"), "serie": r.get("serie")}


def main():
    historico = "--historico" in sys.argv
    PASTA.mkdir(parents=True, exist_ok=True)
    saida_f = PASTA / "argentina.json"
    ant = json.loads(saida_f.read_text()) if saida_f.exists() else {}
    informes = [r for r in coletar_informes(historico) if "erro" not in r]
    ult = informes[-1]
    print("informe mais recente:", ult["data"])
    sa = series_avanco(informes)
    curvas = {}
    for c in PRINCIPAIS:
        for op, ser in (sa.get(c) or {}).items():
            s_at = max(ser)
            # só mostra operações em andamento ou terminadas há pouco
            ult_data = max(ser[s_at]); dias = (date.fromisoformat(ult["data"]) - date.fromisoformat(ult_data)).days
            if dias > 60:
                continue
            datas = sorted(ser[s_at])
            curvas.setdefault(c, {})[op] = {"safra": f"{s_at}/{str(s_at + 1)[2:]}", "atual": curva(ser, s_at), "anterior": curva(ser, s_at - 1),
                                           "media5": [[d, v] for d, v in zip(datas, media_safras(ser, s_at, datas)) if v is not None],
                                           "n_safras_media": sum(1 for s in range(s_at - 5, s_at) if len(ser.get(s) or {}) >= 3)}
    se = series_estado(informes)
    estado_hist = {c: {f"{s}/{str(s + 1)[2:]}": v for s, v in sorted(d.items())[-2:]} for c, d in se.items() if c in PRINCIPAIS}
    clima = json.loads((RAIZ / "dados/clima/clima.json").read_text())
    prodt = ant.get("produtividade")
    if "--produtividade" in sys.argv or not prodt or date.today().weekday() == 0:
        try:
            prodt = produtividade(clima["fases_safra"])
        except Exception as e:
            print("produtividade falhou:", e)
    b = bcr()
    hb = historico_bcr(b)
    try:
        polos, enso = chuva()
    except Exception as e:
        print("chuva falhou:", e); polos, enso = ant.get("chuva", []), None
    saida = {"atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "fontes": {"sagyp": "Secretaría de Agricultura, Ganadería y Pesca (Argentina), Estimaciones Agrícolas",
                        "bcr": "Bolsa de Comercio de Rosario, GEA", "usda": "USDA/FAS PSD", "chuva": "ERA5 e ECMWF via Open-Meteo"},
             "informe": resumo_atual(ult), "curvas": curvas, "estado_hist": estado_hist,
             "n_informes": len(informes), "primeiro_informe": informes[0]["data"],
             "bcr": b | {"historico": hb[-12:]}, "usda": usda(), "produtividade": prodt,
             "chuva": polos or ant.get("chuva", []), "enso": enso or (clima.get("enso") or {}).get("status")}
    saida_f.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    print("ok", saida_f, round(saida_f.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
