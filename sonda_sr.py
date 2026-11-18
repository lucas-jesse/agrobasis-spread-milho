"""Sonda temporária: estrutura do formulário de histórico de cotações (praça Santa Rosa)."""
import re, sys, requests
U = "https://www.coopermil.com/cotacao"
s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
r = s.get(U, timeout=30); h = r.text
print("GET", r.status_code, len(h))
for m in re.finditer(r"<(input|select|button)[^>]*>", h, re.I):
    print(m.group(0)[:220])
for m in re.finditer(r"<select[^>]*name=\"([^\"]+)\"[^>]*>(.*?)</select>", h, re.S | re.I):
    print("SELECT", m.group(1), re.findall(r'value="([^"]*)"', m.group(2))[:30])
f = {n: v for n, v in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', h)}
f.update({"ddlMes": "1", "ddlAno": "2026", "btnSend": "Consultar"})
r = s.post(U, data=f, timeout=30); h2 = r.text
print("POST", r.status_code, len(h2))
i = h2.find("02/01/2026"); print(h2[max(0, i - 1500):i + 1200])
