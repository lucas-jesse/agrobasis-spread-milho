"""Leitura do Informe Semanal de Estimaciones Agrícolas (Secretaría de Agricultura, Ganadería y Pesca da Argentina).

O informe sai às quintas-feiras em PDF. Daqui saem:
  - avanço de plantio e colheita por delegação, província e total do país (6 semanas + mesma data da safra anterior);
  - estado das lavouras (MB, B, R, M), fase e umidade do solo por delegação;
  - quadro de produção da última safra fechada e série de 10 anos de área e produção.
"""
import re
import unicodedata
from datetime import date

import pdfplumber

CULTIVOS = {"SOJA": "soja", "MAIZ": "milho", "TRIGO": "trigo", "GIRASOL": "girassol", "CEBADA": "cevada",
            "SORGO": "sorgo", "ALGODON": "algodao", "MANI": "amendoim", "ARROZ": "arroz"}
NUM = re.compile(r"^\d{1,3}(?:\.\d{3})+$|^\d+(?:,\d+)?$")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def chave(s):
    """nome normalizado para casar delegações entre tabelas"""
    s = sem_acento(s).upper().replace("GRAL ", "GENERAL ").replace("PCIA. ", "").replace("STGO.", "SANTIAGO DEL")
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s).split()).replace("DEL DEL", "DEL")


def num(t):
    if t in ("-", ""):
        return None
    return float(t.replace(".", "").replace(",", ".")) if "," in t else float(t.replace(".", ""))


def cultivo_de(titulo):
    t = sem_acento(titulo).upper()
    for k, v in CULTIVOS.items():
        if re.search(rf"\b{k}\b", t):
            return v
    return None


def data_do_informe(texto):
    m = re.search(r"al (\d{1,2}) de (\w+) de (\d{4})", texto)
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    if m and m.group(2).lower() in meses:
        return date(int(m.group(3)), meses.index(m.group(2).lower()) + 1, int(m.group(1)))
    return None


def semanas_iso(rotulos, ref):
    """'08/10' -> data completa, voltando um ano quando o mês é posterior ao do informe"""
    out = []
    for r in rotulos:
        d, m = map(int, r.split("/"))
        y = ref.year - (1 if m > ref.month + 1 else 0)
        out.append(date(y, m, d).isoformat())
    return out


# ------------------------------------------------------------------ avanço
def ler_avanco(linhas, ref):
    """linhas de todas as páginas de um mesmo quadro (cultura + operação)"""
    semanas = None
    for l in linhas:
        ds = re.findall(r"\b\d{2}/\d{2}\b", l)
        if len(ds) >= 3:
            semanas = ds
            break
    if not semanas:
        return None
    n = len(semanas)
    prov, pend, dele = {}, [], {}
    ult = None
    i = 0
    while i < len(linhas):
        l = linhas[i].strip()
        m = re.match(r"^(\d{2}/\d{2}) ([\d.]+)((?: [\d.,]+)*)$", l)
        if m and i + 1 < len(linhas):
            nome = linhas[i + 1].strip()
            atual = [num(x) for x in m.group(3).split()][:n]
            ant, area_ant = None, None
            if i + 2 < len(linhas):
                m2 = re.match(r"^(\d{2}/\d{2}) ([\d.]+)((?: [\d.,]+)*)$", linhas[i + 2].strip())
                if m2:
                    ant = [num(x) for x in m2.group(3).split()][:n]; area_ant = num(m2.group(2))
            reg = {"area": num(m.group(2)), "atual": atual, "area_ant": area_ant, "anterior": ant}
            k = "TOTAL PAIS" if "TOTAL" in sem_acento(nome).upper() else chave(nome)
            prov[k] = reg | {"nome": nome.title() if k != "TOTAL PAIS" else "Total do país"}
            if k != "TOTAL PAIS":
                for d in pend:
                    dele[d]["prov"] = k
            pend = []
            i += 3 if ant is not None else 2
            continue
        toks = l.split()
        # linha de continuação de delegação: "2ª 90.000" ou "T. fideo 3.000"
        mc = re.match(r"^(2ª|1ª|T\. ?fideo|T\. ?pan)\s+([\d.]+)", l)
        if mc and ult:
            dele[ult]["area"] = (dele[ult]["area"] or 0) + num(mc.group(2))
            if dele[ult].get("unica"):
                prov[dele[ult]["prov"]]["area"] += num(mc.group(2))
            i += 1
            continue
        j = len(toks)
        while j > 0 and NUM.match(toks[j - 1]):
            j -= 1
        nums = toks[j:]
        nome_t = [t for t in toks[:j] if t not in ("1ª", "2ª", "T.", "pan", "fideo")]
        if nums and nome_t and re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", " ".join(nome_t)) and not re.search(r"Hect|ÁREA|AREA|DELEG|CAMPA|Cifras", l):
            nome = " ".join(nome_t)
            area = num(nums[0]); pct = [num(x) for x in nums[1:]]
            k = chave(nome)
            par = re.search(r"\((.*)\)", nome)
            if par:  # "CHACO (Charata)", "STGO. ESTERO (Quimilí)": a delegação é o que está entre parênteses
                k = {"R S PENA": "ROQUE SAENZ PENA"}.get(chave(par.group(1)), chave(par.group(1)))
            if nome_t[0].isupper() and len(nome_t[0]) > 1 and sem_acento(nome_t[0]).replace(".", "").isalpha():
                # província com uma linha só (ex.: SAN LUIS, CORRIENTES)
                pr = re.sub(r"\s*\(.*\)", "", nome).replace("STGO. ESTERO", "SANTIAGO DEL ESTERO").replace("STGO.ESTERO", "SANTIAGO DEL ESTERO")
                prov.setdefault(chave(pr), {"area": 0, "atual": None, "area_ant": None, "anterior": None, "nome": pr.title().replace(" Del ", " del ")})
                prov[chave(pr)]["area"] += area or 0
                dele[k] = {"nome": nome, "area": area, "prov": chave(pr), "pct": pct[-n:] if len(pct) <= n else None, "unica": True}
            else:
                dele[k] = {"nome": nome, "area": area, "prov": None, "pct": pct if len(pct) <= n else None}
                pend.append(k)
            ult = k
        i += 1
    return {"semanas": semanas_iso(semanas, ref), "provincias": prov, "delegacoes": dele}


# ------------------------------------------------------------------ estado e umidade
def ler_estado(linhas, delegs):
    cab = next((l for l in linhas if re.search(r"\bMB B R M\b", l)), None)
    if not cab:
        return None
    toks = cab.split(); nfen = toks.index("MB")
    fen = toks[:nfen]
    alvo = sorted(delegs, key=len, reverse=True)
    out = {}
    for l in linhas:
        t = l.split()
        if len(t) < nfen + 5:
            continue
        vals = t[-(nfen + 5):-1]; um = t[-1]
        if not all(v == "-" or v.isdigit() for v in vals) or not re.match(r"^[A-Z]{1,2}(/[A-Z]{1,2})*$", um):
            continue
        nome = " ".join(t[:-(nfen + 5)])
        if not nome:
            continue
        k = chave(nome)
        hit = next((d for d in alvo if k == d or k.endswith(" " + d)), None)
        est = [int(v) if v != "-" else 0 for v in vals[nfen:]]
        if sum(est) == 0:
            continue
        out[hit or k] = {"fase": dict(zip(fen, [int(v) if v != "-" else 0 for v in vals[:nfen]])),
                         "estado": est, "umidade": um, "casou": bool(hit)}
    return {"fases": fen, "delegacoes": out}


def nacional_estado(est, delegs):
    """média do estado ponderada pela área de cada delegação"""
    s = [0.0] * 4; a = 0.0
    um = {"seca": 0.0, "adequada": 0.0, "excesso": 0.0}
    fase = {}
    for k, v in est["delegacoes"].items():
        area = (delegs.get(k) or {}).get("area")
        if not area:
            continue
        a += area
        for i in range(4):
            s[i] += v["estado"][i] * area
        cods = v["umidade"].split("/")
        for c in cods:
            g = "seca" if c in ("S", "PS", "R") else "excesso" if c in ("E", "I") else "adequada"
            um[g] += area / len(cods)
        for f, p in v["fase"].items():
            fase[f] = fase.get(f, 0) + p * area
    if not a:
        return None
    return {"estado": [round(x / a, 1) for x in s], "umidade": {k: round(v / a * 100, 1) for k, v in um.items()},
            "fase": {k: round(v / a, 1) for k, v in fase.items()}, "area_coberta": round(a)}


# ------------------------------------------------------------------ produção
def ler_producao(linhas):
    camp = next((re.search(r"(\d{4}/\d{4})", l).group(1) for l in linhas if "CAMPAÑA" in l and re.search(r"\d{4}/\d{4}", l)), None)
    out = {}
    for l in linhas:
        t = l.split()
        if len(t) >= 7 and cultivo_de(t[0]) and NUM.match(t[-1]):
            c = cultivo_de(" ".join(t[:-6]))
            if c and c not in out:
                v = [num(x) if x != "-" else None for x in t[-6:]]
                out[c] = {"semeada_mil_ha": v[0], "colhida_mil_ha": v[2], "rend_qq_ha": v[4], "prod_mil_t": v[5]}
    return {"campanha": camp, "cultivos": out} if out else None


def ler_serie(linhas):
    cab = next((l for l in linhas if l.startswith("CULTIVOS") and re.search(r"\d{4}/\d{4}", l)), None)
    if not cab:
        return None
    camps = [c.rstrip("*") for c in re.findall(r"\d{4}/\d{4}\*?", cab)]
    out = {}
    for l in linhas:
        t = l.split()
        if len(t) > len(camps) and all(NUM.match(x) for x in t[-len(camps):]):
            c = cultivo_de(" ".join(t[:-len(camps)]))
            if c and c not in out and "Subtotal" not in l:
                out[c] = [num(x) for x in t[-len(camps):]]
    return {"campanhas": camps, "cultivos": out}


# ------------------------------------------------------------------ informe completo
def ler_informe(caminho):
    with pdfplumber.open(caminho) as pdf:
        paginas = [(p.extract_text() or "") for p in pdf.pages]
    ref = None
    for t in paginas[:3]:
        ref = ref or data_do_informe(t)
    if not ref:
        raise ValueError("data do informe não encontrada")
    blocos = {}
    est_pag = []
    prod = serie_area = serie_prod = None
    for t in paginas:
        ls = [l for l in t.split("\n") if l.strip()]
        txt = sem_acento(t).upper()
        m = re.search(r"AVANCE DE LA (SIEMBRA|COSECHA) DE ([A-Z ]+)", txt)
        if m:
            op = "plantio" if m.group(1) == "SIEMBRA" else "colheita"
            c = cultivo_de(m.group(2))
            if c:
                blocos.setdefault((c, op), []).extend(ls)
            continue
        if "HUMEDAD Y ESTADO" in txt or "HUMEDAD DEL SUELO Y" in txt:
            c = next((cultivo_de(l) for l in ls[:8] if cultivo_de(l) and len(l.split()) <= 3), None)
            if c:
                est_pag.append((c, ls))
            continue
        if "PRODUCCION DE CULTIVOS EN LA REPUBLICA" in txt:
            prod = ler_producao(ls)
        elif "AREA SEMBRADA DE GRANOS" in txt:
            serie_area = ler_serie(ls)
        elif "VOLUMENES DE PRODUCCION" in txt:
            serie_prod = ler_serie(ls)
    avanco = {}
    for (c, op), ls in blocos.items():
        try:
            a = ler_avanco(ls, ref)
        except Exception as e:  # um quadro com layout novo não derruba o resto
            a = {"erro": repr(e)[:200]}
        if a:
            avanco.setdefault(c, {})[op] = a
    estado = {}
    for c, ls in est_pag:
        delegs = {}
        for op in ("plantio", "colheita"):
            for k, v in ((avanco.get(c) or {}).get(op) or {}).get("delegacoes", {}).items():
                delegs.setdefault(k, v)
        e = ler_estado(ls, delegs)
        if e:
            e["nacional"] = nacional_estado(e, delegs)
            estado[c] = e
    return {"data": ref.isoformat(), "avanco": avanco, "estado": estado, "producao": prod,
            "serie": {"area_ha": serie_area, "producao_t": serie_prod}}


if __name__ == "__main__":
    import json, sys
    r = ler_informe(sys.argv[1])
    print(json.dumps(r, ensure_ascii=False)[:3000])
