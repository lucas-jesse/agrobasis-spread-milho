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
