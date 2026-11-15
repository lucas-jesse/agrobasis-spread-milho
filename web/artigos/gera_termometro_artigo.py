"""Gera o artigo de lançamento do Termômetro de Venda AgroBasis (termometro-de-venda.html) e a capa 1200x630.
Números de dados/termometro.json (exporta_termometro.py): notas de hoje, teste histórico diário por praça
(retorno do preço físico nos 63 pregões seguintes, por faixa do termômetro) e histórico semanal."""
import json
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
T = json.loads((RAIZ / "dados/termometro.json").read_text())
CSS = (AQUI / "el-nino-2026-safra.html").read_text()
CSS = CSS[CSS.index("<link rel=\"preconnect\""):CSS.index("</style>") + 8]
VD, VC, MR, TX, MT = "#1E4812", "#54931B", "#A17149", "#222222", "#7a7a7a"
CORES = [(70, "#1E4812", "Muito favorável"), (55, "#54931B", "Favorável"), (45, "#C9A227", "Neutro"), (30, "#C07A2E", "Pouco favorável"), (-1, "#A35A1E", "Desfavorável")]
FORA = {"Santa Rosa", "Santa Rosa RS"}     # praça da casa fica no painel, não no texto
SLUG = "termometro-de-venda-soja-milho"
URL = f"https://agrobasis.com.br/analises/{SLUG}/"
HOJE = "2026-11-15"


def br(v, c=1):
    return f"{v:,.{c}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sinal(v, c=1):
    v = round(v, c)
    return ("+" if v > 0 else "−" if v < 0 else "") + br(abs(v), c)


def faixa(n):
    return next((c, t) for lim, c, t in CORES if n >= lim)


def nome(k):
    return k[:-3] if k[-3:-2] == " " and k[-2:].isupper() else k


def uf(k):
    UF = {"Uberlândia": "MG", "Sorriso": "MT", "Dourados": "MS", "Rondonópolis": "MT", "Paranaguá": "PR", "Cascavel": "PR",
          "Rio Grande": "RS", "Maringá": "PR", "Passo Fundo": "RS"}
    return k[-2:] if k[-3:-2] == " " else UF.get(k, "")


# ------------------------------------------------------------------ números
def teste(p):
    return {k: {b["faixa"]: b for b in v["teste"]} for k, v in T[p].items()}


def agregado(p):
    a = defaultdict(lambda: [0, 0.0, 0.0])
    for k, t in teste(p).items():
        for f, b in t.items():
            x = a[f]; x[0] += b["n"]; x[1] += b["ret_medio"] * b["n"]; x[2] += b["pct_caiu"] * b["n"]
    return {f: {"n": x[0], "ret": x[1] / x[0], "caiu": x[2] / x[0]} for f, x in a.items()}


def media(p):
    v = [x["nota"] for x in T[p].values()]
    return sum(v) / len(v)


def por_ano(p):
    """Série semanal: retorno do preço 13 semanas depois, por faixa e ano da leitura."""
    a = defaultdict(lambda: [0, 0.0])
    for v in T[p].values():
        d, n, pr = v["hist"]["datas"], v["hist"]["nota"], v["hist"]["preco"]
        for i in range(len(d) - 13):
            if None in (n[i], pr[i], pr[i + 13]):
                continue
            f = "ate40" if n[i] < 40 else ("acima60" if n[i] > 60 else "meio")
            x = a[(f, d[i][:4])]; x[0] += 1; x[1] += pr[i + 13] / pr[i] - 1
    return {k: (x[0], x[1] / x[0] * 100) for k, x in a.items()}


AS, AM = agregado("soja"), agregado("milho")
MS, MM = media("soja"), media("milho")
TS, TM = teste("soja"), teste("milho")
YS, YM = por_ano("soja"), por_ano("milho")
NS, NM = len(T["soja"]), len(T["milho"])
NDIAS = sum(x["n"] for x in AS.values()) + sum(x["n"] for x in AM.values())
REF = T["referencia_mercado"]; REFBR = f"{REF[8:10]}/{REF[5:7]}/{REF[:4]}"
for p, A in (("soja", AS), ("milho", AM)):
    print(p, {f: (x["n"], round(x["ret"], 2), round(x["caiu"])) for f, x in A.items()}, file=sys.stderr)


# ------------------------------------------------------------------ SVG
def svg_grupos(aria, w=640, h=300):
    grupos = [("ate40", "Termômetro até 40"), ("40a60", "De 40 a 60"), ("acima60", "Acima de 60")]
    ser = [("Soja", AS, "#8FB27A"), ("Milho", AM, VD)]
    esq, dir_, topo, base = 46, 16, 22, h - 40
    lo, hi = -9, 6
    Y = lambda v: topo + (hi - v) / (hi - lo) * (base - topo)
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{aria}">']
    for v in range(lo, hi + 1, 3):
        s.append(f'<line x1="{esq}" x2="{w - dir_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{"#999" if v == 0 else "#EEF1ED"}"{" stroke-dasharray=\"3 3\"" if v == 0 else ""}/>')
        s.append(f'<text x="{esq - 8}" y="{Y(v) + 4:.1f}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="end">{sinal(v, 0) if v else "0"}%</text>')
    larg = (w - esq - dir_) / 3
    for i, (f, rot) in enumerate(grupos):
        cx = esq + larg * (i + .5)
        s.append(f'<text x="{cx:.1f}" y="{base + 26}" font-family="Geist,Arial" font-size="12.5" font-weight="600" fill="{TX}" text-anchor="middle">{rot}</text>')
        for j, (_, A, cor) in enumerate(ser):
            v = A[f]["ret"]; x = cx - 52 + j * 56; y0, y1 = sorted([Y(0), Y(v)])
            s.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="48" height="{max(y1 - y0, 1.5):.1f}" rx="4" fill="{cor}"/>')
            ty = Y(v) - 7 if v >= 0 else Y(v) + 16
            s.append(f'<text x="{x + 24:.1f}" y="{ty:.1f}" font-family="Geist,Arial" font-size="12.5" font-weight="700" fill="{cor if cor != "#8FB27A" else "#5E8A44"}" text-anchor="middle">{sinal(v, 1)}%</text>')
    s.append("</svg>")
    return "".join(s)


def svg_hist(praca, p, aria, w=640, h=320):
    hh = T[p][praca]["hist"]; d, n, pr = hh["datas"], hh["nota"], hh["preco"]
    esq, dir_, topo, base = 34, 52, 14, h - 34
    N = len(d) - 1
    X = lambda i: esq + i / N * (w - esq - dir_)
    Y = lambda v: base - v / 100 * (base - topo)
    pv = [x for x in pr if x is not None]; plo, phi = min(pv) * .95, max(pv) * 1.03
    YP = lambda v: base - (v - plo) / (phi - plo) * (base - topo)
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{aria}">']
    s.append(f'<rect x="{esq}" y="{Y(100):.1f}" width="{w - esq - dir_}" height="{Y(60) - Y(100):.1f}" fill="rgba(30,72,18,.07)"/>')
    s.append(f'<rect x="{esq}" y="{Y(40):.1f}" width="{w - esq - dir_}" height="{Y(0) - Y(40):.1f}" fill="rgba(161,113,73,.08)"/>')
    for v in (0, 20, 40, 60, 80, 100):
        s.append(f'<line x1="{esq}" x2="{w - dir_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#EEF1ED"/>')
        s.append(f'<text x="{esq - 6}" y="{Y(v) + 4:.1f}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="end">{v}</text>')
    passo = max(1, round((phi - plo) / 5 / 5) * 5)
    v = (int(plo) // passo + 1) * passo
    while v < phi:
        s.append(f'<text x="{w - dir_ + 6}" y="{YP(v) + 4:.1f}" font-family="Geist,Arial" font-size="11" fill="#9a9a9a">R$ {v:.0f}</text>'); v += passo
    vistos = set()
    for i, x in enumerate(d):
        if x[5:7] == "01" and x[:4] not in vistos:
            vistos.add(x[:4])
            s.append(f'<text x="{X(i):.1f}" y="{base + 20}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="middle">{x[:4]}</text>')
            s.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{base}" y2="{base + 5}" stroke="#ccc"/>')
    lp = " ".join(f"{X(i):.1f},{YP(v):.1f}" for i, v in enumerate(pr) if v is not None)
    ln = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(n) if v is not None)
    s.append(f'<polyline points="{lp}" fill="none" stroke="#AEB7B0" stroke-width="1.8" stroke-linejoin="round"/>')
    s.append(f'<polyline points="{ln}" fill="none" stroke="{VD}" stroke-width="2.4" stroke-linejoin="round"/>')
    s.append(f'<circle cx="{X(N):.1f}" cy="{Y(n[-1]):.1f}" r="4.5" fill="{VD}" stroke="#fff" stroke-width="2"/>')
    s.append("</svg>")
    return "".join(s)


def svg_ranking(p, aria, w=640):
    itens = sorted(((k, v["nota"]) for k, v in T[p].items() if k not in FORA), key=lambda x: -x[1])
    lh = 30; h = 16 + lh * len(itens) + 6; esq = 170; dir_ = 50
    X = lambda v: esq + v / 100 * (w - esq - dir_)
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{aria}">']
    for v in (30, 45, 55, 70):
        s.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="6" y2="{h - 4}" stroke="#E7ECE8" stroke-dasharray="3 3"/>')
    for i, (k, v) in enumerate(itens):
        y = 12 + i * lh; cor = faixa(v)[0]
        s.append(f'<text x="{esq - 10}" y="{y + 15}" font-family="Geist,Arial" font-size="12.5" font-weight="600" fill="{TX}" text-anchor="end">{nome(k)} ({uf(k)})</text>')
        s.append(f'<rect x="{esq}" y="{y}" width="{X(v) - esq:.1f}" height="21" rx="4" fill="{cor}"/>')
        s.append(f'<text x="{X(v) + 8:.1f}" y="{y + 15}" font-family="Geist,Arial" font-size="12.5" font-weight="700" fill="{cor}">{v:.0f}</text>')
    s.append("</svg>")
    return "".join(s)


def grafico(titulo, sub, corpo, fonte, leg=None):
    lg = ('<div class="abp-legend">' + "".join(f'<span class="abp-legend-item"><span class="abp-legend-dot" style="background:{c};"></span> {t}</span>' for t, c in leg) + "</div>\n    ") if leg else ""
    return f'  <div class="abp-chart-card">\n    <div class="abp-chart-title">{titulo}</div>\n    <div class="abp-chart-sub">{sub}</div>\n    {lg}{corpo}\n    <div class="abp-chart-caption">{fonte} · Elaboração: AgroBasis</div>\n  </div>\n'


FONTE = "Fonte: Conab e AgroBasis (preço físico e basis), CBOT, B3, Banco Central e CFTC"
g_grupos = grafico("O que o preço fez nos 3 meses seguintes", f"Variação média do preço físico nos 63 pregões seguintes à leitura, todas as praças, de nov/2021 a {REF[5:7]}/{REF[:4]}",
                   svg_grupos("Retorno médio do preço físico 3 meses depois, por faixa do termômetro"), FONTE, [("Soja", "#8FB27A"), ("Milho", VD)])
g_hist = grafico("Milho em Rio Verde (GO): termômetro e preço desde 2021", "Leitura semanal. Faixa verde: termômetro acima de 60. Faixa marrom: abaixo de 40",
                 svg_hist("Rio Verde GO", "milho", "Termômetro de venda e preço do milho em Rio Verde desde 2021"), FONTE,
                 [("Termômetro (0 a 100)", VD), ("Preço físico, R$/sc (eixo direito)", "#AEB7B0")])
g_rs = grafico(f"Soja: termômetro por praça em {REFBR}", "De 0 a 100. Quanto maior, mais favorável à venda", svg_ranking("soja", "Termômetro da soja por praça"), FONTE)
g_rm = grafico(f"Milho: termômetro por praça em {REFBR}", "De 0 a 100. Quanto maior, mais favorável à venda", svg_ranking("milho", "Termômetro do milho por praça"), FONTE)


def tabela_pracas(p, Tt):
    linhas = []
    for k in sorted(Tt, key=lambda k: Tt[k]["acima60"]["ret_medio"]):
        if k in FORA:
            continue
        t = Tt[k]
        linhas.append(f'<tr><td>{nome(k)} ({uf(k)})</td><td>{sinal(t["ate40"]["ret_medio"])}%</td><td>{sinal(t["40a60"]["ret_medio"])}%</td>'
                      f'<td><b>{sinal(t["acima60"]["ret_medio"])}%</b></td><td>{t["acima60"]["pct_caiu"]:.0f}%</td></tr>')
    return ('  <table class="abp-table">\n    <thead><tr><th>Praça</th><th>Até 40</th><th>40 a 60</th><th>Acima de 60</th><th>Caiu depois de 60+</th></tr></thead>\n    <tbody>\n      '
            + "\n      ".join(linhas) + "\n    </tbody>\n  </table>\n")


def tabela_anos():
    anos = sorted({a for _, a in list(YS) + list(YM)})
    def cel(Y, f, a):
        x = Y.get((f, a))
        return f"{sinal(x[1])}%" if x and x[0] >= 15 else "-"
    linhas = [f'<tr><td>{a}</td><td>{cel(YS, "acima60", a)}</td><td>{cel(YS, "ate40", a)}</td><td>{cel(YM, "acima60", a)}</td><td>{cel(YM, "ate40", a)}</td></tr>' for a in anos]
    return ('  <table class="abp-table">\n    <thead><tr><th>Ano da leitura</th><th>Soja acima de 60</th><th>Soja até 40</th><th>Milho acima de 60</th><th>Milho até 40</th></tr></thead>\n    <tbody>\n      '
            + "\n      ".join(linhas) + "\n    </tbody>\n  </table>\n")


# ------------------------------------------------------------------ texto
TITULO = "Hora de vender soja e milho? O termômetro que testamos em cinco anos de preços"
SEO_T = "Hora de vender soja e milho? Termômetro de venda | AgroBasis"
DESC = (f"Índice de 0 a 100 por praça indica se é hora de vender soja e milho. No milho, leituras acima de 60 "
        f"vieram antes de queda média de {br(-AM['acima60']['ret'], 1)}% em 3 meses.")
fs, fm = faixa(MS), faixa(MM)
top_s = max(T["soja"], key=lambda k: T["soja"][k]["nota"]); low_m = min(T["milho"], key=lambda k: T["milho"][k]["nota"])
rv = TM["Rio Verde GO"]; ub = TS["Uberlândia"]; pg = TS["Paranaguá"]

FAQ = [
    ("O que é o Termômetro de Venda AgroBasis?",
     f"É um índice de 0 a 100, calculado para {NS} praças de soja e {NM} de milho, que resume se o momento atual favorece a venda do grão. "
     "Ele combina, com pesos fixos, cinco leituras: o preço da praça frente aos últimos 3 anos, o basis frente à mesma época dos anos anteriores, "
     "a sazonalidade dos meses seguintes, a posição dos fundos na Bolsa de Chicago e, no milho, o carrego da B3. Quanto maior a nota, mais favorável à venda."),
    ("Como saber se é hora de vender soja?",
     "Não existe resposta única, porque a decisão depende do custo, do caixa e da capacidade de armazenar de cada produtor. O que o termômetro faz é dizer "
     "se o mercado, na sua praça, está numa posição historicamente boa ou ruim para vender: preço alto frente ao passado, basis firme, sazonalidade desfavorável "
     "à frente e fundos muito comprados costumam indicar uma janela melhor para fixar parte da produção."),
    ("O Termômetro de Venda acerta sempre?",
     f"Não. No teste desde novembro de 2021, depois de leituras acima de 60 o preço do milho caiu em {AM['acima60']['caiu']:.0f}% das vezes e o da soja em "
     f"{AS['acima60']['caiu']:.0f}% das vezes nos 3 meses seguintes. Em parte dos casos, o preço subiu. O exemplo mais claro foi o fim de 2021, quando o termômetro "
     "estava alto e a guerra na Ucrânia levou os grãos a novos recordes. Por isso ele é uma referência para escalonar vendas, não uma garantia."),
    ("Com que frequência o termômetro é atualizado?",
     "Duas vezes por dia útil, às 12h25 e às 18h25 (horário de Brasília), com o fechamento da CBOT e da B3, o dólar do dia e o último basis disponível de cada praça. "
     "A posição dos fundos é atualizada uma vez por semana, quando a CFTC divulga o relatório Commitments of Traders."),
    ("O termômetro é uma recomendação de compra ou venda?",
     "Não. É um indicador educacional, calculado com dados públicos e regras fixas. A decisão de vender depende do custo de produção, das dívidas, do armazenamento, "
     "do frete e do apetite a risco de cada produtor. Desempenho passado não garante resultado futuro."),
    ("Por que a soja e o milho estão em pontas opostas do termômetro?",
     f"Em {REFBR}, a soja estava com média de {MS:.0f} pontos, puxada por preço físico no topo dos últimos 3 anos e fundos comprados em Chicago. O milho estava em "
     f"{MM:.0f}, com preço e basis abaixo do normal para a época e a B3 pagando carrego para quem consegue esperar."),
]
TOC = [("o-que-e", "O que é o Termômetro de Venda"), ("calculo", "Como a nota é calculada"), ("resultados", "O que cinco anos de dados mostram"),
       ("pracas", "O resultado praça por praça"), ("erros", "Onde o termômetro errou"), ("hoje", "O que o termômetro diz hoje"),
       ("como-usar", "Como usar na decisão de venda"), ("faq", "Perguntas frequentes")]

corpo = f"""
<div class="abp-article">
<div class="abp-narrow">

  <div class="abp-breadcrumb">
    <a href="/">Início</a> &nbsp;›&nbsp;
    <a href="/analises/">Análises</a> &nbsp;›&nbsp;
    Termômetro de venda
  </div>

  <div class="abp-badge"><i data-lucide="gauge"></i> Ferramenta · Comercialização</div>
  <h1 class="abp-h1">{TITULO}</h1>
  <p class="abp-lead">Todo produtor faz a mesma pergunta várias vezes por safra: o preço de hoje está bom para vender? Criamos um índice de 0 a 100 que responde a essa pergunta para {NS} praças de soja e {NM} de milho, e testamos o que aconteceu com o preço físico depois de cada leitura desde 2021. No milho, quando o termômetro passou de 60, o preço caiu em média {br(-AM['acima60']['ret'], 1)}% nos três meses seguintes.</p>
  <div class="abp-meta">Por Equipe AgroBasis · Atualizado em 15 de novembro de 2026 · Leitura de 8 min</div>

  <div class="abp-toc">
    <div class="abp-toc-title">Neste artigo</div>
    <ol>
{chr(10).join(f'      <li><a href="#{a}">{t}</a></li>' for a, t in TOC)}
    </ol>
  </div>

  <h2 class="abp-h2" id="o-que-e">O que é o Termômetro de Venda</h2>
  <p class="abp-p">Decidir quando vender é a parte mais difícil da comercialização de grãos. O preço muda todo dia em Chicago e na B3, o dólar mexe na conta, o basis de cada região tem o seu próprio ritmo e a sazonalidade da colheita pesa de forma diferente em cada praça. Olhar tudo isso ao mesmo tempo, todos os dias, não é simples.</p>
  <p class="abp-p">O <b>Termômetro de Venda AgroBasis</b> junta essas informações num número só, de 0 a 100, calculado para cada praça. A leitura é direta: <b>quanto maior a nota, mais favorável o momento para vender</b>. Acima de 70, o momento é muito favorável; entre 55 e 70, favorável; entre 45 e 55, neutro; entre 30 e 45, pouco favorável; abaixo de 30, desfavorável.</p>
  <p class="abp-p">O índice não tenta adivinhar o preço de amanhã. Ele compara a situação de hoje com a história de cada praça e diz se o produtor está diante de uma janela boa ou ruim, pelos critérios que um analista de comercialização olharia.</p>

  <h2 class="abp-h2" id="calculo">Como a nota é calculada</h2>
  <p class="abp-p">Cada componente recebe uma nota de 0 a 100 e entra no termômetro com um peso fixo. As regras são as mesmas para todas as praças e não mudam conforme o resultado.</p>
  <table class="abp-table">
    <thead><tr><th>Componente</th><th>Soja</th><th>Milho</th><th>Nota alta quando</th></tr></thead>
    <tbody>
      <tr><td>Preço na praça</td><td>{T['pesos']['soja']['preco']}%</td><td>{T['pesos']['milho']['preco']}%</td><td>o preço está alto frente aos últimos 3 anos</td></tr>
      <tr><td>Basis</td><td>{T['pesos']['soja']['basis']}%</td><td>{T['pesos']['milho']['basis']}%</td><td>o basis está firme frente à mesma época dos 5 anos anteriores</td></tr>
      <tr><td>Sazonalidade</td><td>{T['pesos']['soja']['sazonal']}%</td><td>{T['pesos']['milho']['sazonal']}%</td><td>o preço costuma cair nos 3 meses seguintes a esta época</td></tr>
      <tr><td>Fundos na CBOT</td><td>{T['pesos']['soja']['fundos']}%</td><td>{T['pesos']['milho']['fundos']}%</td><td>os fundos estão muito comprados em Chicago</td></tr>
      <tr><td>Carrego na B3</td><td>-</td><td>{T['pesos']['milho']['carrego']}%</td><td>a B3 paga pouco para esperar até o vencimento seguinte</td></tr>
    </tbody>
  </table>
  <h3 class="abp-h3">Preço e basis: onde estamos frente ao passado</h3>
  <p class="abp-p">O preço físico de cada praça é comparado com todos os pregões dos últimos 3 anos. Se o preço de hoje é maior que 90% deles, a nota do componente é 90. O <a href="/dashboards/basis-soja-brasil/">basis</a>, diferença entre o físico e a bolsa, é comparado com o que foi registrado na mesma época do ano nos 5 anos anteriores, porque o basis tem sazonalidade própria: costuma afrouxar na colheita e firmar na entressafra.</p>
  <h3 class="abp-h3">Sazonalidade, fundos e carrego</h3>
  <p class="abp-p">A sazonalidade olha o que o preço daquela praça fez nos 3 meses seguintes à mesma data em anos anteriores. Se costumou cair, vender agora ganha pontos. A <a href="/dashboards/posicao-fundos-cftc/">posição dos fundos</a> vem do relatório semanal da CFTC: fundos muito comprados deixam o preço exposto a realização de lucros. No milho, o <a href="/dashboards/spread-milho-b3/">carrego da B3</a>, diferença entre o contrato de cerca de 6 meses à frente e o mais próximo, mostra quanto o mercado paga para quem armazena. Carrego alto tira pontos da venda imediata.</p>

  <h2 class="abp-h2" id="resultados">O que cinco anos de dados mostram</h2>
  <p class="abp-p">Um indicador só vale se a história confirmar a leitura. Calculamos o termômetro para cada pregão desde novembro de 2021 em todas as praças, o que soma {br(NDIAS, 0).replace(',', '.')} leituras, e medimos a variação do preço físico nos 63 pregões seguintes, cerca de três meses. Em seguida, separamos as leituras em três faixas.</p>
{g_grupos}  <p class="abp-p">O resultado vai na direção esperada nos dois grãos. No <b>milho</b>, depois de leituras até 40, o preço subiu em média {sinal(AM['ate40']['ret'])}% nos três meses seguintes. Depois de leituras acima de 60, caiu {br(-AM['acima60']['ret'])}%, e a queda aconteceu em {AM['acima60']['caiu']:.0f}% dos casos. A diferença entre as duas pontas passa de 11 pontos percentuais.</p>
  <p class="abp-p">Na <b>soja</b>, o sinal é mais fraco, mas tem a mesma direção: {sinal(AS['ate40']['ret'])}% depois de leituras até 40 e {sinal(AS['acima60']['ret'])}% depois de leituras acima de 60, com queda em {AS['acima60']['caiu']:.0f}% das vezes. Para um preço que depende de Chicago, do dólar e dos prêmios de porto ao mesmo tempo, é um resultado relevante.</p>
  <div class="abp-note"><b>Como ler o teste.</b> As porcentagens são médias da variação do preço físico de cada praça nos três meses seguintes à leitura, sem custos de armazenagem, frete ou juros. Leituras de dias vizinhos se sobrepõem, então o número de leituras independentes é menor do que o total indica.</div>

  <div class="abp-cta-box">
    <h3>Veja o termômetro da sua praça</h3>
    <p>Nota de hoje, o que mais pesa em cada componente, o teste histórico da praça e o gráfico desde 2021. Atualizado duas vezes por dia útil.</p>
    <a href="/dashboards/termometro-de-venda/" class="abp-cta-btn">Acessar o Termômetro de Venda <i data-lucide="arrow-right"></i></a>
  </div>

  <h2 class="abp-h2" id="pracas">O resultado praça por praça</h2>
  <p class="abp-p">O padrão se repete na maioria das praças. No milho, o caso mais forte é <b>Rio Verde (GO)</b>: depois de leituras acima de 60, o preço caiu em média {br(-rv['acima60']['ret_medio'])}% nos três meses seguintes; depois de leituras até 40, subiu {sinal(rv['ate40']['ret_medio'])}%. A tabela mostra a variação média do preço físico em cada faixa e a frequência de queda depois de leituras acima de 60.</p>
  <h3 class="abp-h3">Milho</h3>
{tabela_pracas("milho", TM)}  <h3 class="abp-h3">Soja</h3>
{tabela_pracas("soja", TS)}  <p class="abp-p">Na soja, as praças do Centro-Oeste e de Minas Gerais respondem melhor ao termômetro do que as do Sul e as de porto. Em Uberlândia (MG), leituras acima de 60 vieram antes de queda média de {br(-ub['acima60']['ret_medio'])}%. Em Paranaguá (PR), o efeito é menor ({sinal(pg['acima60']['ret_medio'])}%), o que faz sentido: o preço no porto acompanha mais de perto Chicago e o câmbio, enquanto as praças mais distantes do porto sentem mais a pressão da colheita sobre o basis.</p>
{g_hist}  <p class="abp-p">O gráfico de Rio Verde ilustra o funcionamento. As leituras altas de 2022 e do início de 2025 vieram perto de topos de preço, e as leituras baixas de 2023 e 2024 apareceram perto dos fundos. Nem toda virada foi capturada, e em vários momentos o termômetro ficou na faixa neutra enquanto o preço andava.</p>

  <h2 class="abp-h2" id="erros">Onde o termômetro errou</h2>
  <p class="abp-p">Mostrar só a média esconde os períodos em que a leitura falhou. A tabela abaixo separa o resultado pelo ano em que a leitura foi feita, usando a série semanal de todas as praças.</p>
{tabela_anos()}  <p class="abp-p">O erro mais claro foi o fim de <b>2021</b>. O termômetro estava alto para a soja e o milho, mas nos meses seguintes a seca na América do Sul e a guerra na Ucrânia levaram os grãos a recordes, e o preço subiu mais de 10% depois das leituras altas. Choques desse tipo não aparecem em nenhum dos componentes, porque não estão no preço quando a leitura é feita. Na soja, 2023 foi o caso inverso: o termômetro estava baixo, mas a supersafra brasileira continuou pressionando o preço físico, que caiu mesmo depois das leituras até 40.</p>
  <p class="abp-p">Há também uma concentração que precisa ser dita. Na soja, a maior parte das leituras acima de 60 aconteceu em 2022, quando o preço estava no topo histórico, o que deixa o resultado da soja mais dependente daquele período. No milho, o sinal se repetiu em mais anos: leituras acima de 60 vieram antes de queda em 2022, 2025 e 2026, e leituras até 40 vieram antes de alta em 2022, 2024, 2025 e 2026.</p>
  <div class="abp-pullquote">O termômetro organiza a leitura do mercado, mas não antecipa choques. Ele indica quando o preço está historicamente esticado, e é isso que justifica vender por partes, não tudo de uma vez.</div>

  <h2 class="abp-h2" id="hoje">O que o termômetro diz hoje</h2>
  <p class="abp-p">Com os preços de {REFBR}, a soja e o milho estão em pontas opostas. A <b>soja</b> tem média de <b>{MS:.0f} pontos</b> nas {NS} praças, na faixa {fs[1].lower()}. O preço físico está no topo dos últimos três anos em quase todas as praças, a sazonalidade aponta para a pressão da colheita nos próximos meses e os fundos estão comprados em Chicago. A nota mais alta é a de {nome(top_s)} ({T['soja'][top_s]['nota']:.0f}).</p>
{g_rs}  <p class="abp-p">O <b>milho</b> tem média de <b>{MM:.0f} pontos</b>, na faixa {fm[1].lower()}. O preço está abaixo da média dos últimos três anos na maior parte das praças, o basis está fraco para a época e a B3 paga carrego para quem consegue armazenar. As praças do Centro-Oeste estão nas notas mais baixas, como {nome(low_m)} ({uf(low_m)}), com {T['milho'][low_m]['nota']:.0f} pontos.</p>
{g_rm}
  <h2 class="abp-h2" id="como-usar">Como usar na decisão de venda</h2>
  <p class="abp-p">O termômetro funciona melhor como régua para <b>escalonar vendas</b>, não como gatilho para vender tudo. Algumas formas práticas de usar:</p>
  <ul class="abp-list">
    <li><b>Defina uma régua antes.</b> Por exemplo, avançar na comercialização quando a praça passa de 60 e segurar quando está abaixo de 40, sempre respeitando o custo de produção e o caixa.</li>
    <li><b>Olhe o que puxa a nota.</b> Uma nota alta puxada por preço e fundos pede uma decisão diferente de uma nota alta puxada só pela sazonalidade. A página mostra o peso de cada componente.</li>
    <li><b>Combine com a proteção.</b> Quando o preço físico não está bom, mas a bolsa está, é possível travar só a parte de Chicago ou da B3 e deixar o basis para depois, ou o contrário.</li>
    <li><b>Considere o custo de esperar.</b> Armazenagem, juros e quebra técnica corroem o ganho de segurar o grão. No milho, o carrego da B3 ajuda a medir se a espera é paga.</li>
  </ul>
  <p class="abp-p">Para quem quer entender o padrão de preço ao longo do ano, o estudo sobre o <a href="/analises/soja/qual-o-melhor-mes-para-vender-soja/">melhor mês para vender soja</a> complementa o componente de sazonalidade do termômetro.</p>

  <h2 class="abp-h2" id="faq">Perguntas frequentes</h2>
{chr(10).join(f'  <details class="abp-faq-item">{chr(10)}    <summary>{q} <i data-lucide="chevron-down"></i></summary>{chr(10)}    <p class="abp-faq-a">{a}</p>{chr(10)}  </details>' for q, a in FAQ)}

  <div class="abp-sources">
    <b>Fontes consultadas para este artigo:</b> preços físicos e basis por praça (Conab e levantamento AgroBasis); futuros de soja e milho na CBOT (CME Group) e de milho na B3; dólar comercial e PTAX (Banco Central do Brasil); posição de fundos (CFTC, Commitments of Traders, categoria Managed Money). Cálculo e teste histórico: AgroBasis, com dados de novembro de 2021 a novembro de 2026.
  </div>

  <div class="abp-author-box">
    <div class="abp-author-icon"><i data-lucide="pen-line"></i></div>
    <div class="abp-author-text"><b>Equipe AgroBasis</b><br>Inteligência de mercado para o agronegócio: dashboards, análises e conteúdo educacional com dados oficiais.</div>
  </div>

  <div class="abp-disclaimer">
    Fonte dos dados: Conab, CME Group, B3, Banco Central e CFTC. Conteúdo referencial para acompanhamento de mercado, elaborado pela equipe AgroBasis. Não constitui recomendação de investimento, compra ou venda. Desempenho passado não garante resultado futuro.
  </div>

</div>
</div>

<script>
  if (window.lucide) {{ lucide.createIcons(); }} else {{ window.addEventListener('load', () => lucide.createIcons()); }}
</script>
"""

art_ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": TITULO, "description": DESC,
                     "image": "https://agrobasis.com.br/wp-content/uploads/2026/11/termometro-de-venda-capa.png",
                     "author": {"@type": "Organization", "name": "AgroBasis"}, "publisher": {"@type": "Organization", "name": "AgroBasis"},
                     "datePublished": HOJE, "dateModified": HOJE, "mainEntityOfPage": URL}, ensure_ascii=False, indent=2)
faq_ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}, ensure_ascii=False, indent=2)
app_ld = json.dumps({"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Termômetro de Venda AgroBasis", "applicationCategory": "BusinessApplication",
                     "operatingSystem": "Web", "url": "https://agrobasis.com.br/dashboards/termometro-de-venda/", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}}, ensure_ascii=False, indent=2)

cab = f"""<!--
============================================================
AGROBASIS · ARTIGO: TERMÔMETRO DE VENDA DA SOJA E DO MILHO
============================================================
URL: /analises/{SLUG}/
  Title (SEO): {SEO_T}
  Meta description: {DESC}
  Frase-chave de foco: hora de vender soja
NOTA DE DADOS: dados/termometro.json gerado por exporta_termometro.py em {T['atualizado_em']} (mercado de {REFBR}).
  Teste diário: retorno do preço físico de cada praça nos 63 pregões seguintes, por faixa do termômetro, nov/2021 em diante.
  Tabela por ano: série semanal, retorno 13 semanas depois, células com menos de 15 leituras omitidas.
============================================================
-->
"""
html = cab + CSS + corpo + f'\n<script type="application/ld+json">\n{art_ld}\n</script>\n\n<script type="application/ld+json">\n{faq_ld}\n</script>\n\n<script type="application/ld+json">\n{app_ld}\n</script>\n'
assert "—" not in html, "travessão"
(AQUI / "termometro-de-venda.html").write_text(html)
print(len(html), SEO_T, len(SEO_T), len(DESC), file=sys.stderr)

# ------------------------------------------------------------------ capa 1200x630
sys.path.insert(0, str(RAIZ / "termometro"))
import card_termometro as C  # noqa: E402

S = C.S; W, H = 1200 * S, 630 * S
im = Image.new("RGB", (W, H), C.FUNDO); d = ImageDraw.Draw(im)
logo = Image.open(C.A / "logo.png").convert("RGBA"); logo = logo.resize((round(logo.width * 46 * S / logo.height), 46 * S), Image.LANCZOS)
im.paste(logo, (64 * S, 56 * S), logo); d = ImageDraw.Draw(im)
d.text((64 * S, 150 * S), "TERMÔMETRO DE VENDA", font=C.geist(22, 600), fill=C.VERDE2)
for i, t in enumerate(("Hora de vender", "soja e milho?")):
    d.text((64 * S, (186 + i * 70) * S), t, font=C.sora(58), fill=C.TEXTO)
d.text((64 * S, 352 * S), "Índice de 0 a 100 por praça, testado", font=C.geist(26), fill=C.TEXTO2)
d.text((64 * S, 388 * S), "em cinco anos de preços físicos", font=C.geist(26), fill=C.TEXTO2)
d.text((64 * S, 540 * S), "agrobasis.com.br", font=C.geist(24, 600), fill=C.VERDE)
for j, (rot, n) in enumerate((("Soja", MS), ("Milho", MM))):
    cx, cy = (790 + j * 0 ) * S, (200 + j * 250) * S
    x0 = 650 * S
    d.rounded_rectangle([x0, cy - 150 * S, 1150 * S, cy + 80 * S], radius=26 * S, fill="#FFFFFF", outline=C.LINHA, width=2 * S)
    cor = C.faixa(n)[1]
    C.ponteiro(d, x0 + 145 * S, cy + 30 * S, 100 * S, n, 20 * S)
    d.text((x0 + 315 * S, cy - 110 * S), rot, font=C.sora(34), fill=C.TEXTO)
    d.text((x0 + 315 * S, cy - 60 * S), f"{n:.0f}", font=C.sora(70), fill=cor)
    d.text((x0 + 315 * S, cy + 26 * S), C.faixa(n)[0].replace(" à venda", ""), font=C.geist(19, 600), fill=cor)
im.resize((1200, 630), Image.LANCZOS).save(AQUI / "img/termometro-de-venda-capa.png", optimize=True)
