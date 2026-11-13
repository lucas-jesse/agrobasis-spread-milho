"""Safra de grãos da Conab por estado, para o dashboard "Safra Brasil (Conab)" do AgroBasis.

Fontes oficiais (Conab):
1. Boletim mensal da safra de grãos: planilha "site_previsao_de_safra-por_produto-<mês>-<ano>.xlsx" de cada levantamento,
   com área, produtividade e produção por UF da safra atual e da anterior. Os levantamentos são descobertos na página
   do boletim (gov.br/conab) e convertidos uma única vez para dados/conab/lev/<safra>_<n>.json.
2. Portal de Informações da Conab: SerieHistoricaGraos.txt (série por UF desde 1976/77) e LevantamentoGraos.txt
   (todas as estimativas mensais por UF desde 2017/18), usados para o histórico e para a trajetória das revisões.

Saída (lida pelo dashboard):
- dados/conab/<produto>.json: levantamentos da safra atual por UF, histórico por UF e Brasil, trajetória das revisões;
- dados/conab/resumo.json: Brasil de cada produto no último levantamento;
- dados/conab/br_uf.json: contorno simplificado dos estados (gerado à parte, não muda).

Uso: python exporta_conab.py [--local PASTA]  (PASTA com as planilhas e os .txt, para testar sem rede)
"""
import argparse
import csv
import io
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl
import requests

BRT = timezone(timedelta(hours=-3))
PASTA = Path("dados/conab"); LEV = PASTA / "lev"
BOLETIM = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/safra-de-graos/boletim-da-safra-de-graos"
PORTAL = "https://portaldeinformacoes.conab.gov.br/downloads/arquivos"
MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
       "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
REGIAO = {"NORTE": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "NORDESTE": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
          "CENTRO-OESTE": ["DF", "GO", "MS", "MT"], "SUDESTE": ["ES", "MG", "RJ", "SP"], "SUL": ["PR", "RS", "SC"]}

# produto: (nome, aba da planilha, (produto na série do portal, filtro de safra ou None = soma das safras), inverno)
PRODUTOS = {
    "graos": ("Total de grãos", "Brasil total por UF", None, False),
    "soja": ("Soja", "Soja", ("SOJA", None), False),
    "milho": ("Milho total", "Milho Total", ("MILHO", None), False),
    "milho1": ("Milho 1ª safra", "Milho 1a", ("MILHO", "1ª SAFRA"), False),
    "milho2": ("Milho 2ª safra", "Milho 2a", ("MILHO", "2ª SAFRA"), False),
    "trigo": ("Trigo", "Trigo", ("TRIGO", None), True),
    "algodao": ("Algodão em pluma", "Algodao em Pluma", ("ALGODAO EM PLUMA", None), False),
    "arroz": ("Arroz", "Arroz Total", ("ARROZ", None), False),
    "feijao": ("Feijão total", "Feijão Total", ("FEIJAO", None), False),
    "sorgo": ("Sorgo", "Sorgo", ("SORGO GRANIFERO", None), False),
}
ANOS_UF = 20  # safras com detalhe por UF no histórico

sessao = requests.Session(); sessao.headers["User-Agent"] = "Mozilla/5.0 (AgroBasis; agrobasis.com.br)"


def baixar(url, tentativas=3):
    for i in range(tentativas):
        try:
            r = sessao.get(url, timeout=180); r.raise_for_status(); return r.content
        except requests.RequestException as e:
            print("falha", url, e); time.sleep(10 * (i + 1))
    raise RuntimeError(f"não consegui baixar {url}")


def r1(v, c=1):
    return None if v is None else round(float(v), c)


# ------------------------------------------------------------------ planilha do levantamento
def ler_aba(ws):
    """linhas UF/região/Brasil de uma aba de produto: área (mil ha), produtividade (kg/ha), produção (mil t)"""
    linhas = [list(r) for r in ws.iter_rows(values_only=True)]
    cab = next(i for i, r in enumerate(linhas) if r and any(isinstance(c, str) and c.strip().upper().startswith("REGIÃO/UF") for c in r))
    safras = [c for c in linhas[cab + 1] if isinstance(c, str) and c.startswith("Safra")]
    out = {}
    for r in linhas[cab + 3:]:
        v = [c for c in r if c is not None]
        if not v or not isinstance(v[0], str):
            continue
        nome = v[0].strip().upper()
        if nome.startswith(("FONTE", "NOTA", "LEGENDA")):
            break
        nums = [float(x) if isinstance(x, (int, float)) else None for x in v[1:]]
        nums += [None] * (9 - len(nums))
        if len(v) < 8:  # linha zerada sem as colunas de variação (ex.: RN 0 0 0 ...)
            nums = [0.0] * 9
        out[nome] = {"area": [r1(nums[0]), r1(nums[1])], "prod": [r1(nums[3], 0), r1(nums[4], 0)], "producao": [r1(nums[6]), r1(nums[7])]}
    return [s.replace("Safra ", "") for s in safras[:2]], out


def ler_levantamento(conteudo, n, mes, ano):
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), data_only=True, read_only=True)
    lev = {"n": n, "mes": mes, "ano": ano, "produtos": {}}
    for slug, (nome, aba, _, _) in PRODUTOS.items():
        if aba not in wb.sheetnames:
            print("aba ausente:", aba); continue
        safras, linhas = ler_aba(wb[aba])
        lev["produtos"][slug] = {"safras": safras, "linhas": linhas}
    return lev


def descobrir(local=None):
    """lista (safra, n, mês, ano, url) dos levantamentos publicados no boletim"""
    html = (Path(local) / "boletim.html").read_text(encoding="utf-8") if local else baixar(BOLETIM).decode("utf-8", "ignore")
    achados = set(re.findall(r'href="([^"]*/(\d+)o-levantamento-safra-(\d{4})-(\d{2})/site_previsao_de_safra-por_produto-([a-z]{3})-(\d{4})\.xlsx)', html))
    return sorted({(f"{a}/{b}", int(n), MESES[m], int(y), u) for u, n, a, b, m, y in achados})


# ------------------------------------------------------------------ portal: séries históricas e revisões
def ler_txt(conteudo):
    txt = conteudo.decode("latin-1")
    linhas = list(csv.reader(io.StringIO(txt), delimiter=";"))
    cab = [c.strip() for c in linhas[0]]
    return [dict(zip(cab, [c.strip() for c in r])) for r in linhas[1:] if len(r) >= len(cab)]


def num(s):
    try:
        return float(s.replace(",", "."))
    except (ValueError, AttributeError):
        return 0.0


def agrega(regs, produto, filtro, chave_ano, extra=None):
    """soma área e produção por (ano[, extra], UF) para um produto (e uma safra, se houver filtro)"""
    acc = {}
    for r in regs:
        if r["produto"] != produto:
            continue
        sf = r.get("dsc_safra_previsao") or r.get("safra")
        if filtro and sf != filtro:
            continue
        k = (r[chave_ano],) + ((r[extra],) if extra else ()) + (r["uf"],)
        a = acc.setdefault(k, [0.0, 0.0])
        a[0] += num(r["area_plantada_mil_ha"]); a[1] += num(r["producao_mil_t"])
    return acc


def historico(serie, produto, filtro):
    acc = agrega(serie, produto, filtro, "ano_agricola")
    anos = sorted({k[0] for k in acc}, key=lambda s: (int(s[:4]), s))
    br = {"area": [], "producao": [], "prod": []}
    ufs = {}
    for a in anos:
        ta = sum(v[0] for k, v in acc.items() if k[0] == a); tp = sum(v[1] for k, v in acc.items() if k[0] == a)
        br["area"].append(r1(ta)); br["producao"].append(r1(tp)); br["prod"].append(r1(tp / ta * 1000, 0) if ta else None)
    for uf in UFS:
        ufs[uf] = {m: [] for m in ("area", "producao", "prod")}
        for a in anos[-ANOS_UF:]:
            v = acc.get((a, uf), [0.0, 0.0])
            ufs[uf]["area"].append(r1(v[0])); ufs[uf]["producao"].append(r1(v[1]))
            ufs[uf]["prod"].append(r1(v[1] / v[0] * 1000, 0) if v[0] else None)
    return {"anos": anos, "brasil": br, "anos_uf": anos[-ANOS_UF:], "ufs": ufs}


def revisoes(levs, produto, filtro):
    """produção Brasil em cada levantamento de cada ano-safra (mil t)"""
    acc = agrega(levs, produto, filtro, "ano_agricola", extra="id_levantamento")
    out = {}
    for (a, n, uf), v in acc.items():
        out.setdefault(a, {}).setdefault(int(n), 0.0)
        out[a][int(n)] += v[1]
    return {a: [r1(d[k]) for k in sorted(d)] for a, d in sorted(out.items(), key=lambda x: (int(x[0][:4]), x[0]))}


# ------------------------------------------------------------------ montagem
def regioes_de(linhas, i):
    return {r: linhas[r]["producao"][i] for r in REGIAO if r in linhas}


def rotulo(s):
    """'25/26' -> '2025/26'; '2026' fica igual"""
    return f"20{s}" if re.fullmatch(r"\d{2}/\d{2}", s) else s


def completar(hist, safra_ant, L, inverno=False):
    """garante no histórico a safra anterior com os números da planilha mais recente (o portal atualiza com atraso).
    Nas culturas de inverno a coluna da safra anterior da planilha nem sempre bate com o fechamento do portal:
    ali o portal prevalece e a planilha só preenche o ano se ele ainda não existir."""
    a = rotulo(safra_ant); b = L.get("BRASIL")
    if not b or (inverno and a in hist["anos"]):
        return
    if a not in hist["anos"]:
        hist["anos"].append(a)
        for m in ("area", "producao", "prod"): hist["brasil"][m].append(None)
    i = hist["anos"].index(a)
    hist["brasil"]["area"][i], hist["brasil"]["producao"][i], hist["brasil"]["prod"][i] = b["area"][0], b["producao"][0], b["prod"][0]
    if a not in hist["anos_uf"]:
        hist["anos_uf"].append(a)
        for uf in hist["ufs"]:
            for m in ("area", "producao", "prod"): hist["ufs"][uf][m].append(None)
        if len(hist["anos_uf"]) > ANOS_UF:
            hist["anos_uf"].pop(0)
            for uf in hist["ufs"]:
                for m in ("area", "producao", "prod"): hist["ufs"][uf][m].pop(0)
    j = hist["anos_uf"].index(a)
    for uf in hist["ufs"]:
        if uf in L:
            for m in ("area", "producao", "prod"): hist["ufs"][uf][m][j] = L[uf][m][0]


def montar(slug, levs_atuais, hist, rev):
    nome, aba, _, inverno = PRODUTOS[slug]
    ult = levs_atuais[-1]
    p = ult["produtos"][slug]; L = p["linhas"]
    completar(hist, p["safras"][0], L, inverno)
    out = {
        "produto": nome, "slug": slug, "inverno": inverno,
        "safra_atual": rotulo(p["safras"][1]), "safra_anterior": rotulo(p["safras"][0]),
        "levantamento": {"n": ult["n"], "mes": ult["mes"], "ano": ult["ano"]},
        "unidades": {"area": "mil ha", "prod": "kg/ha", "producao": "mil t"},
        "ufs": {uf: L[uf] for uf in UFS if uf in L},
        "regioes": {r: L[r] for r in REGIAO if r in L},
        "brasil": L.get("BRASIL"),
        # mesma safra, levantamento a levantamento (revisões da safra atual)
        "levantamentos": [{"n": lv["n"], "mes": lv["mes"], "ano": lv["ano"],
                           "brasil": lv["produtos"][slug]["linhas"].get("BRASIL"),
                           "ufs": {uf: lv["produtos"][slug]["linhas"][uf]["producao"][1] for uf in UFS if uf in lv["produtos"][slug]["linhas"]}}
                          for lv in levs_atuais if slug in lv["produtos"]],
        "historico": hist, "revisoes": rev,
        "fonte": "Conab, Acompanhamento da Safra Brasileira de Grãos e Portal de Informações (séries históricas)",
    }
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--local"); args = ap.parse_args()
    LEV.mkdir(parents=True, exist_ok=True)
    lista = descobrir(args.local)
    if not lista:
        raise SystemExit("nenhum levantamento encontrado na página do boletim")
    safra_atual = max(l[0] for l in lista)
    print("levantamentos da safra", safra_atual, [l[1] for l in lista if l[0] == safra_atual])
    levs = []
    for safra, n, mes, ano, url in [l for l in lista if l[0] == safra_atual]:
        arq = LEV / f"{safra.replace('/', '-')}_{n:02d}.json"
        if not arq.exists():
            conteudo = (Path(args.local) / Path(url).name).read_bytes() if args.local else baixar(url)
            arq.write_text(json.dumps(ler_levantamento(conteudo, n, mes, ano), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print("novo levantamento:", safra, n)
        levs.append(json.loads(arq.read_text(encoding="utf-8")))
    levs.sort(key=lambda l: l["n"])
    src = (lambda f: (Path(args.local) / f).read_bytes()) if args.local else (lambda f: baixar(f"{PORTAL}/{f}"))
    serie = ler_txt(src("SerieHistoricaGraos.txt")); levtxt = ler_txt(src("LevantamentoGraos.txt"))
    resumo = {"safra": safra_atual,
              "levantamento": {"n": levs[-1]["n"], "mes": levs[-1]["mes"], "ano": levs[-1]["ano"]}, "produtos": {}}
    for slug, (nome, aba, fonte_hist, inverno) in PRODUTOS.items():
        if slug not in levs[-1]["produtos"]:
            continue
        if fonte_hist:
            if inverno:  # rótulos do portal para o ano da colheita, como no boletim
                s_ = [dict(r, ano_agricola=ano_inverno(r["ano_agricola"])) for r in serie]
                l_ = [dict(r, ano_agricola=ano_inverno(r["ano_agricola"])) for r in levtxt]
                hist = historico(s_, *fonte_hist); rev = revisoes(l_, *fonte_hist)
            else:
                hist = historico(serie, *fonte_hist); rev = revisoes(levtxt, *fonte_hist)
        else:  # total de grãos: soma dos produtos que a Conab inclui no total
            hist = historico_total(serie); rev = revisoes_total(levtxt)
        d = montar(slug, levs, hist, rev)
        (PASTA / f"{slug}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        b = d["brasil"]; ant = d["levantamentos"][-2]["brasil"] if len(d["levantamentos"]) > 1 else None
        resumo["produtos"][slug] = {"produto": nome, "safra": d["safra_atual"], "producao": b["producao"][1], "producao_ant": b["producao"][0],
                                    "area": b["area"][1], "prod": b["prod"][1], "producao_lev_ant": ant["producao"][1] if ant else None}
        print(slug, d["safra_atual"], b["producao"])
    (PASTA / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")


TOTAL_EXCLUI = {"ALGODAO EM PLUMA", "ALGODAO EM CAROCO"}  # o total da Conab usa o caroço de algodão


def safra_de(ano):
    """No portal, as culturas de inverno vêm com o ano de início do ciclo: "2025" é o trigo colhido em 2026, que o
    boletim chama de "Safra 2026" e soma no total do ano-safra 2025/26."""
    return f"{ano}/{int(ano[2:]) + 1:02d}" if re.fullmatch(r"\d{4}", ano) else ano


def ano_inverno(ano):
    """rótulo do portal ("2025") para o rótulo do boletim ("2026"), o ano da colheita"""
    return str(int(ano) + 1) if re.fullmatch(r"\d{4}", ano) else ano


def historico_total(serie):
    regs = [dict(r, produto="TOTAL", ano_agricola=safra_de(r["ano_agricola"])) for r in serie if r["produto"] not in TOTAL_EXCLUI]
    return historico(regs, "TOTAL", None)


def revisoes_total(levtxt):
    regs = [dict(r, produto="TOTAL", ano_agricola=safra_de(r["ano_agricola"])) for r in levtxt if r["produto"] not in TOTAL_EXCLUI]
    return revisoes(regs, "TOTAL", None)


if __name__ == "__main__":
    main()
