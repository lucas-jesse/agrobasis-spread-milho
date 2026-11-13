"""Gera o artigo 'Conab novembro 2026: 2º levantamento da safra 2026/27' (conab-novembro-2026.html).
Números por cultura e por UF lidos de dados/conab/lev/2026-27_01.json e 2026-27_02.json (planilha oficial da Conab)."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
L1 = json.loads((RAIZ / "dados/conab/lev/2026-27_01.json").read_text())["produtos"]
L2 = json.loads((RAIZ / "dados/conab/lev/2026-27_02.json").read_text())["produtos"]
PG = json.loads((RAIZ / "dados/progresso/progresso.json").read_text())["culturas"]
CSS = Path(__file__).with_name("usda-novembro-2026.html").read_text()
CSS = CSS[CSS.index("<link rel=\"preconnect\""):CSS.index("</style>") + 8]

VD, VC, MR, CZ, TX, MT = "#1E4812", "#54931B", "#A17149", "#C9D1CB", "#222222", "#7a7a7a"


def br(v, c=1):
    s = f"{v:,.{c}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def sinal(v, c=1):
    return ("+" if v > 0 else "−" if v < 0 else "") + br(abs(v), c)


def B(p, uf="BRASIL", lev=L2):
    return lev[p]["linhas"][uf]


def mt(p, uf="BRASIL", i=1, lev=L2):
    return B(p, uf, lev)["producao"][i] / 1000


def pc(a, b):
    return (b / a - 1) * 100


# ---------------------------------------------------------------- SVG
def svg_div(itens, titulo_aria):
    """Barras horizontais divergentes: [(rótulo, valor %)]"""
    w, h0, lh = 640, 18, 40
    h = h0 + lh * len(itens) + 26
    x0, esc = 300, 6.4   # centro e px por ponto percentual
    lim = max(abs(v) for _, v in itens)
    esc = min(esc, 250 / lim)
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{titulo_aria}">']
    s.append(f'<line x1="{x0}" x2="{x0}" y1="8" y2="{h-22}" stroke="#cfd6cf" stroke-width="1"/>')
    for i, (rot, v) in enumerate(itens):
        y = h0 + i * lh
        cor = VD if v >= 0 else MR
        bw = abs(v) * esc
        xb = x0 if v >= 0 else x0 - bw
        s.append(f'<text x="{x0 - 10 if v >= 0 else x0 + 10}" y="{y + 15}" font-family="Geist,Arial" font-size="13" font-weight="600" fill="{TX}" text-anchor="{"end" if v >= 0 else "start"}">{rot}</text>')
        s.append(f'<rect x="{xb:.1f}" y="{y}" width="{max(bw, 1.5):.1f}" height="22" rx="4" fill="{cor}"/>')
        tx = xb + bw + 8 if v >= 0 else xb - 8
        s.append(f'<text x="{tx:.1f}" y="{y + 15}" font-family="Geist,Arial" font-size="12.5" font-weight="700" fill="{cor}" text-anchor="{"start" if v >= 0 else "end"}">{sinal(v)}%</text>')
    s.append(f'<text x="{x0}" y="{h - 6}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="middle">variação da produção sobre 2025/26</text>')
    s.append("</svg>")
    return "".join(s)


def svg_grupos(cats, series, cores, titulo_aria, unid="mi t", dec=2, w=640, h=320, rotulo_ultima=True):
    """Barras verticais agrupadas. series: lista de listas (uma por série)."""
    esq, dir_, topo, base = 48, 16, 18, 280
    vmax = max(max(s) for s in series)
    passo = [0.5, 1, 2, 2.5, 5, 10, 20, 25, 50][0]
    for p in [0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000]:
        if vmax / p <= 5:
            passo = p; break
    top = passo * (int(vmax / passo) + 1)
    alt = base - topo
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{titulo_aria}">']
    k = 0
    while k <= top + 1e-9:
        y = base - k / top * alt
        s.append(f'<line x1="{esq}" x2="{w - dir_}" y1="{y:.1f}" y2="{y:.1f}" stroke="#EEF1ED"/>')
        s.append(f'<text x="{esq - 8}" y="{y + 4:.1f}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="end">{br(k, 0 if passo >= 1 else 1)}</text>')
        k += passo
    gw = (w - esq - dir_) / len(cats)
    n = len(series); bw = min(30, gw * 0.72 / n); gap = 4
    for i, c in enumerate(cats):
        cx = esq + gw * i + gw / 2
        x = cx - (n * bw + (n - 1) * gap) / 2
        for j, sr in enumerate(series):
            v = sr[i]; bh = v / top * alt
            s.append(f'<rect x="{x:.1f}" y="{base - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{cores[j]}"/>')
            if j == n - 1 and rotulo_ultima:
                s.append(f'<text x="{x + bw / 2:.1f}" y="{base - bh - 6:.1f}" font-family="Geist,Arial" font-size="11" font-weight="700" fill="{cores[j]}" text-anchor="middle">{br(v, dec)}</text>')
            x += bw + gap
        s.append(f'<text x="{cx:.1f}" y="{base + 20}" font-family="Geist,Arial" font-size="12.5" font-weight="600" fill="{TX}" text-anchor="middle">{c}</text>')
    s.append("</svg>")
    return "".join(s)


def legenda(itens):
    return '<div class="abp-legend">' + "".join(f'<span class="abp-legend-item"><span class="abp-legend-dot" style="background:{c};"></span> {t}</span>' for t, c in itens) + "</div>"


def grafico(titulo, sub, corpo, fonte, leg=None):
    return (f'  <div class="abp-chart-card">\n    <div class="abp-chart-title">{titulo}</div>\n    <div class="abp-chart-sub">{sub}</div>\n'
            + (f"    {legenda(leg)}\n" if leg else "") + f"    {corpo}\n    <div class=\"abp-chart-caption\">{fonte} · Elaboração: AgroBasis</div>\n  </div>\n")


# ---------------------------------------------------------------- números
g1, g2 = mt("graos", lev=L1), mt("graos")
g25 = mt("graos", i=0)
soja, soja25 = mt("soja"), mt("soja", i=0)
milho, milho25 = mt("milho"), mt("milho", i=0)
m1, m2 = mt("milho1"), mt("milho2")
t1, t2, t25 = mt("trigo", lev=L1), mt("trigo"), mt("trigo", i=0)
ar1, ar2, ar25 = mt("arroz", lev=L1), mt("arroz"), mt("arroz", i=0)
fe1, fe2, fe25 = mt("feijao", lev=L1), mt("feijao"), mt("feijao", i=0)
alg, alg25 = mt("algodao"), mt("algodao", i=0)
sor, sor25 = mt("sorgo"), mt("sorgo", i=0)
area, area25 = B("graos")["area"][1] / 1000, B("graos")["area"][0] / 1000
prod_g = B("graos")["prod"]
tp = B("trigo")["prod"]; tp1 = B("trigo", lev=L1)["prod"][1]
ta = B("trigo")["area"]; ta1 = B("trigo", lev=L1)["area"][1]
sp = B("soja")["prod"]


def uf(p, u, i=1, lev=L2):
    return mt(p, u, i, lev)


ps = PG["soja"]["ops"]["plantio"]["2026/27"]["semanas"][-1]
pm = PG["milho1"]["ops"]["plantio"]["2026/27"]["semanas"][-1]
ptr = PG["trigo"]["ops"]["colheita"]["2026"]["semanas"][-1]

var = [("Sorgo", pc(sor25, sor)), ("Milho total", pc(milho25, milho)), ("Soja", pc(soja25, soja)), ("Algodão (pluma)", pc(alg25, alg)),
       ("Feijão", pc(fe25, fe2)), ("Arroz", pc(ar25, ar2)), ("Trigo", pc(t25, t2))]

TRIGO_UF = ["RS", "PR", "MG", "SP", "SC"]
SOJA_UF = ["MT", "PR", "GO", "RS", "MS", "BA", "MG"]

g_var = grafico("Safra 2026/27: o que cresce e o que encolhe", "Produção estimada no 2º levantamento contra a safra 2025/26, por cultura",
                svg_div(var, "Variação da produção por cultura"), "Fonte: Conab, 2º levantamento da safra de grãos 2026/27 (13/11/2026)")
g_trigo = grafico("Trigo: produção por estado", "Mil toneladas · safra 2025 e as duas estimativas para 2026",
                  svg_grupos(TRIGO_UF, [[uf("trigo", u, 0) * 1000 for u in TRIGO_UF], [uf("trigo", u, 1, L1) * 1000 for u in TRIGO_UF], [uf("trigo", u) * 1000 for u in TRIGO_UF]],
                             [CZ, "#8FB27A", VD], "Produção de trigo por estado", dec=0),
                  "Fonte: Conab, 1º e 2º levantamentos da safra 2026/27", [("Safra 2025", CZ), ("2026, 1º levantamento (out)", "#8FB27A"), ("2026, 2º levantamento (nov)", VD)])
g_soja = grafico("Soja: produção nos principais estados", "Milhões de toneladas · safra 2025/26 contra a estimativa para 2026/27",
                 svg_grupos(SOJA_UF, [[uf("soja", u, 0) for u in SOJA_UF], [uf("soja", u) for u in SOJA_UF]], [CZ, VD], "Produção de soja por estado", dec=1),
                 "Fonte: Conab, 2º levantamento da safra de grãos 2026/27", [("Safra 2025/26", CZ), ("Safra 2026/27 (estimativa)", VD)])

rs_t, pr_t = (uf("trigo", "RS", 1, L1) - uf("trigo", "RS")) * 1000, (uf("trigo", "PR", 1, L1) - uf("trigo", "PR")) * 1000
corte_t = (t1 - t2) * 1000


def linha_tab(nome, a, b1, b2):
    return f"<tr><td>{nome}</td><td>{br(a)}</td><td>{br(b1)}</td><td><b>{br(b2)}</b></td><td>{sinal(b2 - b1, 2) if abs(b2 - b1) >= 0.005 else 'sem mudança'}</td><td>{sinal(pc(a, b2))}%</td></tr>"


tabela = ('  <table class="abp-table">\n    <thead><tr><th>Produção (mi t)</th><th>2025/26</th><th>1º lev. (out)</th><th>2º lev. (nov)</th><th>Revisão no mês</th><th>Sobre 2025/26</th></tr></thead>\n    <tbody>\n'
          + "\n".join("      " + linha_tab(*x) for x in [
              ("<b>Total de grãos</b>", g25, g1, g2), ("Soja", soja25, mt("soja", lev=L1), soja), ("Milho total", milho25, mt("milho", lev=L1), milho),
              ("Milho 1ª safra", mt("milho1", i=0), mt("milho1", lev=L1), m1), ("Milho 2ª safra", mt("milho2", i=0), mt("milho2", lev=L1), m2),
              ("Trigo (safra 2026 x 2025)", t25, t1, t2), ("Arroz", ar25, ar1, ar2), ("Feijão", fe25, fe1, fe2),
              ("Algodão em pluma", alg25, mt("algodao", lev=L1), alg), ("Sorgo", sor25, mt("sorgo", lev=L1), sor)])
          + "\n    </tbody>\n  </table>\n")

FAQ = [
    ("Quanto a Conab estima para a safra de grãos 2026/27?",
     f"No 2º levantamento, divulgado em 13 de novembro de 2026, a Conab estima {br(g2)} milhões de toneladas, {br(g1 - g2)} milhão abaixo do levantamento de outubro e {br(pc(g25, g2))}% acima da safra 2025/26. A área deve chegar a {br(area)} milhões de hectares."),
    ("Por que a Conab cortou a estimativa de trigo?",
     f"Por área menor e clima desfavorável, principalmente no Paraná e no Rio Grande do Sul. A produtividade média caiu de {br(tp1, 0)} para {br(tp[1], 0)} kg/ha e a produção foi para {br(t2, 2)} milhões de toneladas, {br(-pc(t25, t2))}% abaixo de 2025. Parte do trigo colhido tem qualidade menor e deve ir para ração."),
    ("A Conab mudou a estimativa de soja em novembro?",
     f"Não. A soja segue em {br(soja)} milhões de toneladas, com área de {br(B('soja')['area'][1] / 1000)} milhões de hectares e produtividade de {br(sp[1], 0)} kg/ha ({br(sp[1] / 60)} sacas por hectare). A Conab cita chuvas irregulares, calor e os primeiros efeitos do El Niño como fatores de incerteza."),
    ("Quanto de milho o Brasil deve colher em 2026/27?",
     f"{br(milho, 1)} milhões de toneladas, {br(pc(milho25, milho))}% acima de 2025/26: {br(m1)} milhões na 1ª safra, {br(m2)} milhões na 2ª e o restante na 3ª. A exportação de 2026/27 está estimada em cerca de 43 milhões de toneladas."),
    ("Quando sai o próximo levantamento da Conab?",
     "O 3º levantamento da safra 2026/27 deve sair em dezembro de 2026. O calendário oficial fica no site da Conab, e o painel Safra Brasil por Estado do AgroBasis atualiza sozinho no dia da divulgação."),
]
faq_html = "\n".join(f'  <details class="abp-faq-item">\n    <summary>{q} <i data-lucide="chevron-down"></i></summary>\n    <p class="abp-faq-a">{a}</p>\n  </details>' for q, a in FAQ)
faq_ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}, ensure_ascii=False, indent=2)

TITULO = f"Conab novembro 2026: safra de grãos vai a {br(g2)} milhões de toneladas com corte no trigo"
DESC = f"2º levantamento da Conab: safra 2026/27 em {br(g2)} mi t, trigo cai para {br(t2)} mi t e soja segue em {br(soja)} mi t. Números por estado e o que muda no mercado."
art_ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": TITULO, "description": DESC, "author": {"@type": "Organization", "name": "AgroBasis"},
                     "publisher": {"@type": "Organization", "name": "AgroBasis"}, "datePublished": "2026-11-13", "dateModified": "2026-11-13",
                     "mainEntityOfPage": "https://agrobasis.com.br/analises/conab-novembro-2026-safra-graos-2026-27/"}, ensure_ascii=False, indent=2)

html = f"""<!--
============================================================
AGROBASIS · ANÁLISE: CONAB, 2º LEVANTAMENTO DA SAFRA 2026/27 (NOVEMBRO DE 2026)
============================================================
URL: /analises/conab-novembro-2026-safra-graos-2026-27/

CONFIGURAÇÃO NO PLUGIN DE SEO:
  Title (SEO): Conab novembro 2026: safra 2026/27 em {br(g2)} mi t | AgroBasis
  Meta description: {DESC}
  Slug: conab-novembro-2026-safra-graos-2026-27
  Frase-chave de foco: levantamento Conab novembro 2026

NOTA DE DADOS (conferidos em 13/11/2026):
  Produção, área e produtividade por cultura e por UF: planilha oficial da Conab
  "site_previsao_de_safra-por_produto" do 1º (out/2026) e do 2º (nov/2026) levantamentos da safra 2026/27,
  convertida pelo coletor AgroBasis (dados/conab/lev/2026-27_01.json e 2026-27_02.json).
  Exportação de milho (40,9 mi t em 2025/26, cerca de 43 mi t em 2026/27), estoques de passagem de milho
  (19 mi t em jan/2027, 20,9 mi t em jan/2028), estoques de trigo e motivos das revisões: comunicado
  da Conab de 13/11/2026, reproduzido por Mais Soja e Canal Rural.
  Andamento do plantio e da colheita: Conab, Progresso de Safra, semana até 06/11/2026 (dados/progresso).
  Conversão: saca de 60 kg.

NOTA DE ESTILO: sem travessão em H1/H2 e na prosa, tom sóbrio e direto.
NOTA DE DESIGN: Design System AgroBasis, Geist + Sora, Lucide, gráficos em SVG puro.
============================================================
-->

{CSS}

<div class="abp-article">
<div class="abp-narrow">

  <div class="abp-breadcrumb">
    <a href="/">Início</a> &nbsp;›&nbsp;
    <a href="/analises/">Análises</a> &nbsp;›&nbsp;
    Conab novembro 2026
  </div>

  <div class="abp-badge"><i data-lucide="sprout"></i> Análise · Safra Brasil</div>
  <h1 class="abp-h1">{TITULO}</h1>
  <p class="abp-lead">O 2º levantamento da safra 2026/27 tirou {br(g1 - g2)} milhão de toneladas da estimativa de outubro. Quase todo o corte veio do trigo, que perdeu produtividade no Paraná e no Rio Grande do Sul. Soja e milho ficaram onde estavam, e a atenção agora se volta para o clima de dezembro e janeiro.</p>
  <div class="abp-meta">Por Equipe AgroBasis · Atualizado em 13 de novembro de 2026 · Leitura de 7 min</div>

  <div class="abp-toc">
    <div class="abp-toc-title">Neste artigo</div>
    <ol>
      <li><a href="#resumo">Os números do 2º levantamento</a></li>
      <li><a href="#trigo">Trigo: o maior corte do mês</a></li>
      <li><a href="#soja">Soja mantida em {br(soja)} milhões de toneladas</a></li>
      <li><a href="#milho">Milho: produção estável e exportação menor</a></li>
      <li><a href="#arroz-feijao">Arroz e feijão encolhem</a></li>
      <li><a href="#plantio">Como está o plantio</a></li>
      <li><a href="#mercado">O que o relatório muda no mercado</a></li>
      <li><a href="#faq">Perguntas frequentes</a></li>
    </ol>
  </div>

  <h2 class="abp-h2" id="resumo">Os números do 2º levantamento</h2>
  <p class="abp-p">A Companhia Nacional de Abastecimento (Conab) divulgou nesta sexta-feira, 13 de novembro, a segunda estimativa para a safra brasileira de grãos 2026/27: <b>{br(g2)} milhões de toneladas</b>. O número é {br(g1 - g2)} milhão de toneladas menor que o de outubro ({br(g1)} milhões), mas ainda {br(pc(g25, g2))}% maior que a safra 2025/26, que a Conab também revisou, para {br(g25)} milhões.</p>
  <p class="abp-p">O crescimento continua apoiado na área. A Conab projeta {br(area)} milhões de hectares, {br(area - area25)} milhão a mais que no ciclo anterior, enquanto a produtividade média recua de {br(prod_g[0], 0)} para {br(prod_g[1], 0)} kg por hectare. Em outras palavras, o Brasil planta mais, mas a estatal já embute um rendimento médio menor, coerente com um ano de El Niño.</p>
{tabela}  <p class="abp-p">A revisão do mês se concentrou nas culturas de inverno e nas de menor peso. Soja, milho, algodão e sorgo repetiram os números de outubro, algo comum em novembro: com o plantio de verão em andamento, a Conab só costuma mexer na produtividade das culturas principais quando o clima já deixou marcas claras nas lavouras.</p>
{g_var}
  <h2 class="abp-h2" id="trigo">Trigo: o maior corte do mês</h2>
  <p class="abp-p">O trigo respondeu por quase toda a redução do levantamento. A produção estimada caiu de {br(t1, 2)} para <b>{br(t2, 2)} milhões de toneladas</b>, um corte de {br(corte_t, 0)} mil toneladas em um mês. Frente aos {br(t25, 2)} milhões colhidos em 2025, a queda chega a {br(-pc(t25, t2))}%.</p>
  <p class="abp-p">A área foi levemente ajustada, de {br(ta1, 0)} para {br(ta[1], 0)} mil hectares, mas o peso maior veio da produtividade, que passou de {br(tp1, 0)} para {br(tp[1], 0)} kg por hectare (de {br(tp1 / 60)} para {br(tp[1] / 60)} sacas). Segundo a Conab, o clima desfavorável no Paraná e no Rio Grande do Sul derrubou o rendimento e também a qualidade, o que deve desviar uma parcela maior do trigo para a ração animal.</p>
{g_trigo}  <p class="abp-p">O Paraná perdeu {br(pr_t, 0)} mil toneladas no mês e deve colher {br(uf("trigo", "PR"), 2)} milhões de toneladas, com produtividade de {br(B("trigo", "PR")["prod"][1], 0)} kg/ha, ante {br(B("trigo", "PR")["prod"][0], 0)} kg/ha em 2025. No Rio Grande do Sul, o corte foi de {br(rs_t, 0)} mil toneladas, para {br(uf("trigo", "RS"), 2)} milhões. Somados, os dois estados que lideram a produção nacional devem entregar {br(uf("trigo", "RS") + uf("trigo", "PR"), 2)} milhões de toneladas, contra {br(uf("trigo", "RS", 0) + uf("trigo", "PR", 0), 2)} milhões em 2025.</p>
  <div class="abp-note">Com produção de {br(t2, 1)} milhões de toneladas, bem abaixo do que os moinhos e a ração consomem no país, a dependência de importação aumenta. A Conab estima estoque de passagem de trigo de apenas 436,5 mil toneladas ao fim da safra 2026, ante 955,5 mil toneladas da safra 2025.</div>

  <h2 class="abp-h2" id="soja">Soja mantida em {br(soja)} milhões de toneladas</h2>
  <p class="abp-p">A Conab manteve a estimativa de soja em <b>{br(soja)} milhões de toneladas</b>, {br(pc(soja25, soja))}% acima da safra 2025/26. A área cresce para {br(B("soja")["area"][1] / 1000)} milhões de hectares e a produtividade projetada é de {br(sp[1], 0)} kg por hectare, ou {br(sp[1] / 60)} sacas, abaixo dos {br(sp[0] / 60)} sacas da safra passada.</p>
  <p class="abp-p">A estatal descreve realidades distintas entre as regiões produtoras. Chuvas irregulares, temperaturas elevadas e os primeiros efeitos do El Niño mantêm o potencial produtivo em aberto, sobretudo nas áreas plantadas mais cedo no Centro-Oeste e no Matopiba.</p>
{g_soja}  <p class="abp-p">A distribuição por estado mostra o efeito esperado do El Niño, que costuma favorecer o Sul e penalizar o Norte e o Nordeste. O Rio Grande do Sul é o destaque positivo: depois de uma safra 2025/26 de {br(uf("soja", "RS", 0))} milhões de toneladas, a Conab projeta {br(uf("soja", "RS"))} milhões, com produtividade de {br(B("soja", "RS")["prod"][1] / 60)} sacas por hectare. Mato Grosso, maior produtor, deve colher {br(uf("soja", "MT"))} milhões, {br(-pc(uf("soja", "MT", 0), uf("soja", "MT")))}% abaixo do ciclo anterior, com produtividade estimada de {br(B("soja", "MT")["prod"][1] / 60)} sacas contra {br(B("soja", "MT")["prod"][0] / 60)}. Bahia e Tocantins também têm produtividade projetada menor.</p>

  <div class="abp-cta-box">
    <h3>Safra Brasil por estado, atualizada a cada levantamento</h3>
    <p>Mapa, ranking, série histórica e a revisão mês a mês de soja, milho, trigo, algodão, arroz, feijão e sorgo em cada estado.</p>
    <a href="/dashboards/safra-brasil-conab/" class="abp-cta-btn">Acessar o dashboard <i data-lucide="arrow-right"></i></a>
  </div>

  <h2 class="abp-h2" id="milho">Milho: produção estável e exportação menor</h2>
  <p class="abp-p">A produção total de milho foi mantida em <b>{br(milho, 1)} milhões de toneladas</b>, {br(pc(milho25, milho))}% acima de 2025/26. A 1ª safra deve render {br(m1)} milhões de toneladas, com área {br(pc(B("milho1")["area"][0], B("milho1")["area"][1]))}% maior, para {br(B("milho1")["area"][1] / 1000, 2)} milhões de hectares. A 2ª safra, que ainda nem foi plantada, segue estimada em {br(m2)} milhões de toneladas.</p>
  <p class="abp-p">A mudança relevante veio no balanço de oferta e demanda. A Conab reduziu a exportação de milho da safra 2025/26 para 40,9 milhões de toneladas, 6,8% abaixo da estimativa anterior, e projeta cerca de 43 milhões para 2026/27. O ritmo mais lento é atribuído à colheita americana, ao avanço da Argentina no mercado externo e à menor demanda chinesa. Com menos milho saindo pelos portos, o estoque de passagem previsto para o fim de janeiro de 2027 subiu para 19 milhões de toneladas, e o de janeiro de 2028 para 20,9 milhões.</p>
  <table class="abp-table">
    <thead><tr><th>Milho por estado (mi t)</th><th>2025/26</th><th>2026/27</th><th>Variação</th></tr></thead>
    <tbody>
{chr(10).join(f'      <tr><td>{n}</td><td>{br(uf(p, u, 0))}</td><td><b>{br(uf(p, u))}</b></td><td>{sinal(pc(uf(p, u, 0), uf(p, u)))}%</td></tr>' for n, p, u in [("Mato Grosso, 2ª safra", "milho2", "MT"), ("Paraná, 2ª safra", "milho2", "PR"), ("Mato Grosso do Sul, 2ª safra", "milho2", "MS"), ("Goiás, 2ª safra", "milho2", "GO"), ("Rio Grande do Sul, 1ª safra", "milho1", "RS"), ("Minas Gerais, 1ª safra", "milho1", "MG"), ("Paraná, 1ª safra", "milho1", "PR")])}
    </tbody>
  </table>
  <p class="abp-p">No Sul, o milho de verão ganha espaço: a área do Rio Grande do Sul sobe de {br(B("milho1", "RS")["area"][0], 0)} para {br(B("milho1", "RS")["area"][1], 0)} mil hectares, e a produção gaúcha da 1ª safra deve passar de {br(uf("milho1", "RS", 0))} para {br(uf("milho1", "RS"))} milhões de toneladas.</p>

  <h2 class="abp-h2" id="arroz-feijao">Arroz e feijão encolhem</h2>
  <p class="abp-p">No arroz, a estimativa caiu de {br(ar1, 2)} para <b>{br(ar2, 2)} milhões de toneladas</b>, {br(-pc(ar25, ar2))}% abaixo de 2025/26. A área irrigada recua 2,4% depois de um ciclo de margens apertadas, e só o arroz de sequeiro cresce. O Rio Grande do Sul, responsável por {br(uf("arroz", "RS") / ar2 * 100, 0)}% da produção nacional, teve a estimativa reduzida de {br(uf("arroz", "RS", 1, L1), 2)} para {br(uf("arroz", "RS"), 2)} milhões de toneladas, com área de {br(B("arroz", "RS")["area"][1], 0)} mil hectares.</p>
  <p class="abp-p">O feijão foi ajustado para {br(fe2, 2)} milhões de toneladas, {br(-pc(fe25, fe2))}% abaixo da safra anterior, com pequena redução de área e de produtividade.</p>

  <h2 class="abp-h2" id="plantio">Como está o plantio</h2>
  <p class="abp-p">O levantamento chega com o plantio de verão adiantado. Até {ps["d"][8:10]}/{ps["d"][5:7]}, segundo o Progresso de Safra da Conab, <b>{br(ps["br"])}% da área de soja</b> estava semeada, contra {br(ps["br_aa"])}% no mesmo período do ano passado e {br(ps["br_m5"])}% na média de cinco anos. Mato Grosso praticamente encerrou a semeadura, com {br(ps["ufs"]["MT"])}%, enquanto o Rio Grande do Sul estava em {br(ps["ufs"]["RS"])}%.</p>
  <p class="abp-p">O milho de 1ª safra tinha {br(pm["br"])}% da área plantada ({br(pm["br_aa"])}% um ano antes), e a colheita do trigo chegava a {br(ptr["br"])}%, com o Rio Grande do Sul em {br(ptr["ufs"]["RS"])}%. Plantio rápido da soja abre uma janela melhor para a safrinha de milho em 2027, o que ajuda a sustentar a estimativa de {br(m2)} milhões de toneladas da 2ª safra.</p>

  <div class="abp-cta-box">
    <h3>Plantio e colheita semana a semana</h3>
    <p>Curvas da safra atual contra o ano passado e a média de 5 anos, mapa e ranking por estado, com os dados da Conab.</p>
    <a href="/dashboards/plantio-e-colheita-brasil/" class="abp-cta-btn">Acessar o dashboard <i data-lucide="arrow-right"></i></a>
  </div>

  <h2 class="abp-h2" id="mercado">O que o relatório muda no mercado</h2>
  <h3 class="abp-h3">Soja: neutro, com o clima no comando</h3>
  <p class="abp-p">Sem mudança nos números, o relatório não altera a leitura de oferta da soja brasileira. Uma safra de {br(soja)} milhões de toneladas segue no radar do mercado internacional como a maior da história, e é ela que limita a alta de Chicago no primeiro semestre de 2027. O risco está na produtividade: cada saca por hectare a menos na média nacional representa cerca de {br(B("soja")["area"][1] * 60 / 1e6, 1)} milhões de toneladas. Os próximos levantamentos vão depender do comportamento das chuvas no Centro-Oeste e no Matopiba entre dezembro e janeiro.</p>
  <h3 class="abp-h3">Milho: estoque maior pesa nos preços internos</h3>
  <p class="abp-p">Para o milho, o dado mais importante não foi a produção, e sim a exportação. Menos embarques significam mais milho disponível no mercado interno e estoque de passagem de 19 milhões de toneladas em janeiro de 2027. Esse quadro tende a limitar a valorização do milho no físico durante a entressafra, mesmo com a demanda crescente das usinas de etanol de milho.</p>
  <h3 class="abp-h3">Trigo: mais importação e prêmio para o trigo de qualidade</h3>
  <p class="abp-p">No trigo, o efeito é o oposto. Com produção de {br(t2, 1)} milhões de toneladas e parte dela com qualidade inferior, o moinho brasileiro deve depender mais do trigo argentino e de outras origens em 2027. O trigo de padrão panificável tende a ganhar prêmio sobre o lote de menor qualidade, e o preço interno passa a acompanhar mais de perto a paridade de importação.</p>

  <div class="abp-pullquote">Em resumo: o 2º levantamento corta o trigo, não mexe na soja e no milho e reforça um ano de oferta folgada de milho no Brasil. O clima de dezembro e janeiro decide os próximos números.</div>

  <h2 class="abp-h2" id="faq">Perguntas frequentes</h2>
{faq_html}

  <div class="abp-sources">
    <b>Fontes consultadas para este artigo:</b> Conab, Acompanhamento da Safra Brasileira de Grãos, 1º e 2º levantamentos da safra 2026/27 (planilhas por produto e comunicado de 13/11/2026); Conab, Progresso de Safra, semana até 06/11/2026.
  </div>

  <div class="abp-author-box">
    <div class="abp-author-icon"><i data-lucide="pen-line"></i></div>
    <div class="abp-author-text"><b>Equipe AgroBasis</b><br>Inteligência de mercado para o agronegócio: dashboards, análises e conteúdo educacional com dados oficiais.</div>
  </div>

  <div class="abp-disclaimer">
    Fonte dos dados: Conab. Conteúdo referencial para acompanhamento de mercado, elaborado pela equipe AgroBasis. Não constitui recomendação de investimento, compra ou venda.
  </div>

</div>
</div>

<script>
  if (window.lucide) {{ lucide.createIcons(); }} else {{ window.addEventListener('load', () => lucide.createIcons()); }}
</script>

<script type="application/ld+json">
{art_ld}
</script>

<script type="application/ld+json">
{faq_ld}
</script>
"""
saida = Path(__file__).with_name("conab-novembro-2026.html")
saida.write_text(html)
print("ok", len(html), "| div", html.count("<div"), html.count("</div>"), "| details", html.count("<details"), "| faq", len(FAQ))
print("SEO:", f"Conab novembro 2026: safra 2026/27 em {br(g2)} mi t | AgroBasis", "|", DESC, len(DESC))
