"""Carrosséis Instagram (1080x1350, PNG; PDF também) de 13/11/2026: Conab 2º levantamento 2026/27 e USDA Export Sales (semana até 05/11).

Mesma identidade dos carrosséis do Instagram (claude/instagram/carrossel_usda_v2.py): fundo branco, logo, contador,
assinatura com credenciais. Renderiza em 2x e reduz.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

S = 2
W, H = 1080 * S, 1350 * S
M = 90 * S
VERDE, VERDE2, MARROM, TEXTO, TEXTO2, LINHA, FAIXA = "#1E4812", "#54931B", "#A17149", "#222222", "#6B716D", "#E3E7E4", "#F6F8F6"
FD = Path("/home/claude/instagram/fonts")
OUT = Path("/home/claude/agrobasis-spread-milho/web/artigos/img/instagram-nov13"); OUT.mkdir(parents=True, exist_ok=True)
LOGO_PNG = "/tmp/claude-tool-results/fa480465-bbb1-558a-82f8-98335ae36660/project-file-cf879452-5de7-4cca-a210-857a33f4fba0-Logo_Agrobasis-f1ee6bb5.png"
ASSINATURA = "Lucas Jesse  ·  CNPI-P | CFP® | Ancord Agro 100"

sora = lambda t, w=600: ImageFont.truetype(str(FD / f"sora-{w}.ttf"), t * S)
geist = lambda t, w=400: ImageFont.truetype(str(FD / f"geist-sans-{w}.ttf"), t * S)


def _logo(alt):
    lg = Image.open(LOGO_PNG).convert("RGBA")
    lg = lg.crop(lg.split()[3].point(lambda v: 255 if v > 24 else 0).getbbox())
    return lg.resize((round(lg.width * alt / lg.height), alt), Image.LANCZOS)


LOGO = _logo(64 * S)


class Carrossel:
    def __init__(self, nome, fonte, total):
        self.nome, self.fonte, self.total, self.paginas = nome, fonte, total, []

    def base(self, capa=False):
        n = len(self.paginas) + 1
        im = Image.new("RGB", (W, H), "#FFFFFF"); d = ImageDraw.Draw(im)
        y = 78 * S
        im.paste(LOGO, (M - 4 * S, y + 18 * S - LOGO.height // 2), LOGO); d = ImageDraw.Draw(im)
        c = f"{n} / {self.total}"; fc = geist(24, 400)
        d.text((W - M - d.textlength(c, font=fc), y + 4 * S), c, font=fc, fill=TEXTO2)
        yr = H - 150 * S
        d.line([M, yr, W - M, yr], fill=LINHA, width=2 * S)
        d.text((M, yr + 26 * S), ASSINATURA, font=geist(25, 500), fill=TEXTO)
        d.text((M, yr + 66 * S), self.fonte, font=geist(19, 400), fill=TEXTO2)
        if capa:
            seta(d, yr - 120 * S)
        return im, d

    def salvar(self, im):
        self.paginas.append(im.resize((W // S, H // S), Image.LANCZOS))

    def pdf(self):
        for i, p in enumerate(self.paginas, 1):
            p.save(OUT / f"{self.nome}_{i:02d}.png")
        self.paginas[0].save(OUT / f"{self.nome}.pdf", save_all=True, append_images=self.paginas[1:], resolution=150)
        assert len(self.paginas) == self.total, (self.nome, len(self.paginas))


def seta(d, y, texto="Arraste para o lado"):
    fa = geist(26, 500); r = 30 * S
    cx, cy = W - M - r, y + 62 * S
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=VERDE)
    d.line([cx - 13 * S, cy, cx + 11 * S, cy], fill="#FFFFFF", width=4 * S)
    d.line([cx + 2 * S, cy - 10 * S, cx + 12 * S, cy], fill="#FFFFFF", width=4 * S)
    d.line([cx + 2 * S, cy + 10 * S, cx + 12 * S, cy], fill="#FFFFFF", width=4 * S)
    d.text((cx - r - 22 * S - d.textlength(texto, font=fa), cy - 17 * S), texto, font=fa, fill=TEXTO)


def quebrar(d, texto, fonte, larg):
    linhas, atual = [], ""
    for p in texto.split():
        t = (atual + " " + p).strip()
        if d.textlength(t, font=fonte) <= larg:
            atual = t
        else:
            linhas.append(atual); atual = p
    return linhas + [atual]


def paragrafo(d, x, y, texto, fonte, cor, larg, entre=1.42):
    alt = fonte.size * entre
    for l in quebrar(d, texto, fonte, larg):
        d.text((x, y), l, font=fonte, fill=cor); y += alt
    return y


def cabecalho(d, kicker, titulo, y=190):
    d.text((M, y * S), kicker, font=geist(28, 500), fill=TEXTO2)
    return paragrafo(d, M - 3 * S, (y + 46) * S, titulo, sora(64, 700), TEXTO, W - 2 * M, 1.2)


def tabela(d, y, colunas, linhas, destaque, larg_rot=330):
    """colunas: [(titulo, subtitulo)] após a coluna de rótulos; linhas: [(rotulo, sub, [valores], [cores ou None])]."""
    n = len(colunas); x0 = M + larg_rot * S; passo = (W - M - 20 * S - x0) / n
    xs = [x0 + passo * (i + 1) for i in range(n)]
    fh, fs = geist(22, 600), geist(19, 400)
    for (t1, t2), x in zip(colunas, xs):
        d.text((x - d.textlength(t1, font=fh), y), t1, font=fh, fill=TEXTO)
        d.text((x - d.textlength(t2, font=fs), y + 30 * S), t2, font=fs, fill=TEXTO2)
    y += 74 * S
    d.line([M, y, W - M, y], fill=TEXTO, width=2 * S)
    alt = (112 if len(linhas) <= 6 else 96) * S
    for i, (rot, sub, vals, cores) in enumerate(linhas):
        if i % 2 == 0:
            d.rectangle([M, y + 1 * S, W - M, y + alt], fill=FAIXA)
        cy = y + alt / 2
        d.text((M + 20 * S, cy - (36 if sub else 20) * S), rot, font=geist(30, 500), fill=TEXTO)
        if sub:
            d.text((M + 20 * S, cy + 8 * S), sub, font=geist(19, 400), fill=TEXTO2)
        for j, (v, x) in enumerate(zip(vals, xs)):
            f = geist(32, 700) if j == destaque else geist(32, 400)
            cor = (cores[j] if cores and cores[j] else (TEXTO if j == destaque else TEXTO2))
            d.text((x - d.textlength(v, font=f), cy - 20 * S), v, font=f, fill=cor)
        y += alt
        d.line([M, y, W - M, y], fill=LINHA, width=1 * S)
    return y


def cartoes(d, y, itens, cols=2, alt=230):
    """itens: [(rotulo, valor, detalhe, cor)]."""
    gap = 24 * S; lw = (W - 2 * M - gap * (cols - 1)) / cols
    for i, (rot, val, det, cor) in enumerate(itens):
        cx = M + (i % cols) * (lw + gap); cy = y + (i // cols) * (alt * S + gap)
        d.rounded_rectangle([cx, cy, cx + lw, cy + alt * S], radius=18 * S, fill=FAIXA, outline=LINHA, width=2 * S)
        d.text((cx + 30 * S, cy + 28 * S), rot.upper(), font=geist(20, 600), fill=TEXTO2)
        d.text((cx + 28 * S, cy + 66 * S), val, font=sora(58, 700), fill=cor)
        paragrafo(d, cx + 30 * S, cy + 158 * S, det, geist(22, 400), TEXTO2, lw - 60 * S, 1.3)
    return y + ((len(itens) + cols - 1) // cols) * (alt * S + gap)


def capa(c, kicker, titulo, sub, numero, num_rot, num_det):
    im, d = c.base(capa=True)
    d.rectangle([M, 250 * S, M + 70 * S, 256 * S], fill=VERDE)
    d.text((M, 290 * S), kicker, font=geist(34, 500), fill=TEXTO2)
    y = paragrafo(d, M - 4 * S, 350 * S, titulo, sora(84, 700), TEXTO, W - 2 * M, 1.16)
    y = paragrafo(d, M, y + 26 * S, sub, geist(32, 400), TEXTO2, W - 2 * M, 1.4)
    y = max(y + 60 * S, 820 * S)
    d.line([M, y, W - M, y], fill=TEXTO, width=2 * S)
    d.text((M, y + 30 * S), num_rot, font=geist(26, 500), fill=TEXTO2)
    d.text((M - 3 * S, y + 72 * S), numero, font=sora(96, 700), fill=VERDE)
    d.text((M, y + 200 * S), num_det, font=geist(26, 400), fill=TEXTO2)
    c.salvar(im)


def fechamento(c, kicker, titulo, pontos, link, chamada):
    im, d = c.base()
    y = cabecalho(d, kicker, titulo)
    y += 30 * S
    for t, txt in pontos:
        d.rectangle([M, y + 10 * S, M + 8 * S, y + 46 * S], fill=VERDE2)
        d.text((M + 30 * S, y), t, font=geist(31, 700), fill=TEXTO)
        y = paragrafo(d, M + 30 * S, y + 48 * S, txt, geist(26, 400), TEXTO2, W - 2 * M - 30 * S, 1.42) + 34 * S
    yb = H - 150 * S - 190 * S
    d.rounded_rectangle([M, yb, W - M, yb + 150 * S], radius=18 * S, fill=VERDE)
    d.text((M + 36 * S, yb + 32 * S), chamada, font=geist(26, 500), fill="#CFE3BF")
    d.text((M + 36 * S, yb + 76 * S), link, font=geist(32, 700), fill="#FFFFFF")
    c.salvar(im)


# =====================================================================================
# 1) Conab
# =====================================================================================
c = Carrossel("conab-novembro-2026", "Fonte: Conab, 2º levantamento da safra de grãos 2026/27 (13/11/2026). Elaboração: AgroBasis.", 7)
capa(c, "Conab · 2º levantamento da safra 2026/27", "A Conab cortou a safra. O corte veio do trigo.",
     "Soja e milho ficaram onde estavam. O que mudou e o que isso significa para o mercado.",
     "366,1 mi t", "Safra brasileira de grãos 2026/27", "−1,0 milhão de t frente a outubro  ·  +1,3% sobre 2025/26")

im, d = c.base()
y = cabecalho(d, "Os números do levantamento", "Produção por cultura")
V, Mr = VERDE2, MARROM
tabela(d, y + 50 * S, [("2025/26", "safra passada"), ("Outubro", "previsão"), ("Novembro", "previsão"), ("Mudança", "no mês")], [
    ("Total de grãos", "milhões de t", ["361,5", "367,1", "366,1", "−1,0"], [None, None, None, Mr]),
    ("Soja", "milhões de t", ["180,4", "181,6", "181,6", "–"], None),
    ("Milho total", "milhões de t", ["144,5", "148,0", "148,0", "–"], None),
    ("Trigo", "safra 2025 x 2026", ["7,87", "5,73", "5,26", "−0,47"], [None, None, None, Mr]),
    ("Arroz", "milhões de t", ["11,1", "10,8", "10,6", "−0,2"], [None, None, None, Mr]),
    ("Feijão", "milhões de t", ["3,0", "2,9", "2,9", "–"], None)], destaque=2)
c.salvar(im)

im, d = c.base()
y = cabecalho(d, "Trigo", "Paraná e Rio Grande do Sul perdem 2,4 milhões de t")
y = tabela(d, y + 50 * S, [("Safra 2025", "colhida"), ("Safra 2026", "Conab, out"), ("Safra 2026", "Conab, nov"), ("Sobre 2025", "variação")], [
    ("Rio Grande do Sul", "milhões de t", ["3,58", "2,26", "2,10", "−41%"], [None, None, None, Mr]),
    ("Paraná", "milhões de t", ["2,77", "2,16", "1,87", "−33%"], [None, None, None, Mr]),
    ("Santa Catarina", "milhões de t", ["0,41", "0,27", "0,25", "−38%"], [None, None, None, Mr]),
    ("Minas Gerais", "milhões de t", ["0,42", "0,46", "0,46", "+10%"], [None, None, None, V]),
    ("Brasil", "milhões de t", ["7,87", "5,73", "5,26", "−33%"], [None, None, None, Mr])], destaque=2)
paragrafo(d, M, y + 30 * S, "Clima desfavorável no Paraná e no Rio Grande do Sul derrubou a produtividade e a qualidade. Uma parte maior do trigo deve ir para ração.", geist(25, 400), TEXTO2, W - 2 * M)
c.salvar(im)

im, d = c.base()
y = cabecalho(d, "Trigo", "Menos produção, estoque curto e mais importação")
cartoes(d, y + 50 * S, [
    ("Produtividade no Paraná", "2.600 kg/ha", "eram 3.383 kg/ha na safra 2025, queda de 23%", Mr),
    ("Produtividade no RS", "2.727 kg/ha", "eram 3.097 kg/ha na safra 2025, queda de 12%", Mr),
    ("Estoque de passagem", "437 mil t", "no fim da safra 2026, contra 956 mil t em 2025", Mr),
    ("Corte em um mês", "474 mil t", "de 5,73 para 5,26 milhões de t entre outubro e novembro", Mr)])
c.salvar(im)

im, d = c.base()
y = cabecalho(d, "Soja · 181,6 milhões de t, sem mudança", "El Niño já aparece na conta por estado")
y = tabela(d, y + 50 * S, [("2025/26", "mi t"), ("2026/27", "mi t"), ("Produtiv.", "sc/ha 25/26"), ("Produtiv.", "sc/ha 26/27")], [
    ("Mato Grosso", None, ["51,6", "50,9", "66,2", "64,8"], [None, None, None, Mr]),
    ("Paraná", None, ["22,0", "21,8", "63,0", "62,5"], None),
    ("Goiás", None, ["20,2", "20,3", "65,2", "65,1"], None),
    ("Rio Grande do Sul", None, ["18,6", "20,2", "46,1", "49,9"], [None, None, None, V]),
    ("Mato Grosso do Sul", None, ["15,8", "15,9", "60,0", "59,6"], None)], destaque=1)
paragrafo(d, M, y + 30 * S, "O El Niño costuma favorecer o Sul e penalizar o Norte e o Nordeste. A Conab já reduziu a produtividade esperada em Mato Grosso, Bahia e Tocantins e aumentou a do Rio Grande do Sul.", geist(25, 400), TEXTO2, W - 2 * M)
c.salvar(im)

im, d = c.base()
y = cabecalho(d, "Milho · 148,0 milhões de t, sem mudança", "Exportação menor, estoque maior")
cartoes(d, y + 50 * S, [
    ("Exportação 2025/26", "40,9 mi t", "6,8% abaixo da estimativa anterior", Mr),
    ("Exportação 2026/27", "43 mi t", "projeção inicial da Conab", TEXTO),
    ("Estoque em jan/2027", "19,0 mi t", "estoque de passagem revisado para cima", VERDE),
    ("Estoque em jan/2028", "20,9 mi t", "oferta folgada também no próximo ciclo", VERDE)])
c.salvar(im)

fechamento(c, "O que muda no mercado", "Três leituras do relatório", [
    ("Trigo", "Com 5,3 milhões de t e estoque curto, a dependência de importação aumenta. O trigo de qualidade panificável tende a ganhar prêmio sobre o lote de ração."),
    ("Milho", "Menos exportação e estoque de 19 milhões de t pesam nos preços do interior durante o plantio da safrinha."),
    ("Soja", "Nada mudou no número, mas o clima de dezembro e janeiro decide os próximos levantamentos.")],
    "agrobasis.com.br  ·  link na bio", "Painel de safra por estado, atualizado a cada levantamento")
c.pdf()

# =====================================================================================
# 2) Vendas de exportação dos EUA
# =====================================================================================
e = Carrossel("vendas-eua-semana-05-11-2026", "Fonte: USDA FAS, Export Sales (semana até 05/11/2026) e WASDE. Elaboração: AgroBasis.", 6)
capa(e, "USDA · vendas de exportação · semana até 05/11", "A China sustenta a soja americana",
     "Sem ela, as vendas cairiam 14%. No milho, a maior venda semanal da safra.",
     "31,4 mi t", "Soja dos EUA já vendida para a safra 2026/27", "+78% sobre o mesmo ponto de 2025/26")

im, d = e.base()
y = cabecalho(d, "Os números da semana", "Vendas e compromisso acumulado")
y = tabela(d, y + 50 * S, [("Semana", "mil t"), ("Acumulado", "mi t"), ("Ano ant.", "variação"), ("Vendido", "da projeção"), ("Média", "5 anos")], [
    ("Soja", None, ["1.155", "31,4", "+78%", "67%", "56%"], [None, None, V, V, None]),
    ("Milho", None, ["2.881", "27,7", "−28%", "33%", "42%"], [None, None, Mr, Mr, None]),
    ("Trigo", None, ["183", "12,2", "−29%", "60%", "63%"], [None, None, Mr, None, None]),
    ("Farelo", None, ["361", "6,8", "+2%", "33%", "38%"], None),
    ("Óleo", None, ["2", "0,04", "−78%", "22%", "24%"], None)], destaque=1, larg_rot=150)
paragrafo(d, M, y + 30 * S, "Vendido: quanto da exportação projetada pelo USDA já foi contratado. Média: o mesmo indicador nas cinco safras anteriores, na mesma semana.", geist(25, 400), TEXTO2, W - 2 * M)
e.salvar(im)

im, d = e.base()
y = cabecalho(d, "Soja", "Sem a China, as vendas caem 14%")
y = tabela(d, y + 50 * S, [("2025/26", "mesma semana"), ("2026/27", "até 05/11"), ("Variação", "")], [
    ("China", "milhões de t", ["0,5", "16,6", "36x"], [None, None, V]),
    ("Demais destinos", "milhões de t", ["17,2", "14,8", "−14%"], [None, None, Mr]),
    ("Total", "milhões de t", ["17,6", "31,4", "+78%"], [None, None, V])], destaque=1)
cartoes(d, y + 50 * S, [("Fatia da China", "53%", "de todo o compromisso de soja dos EUA", VERDE),
                        ("Destino a definir", "5,4 mi t", "parte tende a virar China nas próximas semanas", TEXTO)])
e.salvar(im)

im, d = e.base()
y = cabecalho(d, "Milho", "A maior venda semanal da safra, puxada pelo México")
cartoes(d, y + 50 * S, [
    ("Vendido na semana", "2,88 mi t", "mais que o dobro da semana anterior (1,30 mi t)", VERDE),
    ("Só o México", "1,96 mi t", "68% do total da semana", VERDE),
    ("Acumulado", "27,7 mi t", "28% abaixo de 2025/26 e 33% da projeção (média de 42%)", Mr),
    ("Embarque necessário", "1,70 mi t", "por semana até agosto, contra 0,81 mi t nas últimas 4", Mr)])
e.salvar(im)

im, d = e.base()
y = cabecalho(d, "Trigo, farelo e óleo", "O resto do complexo")
y += 40 * S
for t, txt in [("Trigo: semana fraca", "183 mil t vendidas, ante 538 mil na semana anterior. O acumulado de 12,2 milhões de t está 29% abaixo do ano passado, mas perto da média histórica como fatia da projeção."),
               ("Farelo de soja: ritmo estável", "361 mil t vendidas, com Filipinas, México, Colômbia e Vietnã. A projeção do USDA, de 20,6 milhões de t, exige um ritmo forte daqui para frente."),
               ("Óleo de soja: fora do mercado externo", "Só 40 mil t contratadas, quase tudo para o Canadá. O mandato de biocombustíveis absorve o óleo dentro dos EUA.")]:
    d.rectangle([M, y + 10 * S, M + 8 * S, y + 46 * S], fill=VERDE2)
    d.text((M + 30 * S, y), t, font=geist(31, 700), fill=TEXTO)
    y = paragrafo(d, M + 30 * S, y + 50 * S, txt, geist(26, 400), TEXTO2, W - 2 * M - 30 * S) + 44 * S
e.salvar(im)

fechamento(e, "O que isso significa para o Brasil", "Três leituras do relatório", [
    ("Soja", "A China compra nos EUA justamente na janela em que o Brasil tem pouca soja para vender. O efeito aparece mais no prêmio nos portos do que em Chicago. A partir de fevereiro, com a nossa colheita, o Brasil volta a ser a origem mais competitiva."),
    ("Milho", "Os EUA voltaram a vender forte, e o México é o maior comprador. A concorrência com o milho brasileiro no mercado externo fica mais dura."),
    ("Risco", "Com tanta dependência de um comprador só, qualquer ruído entre Washington e Pequim mexe direto no mercado.")],
    "agrobasis.com.br  ·  link na bio", "Painel de vendas dos EUA, atualizado a cada relatório")
e.pdf()
print("ok")
