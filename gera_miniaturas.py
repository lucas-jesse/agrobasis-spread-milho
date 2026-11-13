"""Miniaturas dos dashboards para a página /dashboards/ do AgroBasis (web/miniaturas/<slug>.webp).

Abre cada dashboard (web/*.html) num Chromium sem interface, com os dados e bibliotecas servidos a partir do
próprio repositório (sem depender de rede), e fotografa um gráfico escolhido de cada painel.
Roda toda semana no GitHub Actions; o resultado é o gráfico real, com os dados daquela semana.

Requisitos: pip install playwright pillow && playwright install chromium; npm install echarts@5.5.1
Uso: python gera_miniaturas.py
"""
import io
import re
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "web/miniaturas"
FONTES = RAIZ / "fechamento/assets"
ECHARTS = next((p for p in [RAIZ / "node_modules/echarts/dist/echarts.min.js", Path("/home/claude/spread/node_modules/echarts/dist/echarts.min.js")] if p.exists()), None)
LARGURA = 900  # px da miniatura final

# @font-face apontando para as fontes do repositório (Geist e Sora)
CSS = "".join(f"@font-face{{font-family:'{f}';font-weight:{w};src:url(https://fontes.local/{n})}}" for f, w, n in [
    ("Geist", 400, "geist-sans-400.ttf"), ("Geist", 500, "geist-sans-500.ttf"), ("Geist", 600, "geist-sans-600.ttf"),
    ("Geist", 700, "geist-sans-600.ttf"), ("Sora", 600, "sora-600.ttf"), ("Sora", 700, "sora-700.ttf")])

PRACA = "var e=document.getElementById('abbPraca');e.value='{}';e.dispatchEvent(new Event('change'))"
# painel: (arquivo, gráfico, ajuste antes da foto). Basis sem as praças de Santa Rosa.
ALVOS = {
    "usda-complexo-soja": ("usda-soja.html", "#abuG4", ""),
    "usda-milho": ("usda-milho.html", "#abuG3", ""),
    "usda-trigo": ("usda-trigo.html", "#abuG0", ""),
    "exportacoes-eua-usda": ("exportacoes-eua.html", "#abcG0", ""),
    "condicao-de-safra-eua": ("safra-eua.html", "#abxG0", ""),
    "exportacao-e-importacao-de-graos": ("comex.html", "#abxG0", ""),
    "spread-milho-b3": ("spread-milho.html", "#absG1", ""),
    "basis-milho-brasil": ("basis-milho.html", "#abbG0", PRACA.format("Passo Fundo RS")),
    "basis-soja-brasil": ("basis-soja.html", "#abbG2", PRACA.format("Paranaguá")),
    "posicao-fundos-cftc": ("cot.html", "#abcG0", ""),
    "curva-do-dolar": ("curva-dolar.html", "#abdG0", ""),
    "safra-brasil-conab": ("conab.html", "#abcG0", ""),
    "plantio-e-colheita-brasil": ("progresso.html", "#abcG0", ""),
    "relacao-de-troca-fertilizantes": ("troca.html", "#abcG0", ""),
    "clima-el-nino": ("clima.html", "#abcG0", ""),
    "armazenagem-graos-brasil": ("armazenagem.html", "#abcG2", ""),
}


def arquivo_do_repo(url):
    """URLs do raw.githubusercontent e do jsDelivr deste repositório viram arquivos locais"""
    m = re.search(r"agrobasis-spread-milho(?:/|@)[^/]+/(.+?)(?:\?|$)", url)
    return RAIZ / m.group(1) if m else None


def rota(route):
    u = route.request.url
    if "echarts" in u and u.endswith(".js") and ECHARTS:
        return route.fulfill(path=str(ECHARTS), content_type="application/javascript")
    if "fonts.googleapis.com" in u:
        return route.fulfill(body=CSS, content_type="text/css")
    if u.startswith("https://fontes.local/"):
        return route.fulfill(path=str(FONTES / u.rsplit("/", 1)[1]), content_type="font/ttf")
    if u.startswith("https://agrobasis.test/"):
        html = (RAIZ / "web" / u.rsplit("/", 1)[1]).read_text(encoding="utf-8")
        return route.fulfill(body='<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#fff">' + html + "</body></html>",
                             content_type="text/html")
    p = arquivo_do_repo(u)
    if p and p.exists():
        return route.fulfill(path=str(p))
    return route.abort()


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    falhas = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        for slug, (pagina, alvo, ajuste) in ALVOS.items():
            pg = nav.new_page(viewport={"width": 760, "height": 1000}, device_scale_factor=2)
            pg.route("**/*", rota)
            erros = []
            pg.on("pageerror", lambda e: erros.append(str(e)))
            try:
                pg.goto("https://agrobasis.test/" + pagina)
                pg.wait_for_timeout(2500)
                if ajuste:
                    pg.evaluate(ajuste); pg.wait_for_timeout(800)
                el = pg.query_selector(alvo)
                el.scroll_into_view_if_needed(); pg.wait_for_timeout(600)
                img = Image.open(io.BytesIO(el.screenshot())).convert("RGB")
                img = img.resize((LARGURA, round(img.height * LARGURA / img.width)), Image.LANCZOS)
                img.save(SAIDA / f"{slug}.webp", "WEBP", quality=82, method=6)
                print(slug, img.size, erros[:1])
            except Exception as e:  # noqa: BLE001
                falhas.append(slug); print(slug, "FALHOU", e, erros[:1])
            pg.close()
        nav.close()
    if len(falhas) == len(ALVOS):
        raise SystemExit("nenhuma miniatura gerada")


if __name__ == "__main__":
    main()
