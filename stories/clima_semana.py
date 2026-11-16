"""Story 1080x1920 com a chuva prevista da semana nos polos (ECMWF), em mm e contra a normal 1991-2020.
Uso: python stories/clima_semana.py  -> stories/saida/clima-semana-AAAA-MM-DD.png"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "termometro"))
import card_termometro as C  # noqa: E402  (fontes, cores e logo do padrão AgroBasis)

S = C.S; W, H, M = C.W, C.H, C.M
d = None
PERIODO = "16 a 22 de novembro"
ARQ = "clima-semana-2026-11-16.png"
# (polo, UF, chuva prevista mm, normal mm) - ECMWF IFS 0,25, rodada de 16/11 ~06h
POLOS = [("Sorriso", "MT", 91, 46), ("Primavera do Leste", "MT", 69, 44), ("Rio Verde", "GO", 36, 49),
         ("Dourados", "MS", 35, 34), ("Unaí", "MG", 101, 45), ("Porto Nacional", "TO", 101, 52),
         ("Luís E. Magalhães", "BA", 91, 39), ("Balsas", "MA", 55, 31), ("Cascavel", "PR", 63, 34),
         ("Chapecó", "SC", 89, 40), ("Passo Fundo", "RS", 97, 40)]
AZUL, VERDE, AMBAR, MARROM = "#2F6FA8", "#3d7a14", "#C9902B", "#A35A1E"


def cor(p):
    return AZUL if p >= 130 else VERDE if p >= 85 else AMBAR if p >= 60 else MARROM


def main():
    im = Image.new("RGB", (W, H), C.FUNDO); g = ImageDraw.Draw(im)
    logo = Image.open(C.A / "logo.png").convert("RGBA")
    logo = logo.resize((round(logo.width * 62 * S / logo.height), 62 * S), Image.LANCZOS)
    im.paste(logo, (M, 120 * S), logo); g = ImageDraw.Draw(im)
    g.text((M, 228 * S), "CLIMA DA SEMANA", font=C.geist(26, 600), fill=C.VERDE2)
    g.text((M, 266 * S), "Chuva volta forte", font=C.sora(62), fill=C.TEXTO)
    g.text((M, 344 * S), "ao Mato Grosso", font=C.sora(62), fill=C.TEXTO)
    g.text((M, 432 * S), f"Chuva prevista de {PERIODO}, em mm", font=C.geist(27), fill=C.TEXTO2)
    # cartão com as barras
    y0, lh = 500 * S, 78 * S
    altura = 70 * S + lh * len(POLOS) + 20 * S
    g.rounded_rectangle([M, y0, W - M, y0 + altura], radius=34 * S, fill="#FFFFFF", outline=C.LINHA, width=2 * S)
    x_nome, x_bar, x_fim = M + 40 * S, M + 330 * S, W - M - 150 * S
    vmax = 110
    X = lambda v: x_bar + v / vmax * (x_fim - x_bar)
    g.text((x_nome, y0 + 26 * S), "POLO", font=C.geist(19, 600), fill=C.TEXTO2)
    g.text((x_bar, y0 + 26 * S), "PREVISÃO  |  NORMAL", font=C.geist(19, 600), fill=C.TEXTO2)
    g.text((x_fim + 14 * S, y0 + 26 * S), "% NORMAL", font=C.geist(19, 600), fill=C.TEXTO2)
    for i, (nome, uf, mm, nrm) in enumerate(POLOS):
        y = y0 + 70 * S + i * lh
        if i:
            g.line([x_nome, y - 4 * S, W - M - 40 * S, y - 4 * S], fill="#EEF1EE", width=2 * S)
        p = round(mm / nrm * 100); c = cor(p)
        g.text((x_nome, y + 6 * S), nome, font=C.geist(27, 600), fill=C.TEXTO)
        g.text((x_nome, y + 40 * S), uf, font=C.geist(20, 500), fill=C.TEXTO2)
        g.rounded_rectangle([x_bar, y + 20 * S, x_fim, y + 52 * S], radius=8 * S, fill="#EEF2EE")
        g.rounded_rectangle([x_bar, y + 20 * S, max(X(min(mm, vmax)), x_bar + 12 * S), y + 52 * S], radius=8 * S, fill=c)
        xn = X(nrm)
        g.line([xn, y + 12 * S, xn, y + 60 * S], fill=C.TEXTO, width=4 * S)
        txt = f"{mm}"
        tw = g.textlength(txt, font=C.sora(22))
        if X(mm) - x_bar > tw + 30 * S:
            g.text((X(min(mm, vmax)) - tw - 12 * S, y + 22 * S), txt, font=C.sora(22), fill="#FFFFFF")
        else:
            g.text((X(mm) + 10 * S, y + 22 * S), txt, font=C.sora(22), fill=c)
        g.text((x_fim + 14 * S, y + 18 * S), f"{p}%", font=C.sora(30), fill=c)
    # legenda
    yl = y0 + altura + 28 * S
    g.line([M + 6 * S, yl + 4 * S, M + 6 * S, yl + 34 * S], fill=C.TEXTO, width=4 * S)
    g.text((M + 22 * S, yl + 2 * S), "chuva normal da semana (média 1991-2020)", font=C.geist(22), fill=C.TEXTO2)
    x = M
    for t, cc in (("acima do normal", AZUL), ("normal", VERDE), ("abaixo do normal", AMBAR)):
        g.rounded_rectangle([x, yl + 52 * S, x + 22 * S, yl + 74 * S], radius=5 * S, fill=cc)
        g.text((x + 32 * S, yl + 48 * S), t, font=C.geist(22), fill=C.TEXTO2)
        x += 32 * S + g.textlength(t, font=C.geist(22)) + 34 * S
    yb = H - 290 * S
    g.text((M, yb), "Previsão para a sua cidade:", font=C.geist(27), fill=C.TEXTO2)
    g.text((M, yb + 40 * S), "agrobasis.com.br  ·  Clima", font=C.sora(34), fill=C.VERDE)
    g.text((M, yb + 104 * S), "Modelo europeu (ECMWF). Previsão sujeita a mudanças.", font=C.geist(21), fill=C.TEXTO2)
    g.text((M, yb + 138 * S), C.ASSINATURA, font=C.geist(21), fill=C.TEXTO2)
    (RAIZ / "stories/saida").mkdir(exist_ok=True)
    out = RAIZ / "stories/saida" / ARQ
    im.resize((W // S, H // S), Image.LANCZOS).save(out, optimize=True)
    print(out)


if __name__ == "__main__":
    main()
