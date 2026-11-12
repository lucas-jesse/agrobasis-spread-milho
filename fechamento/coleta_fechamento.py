"""Coleta do fechamento de mercado para o story diário do AgroBasis.

Roda no GitHub Actions no fim da tarde (depois do fechamento da CBOT, da B3 e do câmbio) e grava
dados/fechamento.json com preço de fechamento e variação do dia de:
- CBOT: soja, milho, trigo, farelo e óleo (contrato de referência, mesma convenção do coleta_manha.py);
- B3: milho (CCM, primeiro vencimento depois do mês corrente);
- Brasil e exterior: dólar comercial, Ibovespa, índice dólar (DXY) e petróleo Brent.
Fonte: scanner público do TradingView. Se a CBOT e a B3 não variaram nada, trata como feriado e não grava.

Uso (na raiz do repositório): python fechamento/coleta_fechamento.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coleta_manha import BRT, CBOT, LETRAS, contratos, tentar, tv_scan  # noqa: E402

MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
CCM_MESES = "FHKNUX"
# chave: (ticker, nome, complemento, formato)
OUTROS_BR = {"usdbrl": ("FX_IDC:USDBRL", "Dólar comercial", "venda", "rs4"),
             "ibov": ("BMFBOVESPA:IBOV", "Ibovespa", "pontos", "pts")}
EXTERIOR = {"dxy": ("TVC:DXY", "Índice dólar (DXY)", "", "pts2"),
            "brent": ("ICEEUR:BRN1!", "Petróleo Brent", "US$/barril", "usd")}
FORMATO_CBOT = {"soja": "usbu", "milho": "usbu", "trigo": "usbu", "farelo": "ust", "oleo": "uslb"}


def item(d, nome, compl, fmt):
    if not d or d.get("preco") is None or d.get("ajuste_anterior") is None:
        return None
    preco, ant = float(d["preco"]), float(d["ajuste_anterior"])
    return {"nome": nome, "compl": compl, "preco": preco, "anterior": ant, "formato": fmt,
            "var_pct": round((preco / ant - 1) * 100, 4) if ant else None}


def main():
    agora = datetime.now(BRT); hoje = agora.date()
    tickers, mapa = [], {}
    for chave, (raiz, meses, nome, _) in CBOT.items():
        letra, ano = contratos(meses, hoje, 1)[0]
        t = f"CBOT:{raiz}{letra}{ano}"; tickers.append(t)
        mapa[t] = ("cbot", chave, nome, f"{MES[LETRAS.index(letra)]}/{str(ano)[2:]}", FORMATO_CBOT[chave])
    letra, ano = contratos(CCM_MESES, hoje, 1)[0]
    t = f"BMFBOVESPA:CCM{letra}{ano}"; tickers.append(t)
    mapa[t] = ("brasil", "milho_b3", "Milho B3", f"{MES[LETRAS.index(letra)]}/{str(ano)[2:]}", "rssc")
    for grupo, dic in (("brasil", OUTROS_BR), ("exterior", EXTERIOR)):
        for chave, (t, nome, compl, fmt) in dic.items():
            tickers.append(t); mapa[t] = (grupo, chave, nome, compl, fmt)
    dados = tentar(tv_scan, tickers)
    if "erro" in dados and isinstance(dados["erro"], str):
        raise SystemExit(f"TradingView indisponível: {dados['erro']}")
    saida = {"data": hoje.isoformat(), "gerado_em_brt": agora.strftime("%Y-%m-%d %H:%M"),
             "fonte": "TradingView (CBOT, B3, câmbio e índices)", "cbot": [], "brasil": [], "exterior": []}
    for t, (grupo, chave, nome, compl, fmt) in mapa.items():
        x = item(dados.get(t), nome, compl, fmt)
        if x:
            x["chave"] = chave; saida[grupo].append(x)
        else:
            print(f"sem dado: {t}")
    # feriado ou mercado parado: nenhum grão variou na CBOT nem na B3
    graos = [x for x in saida["cbot"] + saida["brasil"] if x["chave"] in set(CBOT) | {"milho_b3"}]
    if len(saida["cbot"]) < 3 or all(abs(x["var_pct"] or 0) < 1e-9 for x in graos):
        print("sem pregão de grãos hoje (ou coleta incompleta): card não gerado")
        return False
    Path(RAIZ / "dados/fechamento.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(saida, ensure_ascii=False)[:2500])
    return True


if __name__ == "__main__":
    ok = main()
    # o passo seguinte do workflow só gera o card se houve coleta
    Path(RAIZ / "fechamento/.gerar").write_text("1" if ok else "0")
