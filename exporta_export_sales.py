"""Vendas semanais de exportação dos EUA (USDA FAS Export Sales Reporting) para o dashboard do AgroBasis.

Fonte: API pública do USDA FAS (https://api.fas.usda.gov/api/esr), com chave do api.data.gov.
Sem a variável FAS_API_KEY, usa a DEMO_KEY (limite de ~10 consultas por hora): nesse caso o script
espera entre as consultas e só baixa o que falta.

Saída
- dados/export_sales/cache/<produto>_<ano>.json: agregado de cada ano-safra (não é baixado de novo depois de fechado);
- dados/export_sales/<produto>.json: arquivo público lido pelo dashboard (6 anos-safra, destinos, projeção do USDA);
- dados/export_sales/resumo.json: última semana de cada produto.

Unidades: a API entrega toneladas métricas; os arquivos públicos usam mil toneladas.
Uso: python exporta_export_sales.py [--max-consultas N]
"""
import argparse
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

BRT = timezone(timedelta(hours=-3))
API = "https://api.fas.usda.gov/api/esr"
CHAVE = os.environ.get("FAS_API_KEY") or "DEMO_KEY"
PASTA = Path("dados/export_sales"); CACHE = PASTA / "cache"
ANOS = 6  # anos-safra exibidos: o atual e os 5 anteriores

# produto: (código ESR, nome, mês de início do ano-safra nos EUA, produto/linha no PSD do AgroBasis)
PRODUTOS = {
    "soja": (801, "Soja em grão", 9, ("soja", "grao")),
    "milho": (401, "Milho", 9, ("milho", "grao")),
    "trigo": (107, "Trigo (todas as classes)", 6, ("trigo", "grao")),
    "farelo": (901, "Farelo de soja", 10, ("soja", "farelo")),
    "oleo": (902, "Óleo de soja", 10, ("soja", "oleo")),
}

PAISES_PT = {
    "CHINA": "China", "CHINA, PEOPLES REPUBLIC OF": "China", "KOREA, REPUBLIC OF": "Coreia do Sul", "GREECE": "Grécia", "CAMBODIA": "Camboja", "LAOS": "Laos", "NEPAL": "Nepal", "QATAR": "Catar", "SENEGAL": "Senegal", "BARBADOS": "Barbados", "LEEWARD-WINDWARD ISLANDS": "Ilhas de Barlavento", "GHANA": "Gana", "ANGOLA": "Angola", "MOZAMBIQUE": "Moçambique", "OMAN": "Omã", "KUWAIT": "Kuwait", "BAHRAIN": "Bahrein", "TANZANIA": "Tanzânia", "UGANDA": "Uganda", "YEMEN (SANAA)": "Iêmen", "SURINAME": "Suriname", "BOLIVIA": "Bolívia", "PARAGUAY": "Paraguai", "URUGUAY": "Uruguai", "BAHAMAS, THE": "Bahamas", "BELIZE": "Belize", "MEXICO": "México", "JAPAN": "Japão", "KOREA, SOUTH": "Coreia do Sul", "TAIWAN": "Taiwan",
    "EUROPEAN UNION - 27": "União Europeia", "EGYPT": "Egito", "INDONESIA": "Indonésia", "COLOMBIA": "Colômbia",
    "PHILIPPINES": "Filipinas", "VIETNAM": "Vietnã", "CANADA": "Canadá", "GUATEMALA": "Guatemala", "SPAIN": "Espanha",
    "NETHERLANDS": "Holanda", "GERMANY": "Alemanha", "ITALY": "Itália", "PORTUGAL": "Portugal", "IRELAND": "Irlanda",
    "THAILAND": "Tailândia", "MALAYSIA": "Malásia", "BANGLADESH": "Bangladesh", "PAKISTAN": "Paquistão",
    "TURKEY": "Turquia", "SAUDI ARABIA": "Arábia Saudita", "ISRAEL": "Israel", "MOROCCO": "Marrocos", "TUNISIA": "Tunísia",
    "ALGERIA": "Argélia", "NIGERIA": "Nigéria", "SOUTH AFRICA": "África do Sul", "PERU": "Peru", "CHILE": "Chile",
    "ECUADOR": "Equador", "VENEZUELA": "Venezuela", "HONDURAS": "Honduras", "EL SALVADOR": "El Salvador",
    "COSTA RICA": "Costa Rica", "PANAMA": "Panamá", "NICARAGUA": "Nicarágua", "DOMINICAN REPUBLIC": "Rep. Dominicana",
    "JAMAICA": "Jamaica", "CUBA": "Cuba", "HAITI": "Haiti", "BRAZIL": "Brasil", "ARGENTINA": "Argentina",
    "UNKNOWN": "Destino a definir", "UNITED KINGDOM": "Reino Unido", "IRAN": "Irã", "IRAQ": "Iraque", "YEMEN": "Iêmen",
    "UNITED ARAB EMIRATES": "Emirados Árabes", "INDIA": "Índia", "SRI LANKA": "Sri Lanka", "BURMA": "Mianmar",
    "SINGAPORE": "Singapura", "HONG KONG": "Hong Kong", "KOREA, NORTH": "Coreia do Norte", "RUSSIA": "Rússia",
    "UKRAINE": "Ucrânia", "POLAND": "Polônia", "ROMANIA": "Romênia", "FRANCE": "França", "BELGIUM-LUXEMBOURG": "Bélgica",
    "BELGIUM": "Bélgica", "NORWAY": "Noruega", "LEBANON": "Líbano", "JORDAN": "Jordânia", "KENYA": "Quênia",
    "ETHIOPIA": "Etiópia", "SUDAN": "Sudão", "LIBYA": "Líbia", "TRINIDAD": "Trinidad e Tobago", "GUYANA": "Guiana",
    "AUSTRALIA": "Austrália", "NEW ZEALAND": "Nova Zelândia", "FRENCH PACIFIC ISLANDS": "Ilhas do Pacífico (França)",
}

sessao = requests.Session(); sessao.headers["User-Agent"] = "AgroBasis/1.0 (agrobasis.com.br)"
consultas = 0


class CotaEsgotada(RuntimeError):
    """a API recusou de novo depois da espera: a cota da chave acabou por agora"""


def get(caminho, max_consultas):
    """GET na API respeitando o limite da chave. Com 429 espera 10 min uma vez; se repetir, encerra a execução."""
    global consultas
    if consultas >= max_consultas:
        raise RuntimeError("limite de consultas desta execução")
    for tentativa in range(2):
        r = sessao.get(f"{API}/{caminho}", params={"api_key": CHAVE}, timeout=180)
        if r.status_code == 429:
            if tentativa == 0:
                print("limite da API: aguardando 10 min"); time.sleep(600); continue
            raise CotaEsgotada("cota da API esgotada")
        r.raise_for_status()
        consultas += 1
        resta = int(r.headers.get("x-ratelimit-remaining", "99"))
        if CHAVE == "DEMO_KEY" and resta <= 1:
            print(f"restam {resta} consultas na hora: aguardando 6 min"); time.sleep(370)
        return r.json()
    raise RuntimeError(f"API indisponível: {caminho}")


def nome_pais(desc):
    d = " ".join((desc or "").split()).upper()
    return PAISES_PT.get(d, d.title())


def inicio_safra(my, mes):
    """ESR: marketYear 2027 da soja começa em 1º/set/2026."""
    return date(my - 1, mes, 1)


def agregar(linhas, my, mes, paises):
    """soma por semana (total e por país) a resposta de allCountries de um ano-safra"""
    ini = inicio_safra(my, mes)
    sem = {}
    for x in linhas:
        dt = x["weekEndingDate"][:10]
        s = sem.setdefault(dt, {"net": 0, "emb": 0, "acum": 0, "comp": 0, "saldo": 0, "prox": 0, "pais": {}})
        for k, c in (("net", "currentMYNetSales"), ("emb", "weeklyExports"), ("acum", "accumulatedExports"),
                     ("comp", "currentMYTotalCommitment"), ("saldo", "outstandingSales"), ("prox", "nextMYNetSales")):
            s[k] += x.get(c) or 0
        p = nome_pais(paises.get(x["countryCode"], str(x["countryCode"])))
        q = s["pais"].setdefault(p, [0, 0, 0, 0])  # vendas líquidas, embarques, compromisso, exportado acumulado
        q[0] += x.get("currentMYNetSales") or 0; q[1] += x.get("weeklyExports") or 0
        q[2] += x.get("currentMYTotalCommitment") or 0; q[3] += x.get("accumulatedExports") or 0
    datas = sorted(sem)
    return {"ano": my, "inicio": ini.isoformat(), "baixado_em": date.today().isoformat(),
            "baixado_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), "datas": datas,
            "semana": [(date.fromisoformat(d) - ini).days // 7 for d in datas],
            **{k: [sem[d][k] for d in datas] for k in ("net", "emb", "acum", "comp", "saldo", "prox")},
            "pais": {d: sem[d]["pais"] for d in datas}}


def projecao_usda(prod, linha):
    """exportação dos EUA projetada pelo USDA (WASDE/PSD) por ano-safra, em mil t. Chave: ano de início."""
    try:
        d = json.loads(Path(f"dados/usda/{prod}.json").read_text(encoding="utf-8"))
        v = d["produtos"][linha]["paises"]["US"]["dados"]["exportacao"]
        return {int(a): x for a, x in zip(d["anos"], v) if x is not None}
    except Exception as e:  # noqa: BLE001
        print("sem projeção do USDA para", prod, linha, e); return {}


def mil(v, c=1):
    return round(v / 1000, c)


def publicar(slug, cod, nome, mes, psd, cacheados, release):
    anos = sorted(cacheados)[-ANOS:]
    atual = cacheados[anos[-1]]; ant = cacheados.get(anos[-1] - 1)
    proj = projecao_usda(*psd)
    ult = atual["datas"][-1]; sem_ult = atual["semana"][-1]
    # destinos: compromisso total no ano-safra atual x mesma semana do ano anterior
    pa = atual["pais"][ult]
    pa_ant = {}
    if ant:
        i = min(range(len(ant["semana"])), key=lambda k: abs(ant["semana"][k] - sem_ult))
        pa_ant = ant["pais"][ant["datas"][i]]
    tops = sorted(pa, key=lambda p: -pa[p][2])
    lista = []
    for p in tops:
        if pa[p][2] <= 0 and pa[p][0] == 0: continue
        lista.append({"pais": p, "comp": mil(pa[p][2]), "acum": mil(pa[p][3]), "net_sem": mil(pa[p][0]), "emb_sem": mil(pa[p][1]),
                      "comp_ant": mil(pa_ant.get(p, [0, 0, 0, 0])[2])})
    # países que compravam no ano passado e sumiram (ex.: China) também entram
    for p in sorted(pa_ant, key=lambda p: -pa_ant[p][2])[:15]:
        if p not in pa and pa_ant[p][2] > 0:
            lista.append({"pais": p, "comp": 0, "acum": 0, "net_sem": 0, "emb_sem": 0, "comp_ant": mil(pa_ant[p][2])})
    out = {
        "atualizado_em": datetime.now(BRT).strftime("%d/%m/%Y %H:%M"),
        "fonte": "USDA FAS, Export Sales Reporting (vendas semanais de exportação dos EUA)",
        "produto": nome, "slug": slug, "unidade": "mil toneladas", "semana_ate": ult, "divulgado_em": release,
        "safra_atual": f"{anos[-1] - 1}/{str(anos[-1])[2:]}", "inicio_safra": atual["inicio"],
        "anos": [{"safra": f"{a - 1}/{str(a)[2:]}", "inicio": cacheados[a]["inicio"], "datas": cacheados[a]["datas"], "semana": cacheados[a]["semana"],
                  "net": [mil(v) for v in cacheados[a]["net"]], "emb": [mil(v) for v in cacheados[a]["emb"]],
                  "comp": [mil(v) for v in cacheados[a]["comp"]], "acum": [mil(v) for v in cacheados[a]["acum"]],
                  "saldo": [mil(v) for v in cacheados[a]["saldo"]], "prox": [mil(v) for v in cacheados[a]["prox"]],
                  "projecao_usda": proj.get(a - 1)} for a in anos],
        "destinos": lista,
        "semana_destinos": sorted([{"pais": p, "net": mil(v[0]), "emb": mil(v[1])} for p, v in pa.items() if v[0] or v[1]], key=lambda x: -abs(x["net"]))[:12],
    }
    (PASTA / f"{slug}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    a = out["anos"][-1]; b = out["anos"][-2] if len(out["anos"]) > 1 else None
    comp_ant = None
    if b:
        i = min(range(len(b["semana"])), key=lambda k: abs(b["semana"][k] - sem_ult)); comp_ant = b["comp"][i]
    return {"produto": nome, "semana_ate": ult, "net": a["net"][-1], "emb": a["emb"][-1], "comp": a["comp"][-1],
            "comp_ano_anterior": comp_ant, "projecao_usda": a["projecao_usda"]}


def pub_utc(v):
    """releaseTimeStamp do FAS em UTC ('AAAA-MM-DDTHH:MM:SS'); sem fuso, é horário de Washington."""
    if not v:
        return ""
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if d.tzinfo is None:
        from zoneinfo import ZoneInfo
        d = d.replace(tzinfo=ZoneInfo("America/New_York"))
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max-consultas", type=int, default=60); args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    rel = get("datareleasedates", args.max_consultas)
    paises_p = PASTA / "paises.json"
    if paises_p.exists():
        paises = {int(k): v for k, v in json.loads(paises_p.read_text(encoding="utf-8")).items()}
    else:
        paises = {x["countryCode"]: x["countryDescription"] for x in get("countries", args.max_consultas)}
        paises_p.write_text(json.dumps(paises, ensure_ascii=False), encoding="utf-8")
    resumo = {"atualizado_em": datetime.now(BRT).strftime("%d/%m/%Y %H:%M"), "produtos": {}, "pendentes": []}
    # primeiro o ano-safra atual de todos os produtos; depois os anos que faltam no cache
    fila = []
    for slug, (cod, nome, mes, psd) in PRODUTOS.items():
        r = next(x for x in rel if x["commodityCode"] == cod)
        my = r["marketYear"]
        c_at = CACHE / f"{slug}_{my}.json"
        # o ano-safra atual é baixado de novo quando o USDA publica um relatório depois da última cópia
        # (releaseTimeStamp de datareleasedates); sem essa informação, vale a regra antiga por idade da cópia
        info = json.loads(c_at.read_text()) if c_at.exists() else {}
        baixado = info.get("baixado_em", "2000-01-01")
        idade = (date.today() - date.fromisoformat(baixado)).days
        pub = pub_utc(r.get("releaseTimeStamp"))
        if pub:
            novo = pub > info.get("baixado_ts", baixado + "T00:00:00") or idade > 6
        else:
            novo = idade >= 1 and (CHAVE != "DEMO_KEY" or date.today().weekday() in (3, 4) or idade > 6)
        print(slug, my, "publicado (UTC):", pub, "| cópia:", info.get("baixado_ts", baixado), "| baixar:", not c_at.exists() or novo)
        if not c_at.exists() or novo:
            fila.append((0, slug, my, True))
        for a in range(my - ANOS + 1, my):
            c = CACHE / f"{slug}_{a}.json"
            fechado = c.exists() and json.loads(c.read_text())["datas"][-1] >= (inicio_safra(a + 1, mes) - timedelta(days=7)).isoformat()
            if not fechado:
                fila.append((1 if a == my - 1 else 2, slug, a, False))
    fila.sort(key=lambda x: (x[0], -x[2]))
    print("na fila:", [(f[1], f[2]) for f in fila])
    esgotada = False
    for _, slug, a, atual in fila:
        cod, nome, mes, psd = PRODUTOS[slug]
        if esgotada:
            resumo["pendentes"].append(f"{slug} {a}"); continue
        try:
            linhas = get(f"exports/commodityCode/{cod}/allCountries/marketYear/{a}", args.max_consultas)
        except CotaEsgotada as e:
            print(slug, a, e); esgotada = True; resumo["pendentes"].append(f"{slug} {a}"); continue
        except RuntimeError as e:
            print(slug, a, e); resumo["pendentes"].append(f"{slug} {a}"); continue
        if not linhas:
            print(slug, a, "sem linhas"); continue
        (CACHE / f"{slug}_{a}.json").write_text(json.dumps(agregar(linhas, a, mes, paises), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(slug, a, len(linhas), "linhas")
    for slug, (cod, nome, mes, psd) in PRODUTOS.items():
        cacheados = {int(p.stem.split("_")[1]): json.loads(p.read_text()) for p in CACHE.glob(f"{slug}_*.json")}
        if not cacheados: continue
        r = next(x for x in rel if x["commodityCode"] == cod)
        resumo["produtos"][slug] = publicar(slug, cod, nome, mes, psd, cacheados, r["releaseTimeStamp"][:16])
    (PASTA / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    # sinal para a página /dashboards/ mostrar o cartão: só com o histórico completo
    if not resumo["pendentes"] and len(resumo["produtos"]) == len(PRODUTOS):
        (PASTA / "completo.json").write_text(json.dumps({"desde": resumo["atualizado_em"]}), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False)[:1500]); print("consultas:", consultas)


if __name__ == "__main__":
    main()
