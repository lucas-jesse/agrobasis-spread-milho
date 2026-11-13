"""Progresso de plantio e colheita no Brasil (Conab, semanal), para o dashboard "Plantio e Colheita Brasil" do AgroBasis.

Fonte oficial: Conab, "Progresso de Safra" (gov.br/conab > Informações agropecuárias > Safras > Progresso de safra).
Toda semana a Conab publica uma pasta "acompanhamento-das-lavouras-DD-MM-a-DD-MM-AA" com a planilha
"plantio-e-colheita-DD-MM-a-DD-MM(.xlsx)". Cada aba traz, por cultura e operação (semeadura ou colheita), o percentual
da área de cada estado acompanhado na semana atual, na semana anterior, na mesma semana do ano passado e a média de 5 anos,
além do agregado dos estados acompanhados (que a Conab divulga como o número do Brasil).

Cada planilha é convertida uma única vez para dados/progresso/semanas/<pasta>.json (cache). A saída do dashboard é
dados/progresso/progresso.json, com uma série por cultura, operação e safra.

Uso: python exporta_progresso.py [--local PASTA]  (PASTA com planilhas .xlsx, para testar sem rede)
"""
import argparse
import json
import re
import time
import unicodedata
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import openpyxl
import requests

PASTA = Path("dados/progresso"); SEMANAS = PASTA / "semanas"
BASE = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/progresso-de-safra"
UF_NOME = {
    "acre": "AC", "alagoas": "AL", "amazonas": "AM", "amapa": "AP", "bahia": "BA", "ceara": "CE", "distrito federal": "DF",
    "espirito santo": "ES", "goias": "GO", "maranhao": "MA", "minas gerais": "MG", "mato grosso do sul": "MS",
    "mato grosso": "MT", "para": "PA", "paraiba": "PB", "pernambuco": "PE", "piaui": "PI", "parana": "PR",
    "rio de janeiro": "RJ", "rio grande do norte": "RN", "rondonia": "RO", "roraima": "RR", "rio grande do sul": "RS",
    "santa catarina": "SC", "sergipe": "SE", "sao paulo": "SP", "tocantins": "TO",
}
# nome normalizado da cultura na planilha -> (slug, nome no painel, ordem)
CULTURAS = [
    (r"^soja", "soja", "Soja"),
    (r"^milho\s*1", "milho1", "Milho 1ª safra"),
    (r"^milho\s*2", "milho2", "Milho 2ª safra"),
    (r"^milho\s*3", "milho3", "Milho 3ª safra"),
    (r"^algod", "algodao", "Algodão"),
    (r"^arroz", "arroz", "Arroz"),
    (r"^feij\w*\s*1", "feijao1", "Feijão 1ª safra"),
    (r"^feij\w*\s*2", "feijao2", "Feijão 2ª safra"),
    (r"^feij\w*\s*3", "feijao3", "Feijão 3ª safra"),
    (r"^trigo", "trigo", "Trigo"),
    (r"^sorgo", "sorgo", "Sorgo"),
    (r"^amendoim", "amendoim", "Amendoim"),
    (r"^girassol", "girassol", "Girassol"),
    (r"^cevada", "cevada", "Cevada"),
    (r"^aveia", "aveia", "Aveia"),
    (r"^canola", "canola", "Canola"),
]

sessao = requests.Session()
sessao.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").lower().strip()


def baixar(url, tentativas=3):
    for i in range(tentativas):
        try:
            r = sessao.get(url, timeout=120); r.raise_for_status(); return r
        except requests.RequestException as e:
            if i == tentativas - 1:
                raise
            print(f"  nova tentativa ({e})"); time.sleep(5 * (i + 1))


# ---------------------------------------------------------------- descoberta das pastas semanais
def listar_pastas():
    """Pastas semanais 'acompanhamento-das-lavouras-DD-MM-a-DD-MM-AA', com a data final da semana."""
    pastas = {}
    for inicio in range(0, 400, 20):
        html = baixar(f"{BASE}?b_start:int={inicio}").text
        novos = 0
        for nome in re.findall(re.escape(BASE) + r"/(acompanhamento-das-lavouras-[0-9]{2}-[0-9]{2}-a-[0-9]{2}-[0-9]{2}-[0-9]{2})\b", html):
            if nome not in pastas:
                d1, m1, d2, m2, a = re.findall(r"\d+", nome)[:5]
                fim = date(2000 + int(a), int(m2), int(d2))
                pastas[nome] = fim; novos += 1
        if "b_start:int=%d" % (inicio + 20) not in html:
            break
    return dict(sorted(pastas.items(), key=lambda kv: kv[1]))


def baixar_planilha(pasta):
    """Planilha de plantio e colheita da pasta (o link termina em /view; o arquivo pode não ter extensão)."""
    html = baixar(f"{BASE}/{pasta}").text
    links = sorted(set(re.findall(re.escape(f"{BASE}/{pasta}/") + r"(plantio-e-colheita[^\"'/?#]*)", html)))
    if not links:
        return None
    for nome in links:
        for url in (f"{BASE}/{pasta}/{nome}/@@download/file", f"{BASE}/{pasta}/{nome}"):
            try:
                r = baixar(url, tentativas=2)
            except requests.RequestException:
                continue
            if r.content[:2] == b"PK":
                return r.content
    return None


# ---------------------------------------------------------------- leitura da planilha
def num(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        t = v.strip().replace("%", "").replace(",", ".")
        try:
            return float(t)
        except ValueError:
            return None
    return None


def como_data(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", v.strip())
        if m:
            a = int(m.group(3)); a = a + 2000 if a < 100 else a
            return date(a, int(m.group(2)), int(m.group(1)))
    return None


def cultura_de(titulo):
    t = sem_acento(titulo)
    for padrao, slug, nome in CULTURAS:
        if re.search(padrao, t):
            return slug, nome
    slug = re.sub(r"[^a-z0-9]+", "", t.split("-")[0])
    return slug, titulo.split("-")[0].strip()


def ler_planilha(conteudo):
    """Lista de tabelas: {cultura, nome, safra, op, cobertura, d, d_ant, d_aa, linhas: {UF: [aa, ant, atual, m5]}, br: [...]}"""
    wb = openpyxl.load_workbook(BytesIO(conteudo), data_only=True, read_only=True)
    tabelas = []
    for ws in wb.worksheets:
        linhas = [list(r) for r in ws.iter_rows(values_only=True)]
        cult = None; cobertura = None; op = None; i = 0
        while i < len(linhas):
            textos = [str(v).strip() for v in linhas[i] if isinstance(v, str) and v.strip()]
            primeiro = textos[0] if textos else ""
            m = re.match(r"^(.+?)\s*[-–]\s*Safra\s*(\d{4}(?:\s*/\s*\d{2,4})?)", primeiro, re.I)
            if m:
                slug, nome = cultura_de(m.group(1))
                safra = re.sub(r"\s", "", m.group(2))
                if re.fullmatch(r"\d{4}/\d{4}", safra):
                    safra = safra[:5] + safra[7:]
                cult = (slug, nome, safra); cobertura = None; op = None; i += 1; continue
            m = re.search(r"Esses\s+(\d+)\s+estados\s+correspondem\s+a\s+([\d.,]+)\s*%", primeiro, re.I)
            if m:
                cobertura = {"estados": int(m.group(1)), "pct_area": float(m.group(2).replace(",", "."))}
                i += 1; continue
            p = sem_acento(primeiro)
            if p.startswith(("semeadura", "plantio")):
                op = "plantio"; i += 1; continue
            if p.startswith("colheita"):
                op = "colheita"; i += 1; continue
            if cult and op and (p.startswith("estado") or p.startswith("unidade da federa") or p == "uf"):
                cab = linhas[i]
                col_nome = next(j for j, v in enumerate(cab) if isinstance(v, str) and v.strip() == primeiro)
                col_m5 = next((j for j, v in enumerate(cab) if isinstance(v, str) and "dia" in sem_acento(v)), None)
                # linha com as datas (até 3 linhas abaixo do cabeçalho)
                k = i + 1; datas = {}
                while k < min(i + 4, len(linhas)):
                    ds = {j: como_data(v) for j, v in enumerate(linhas[k]) if como_data(v)}
                    if len(ds) >= 2:
                        datas = ds; break
                    k += 1
                if not datas:
                    i += 1; continue
                cols = sorted(datas)  # [ano anterior, semana anterior, semana atual]
                if len(cols) < 3:
                    i = k + 1; continue
                c_aa, c_ant, c_at = cols[0], cols[-2], cols[-1]
                if col_m5 is None:
                    col_m5 = c_at + 1
                tab = {"cultura": cult[0], "nome": cult[1], "safra": cult[2], "op": op, "cobertura": cobertura,
                       "d": datas[c_at].isoformat(), "d_ant": datas[c_ant].isoformat(), "d_aa": datas[c_aa].isoformat(),
                       "ufs": {}, "br": None}
                fator = None
                k += 1
                while k < len(linhas):
                    r = linhas[k]
                    nome = r[col_nome] if col_nome < len(r) else None
                    if not isinstance(nome, str) or not nome.strip():
                        break
                    vals = [num(r[c]) if c < len(r) else None for c in (c_aa, c_ant, c_at, col_m5)]
                    if fator is None and any(v is not None for v in vals):
                        fator = 100.0 if max(v for v in vals if v is not None) <= 1.0001 else 1.0
                    vals = [None if v is None else round(v * (fator or 100.0), 2) for v in vals]
                    n = sem_acento(nome)
                    if re.match(r"^\d+\s+estados", n) or n.startswith(("brasil", "total")):
                        tab["br"] = vals; k += 1; break
                    uf = UF_NOME.get(re.sub(r"\s+", " ", n))
                    if uf:
                        tab["ufs"][uf] = vals
                    k += 1
                if tab["ufs"]:
                    tabelas.append(tab)
                i = k; continue
            i += 1
    return tabelas


# ---------------------------------------------------------------- montagem da saída
def montar(semanas):
    """semanas: lista de listas de tabelas (uma por planilha). Série por cultura/op/safra, sem duplicar datas."""
    series = {}; nomes = {}; cob = {}
    for tabs in semanas:
        for t in tabs:
            chave = (t["cultura"], t["op"], t["safra"])
            nomes[t["cultura"]] = t["nome"]
            if t["cobertura"]:
                cob[chave] = t["cobertura"]
            s = series.setdefault(chave, {})
            ufs = sorted(t["ufs"])
            s[t["d"]] = {
                "d": t["d"], "d_aa": t["d_aa"],
                "br": t["br"][2] if t["br"] else None,
                "br_ant": t["br"][1] if t["br"] else None,
                "br_aa": t["br"][0] if t["br"] else None,
                "br_m5": t["br"][3] if t["br"] else None,
                "ufs": {u: t["ufs"][u][2] for u in ufs},
                "ufs_aa": {u: t["ufs"][u][0] for u in ufs},
                "ufs_m5": {u: t["ufs"][u][3] for u in ufs},
            }
    saida = {}
    for (cult, op, safra), pontos in series.items():
        c = saida.setdefault(cult, {"nome": nomes[cult], "ops": {}})
        c["ops"].setdefault(op, {})[safra] = {
            "cobertura": cob.get((cult, op, safra)),
            "semanas": [pontos[d] for d in sorted(pontos)],
        }
    ordem = [slug for _, slug, _ in CULTURAS]
    return {k: saida[k] for k in sorted(saida, key=lambda s: (ordem.index(s) if s in ordem else 99, s))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--local"); args = ap.parse_args()
    SEMANAS.mkdir(parents=True, exist_ok=True)
    if args.local:
        for f in sorted(Path(args.local).glob("*.xlsx")):
            tabs = ler_planilha(f.read_bytes())
            (SEMANAS / (f.stem + ".json")).write_text(json.dumps(tabs, ensure_ascii=False))
            print(f.name, len(tabs), "tabelas")
    else:
        pastas = listar_pastas()
        print(len(pastas), "pastas semanais")
        hoje = date.today()
        for pasta, fim in pastas.items():
            alvo = SEMANAS / f"{pasta}.json"
            # semanas recentes podem ser corrigidas: rebaixa as das últimas 3 semanas
            if alvo.exists() and (hoje - fim).days > 21:
                continue
            try:
                xlsx = baixar_planilha(pasta)
            except requests.RequestException as e:
                print(f"  {pasta}: falha ({e})"); continue
            if not xlsx:
                print(f"  {pasta}: sem planilha"); continue
            try:
                tabs = ler_planilha(xlsx)
            except Exception as e:  # planilha fora do padrão: registra e segue
                print(f"  {pasta}: erro de leitura ({e})"); continue
            if tabs:
                alvo.write_text(json.dumps(tabs, ensure_ascii=False, separators=(",", ":")))
            print(f"  {pasta}: {len(tabs)} tabelas")
            time.sleep(0.5)

    semanas = [json.loads(f.read_text()) for f in sorted(SEMANAS.glob("*.json"))]
    culturas = montar(semanas)
    ultima = max((s["d"] for c in culturas.values() for o in c["ops"].values() for sf in o.values() for s in sf["semanas"]),
                 default=None)
    saida = {"fonte": "Conab, Progresso de Safra (semanal)", "url": BASE, "ultima_semana": ultima, "culturas": culturas}
    (PASTA / "progresso.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    print("ultima semana:", ultima, "| culturas:", ", ".join(f"{k}({'/'.join(v['ops'])})" for k, v in culturas.items()))


if __name__ == "__main__":
    main()
