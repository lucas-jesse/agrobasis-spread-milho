"""Card do Termômetro de venda AgroBasis para stories e grupo (1080x1920), a partir de dados/termometro.json.

Mostra soja e milho: a média das praças em ponteiro e a praça mais alta e a mais baixa de cada grão.
Saída: termometro/saida/AAAA-MM-DD.png e termometro/ultimo.png.
Uso (na raiz do repositório): python termometro/card_termometro.py
"""
import datetime as dt
import json
import math
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
A = RAIZ / "fechamento" / "assets"
S = 2
W, H, M = 1080 * S, 1920 * S, 84 * S
VERDE, VERDE2, AMBAR, LARANJA, MARROM = "#1E4812", "#54931B", "#D9A23B", "#C07A2E", "#A35A1E"
TEXTO, TEXTO2, LINHA, FUNDO = "#1d2420", "#6B716D", "#E3E7E4", "#F6F8F4"
ASSINATURA = "Lucas Jesse  ·  CNPI-P | CFP® | Ancord Agro 100"
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

sora = lambda t: ImageFont.truetype(str(A / "sora-700.ttf"), int(t * S))
geist = lambda t, w=400: ImageFont.truetype(str(A / f"geist-sans-{w}.ttf"), int(t * S))


def faixa(n):
    if n >= 70: return "Muito favorável à venda", VERDE
    if n >= 55: return "Favorável à venda", VERDE2
    if n >= 45: return "Neutro", AMBAR
    if n >= 30: return "Pouco favorável à venda", LARANJA
    return "Desfavorável à venda", MARROM


def centro(d, x, y, txt, fonte, cor):
    w = d.textlength(txt, font=fonte)
    d.text((x - w / 2, y), txt, font=fonte, fill=cor)


def ponteiro(d, cx, cy, r, nota, larg):
    """Semicírculo de 180° a 0° (esquerda para a direita) com 5 faixas de cor e o ponteiro."""
    faixas = [(0, 30, MARROM), (30, 45, LARANJA), (45, 55, AMBAR), (55, 70, VERDE2), (70, 100, VERDE)]
    caixa = [cx - r, cy - r, cx + r, cy + r]
    for a, b, cor in faixas:
        d.arc(caixa, start=180 + a * 1.8, end=180 + b * 1.8, fill=cor, width=larg)
    for v in (30, 45, 55, 70):   # separadores brancos
        ang = math.radians(180 + v * 1.8)
        d.line([(cx + (r - larg - 2 * S) * math.cos(ang), cy + (r - larg - 2 * S) * math.sin(ang)),
                (cx + (r + 2 * S) * math.cos(ang), cy + (r + 2 * S) * math.sin(ang))], fill=FUNDO, width=5 * S)
    ang = math.radians(180 + nota * 1.8)
    ponta = (cx + (r - larg - 18 * S) * math.cos(ang), cy + (r - larg - 18 * S) * math.sin(ang))
    perp = ang + math.pi / 2
    base = [(cx + 11 * S * math.cos(perp), cy + 11 * S * math.sin(perp)), (cx - 11 * S * math.cos(perp), cy - 11 * S * math.sin(perp))]
    d.polygon([ponta, base[0], base[1]], fill=TEXTO)
    d.ellipse([cx - 20 * S, cy - 20 * S, cx + 20 * S, cy + 20 * S], fill=TEXTO, outline=FUNDO, width=5 * S)
    for v in (0, 50, 100):
        ang = math.radians(180 + v * 1.8)
        tx, ty = cx + (r + 34 * S) * math.cos(ang), cy + (r + 34 * S) * math.sin(ang)
        centro(d, tx, ty - 14 * S, str(v), geist(22, 500), TEXTO2)


def bloco(im, d, y0, titulo, pracas):
    notas = {k: v["nota"] for k, v in pracas.items() if v.get("nota") is not None}
    media = sum(notas.values()) / len(notas)
    alto = max(notas, key=notas.get); baixo = min(notas, key=notas.get)
    f, cor = faixa(media)
    # cartão
    d.rounded_rectangle([M, y0, W - M, y0 + 640 * S], radius=36 * S, fill="#FFFFFF", outline=LINHA, width=2 * S)
    d.text((M + 44 * S, y0 + 38 * S), titulo, font=sora(44), fill=TEXTO)
    d.text((M + 44 * S, y0 + 100 * S), f"média de {len(notas)} praças", font=geist(26), fill=TEXTO2)
    cx, cy, r = W / 2, y0 + 372 * S, 178 * S
    ponteiro(d, cx, cy, r, media, 38 * S)
    centro(d, cx, cy + 22 * S, str(round(media)), sora(88), cor)
    centro(d, cx, cy + 122 * S, f, sora(32), cor)
    # rodapé do cartão: maior e menor
    yb = y0 + 560 * S
    d.line([M + 44 * S, yb - 16 * S, W - M - 44 * S, yb - 16 * S], fill=LINHA, width=2 * S)
    meio = W / 2
    for i, (rot, k) in enumerate((("Mais alta", alto), ("Mais baixa", baixo))):
        x = M + 44 * S if i == 0 else meio + 20 * S
        d.text((x, yb), rot.upper(), font=geist(20, 600), fill=TEXTO2)
        nome = k.replace(" RS", "").replace(" GO", "").replace(" PR", "").replace(" MT", "").replace(" SP", "").replace(" RO", "")
        d.text((x, yb + 30 * S), f"{nome}  {round(notas[k])}", font=geist(30, 600), fill=TEXTO)
    return media


def main():
    T = json.loads((RAIZ / "dados/termometro.json").read_text(encoding="utf-8"))
    ref = dt.date.fromisoformat(T["referencia_mercado"])
    im = Image.new("RGB", (W, H), FUNDO); d = ImageDraw.Draw(im)
    logo = Image.open(A / "logo.png").convert("RGBA")
    logo = logo.resize((round(logo.width * 62 * S / logo.height), 62 * S), Image.LANCZOS)
    im.paste(logo, (M, 80 * S), logo); d = ImageDraw.Draw(im)
    d.text((M, 188 * S), "TERMÔMETRO DE VENDA", font=geist(26, 600), fill=VERDE2)
    d.text((M, 226 * S), "O momento está bom", font=sora(60), fill=TEXTO)
    d.text((M, 300 * S), "para vender?", font=sora(60), fill=TEXTO)
    d.text((M, 386 * S), f"{DIAS[ref.weekday()].capitalize()}, {ref.day} de {MESES[ref.month - 1]} de {ref.year}  ·  de 0 a 100", font=geist(26), fill=TEXTO2)
    bloco(im, d, 448 * S, "Soja", T["soja"])
    bloco(im, d, 1110 * S, "Milho", T["milho"])
    # rodapé
    yb = H - 88 * S
    d.text((M, yb - 54 * S), "Veja a sua praça em agrobasis.com.br  ·  Painéis", font=geist(26, 600), fill=VERDE)
    d.text((M, yb - 14 * S), "Indicador educacional, não é recomendação de compra ou venda.", font=geist(21), fill=TEXTO2)
    d.text((M, yb + 20 * S), ASSINATURA, font=geist(21), fill=TEXTO2)
    out = im.resize((W // S, H // S), Image.LANCZOS)
    (AQUI / "saida").mkdir(exist_ok=True)
    caminho = AQUI / "saida" / f"{ref.isoformat()}.png"
    out.save(caminho, optimize=True)
    shutil.copy(caminho, AQUI / "ultimo.png")
    print(caminho)


if __name__ == "__main__":
    main()
