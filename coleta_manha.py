"""Coleta de mercado para o áudio diário do AgroBasis.

Roda no GitHub Actions às 05h de Brasília, com o pregão noturno da CBOT aberto.
Grava dados/manha.json com:
- CBOT (soja, milho, trigo, farelo, óleo): preço no noturno, ajuste anterior e
  fechamentos dos últimos dias, no contrato de referência de cada produto;
- macro: dólar (USD/BRL), DXY, petróleo, S&P futuro, Ibovespa;
- Banco Central: PTAX e meta Selic.
Fontes: Yahoo Finance (chart API, sem chave) e API pública do Banco Central (SGS/Olinda).
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
    "usdbrl": ("BRL=X", "Dólar comercial (USD/BRL)"),
    "dxy": ("DX-Y.NYB", "Índice dólar DXY"),
    "brent": ("BZ=F", "Petróleo Brent (US$/barril)"),
    "sp500_fut": ("ES=F", "S&P 500 futuro"),
    "ibov": ("^BVSP", "Ibovespa"),
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


def yahoo(simbolo):
    """Preço atual (com noturno), horário, ajuste anterior e últimos fechamentos diários."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"
    r = requests.get(url, params={"range": "10d", "interval": "1d", "includePrePost": "true"},
                     headers=UA, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    meta = res["meta"]
    ts = res.get("timestamp") or []
    closes = res["indicators"]["quote"][0].get("close") or []
    hist = [{"data": datetime.fromtimestamp(t, BRT).date().isoformat(), "fech": round(c, 4)}
            for t, c in zip(ts, closes) if c is not None]
    preco = meta.get("regularMarketPrice")
    t_preco = meta.get("regularMarketTime")
    # ajuste anterior: último fechamento diário anterior à data do preço atual
    d_preco = datetime.fromtimestamp(t_preco, BRT).date().isoformat() if t_preco else None
    anteriores = [h for h in hist if d_preco is None or h["data"] < d_preco]
    ajuste_ant = anteriores[-1]["fech"] if anteriores else meta.get("chartPreviousClose")
    var = None
    if preco is not None and ajuste_ant:
        var = round(preco - ajuste_ant, 4)
    return {
        "simbolo": simbolo,
        "preco": preco,
        "horario_brt": datetime.fromtimestamp(t_preco, BRT).strftime("%Y-%m-%d %H:%M") if t_preco else None,
        "ajuste_anterior": ajuste_ant,
        "variacao": var,
        "variacao_pct": round(var / ajuste_ant * 100, 2) if var is not None and ajuste_ant else None,
        "fechamentos": hist[-6:],
    }


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
    hoje = datetime.now(BRT).date()
    saida = {"gerado_em_brt": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"), "cbot": {}, "macro": {}, "bcb": {}}
    for chave, (raiz, meses, nome, unid) in CBOT.items():
        itens = []
        for letra, ano in contratos(meses, hoje):
            cod = f"{raiz}{letra}{str(ano)[-2:]}"
            d = tentar(yahoo, f"{cod}.CBT")
            d["contrato"] = cod
            itens.append(d)
        # reserva: contrato contínuo, caso os contratos específicos falhem
        if all("erro" in i for i in itens):
            d = tentar(yahoo, f"{raiz}=F")
            d["contrato"] = f"{raiz} contínuo"
            itens.append(d)
        saida["cbot"][chave] = {"nome": nome, "unidade": unid, "contratos": itens}
    for chave, (sim, nome) in MACRO.items():
        d = tentar(yahoo, sim)
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
    Path("dados/manha.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    erros = sum("erro" in c for p in saida["cbot"].values() for c in p["contratos"])
    print(json.dumps(saida, ensure_ascii=False)[:3000])
    print(f"contratos com erro: {erros}")


if __name__ == "__main__":
    main()
