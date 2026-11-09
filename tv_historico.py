"""Histórico de preços do TradingView pelo websocket público (dados com atraso, sem login).

Mesmo protocolo usado por bibliotecas como tvDatafeed. Usado pelo exporta_cot.py
quando o Yahoo bloqueia os servidores do GitHub.
"""
import json
import random
import re
import string

import pandas as pd
from websocket import create_connection


def _msg(func, params):
    m = json.dumps({"m": func, "p": params}, separators=(",", ":"))
    return f"~m~{len(m)}~m~{m}"


def _sessao(prefixo):
    return prefixo + "".join(random.choice(string.ascii_lowercase) for _ in range(12))


def historico(simbolo, intervalo="W", barras=1000, timeout=30):
    """Retorna Series de fechamentos indexada por data (ex.: simbolo='CBOT:ZS1!')."""
    ws = create_connection("wss://data.tradingview.com/socket.io/websocket",
                           header={"Origin": "https://data.tradingview.com"}, timeout=timeout)
    cs, qs = _sessao("cs_"), _sessao("qs_")
    for f, p in [("set_auth_token", ["unauthorized_user_token"]), ("chart_create_session", [cs, ""]),
                 ("quote_create_session", [qs]),
                 ("resolve_symbol", [cs, "symbol_1", '={"symbol":"' + simbolo + '","adjustment":"splits","session":"regular"}']),
                 ("create_series", [cs, "s1", "s1", "symbol_1", intervalo, barras])]:
        ws.send(_msg(f, p))
    bruto = ""
    while True:
        r = ws.recv()
        if re.match(r"~m~\d+~m~~h~\d+", r):  # heartbeat
            ws.send(r)
            continue
        bruto += r
        if "series_completed" in r or "symbol_error" in r or "critical_error" in r:
            break
    ws.close()
    m = re.search(r'"s":\[(.+?)\}\]', bruto)
    if not m:
        raise ValueError("TradingView sem dados: " + bruto[-200:])
    linhas = re.findall(r'"v":\[([^\]]+)\]', m.group(1))
    dados = [[float(x) for x in l.split(",")] for l in linhas]
    s = pd.Series([d[4] for d in dados], index=pd.to_datetime([d[0] for d in dados], unit="s").normalize())
    return s.sort_index()
