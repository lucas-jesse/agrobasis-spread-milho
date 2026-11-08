"""
AgroBasis: curva pública de soja CBOT (ZS) e dólar futuro B3 (DOL)
==================================================================

Gera dados/curva_soja.json, consumido pelo simulador de soja do site
(fetch direto no navegador, via jsDelivr com reserva no raw.githubusercontent),
no mesmo modelo do curva_ccm.json do simulador de milho.

Fontes (páginas públicas de contratos do TradingView):
  - CBOT-ZS1!          → preço de cada vencimento da soja em cents/bushel
  - BMFBOVESPA-DOL1!   → preço de cada vencimento do dólar em R$ por US$ 1.000

Regras de robustez:
  - cada fonte é buscada de forma independente; se uma falhar, o script
    mantém o último valor válido daquela fonte que já estava no JSON
    (e marca a falha em "avisos"), em vez de apagar a curva;
  - se as duas falharem, o JSON anterior fica intacto e o script termina
    com erro para o GitHub avisar por e-mail.
"""

import json
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

CAMINHO_JSON = "dados/curva_soja.json"
URL_CBOT = "https://br.tradingview.com/symbols/CBOT-ZS1!/contracts/"
URL_DOL = "https://br.tradingview.com/symbols/BMFBOVESPA-DOL1!/contracts/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


# ── conversões de preço ─────────────────────────────────────────────
def preco_cbot_cents(txt: str) -> float:
    """'1189'0' → 1189.0 | '1193'6' → 1193.75 (a parte após o apóstrofo é em oitavos de cent)."""
    t = txt.strip().replace("’", "'").replace(".", "").replace(",", "").replace(" ", "")
    m = re.fullmatch(r"(\d+)(?:'(\d))?", t)
    if not m:
        raise ValueError(f"preço CBOT em formato inesperado: {txt!r}")
    inteiro = int(m.group(1))
    oitavos = int(m.group(2) or 0)
    return round(inteiro + oitavos / 8, 4)


def preco_dol_brl(txt: str) -> float:
    """'5.524,0' (R$ por US$ 1.000) → 5.524 (R$ por US$ 1)."""
    t = txt.strip().replace(".", "").replace(",", ".").replace(" ", "")
    return round(float(t) / 1000, 5)


# ── leitura da tabela de contratos ──────────────────────────────────
def ler_tabela(url: str):
    """Devolve lista de (simbolo, vencimento AAAA-MM-DD, texto do preço)."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tabela = soup.find("table")
    if tabela is None:
        raise RuntimeError(f"tabela de contratos não encontrada em {url}")
    linhas = []
    for tr in tabela.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        a = tds[0].find("a")
        bruto = a.get_text(strip=True) if a else tds[0].get_text(strip=True)
        m = re.match(r"[A-Z]{2,3}[FGHJKMNQUVXZ]\d{4}", bruto)
        if not m:
            continue
        simbolo = m.group(0)
        venc = tds[1].get_text(strip=True)
        preco = tds[2].get_text(strip=True)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", venc) or preco in ("", "—", "-"):
            continue
        linhas.append((simbolo, venc, preco))
    if not linhas:
        raise RuntimeError(f"nenhum contrato válido lido em {url}")
    return linhas


def rotulo_curto(simbolo: str) -> str:
    """'ZSF2027' → 'ZSF27', 'DOLF2027' → 'DOLF27' (mesmo padrão de rótulo do curva_ccm.json)."""
    return simbolo[:-4] + simbolo[-2:]


def curva_cbot():
    return {
        rotulo_curto(s): {"vencimento": v, "cents_bu": preco_cbot_cents(p)}
        for s, v, p in ler_tabela(URL_CBOT)
    }


def curva_dolar():
    return {
        rotulo_curto(s): {"vencimento": v, "brl": preco_dol_brl(p)}
        for s, v, p in ler_tabela(URL_DOL)
    }


# ── execução ───────────────────────────────────────────────────────
def main():
    anterior = {}
    if os.path.exists(CAMINHO_JSON):
        with open(CAMINHO_JSON, encoding="utf-8") as f:
            anterior = json.load(f)

    agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    saida = {
        "atualizado_em": agora,
        "fonte": "TradingView (CBOT-ZS1! e BMFBOVESPA-DOL1!), preços de fechamento do dia",
        "unidades": {"cbot": "cents de US$ por bushel", "dolar": "R$ por US$"},
        "avisos": [],
    }

    falhas = 0
    for nome, func in (("cbot", curva_cbot), ("dolar", curva_dolar)):
        try:
            saida[nome] = func()
            print(f"{nome}: {len(saida[nome])} vencimentos lidos")
        except Exception as e:  # mantém o último valor bom desta fonte
            falhas += 1
            saida[nome] = anterior.get(nome, {})
            saida["avisos"].append(f"{nome}: falha na atualização de {agora}, mantido o valor anterior ({e})")
            print(f"AVISO {nome}: {e}", file=sys.stderr)

    if falhas == 2:
        print("As duas fontes falharam; JSON anterior mantido sem alteração.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(CAMINHO_JSON), exist_ok=True)
    with open(CAMINHO_JSON, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)
    print(f"JSON gravado em {CAMINHO_JSON}")


if __name__ == "__main__":
    main()
