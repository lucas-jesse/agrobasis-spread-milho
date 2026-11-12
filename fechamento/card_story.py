"""Story de fechamento de mercado AgroBasis (1080x1920) a partir de dados/fechamento.json.

Manchete automática: maior alta e maior queda do dia entre os grãos (CBOT e milho B3);
o dólar entra na manchete quando varia mais de 0,8%.
Saída: fechamento/saida/AAAA-MM-DD.png e fechamento/ultimo.png (endereço fixo).

Uso (na raiz do repositório): python fechamento/card_story.py
"""
import datetime as dt
import json
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
A = AQUI / "assets"
S = 2                                   # desenha em 2x e reduz, para texto nítido
W, H, M = 1080 * S, 1920 * S, 90 * S
VERDE, MARROM, TEXTO, TEXTO2, LINHA, FAIXA = "#1E4812", "#A8642A", "#222222", "#6B716D", "#E3E7E4", "#F6F8F6"
ASSINATURA = "Lucas Jesse  ·  CNPI-P | CFP® | Ancord Agro 100"
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
GRAOS = {"soja", "milho", "trigo", "farelo", "oleo", "milho_b3"}

sora = lambda t: ImageFont.truetype(str(A / "sora-700.ttf"), int(t * S))
geist = lambda t, w=400: ImageFont.truetype(str(A / f"geist-sans-{w}.ttf"), int(t * S))


def br(v, d=2):
    s = f"{abs(v):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "−" + s if v < 0 else s


def preco(v, f):
    return {"usbu": lambda: f"US$ {br(v / 100)}/bu", "ust": lambda: f"US$ {br(v, 1)}/t", "uslb": lambda: f"US¢ {br(v)}/lb",
            "rssc": lambda: f"R$ {br(v)}/sc", "rs4": lambda: f"R$ {br(v, 4)}", "pts": lambda: br(v, 0),
            "pts2": lambda: br(v), "usd": lambda: f"US$ {br(v)}"}[f]()


def manchete(D):
    nome = lambda x: x["nome"].replace(" B3", "")
    onde = lambda x: "na B3" if x["chave"] == "milho_b3" else "em Chicago"
    g = [x for x in D["cbot"] + D["brasil"] if x["chave"] in GRAOS]
    alta, baixa = max(g, key=lambda x: x["var_pct"]), min(g, key=lambda x: x["var_pct"])
    dol = next((x for x in D["brasil"] if x["chave"] == "usdbrl"), None)
    if dol and abs(dol["var_pct"]) >= 0.8:
        x = alta if abs(alta["var_pct"]) >= abs(baixa["var_pct"]) else baixa
        return (f"Dólar {'sobe' if dol['var_pct'] > 0 else 'cai'} {br(abs(dol['var_pct']), 1)}%;\n"
                f"{nome(x).lower()} {'sobe' if x['var_pct'] > 0 else 'cai'} {br(abs(x['var_pct']), 1)}% {onde(x)}")
    if alta["var_pct"] > 0.5 and baixa["var_pct"] < -0.5:
        return (f"{nome(alta)} sobe {br(alta['var_pct'], 1)}% {onde(alta)};\n"
                f"{nome(baixa).lower()} cai {br(-baixa['var_pct'], 1)}% {onde(baixa)}")
    x = alta if abs(alta["var_pct"]) >= abs(baixa["var_pct"]) else baixa
    if abs(x["var_pct"]) < 0.3:
        return "Grãos de lado\nem Chicago e na B3"
    return f"{nome(x)} {'sobe' if x['var_pct'] > 0 else 'cai'} {br(abs(x['var_pct']), 1)}%\n{onde(x)}"


def quebrar(d, texto, fonte, larg):
    """quebra a manchete em linhas que caibam na largura"""
    out = []
    for bloco in texto.split("\n"):
        atual = ""
        for p in bloco.split():
            t = (atual + " " + p).strip()
            if d.textlength(t, font=fonte) > larg and atual:
                out.append(atual); atual = p
            else:
                atual = t
        out.append(atual)
    return out


def pilula(d, xr, cy, v, f):
    t = ("▲ " if v > 0.005 else "▼ " if v < -0.005 else "") + br(abs(v)) + "%"
    cor, fundo = (VERDE, "#E6F0DE") if v > 0.005 else (MARROM, "#F5E9DD") if v < -0.005 else (TEXTO2, "#EEF0EE")
    w = d.textlength(t, font=f) + 36 * S; h = f.size + 22 * S
    d.rounded_rectangle([xr - w, cy - h / 2, xr, cy + h / 2], radius=h / 2, fill=fundo)
    d.text((xr - w + 18 * S, cy - f.size * .62), t, font=f, fill=cor)


def secao(d, y, titulo, linhas, alt):
    fn, fp, fv = geist(29, 500), geist(21, 600), geist(29, 600)
    d.text((M, y), titulo.upper(), font=geist(20, 600), fill=TEXTO2)
    y += 36 * S; d.line([M, y, W - M, y], fill=TEXTO, width=2 * S)
    for i, x in enumerate(linhas):
        if i % 2 == 0:
            d.rectangle([M, y + S, W - M, y + alt], fill=FAIXA)
        cy = y + alt / 2
        d.text((M + 18 * S, cy - fn.size * .62 - (9 * S if x["compl"] else 0)), x["nome"], font=fn, fill=TEXTO)
        if x["compl"]:
            d.text((M + 18 * S, cy + 8 * S), x["compl"], font=geist(18), fill=TEXTO2)
        t = preco(x["preco"], x["formato"])
        d.text((W - M - 220 * S - d.textlength(t, font=fv), cy - fv.size * .62), t, font=fv, fill=TEXTO)
        pilula(d, W - M - 16 * S, cy, x["var_pct"], fp)
        y += alt; d.line([M, y, W - M, y], fill=LINHA, width=S)
    return y


def gerar(D):
    data = dt.date.fromisoformat(D["data"])
    im = Image.new("RGB", (W, H), "#FFFFFF")
    logo = Image.open(A / "logo.png").convert("RGBA"); logo = logo.resize((round(logo.width * 64 * S / logo.height), 64 * S), Image.LANCZOS)
    topo = 130 * S
    im.paste(logo, (M - 4 * S, topo + 18 * S - logo.height // 2), logo); d = ImageDraw.Draw(im)
    t = f"{data:%d/%m/%Y}"; d.text((W - M - d.textlength(t, font=geist(26, 600)), topo - 2 * S), t, font=geist(26, 600), fill=TEXTO)
    t = DIAS[data.weekday()]; d.text((W - M - d.textlength(t, font=geist(20)), topo + 32 * S), t, font=geist(20), fill=TEXTO2)
    y = topo + 110 * S
    d.rectangle([M, y, M + 70 * S, y + 5 * S], fill=VERDE)
    d.text((M, y + 28 * S), "Fechamento de mercado", font=geist(30, 500), fill=TEXTO2)
    y += 74 * S
    f = sora(46)
    for l in quebrar(d, manchete(D), f, W - 2 * M):
        d.text((M, y), l, font=f, fill=VERDE); y += 58 * S
    y += 28 * S
    alt = 72 * S
    y = secao(d, y, "Chicago · CBOT", D["cbot"], alt) + 24 * S
    y = secao(d, y, "Brasil", D["brasil"], alt) + 24 * S
    secao(d, y, "Exterior", D["exterior"], alt)
    # rodapé acima da área coberta pela barra de resposta do story
    yr = H - 360 * S
    d.line([M, yr, W - M, yr], fill=LINHA, width=2 * S)
    d.text(((W - d.textlength(ASSINATURA, font=geist(25, 500))) / 2, yr + 30 * S), ASSINATURA, font=geist(25, 500), fill=TEXTO)
    u = "agrobasis.com.br"; f = sora(30); w = d.textlength(u, font=f) + 80 * S
    d.rounded_rectangle([(W - w) / 2, yr + 96 * S, (W + w) / 2, yr + 176 * S], radius=40 * S, fill=VERDE)
    d.text(((W - d.textlength(u, font=f)) / 2, yr + 116 * S), u, font=f, fill="#FFFFFF")
    return im.resize((W // S, H // S), Image.LANCZOS), data


if __name__ == "__main__":
    D = json.loads((RAIZ / "dados/fechamento.json").read_text(encoding="utf-8"))
    im, data = gerar(D)
    (AQUI / "saida").mkdir(exist_ok=True)
    p = AQUI / "saida" / f"{data:%Y-%m-%d}.png"
    im.save(p, optimize=True); shutil.copy(p, AQUI / "ultimo.png")
    print(manchete(D).replace("\n", " "), "->", p)
