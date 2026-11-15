"""Termômetro de venda AgroBasis (soja e milho, por praça).

Índice de 0 a 100 que resume se o momento está mais ou menos favorável à venda do grão disponível,
juntando indicadores que o próprio AgroBasis já coleta. Quanto MAIOR, mais favorável à venda agora.

Componentes (cada um vira uma nota de 0 a 100):
- Preço: onde o preço físico da praça está dentro da faixa dos últimos 3 anos (percentil).
- Basis: o basis atual comparado com o basis da mesma época nos anos anteriores (percentil).
- Sazonalidade: o que o preço da praça costumou fazer nos ~90 dias seguintes a esta época do ano.
  Se historicamente cai, vender agora pontua mais.
- Fundos: posição líquida dos fundos (managed money, CFTC) na CBOT contra os últimos 3 anos.
  Fundos muito comprados = preço sustentado por especulação = nota maior para vender.
- Carrego (só milho): diferença entre o contrato ~6 meses à frente e o primeiro vencimento na B3.
  Carrego alto paga para esperar = nota menor para vender agora (escala: +15% em 6 meses = 0; -15% = 100).

Também calcula a série histórica (desde 2021) e um teste: o que o preço fez nos 63 pregões (~3 meses)
seguintes, conforme a faixa do termômetro. Indicador educacional, não é recomendação de compra ou venda.

Uso: python exporta_termometro.py  ->  grava dados/termometro.json
"""
import bisect
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BRT = timezone(timedelta(hours=-3))
PESOS = {"soja": {"preco": 35, "basis": 25, "sazonal": 25, "fundos": 15},
         "milho": {"preco": 30, "basis": 20, "sazonal": 20, "carrego": 15, "fundos": 15}}
JANELA = 756          # ~3 anos de pregões
FRENTE = 63           # ~3 meses de pregões
INICIO_HIST = "2021-11-01"


def ler(c):
    return json.loads((RAIZ / c).read_text(encoding="utf-8"))


def pct(v, amostra):
    a = [x for x in amostra if x is not None]
    if v is None or len(a) < 20:
        return None
    menor = sum(1 for x in a if x < v)
    igual = sum(1 for x in a if x == v)
    return 100.0 * (menor + 0.5 * igual) / len(a)


def lim(x):
    return max(0.0, min(100.0, x))


def dt(s):
    return date.fromisoformat(s)


def preencher(v):
    """Repete o último valor conhecido (o físico da Conab é semanal)."""
    out, ult = [], None
    for x in v:
        if x is not None:
            ult = x
        out.append(ult)
    return out


def serie_fundos(cot, datas):
    """Posição líquida dos fundos (contratos), alinhada às datas diárias e percentil de 3 anos (156 semanas)."""
    cd = cot["datas"]
    mm = cot["cat"]["mm"]
    liq = [(l or 0) - (s or 0) for l, s in zip(mm["l"], mm["s"])]
    nota = []
    for d in datas:
        k = bisect.bisect_right(cd, d) - 1
        if k < 30:
            nota.append((None, None)); continue
        nota.append((liq[k], pct(liq[k], liq[max(0, k - 156):k + 1])))
    return nota


def sazonal(datas, preco, i):
    """Retorno médio do preço nos FRENTE pregões seguintes, nesta mesma época, em anos anteriores."""
    d0 = dt(datas[i])
    rets = []
    for anos in range(1, 7):
        try:
            alvo = d0.replace(year=d0.year - anos)
        except ValueError:
            alvo = d0.replace(year=d0.year - anos, day=28)
        j = bisect.bisect_left(datas, alvo.isoformat())
        if j >= len(datas) or j + FRENTE >= i or abs((dt(datas[j]) - alvo).days) > 7:
            continue
        a, b = preco[j], preco[j + FRENTE]
        if a and b:
            rets.append(b / a - 1)
    if len(rets) < 2:
        return None, None
    m = sum(rets) / len(rets)
    return m, lim(50 - m * 100 * 5)   # -10% -> 100 ; +10% -> 0


def basis_epoca(datas, basis, i):
    d0 = dt(datas[i])
    amostra = []
    for anos in range(1, 6):
        try:
            c = d0.replace(year=d0.year - anos)
        except ValueError:
            c = d0.replace(year=d0.year - anos, day=28)
        a = bisect.bisect_left(datas, (c - timedelta(days=25)).isoformat())
        b = bisect.bisect_right(datas, (c + timedelta(days=25)).isoformat())
        amostra += [x for x in basis[a:b] if x is not None]
    return pct(basis[i], amostra)


def carrego_ccm(ccm, datas_alvo):
    """Carrego da B3: contrato ~6 meses à frente / primeiro vencimento em aberto - 1, por data."""
    cd = ccm["datas"]
    cont = ccm["contratos"]
    MES = {"F": 1, "H": 3, "K": 5, "N": 7, "U": 9, "X": 11}
    venc = {c: date(2000 + int(c[4:6]), MES[c[3]], 15) for c in cont}
    out = []
    for d in datas_alvo:
        k = bisect.bisect_right(cd, d) - 1
        if k < 0:
            out.append(None); continue
        hoje = dt(cd[k])
        vivos = sorted([c for c in cont if venc[c] > hoje + timedelta(days=20) and cont[c][k]], key=lambda c: venc[c])
        if len(vivos) < 2:
            out.append(None); continue
        f = vivos[0]
        alvo = venc[f] + timedelta(days=180)
        seg = min(vivos[1:], key=lambda c: abs((venc[c] - alvo).days))
        out.append(cont[seg][k] / cont[f][k] - 1)
    return out


def montar(produto, basis_js, cot, ccm=None, hoje=None):
    datas = basis_js["datas"]
    fundos = serie_fundos(cot, datas)
    carr = carrego_ccm(ccm, datas) if ccm else None
    pesos = PESOS[produto]
    saida = {}
    for praca, s in basis_js["pracas"].items():
        preco = preencher(s["fisico"])
        basis = preencher(s["basis"])
        n = len(datas)

        def comp(i, preco_i=None, basis_i=None):
            p_i = preco[i] if preco_i is None else preco_i
            c = {}
            c["preco"] = (p_i, pct(p_i, preco[max(0, i - JANELA):i + 1] + ([p_i] if preco_i else [])))
            b_i = basis[i] if basis_i is None else basis_i
            bb = list(basis); bb[i] = b_i
            c["basis"] = (b_i, basis_epoca(datas, bb, i))
            c["sazonal"] = sazonal(datas, preco, i)
            c["fundos"] = fundos[i]
            if carr is not None:
                v = carr[i]
                c["carrego"] = (v, None if v is None else lim(50 - v * 100 * 3.33))   # +15% -> 0 ; -15% -> 100
            tot = sum(pesos[k] for k in pesos if c[k][1] is not None)
            if tot < 70:
                return c, None
            nota = sum(pesos[k] * c[k][1] for k in pesos if c[k][1] is not None) / tot
            return c, nota

        # série histórica (todo pregão) e teste com o preço 63 pregões depois
        hist_d, hist_s, hist_p, teste = [], [], [], []
        i0 = bisect.bisect_left(datas, INICIO_HIST)
        for i in range(i0, n):
            _, nota = comp(i)
            if nota is None or preco[i] is None:
                continue
            hist_d.append(datas[i]); hist_s.append(round(nota, 1)); hist_p.append(preco[i])
            if i + FRENTE < n and preco[i + FRENTE]:
                teste.append((nota, preco[i + FRENTE] / preco[i] - 1))
        faixas = []
        for nome, a, b in (("ate40", 0, 40), ("40a60", 40, 60), ("acima60", 60, 101)):
            r = [x for s_, x in teste if a <= s_ < b]
            if r:
                faixas.append({"faixa": nome, "n": len(r), "ret_medio": round(100 * sum(r) / len(r), 2),
                               "pct_caiu": round(100 * sum(1 for x in r if x < 0) / len(r), 1)})
        # hoje: último dado + preço estimado com o fechamento mais recente
        i = n - 1
        est = None
        if hoje:
            if produto == "soja" and hoje.get("cbot") and hoje.get("usd"):
                est = round((hoje["cbot"] + basis[i]) * hoje["usd"] * 2.20462 / 100, 2)
            if produto == "milho" and hoje.get("b3"):
                est = round(hoje["b3"] + basis[i], 2)
        c, nota = comp(i, preco_i=est)
        # reduz a série para semanal (sexta ou último pregão da semana) para o site
        sem_d, sem_s, sem_p, ult = [], [], [], None
        for d, sc, p in zip(hist_d, hist_s, hist_p):
            w = dt(d).isocalendar()[:2]
            if w != ult:
                sem_d.append(d); sem_s.append(sc); sem_p.append(p); ult = w
            else:
                sem_d[-1], sem_s[-1], sem_p[-1] = d, sc, p
        saida[praca] = {
            "nota": None if nota is None else round(nota, 1),
            "preco_ref": est if est else preco[i], "preco_estimado": bool(est), "data_fisico": datas[i],
            "componentes": {k: {"valor": None if v[0] is None else round(v[0], 4), "nota": None if v[1] is None else round(v[1], 1),
                                "peso": pesos[k]} for k, v in c.items()},
            "hist": {"datas": sem_d, "nota": sem_s, "preco": sem_p},
            "teste": faixas,
        }
    return saida


def main():
    fech = ler("dados/fechamento.json")
    allf = {x["chave"]: x for k in ("cbot", "brasil") for x in fech.get(k, [])}
    try:
        ag = ler("dados/cotacoes_agora.json")
        if ag.get("gerado_em_brt", "") > fech.get("gerado_em_brt", ""):
            allf.update({x["chave"]: x for k in ("cbot", "brasil") for x in ag.get(k, [])})
    except FileNotFoundError:
        pass
    hoje = {"cbot": allf.get("soja", {}).get("preco"), "usd": allf.get("usdbrl", {}).get("preco"), "b3": allf.get("milho_b3", {}).get("preco")}
    out = {
        "atualizado_em": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"),
        "referencia_mercado": fech.get("data"),
        "pesos": PESOS,
        "fontes": "Preços físicos: Conab e planilha AgroBasis · CBOT e B3 via TradingView · PTAX (BCB) · CFTC (Commitments of Traders)",
        "soja": montar("soja", ler("dados/basis/soja.json"), ler("dados/cot/soja.json"), hoje=hoje),
        "milho": montar("milho", ler("dados/basis/milho.json"), ler("dados/cot/milho.json"), ccm=ler("dados/ccm_historico.json"), hoje=hoje),
    }
    (RAIZ / "dados/termometro.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for prod in ("soja", "milho"):
        for praca, v in out[prod].items():
            print(prod, praca, v["nota"], {k: c["nota"] for k, c in v["componentes"].items()}, v["teste"])


if __name__ == "__main__":
    main()
