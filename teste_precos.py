"""Teste temporário: quais fontes de preço histórico respondem a partir do GitHub Actions."""
import json, requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
t = {}
def tenta(nome, fn):
    try:
        r = fn(); t[nome] = f"{r.status_code} {r.headers.get('Content-Type','')[:40]} {len(r.content)}b :: {r.text[:160]!r}"
    except Exception as e:
        t[nome] = f"ERRO {type(e).__name__} {str(e)[:150]}"
s = requests.Session(); s.headers.update(UA)
tenta("yahoo_q1", lambda: s.get("https://query1.finance.yahoo.com/v8/finance/chart/ZS=F", params={"range": "1y", "interval": "1wk"}, timeout=30))
tenta("yahoo_q2", lambda: s.get("https://query2.finance.yahoo.com/v8/finance/chart/ZS=F", params={"range": "1y", "interval": "1wk"}, timeout=30))
tenta("stooq_pl", lambda: s.get("https://stooq.pl/q/d/l/", params={"s": "zs.f", "i": "w"}, timeout=30))
tenta("nasdaq", lambda: s.get("https://api.nasdaq.com/api/quote/ZS%3ACMX/chart", params={"assetclass": "commodities", "fromdate": "2024-01-01", "todate": "2026-11-08"}, timeout=30))
def barchart():
    s.get("https://www.barchart.com/futures/quotes/ZS*0/overview", timeout=30)
    x = s.cookies.get("XSRF-TOKEN")
    h = {"X-XSRF-TOKEN": requests.utils.unquote(x)} if x else {}
    return s.get("https://www.barchart.com/proxies/timeseries/queryeod.ashx", params={"symbol": "ZS*0", "data": "weekly", "maxrecords": "50", "volume": "contract", "order": "asc"}, headers=h, timeout=30)
tenta("barchart", barchart)
tenta("tv_history", lambda: s.get("https://www.tradingview.com/symbols/CBOT-ZS1!/", timeout=30))
tenta("cme_settle", lambda: s.get("https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/320/FUT", params={"tradeDate": "11/06/2026", "strategy": "DEFAULT"}, timeout=30))
tenta("fred", lambda: s.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": "PSOYBUSDM"}, timeout=30))
tenta("investing", lambda: s.get("https://api.investing.com/api/financialdata/historical/8916", params={"start-date": "2025-01-01", "end-date": "2026-11-01", "time-frame": "Weekly", "add-missing-rows": "false"}, headers={"domain-id": "www"}, timeout=30))
open("dados/cot/_teste_precos.json", "w").write(json.dumps(t, ensure_ascii=False, indent=1))
print(json.dumps(t, indent=1))
