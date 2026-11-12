"""Resumo leve (dados/painel.json) para a página /dashboards/ do AgroBasis.

Lê os arquivos que os outros workflows já geram e extrai, para cada dashboard, um número do dia,
uma variação, uma linha de tendência curta e a data do dado. A página fica com um único arquivo
pequeno para baixar, em vez dos JSONs completos de cada painel.
Se um arquivo de origem falhar, aquele cartão fica sem número e a página mostra a descrição fixa.

Uso: python exporta_painel.py
"""
import json
import statistics as st
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BRT = timezone(timedelta(hours=-3))
D = Path("dados")
MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def ler(p):
    return json.loads((D / p).read_text(encoding="utf-8"))


def r(v, c=1):
    return None if v is None else round(v, c)


def amostra(v, n=24):
    """reduz uma série a no máximo n pontos para a linha de tendência"""
    v = [x for x in v if x is not None]
    if len(v) <= n: return [r(x, 2) for x in v]
    passo = (len(v) - 1) / (n - 1)
    return [r(v[round(i * passo)], 2) for i in range(n)]


def data_br(s):
    d = date.fromisoformat(s[:10]); return f"{d.day:02d}/{d.month:02d}"


# ------------------------------------------------------------------ cartões
def mercado():
    f = ler("fechamento.json"); itens = {x["chave"]: x for x in f["cbot"] + f["brasil"]}
    out = []
    for k, nome, fmt in (("soja", "Soja Chicago", "usbu"), ("milho", "Milho Chicago", "usbu"), ("milho_b3", "Milho B3", "rssc"), ("usdbrl", "Dólar", "rs")):
        x = itens.get(k)
        if not x: continue
        v = x["preco"] / 100 if fmt == "usbu" else x["preco"]
        un = {"usbu": "US$/bu", "rssc": "R$/sc", "rs": "R$"}[fmt]
        out.append({"nome": nome, "valor": r(v, 4 if fmt == "rs" else 2), "un": un, "var_pct": r(x["var_pct"], 2), "compl": x.get("compl", "")})
    return {"data": f["data"], "itens": out}


def basis(prod, praca, un, dec):
    d = ler(f"basis/{prod}.json"); datas = d["datas"]; b = d["pracas"][praca]["basis"]
    pts = [(datas[i], v) for i, v in enumerate(b) if v is not None]
    ult_d, ult_v = pts[-1]; u = date.fromisoformat(ult_d)
    vals = []
    for a in range(u.year - 5, u.year):
        c = date(a, u.month, min(u.day, 28))
        vals += [v for s, v in pts if abs((date.fromisoformat(s) - c).days) <= 10]
    m = st.mean(vals) if vals else None
    return {"valor": r(ult_v, dec), "un": un, "delta": r(ult_v - m, dec) if m is not None else None, "delta_txt": "vs média de 5 anos",
            "contexto": f"{praca} em {data_br(ult_d)}", "spark": amostra([v for _, v in pts[-90:]]), "data": ult_d}


def fundos():
    p = ler("cot/resumo.json")["produtos"]["soja"]
    return {"valor": r(p["net"] / 1000, 1), "un": "mil contratos", "delta": r(p["d1"] / 1000, 1), "delta_txt": "na semana",
            "contexto": f"Fundos na soja · posição de {data_br(p['data'])}", "spark": amostra(p["spark"]), "data": p["data"]}


def dolar():
    c = ler("cambio.json"); dol = c["dol"]
    a, b = dol[0], next((x for x in dol if x["vencimento"] >= (date.fromisoformat(dol[0]["vencimento"]) + timedelta(days=330)).isoformat()), dol[-1])
    return {"valor": r(a["preco"], 4), "un": "R$", "delta": r(b["preco"] - a["preco"], 4), "delta_txt": f"até {MES[int(b['vencimento'][5:7]) - 1]}/{b['vencimento'][2:4]}",
            "contexto": f"Dólar futuro {a['contrato']} e inclinação da curva", "spark": amostra([x["preco"] for x in dol[:13]]), "data": datetime.strptime(c["atualizado_em"][:10], "%d/%m/%Y").date().isoformat(),
            "sobe_bom": None}


def spread_milho():
    c = ler("curva_ccm.json")["curva"]; ks = list(c)
    a, b = ks[1] if len(ks) > 1 else ks[0], next((k for k in ks if k.startswith("CCMN")), ks[-1])
    at = datetime.strptime(ler("curva_ccm.json")["atualizado_em"][:10], "%d/%m/%Y").date().isoformat()
    return {"valor": r(c[a], 2), "un": "R$/sc", "delta": r(c[b] - c[a], 2), "delta_txt": f"até {MES['FGHJKMNQUVXZ'.index(b[-3])]}/{b[-2:]}",
            "contexto": f"Milho B3 {a} · curva de vencimentos", "spark": amostra(list(c.values())), "data": at}


def usda(prod, pais, campo, rot):
    d = ler(f"usda/{prod}.json"); g = d["produtos"]["grao"]; v = g["paises"][pais]["dados"][campo]; anos = d["anos"]
    rel = d["relatorio"]; ult, ant = v[-1], v[-2]
    return {"valor": r(ult / 1000, 1), "un": "mi t", "delta": r((ult / ant - 1) * 100, 1) if ant else None, "delta_pct": True, "delta_txt": "sobre a safra anterior",
            "contexto": f"{rot} {anos[-1]}/{str(anos[-1] + 1)[2:]} · relatório de {MES[rel['mes'] - 1]}", "spark": amostra([x / 1000 for x in v[-12:] if x]),
            "data": f"{rel['ano']}-{rel['mes']:02d}-10"}


def safra_eua():
    s = ler("safra_eua.json"); c = s["culturas"]["milho"]["condicao"]
    anos = sorted(c, key=int); a = anos[-1]; ult = c[a][-1]; ge = ult[4] + ult[5]
    semana = date.fromisoformat(ult[0]); hist = []
    for y in anos[-6:-1]:
        # mesma semana do ano; se a avaliação daquele ano terminou antes, usa a última dele
        cand = [x for x in c[y] if (date.fromisoformat(x[0]).replace(year=int(a)) - semana).days <= 3]
        if cand: hist.append(cand[-1][4] + cand[-1][5])
    m = st.mean(hist) if hist else None
    return {"valor": r(ge, 0), "un": "% bom/excelente", "delta": r(ge - m, 0) if m is not None else None, "delta_txt": "vs média de 5 anos",
            "contexto": f"Milho EUA · última avaliação, {data_br(ult[0])}", "spark": amostra([x[4] + x[5] for x in c[a]]), "data": ult[0]}


def comex():
    e = ler("comex/resumo.json")["soja"]["export"]
    return {"valor": r(e["ytd_ton"] / 1e6, 1), "un": "mi t", "delta": r(e["var_ytd"], 1), "delta_pct": True, "delta_txt": "sobre o mesmo período de " + str(e["ano"] - 1),
            "contexto": f"Soja exportada pelo Brasil, jan a {MES[e['mes'] - 1]}/{str(e['ano'])[2:]}", "spark": None, "data": f"{e['ano']}-{e['mes']:02d}-28"}


def export_sales():
    p = ler("export_sales/resumo.json")["produtos"]["soja"]; s = ler("export_sales/soja.json")["anos"][-1]
    dv = (p["comp"] / p["comp_ano_anterior"] - 1) * 100 if p.get("comp_ano_anterior") else None
    return {"valor": r(p["comp"] / 1000, 1), "un": "mi t", "delta": r(dv, 0), "delta_pct": True, "delta_txt": "sobre o ano passado",
            "contexto": f"Soja dos EUA já vendida na safra {s['safra']} · semana até {data_br(p['semana_ate'])}", "spark": amostra([x / 1000 for x in s["comp"]], 40),
            "spark_rot": ["início da safra, " + data_br(s["datas"][0]), "semana até " + data_br(s["datas"][-1])], "data": p["semana_ate"]}


CARTOES = {
    "basis-soja-brasil": lambda: basis("soja", "Paranaguá", "c/bu", 1),
    "basis-milho-brasil": lambda: basis("milho", "Rio Verde GO", "R$/sc", 2),
    "curva-do-dolar": dolar,
    "spread-milho-b3": spread_milho,
    "posicao-fundos-cftc": fundos,
    "exportacoes-eua-usda": export_sales,
    "condicao-de-safra-eua": safra_eua,
    "exportacao-e-importacao-de-graos": comex,
    "usda-complexo-soja": lambda: usda("soja", "BR", "producao", "Produção de soja do Brasil"),
    "usda-milho": lambda: usda("milho", "US", "producao", "Produção de milho dos EUA"),
    "usda-trigo": lambda: usda("trigo", "WD", "estoque_final", "Estoque mundial de trigo"),
}


def main():
    out = {"atualizado_em": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"), "cartoes": {}, "erros": {}}
    try:
        out["mercado"] = mercado()
    except Exception as e:  # noqa: BLE001
        out["erros"]["mercado"] = str(e)[:200]
    for k, fn in CARTOES.items():
        try:
            out["cartoes"][k] = fn()
        except Exception as e:  # noqa: BLE001
            out["erros"][k] = f"{type(e).__name__}: {e}"[:200]
    (D / "painel.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
