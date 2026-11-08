"""Coleta de mercado para o áudio diário do AgroBasis.

Roda no GitHub Actions às 05h de Brasília, com o pregão noturno da CBOT aberto.
Grava dados/manha.json com:
- CBOT (soja, milho, trigo, farelo, óleo): preço no noturno, ajuste anterior e
  fechamentos dos últimos dias, no contrato de referência de cada produto;
- macro: dólar (USD/BRL), DXY, petróleo, S&P futuro, Ibovespa;
- Banco Central: PTAX e meta Selic.
Fontes: scanner público do TradingView (atraso de 10 a 15 min) e API pública do Banco Central (SGS/Olinda).
Se uma fonte falhar, o item fica com "erro" e o restante segue.
"""
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
BRT = timezone(timedelta(hours=-3))
LETRAS = "FGHJKMNQUVXZ"

# produto: (raiz, meses negociados, nome, unidade)
CBOT = {
    "soja": ("ZS", "FHKNQUX", "Soja", "US$ cents/bushel"),
    "milho": ("ZC", "HKNUZ", "Milho", "US$ cents/bushel"),
    "trigo": ("ZW", "HKNUZ", "Trigo", "US$ cents/bushel"),
    "farelo": ("ZM", "FHKNQUVZ", "Farelo de soja", "US$/tonelada curta"),
    "oleo": ("ZL", "FHKNQUVZ", "Óleo de soja", "US$ cents/libra"),
}
MACRO = {
    "usdbrl": ("FX_IDC:USDBRL", "Dólar comercial (USD/BRL)"),
    "dxy": ("TVC:DXY", "Índice dólar DXY"),
    "brent": ("TVC:UKOIL", "Petróleo Brent (US$/barril)"),
    "sp500_fut": ("CME_MINI:ES1!", "S&P 500 futuro"),
    "ibov": ("BMFBOVESPA:IBOV", "Ibovespa"),
}


def contratos(meses, hoje, n=2):
    """Próximos n contratos com mês posterior ao mês corrente (convenção do basis AgroBasis)."""
    out, ano, mes = [], hoje.year, hoje.month
    while len(out) < n:
        mes += 1
        if mes > 12:
            mes, ano = 1, ano + 1
        letra = LETRAS[mes - 1]
        if letra in meses:
            out.append((letra, ano))
    return out


COLUNAS = ["close", "change", "change_abs", "open", "high", "low", "description", "update_mode"]


def tv_scan(tickers):
    """Cotação atual (com 10-15 min de atraso) via scanner público do TradingView."""
    r = requests.post("https://scanner.tradingview.com/global/scan",
                      json={"symbols": {"tickers": tickers, "query": {"types": []}}, "columns": COLUNAS},
                      headers=UA, timeout=25)
    r.raise_for_status()
    out = {}
    for item in r.json().get("data", []):
        v = dict(zip(COLUNAS, item["d"]))
        preco, var = v.get("close"), v.get("change_abs")
        out[item["s"]] = {
            "ticker": item["s"], "descricao": v.get("description"), "preco": preco,
            "ajuste_anterior": round(preco - var, 4) if preco is not None and var is not None else None,
            "variacao": var, "variacao_pct": round(v["change"], 2) if v.get("change") is not None else None,
            "maxima": v.get("high"), "minima": v.get("low"), "modo": v.get("update_mode"),
        }
    return out


def tentar(fn, *a):
    for i in range(3):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            erro = f"{type(e).__name__}: {e}"[:200]
            time.sleep(2 + 3 * i)
    return {"erro": erro}


def bcb_ptax():
    fim = date.today()
    ini = fim - timedelta(days=10)
    url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
           "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)")
    r = requests.get(url, params={"@dataInicial": f"'{ini:%m-%d-%Y}'", "@dataFinalCotacao": f"'{fim:%m-%d-%Y}'",
                                  "$format": "json"}, headers=UA, timeout=20)
    r.raise_for_status()
    v = r.json()["value"]
    return [{"data": x["dataHoraCotacao"][:10], "venda": x["cotacaoVenda"]} for x in v[-3:]]


def bcb_selic():
    r = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1",
                     params={"formato": "json"}, headers=UA, timeout=20)
    r.raise_for_status()
    x = r.json()[-1]
    return {"data": x["data"], "meta_selic_aa": float(x["valor"])}


def main():
    agora = datetime.now(BRT)
    hoje = agora.date()
    saida = {"gerado_em_brt": agora.strftime("%Y-%m-%d %H:%M"), "fonte_cotacoes": "TradingView (atraso de 10 a 15 min)",
             "cbot": {}, "macro": {}, "bcb": {}}
    tickers, mapa = [], {}
    for chave, (raiz, meses, nome, unid) in CBOT.items():
        for letra, ano in contratos(meses, hoje):
            t = f"CBOT:{raiz}{letra}{ano}"
            tickers.append(t)
            mapa[t] = (chave, f"{raiz}{letra}{str(ano)[-2:]}")
    for chave, (t, nome) in MACRO.items():
        tickers.append(t)
    dados = tentar(tv_scan, tickers)
    erro = dados.get("erro") if isinstance(dados.get("erro"), str) else None
    for chave, (raiz, meses, nome, unid) in CBOT.items():
        itens = []
        for t, (c, cod) in mapa.items():
            if c == chave:
                d = dict(dados.get(t) or {"erro": erro or "sem dado"})
                d["contrato"] = cod
                itens.append(d)
        saida["cbot"][chave] = {"nome": nome, "unidade": unid, "contratos": itens}
    for chave, (t, nome) in MACRO.items():
        d = dict(dados.get(t) or {"erro": erro or "sem dado"})
        d["nome"] = nome
        saida["macro"][chave] = d
    saida["bcb"]["ptax"] = tentar(bcb_ptax)
    saida["bcb"]["selic"] = tentar(bcb_selic)
    # curva de dólar futuro da B3 (fechamento de ontem), já coletada pelo atualiza_curva_soja.py
    try:
        curva = json.loads(Path("dados/curva_soja.json").read_text(encoding="utf-8"))
        dol = curva.get("dolar", {})
        saida["dolar_futuro_b3"] = {"atualizado_em": curva.get("atualizado_em"),
                                    "contratos": dict(list(dol.items())[:3])}
    except Exception as e:  # noqa: BLE001
        saida["dolar_futuro_b3"] = {"erro": str(e)[:200]}
    Path("dados").mkdir(exist_ok=True)
    hist_p = Path("dados/historico_ajustes.json")
    hist = json.loads(hist_p.read_text(encoding="utf-8")) if hist_p.exists() else {}
    for chave, p in saida["cbot"].items():
        c = p["contratos"][0]
        if c.get("ajuste_anterior") is not None:
            serie = hist.setdefault(c["contrato"], {})
            # o ajuste anterior visto hoje cedo é o fechamento do último pregão
            serie[(hoje - timedelta(days=3 if hoje.weekday() == 0 else 1)).isoformat()] = c["ajuste_anterior"]
            datas = sorted(serie)
            if len(datas) >= 2:
                c["movimento_ontem"] = round(serie[datas[-1]] - serie[datas[-2]], 4)
    hist_p.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    Path("dados/manha.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    erros = sum("erro" in c for p in saida["cbot"].values() for c in p["contratos"])
    if erros == sum(len(p["contratos"]) for p in saida["cbot"].values()):
        raise SystemExit("nenhuma cotação da CBOT coletada")
    print(json.dumps(saida, ensure_ascii=False)[:3000])
    print(f"contratos com erro: {erros}")


if __name__ == "__main__":
    main()
