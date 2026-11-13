"""Imagens 1200x1500 para os posts de LinkedIn de 13/11/2026 (Conab trigo e soja dos EUA x China)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path

F = "/home/claude/instagram/fonts/"
for f in ["geist-sans-400", "geist-sans-500", "geist-sans-600", "geist-sans-700", "sora-600", "sora-700"]:
    fm.fontManager.addfont(F + f + ".ttf")
SORA, GEIST = "Sora", "Geist"
VD, VC, CZ, TX, MT, MR, LN = "#1E4812", "#54931B", "#C9D1CB", "#222222", "#6b756d", "#A17149", "#E7ECE8"
OUT = Path("/home/claude/agrobasis-spread-milho/web/artigos/img")


def br(v, c=1):
    return f"{v:,.{c}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def base(titulo, sub):
    fig = plt.figure(figsize=(12, 15), dpi=100, facecolor="white")
    fig.text(0.07, 0.945, "AGROBASIS", fontfamily=SORA, fontweight=700, fontsize=17, color=VC)
    fig.text(0.07, 0.905, titulo, fontfamily=SORA, fontweight=700, fontsize=38, color=TX, va="top", linespacing=1.18)
    fig.text(0.07, 0.775, sub, fontfamily=GEIST, fontsize=20, color=MT, va="top")
    return fig


def rodape(fig, fonte):
    fig.add_artist(plt.Line2D([0.07, 0.93], [0.06, 0.06], color=LN, lw=1.5))
    fig.text(0.07, 0.035, fonte, fontfamily=GEIST, fontsize=15, color=MT)
    fig.text(0.93, 0.035, "agrobasis.com.br", fontfamily=GEIST, fontweight=600, fontsize=15, color=VD, ha="right")


def barras(ax, nomes, a, b, la, lb, dec=1):
    import numpy as np
    y = np.arange(len(nomes))[::-1] * 1.0
    h = 0.36
    ax.barh(y + h / 2, a, h, color=CZ, label=la)
    ax.barh(y - h / 2, b, h, color=VD, label=lb)
    m = max(max(a), max(b))
    for yy, v in zip(y + h / 2, a):
        ax.text(v + m * 0.015, yy, br(v, dec), va="center", fontfamily=GEIST, fontsize=19, color=MT)
    for yy, v in zip(y - h / 2, b):
        ax.text(v + m * 0.015, yy, br(v, dec), va="center", fontfamily=GEIST, fontweight=700, fontsize=21, color=VD)
    ax.set_yticks(y)
    ax.set_yticklabels(nomes, fontfamily=GEIST, fontweight=600, fontsize=22, color=TX)
    ax.set_xlim(0, m * 1.18)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0, pad=12)
    leg = ax.legend(loc="upper left", bbox_to_anchor=(-0.02, 1.1), ncol=2, frameon=False, prop={"family": GEIST, "size": 18}, handlelength=1.2)
    for t in leg.get_texts():
        t.set_color(MT)


def caixa(fig, x, y, w, rotulo, valor, detalhe, cor):
    fig.patches.append(plt.Rectangle((x, y), w, 0.105, transform=fig.transFigure, facecolor="#F4F7F4", edgecolor=LN, lw=1.5))
    fig.text(x + 0.025, y + 0.078, rotulo, fontfamily=GEIST, fontweight=600, fontsize=16, color=MT)
    fig.text(x + 0.025, y + 0.035, valor, fontfamily=SORA, fontweight=700, fontsize=31, color=cor)
    fig.text(x + 0.025, y + 0.012, detalhe, fontfamily=GEIST, fontsize=15, color=MT)


# ---------- 1. Conab: trigo ----------
T = {"Rio Grande do Sul": (3.5829, 2.0979), "Paraná": (2.7707, 1.8697), "Minas Gerais": (0.4237, 0.4644), "São Paulo": (0.3549, 0.3418), "Santa Catarina": (0.4074, 0.2512)}
perda = (3.5829 + 2.7707) - (2.0979 + 1.8697)
fig = base(f"Trigo: Paraná e Rio Grande do Sul\nperdem {br(perda)} milhões de toneladas", "Produção de trigo por estado, milhões de t")
ax = fig.add_axes([0.29, 0.245, 0.63, 0.46])
barras(ax, list(T), [v[0] for v in T.values()], [v[1] for v in T.values()], "Safra 2025", "Safra 2026 (Conab, nov)", 2)
caixa(fig, 0.07, 0.09, 0.42, "PRODUÇÃO NO BRASIL", "5,26 mi t", "−33% frente aos 7,87 mi t de 2025", MR)
caixa(fig, 0.51, 0.09, 0.42, "ESTOQUE DE PASSAGEM", "437 mil t", "eram 956 mil t na safra 2025", MR)
rodape(fig, "Fonte: Conab, 2º levantamento da safra 2026/27 (13/11/2026)")
fig.savefig(OUT / "linkedin-conab-trigo-nov26.png", facecolor="white")
plt.close(fig)

# ---------- 2. Export sales: soja China ----------
ch, cha, ou, oua, tt, tta = 16637.2, 464.0, 14751.4, 17183.5, 31388.6, 17647.5
fig = base("Soja dos EUA: a China explica\ntoda a alta das vendas", "Compromisso de exportação de soja dos EUA na mesma semana\ndo ano-safra, milhões de t")
ax = fig.add_axes([0.27, 0.27, 0.65, 0.40])
barras(ax, ["China", "Demais destinos", "Total"], [cha / 1e3, oua / 1e3, tta / 1e3], [ch / 1e3, ou / 1e3, tt / 1e3], "2025/26", "2026/27 (até 05/11)")
caixa(fig, 0.07, 0.09, 0.42, "CHINA", "16,6 mi t", "eram 0,5 mi t; 53% do total vendido", VD)
caixa(fig, 0.51, 0.09, 0.42, "SEM A CHINA", f"−{br((1 - ou / oua) * 100, 0)}%", "frente ao mesmo ponto de 2025/26", MR)
rodape(fig, "Fonte: USDA FAS, Export Sales (semana até 05/11/2026)")
fig.savefig(OUT / "linkedin-soja-china-nov26.png", facecolor="white")
plt.close(fig)
print("ok")
