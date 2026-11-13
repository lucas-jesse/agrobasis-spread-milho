"""Gera o artigo 'Vendas de exportação dos EUA, semana até 05/11/2026' (export-sales-2026-11-05.html).
Todos os números vêm de dados/export_sales/*.json (USDA FAS, Export Sales Reporting, via API oficial)."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ES = {p: json.loads((RAIZ / f"dados/export_sales/{p}.json").read_text()) for p in ["soja", "milho", "trigo", "farelo", "oleo"]}
CSS = Path(__file__).with_name("usda-novembro-2026.html").read_text()
CSS = CSS[CSS.index("<link rel=\"preconnect\""):CSS.index("</style>") + 8]
VD, VC, MR, CZ, TX, MT = "#1E4812", "#54931B", "#A17149", "#C9D1CB", "#222222", "#7a7a7a"


def br(v, c=1):
    s = f"{v:,.{c}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def sinal(v, c=1):
    return ("+" if v > 0 else "−" if v < 0 else "") + br(abs(v), c)


def pc(a, b):
    return (b / a - 1) * 100


# ---------------------------------------------------------------- métricas por produto
def metr(p):
    d = ES[p]; anos = d["anos"]; x = anos[-1]; w = x["semana"][-1]

    def at(y, k):
        return y[k][y["semana"].index(w)] if w in y["semana"] else None
    prev = anos[:-1]
    pct5 = [at(y, "comp") / y["projecao_usda"] * 100 for y in prev if at(y, "comp") and y.get("projecao_usda")]
    net5 = [at(y, "net") for y in prev if at(y, "net") is not None]
    rest = 51 - w
    return dict(d=d, x=x, w=w, net=x["net"][-1], net_ant=x["net"][-2], net4=sum(x["net"][-5:-1]) / 4, emb=x["emb"][-1],
                emb4=sum(x["emb"][-4:]) / 4, comp=x["comp"][-1], acum=x["acum"][-1], proj=x["projecao_usda"],
                pct=x["comp"][-1] / x["projecao_usda"] * 100, pct5=sum(pct5) / len(pct5), net5=sum(net5) / len(net5),
                rest=rest, need=(x["projecao_usda"] - x["acum"][-1]) / rest, comp_ant=at(anos[-2], "comp"),
                dest={z["pais"]: z for z in d["destinos"]}, sem=d["semana_destinos"])


M = {p: metr(p) for p in ES}
S, Mi, T, F, O = M["soja"], M["milho"], M["trigo"], M["farelo"], M["oleo"]
SEM = ES["soja"]["semana_ate"]  # AAAA-MM-DD
DDMM = f"{SEM[8:10]}/{SEM[5:7]}"
china = S["dest"]["China"]
sx_at, sx_ant = S["comp"] - china["comp"], S["comp_ant"] - china["comp_ant"]
mex = Mi["dest"]["México"]
mi_max = max(Mi["x"]["net"][:-1])
mi_serie = list(zip(Mi["x"]["datas"], Mi["x"]["net"], Mi["x"]["emb"]))
NOME = {"soja": "Soja", "milho": "Milho", "trigo": "Trigo", "farelo": "Farelo de soja", "oleo": "Óleo de soja"}


# ---------------------------------------------------------------- SVG
def eixo_passo(vmax):
    for p in [0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000]:
        if vmax / p <= 5:
            return p
    return 5000


def svg_grupos(cats, series, cores, aria, dec=0, sufixo="", w=640, h=300, rot_todas=False):
    esq, dir_, topo, base = 48, 16, 18, h - 40
    vmax = max(max(s) for s in series); passo = eixo_passo(vmax); top = passo * (int(vmax / passo) + 1); alt = base - topo
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{aria}">']
    k = 0
    while k <= top + 1e-9:
        y = base - k / top * alt
        s.append(f'<line x1="{esq}" x2="{w - dir_}" y1="{y:.1f}" y2="{y:.1f}" stroke="#EEF1ED"/>')
        s.append(f'<text x="{esq - 8}" y="{y + 4:.1f}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="end">{br(k, 0)}{sufixo}</text>')
        k += passo
    gw = (w - esq - dir_) / len(cats); n = len(series); bw = min(34, gw * 0.7 / n); gap = 4
    for i, c in enumerate(cats):
        cx = esq + gw * i + gw / 2; x = cx - (n * bw + (n - 1) * gap) / 2
        for j, sr in enumerate(series):
            v = sr[i]; bh = max(v, 0) / top * alt
            s.append(f'<rect x="{x:.1f}" y="{base - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{cores[j]}"/>')
            if rot_todas or j == n - 1:
                s.append(f'<text x="{x + bw / 2:.1f}" y="{base - bh - 6:.1f}" font-family="Geist,Arial" font-size="11" font-weight="700" fill="{cores[j] if cores[j] != CZ else MT}" text-anchor="middle">{br(v, dec)}{sufixo}</text>')
            x += bw + gap
        s.append(f'<text x="{cx:.1f}" y="{base + 20}" font-family="Geist,Arial" font-size="12" font-weight="600" fill="{TX}" text-anchor="middle">{c}</text>')
    s.append("</svg>")
    return "".join(s)


def svg_barras_semana(datas, vals, aria, w=640, h=300):
    esq, dir_, topo, base = 48, 16, 22, h - 40
    vmax = max(vals); passo = eixo_passo(vmax); top = passo * (int(vmax / passo) + 1); alt = base - topo
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{aria}">']
    k = 0
    while k <= top + 1e-9:
        y = base - k / top * alt
        s.append(f'<line x1="{esq}" x2="{w - dir_}" y1="{y:.1f}" y2="{y:.1f}" stroke="#EEF1ED"/>')
        s.append(f'<text x="{esq - 8}" y="{y + 4:.1f}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="end">{br(k, 0)}</text>')
        k += passo
    gw = (w - esq - dir_) / len(vals); bw = gw * 0.62
    for i, (dt, v) in enumerate(zip(datas, vals)):
        cx = esq + gw * i + gw / 2; bh = v / top * alt; ult = i == len(vals) - 1
        s.append(f'<rect x="{cx - bw / 2:.1f}" y="{base - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{VD if ult else "#A9C29A"}"/>')
        if ult or v == vmax:
            s.append(f'<text x="{cx:.1f}" y="{base - bh - 6:.1f}" font-family="Geist,Arial" font-size="11" font-weight="700" fill="{VD}" text-anchor="middle">{br(v, 0)}</text>')
        s.append(f'<text x="{cx:.1f}" y="{base + 18}" font-family="Geist,Arial" font-size="10.5" fill="{MT}" text-anchor="middle">{dt[8:10]}/{dt[5:7]}</text>')
    s.append("</svg>")
    return "".join(s)


def legenda(itens):
    return '<div class="abp-legend">' + "".join(f'<span class="abp-legend-item"><span class="abp-legend-dot" style="background:{c};"></span> {t}</span>' for t, c in itens) + "</div>"


def grafico(titulo, sub, corpo, fonte, leg=None):
    return (f'  <div class="abp-chart-card">\n    <div class="abp-chart-title">{titulo}</div>\n    <div class="abp-chart-sub">{sub}</div>\n'
            + (f"    {legenda(leg)}\n" if leg else "") + f"    {corpo}\n    <div class=\"abp-chart-caption\">{fonte} · Elaboração: AgroBasis</div>\n  </div>\n")


FONTE = f"Fonte: USDA FAS, Export Sales Reporting (semana até {DDMM}/2026); projeções: USDA WASDE"
PRODS = ["soja", "milho", "trigo", "farelo"]
g_pct = grafico("Quanto da exportação projetada já foi vendido", "Compromisso de exportação em % da projeção do USDA, na mesma semana do ano-safra",
                svg_grupos([NOME[p] if p != "farelo" else "Farelo" for p in PRODS], [[M[p]["pct5"] for p in PRODS], [M[p]["pct"] for p in PRODS]], [CZ, VD],
                           "Compromisso em percentual da projeção", sufixo="%", rot_todas=True),
                FONTE, [("Média das 5 safras anteriores", CZ), ("Safra atual", VD)])
g_china = grafico("Soja: a China explica toda a diferença", "Compromisso de exportação de soja dos EUA na mesma semana do ano-safra, mil t",
                  svg_grupos(["China", "Demais destinos", "Total"], [[china["comp_ant"], sx_ant, S["comp_ant"]], [china["comp"], sx_at, S["comp"]]], [CZ, VD],
                             "Compromisso de soja com e sem a China", rot_todas=True),
                  FONTE, [("2025/26", CZ), ("2026/27", VD)])
g_milho = grafico("Milho: vendas líquidas semanais na safra 2026/27", "Mil toneladas por semana, de setembro até a semana encerrada em " + DDMM,
                  svg_barras_semana([d for d, _, _ in mi_serie], [n for _, n, _ in mi_serie], "Vendas semanais de milho"), FONTE)


def linha_tab(p):
    m = M[p]
    return (f"<tr><td>{NOME[p]}</td><td><b>{br(m['net'], 0)}</b></td><td>{br(m['emb'], 0)}</td><td>{br(m['comp'] / 1000, 1)}</td>"
            f"<td>{sinal(pc(m['comp_ant'], m['comp']), 0)}%</td><td>{br(m['pct'], 0)}% <span style=\"color:#9a9a9a\">({br(m['pct5'], 0)}%)</span></td></tr>")


tabela = ('  <table class="abp-table">\n    <thead><tr><th>Produto</th><th>Vendas na semana (mil t)</th><th>Embarques (mil t)</th><th>Compromisso (mi t)</th><th>vs ano anterior</th><th>% da projeção (média 5 anos)</th></tr></thead>\n    <tbody>\n'
          + "\n".join("      " + linha_tab(p) for p in ["soja", "milho", "trigo", "farelo", "oleo"]) + "\n    </tbody>\n  </table>\n")

sem_s = {z["pais"]: z for z in S["sem"]}
sem_m = {z["pais"]: z for z in Mi["sem"]}

FAQ = [
    ("Quanto de soja os EUA já venderam na safra 2026/27?",
     f"Até a semana encerrada em {DDMM}/2026, o compromisso de exportação de soja dos EUA somava {br(S['comp'] / 1000)} milhões de toneladas, {br(pc(S['comp_ant'], S['comp']), 0)}% acima do mesmo ponto de 2025/26 e {br(S['pct'], 0)}% da exportação projetada pelo USDA para o ano-safra."),
    ("Quanto a China comprou de soja americana?",
     f"A China tem {br(china['comp'] / 1000)} milhões de toneladas de soja contratadas nos EUA na safra 2026/27, contra apenas {br(china['comp_ant'], 0)} mil toneladas no mesmo ponto da safra anterior. Sem a China, o compromisso americano está {br(-pc(sx_ant, sx_at), 0)}% abaixo do ano passado."),
    ("Por que as vendas de milho da semana foram tão altas?",
     f"Porque o México comprou {br(sem_m['México']['net'], 0)} mil toneladas das {br(Mi['net'], 0)} mil vendidas na semana, a maior venda semanal de milho da safra 2026/27. Mesmo assim, o compromisso total segue {br(-pc(Mi['comp_ant'], Mi['comp']), 0)}% abaixo de 2025/26."),
    ("O que é compromisso de exportação?",
     "É a soma do que já foi embarcado com as vendas fechadas que ainda vão ser embarcadas no ano-safra. É o melhor termômetro da demanda externa, porque mostra o volume já contratado, e não só o que saiu dos portos."),
    ("Quando sai o próximo relatório de vendas semanais?",
     "O USDA divulga o relatório toda quinta-feira às 10h30 de Brasília, com dados da semana encerrada na quinta anterior. Em semanas com feriado nos EUA, a divulgação passa para sexta, como aconteceu nesta semana."),
]
faq_html = "\n".join(f'  <details class="abp-faq-item">\n    <summary>{q} <i data-lucide="chevron-down"></i></summary>\n    <p class="abp-faq-a">{a}</p>\n  </details>' for q, a in FAQ)
faq_ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}, ensure_ascii=False, indent=2)

SLUG = "vendas-exportacao-eua-semana-05-novembro-2026"
TITULO = f"Vendas de exportação dos EUA: milho vende {br(Mi['net'] / 1000)} milhões de t na semana e China sustenta a soja"
DESC = f"USDA, semana até {DDMM}: milho tem a maior venda da safra, puxada pelo México, e a soja chega a {br(S['pct'], 0)}% da meta com a China. Os números e o que mudam."
art_ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": TITULO, "description": DESC, "author": {"@type": "Organization", "name": "AgroBasis"},
                     "publisher": {"@type": "Organization", "name": "AgroBasis"}, "datePublished": "2026-11-13", "dateModified": "2026-11-13",
                     "mainEntityOfPage": f"https://agrobasis.com.br/analises/{SLUG}/"}, ensure_ascii=False, indent=2)

html = f"""<!--
============================================================
AGROBASIS · ANÁLISE: VENDAS SEMANAIS DE EXPORTAÇÃO DOS EUA, SEMANA ATÉ {DDMM}/2026
============================================================
URL: /analises/{SLUG}/

CONFIGURAÇÃO NO PLUGIN DE SEO:
  Title (SEO): Vendas de exportação EUA: milho forte e China na soja | AgroBasis
  Meta description: {DESC}
  Slug: {SLUG}
  Frase-chave de foco: vendas de exportação dos EUA

NOTA DE DADOS (conferidos em 13/11/2026):
  USDA FAS, Export Sales Reporting (API oficial api.fas.usda.gov/api/esr), relatório divulgado em 13/11/2026 às 8h30 de Washington,
  semana encerrada em 05/11/2026: vendas líquidas, embarques, compromisso (embarcado + a embarcar) e destinos, por produto.
  Mesma semana das 5 safras anteriores: mesma fonte. Projeção de exportação 2026/27: USDA WASDE de novembro/2026; das safras
  anteriores: exportação final registrada no USDA. Ritmo necessário = (projeção - embarcado) / semanas restantes do ano-safra.
  Corte da exportação de milho do Brasil: Conab, 2º levantamento da safra 2026/27 (13/11/2026).
  Base de cálculo: dados/export_sales/*.json do repositório AgroBasis.

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
    Vendas de exportação dos EUA
  </div>

  <div class="abp-badge"><i data-lucide="ship"></i> Análise · USDA Export Sales</div>
  <h1 class="abp-h1">{TITULO}</h1>
  <p class="abp-lead">O relatório do USDA da semana encerrada em {DDMM} trouxe a maior venda semanal de milho da safra americana 2026/27, quase toda para o México. Na soja, o ritmo diminuiu, mas o volume acumulado segue {br(pc(S['comp_ant'], S['comp']), 0)}% acima do ano passado graças às compras da China.</p>
  <div class="abp-meta">Por Equipe AgroBasis · Atualizado em 13 de novembro de 2026 · Leitura de 6 min</div>

  <div class="abp-toc">
    <div class="abp-toc-title">Neste artigo</div>
    <ol>
      <li><a href="#resumo">Os números da semana</a></li>
      <li><a href="#milho">Milho: a maior venda da safra, puxada pelo México</a></li>
      <li><a href="#soja">Soja: a China sustenta o ritmo</a></li>
      <li><a href="#trigo-farelo">Trigo, farelo e óleo</a></li>
      <li><a href="#brasil">O que isso significa para o Brasil</a></li>
      <li><a href="#faq">Perguntas frequentes</a></li>
    </ol>
  </div>

  <h2 class="abp-h2" id="resumo">Os números da semana</h2>
  <p class="abp-p">O Departamento de Agricultura dos EUA (USDA) divulgou nesta sexta-feira, 13 de novembro, o relatório de vendas semanais de exportação referente à semana encerrada em {DDMM}. A divulgação, que normalmente acontece na quinta, foi adiada em um dia. O quadro geral mostra uma soja adiantada, um milho atrasado mas reagindo e um trigo abaixo da média.</p>
{tabela}  <p class="abp-p">A comparação mais útil é a última coluna. Ela mostra quanto da exportação projetada pelo USDA para o ano-safra já está contratado, ao lado da média das cinco safras anteriores na mesma semana. A soja está {br(S['pct'] - S['pct5'], 0)} pontos acima do padrão histórico; milho, trigo e farelo estão abaixo.</p>
{g_pct}
  <h2 class="abp-h2" id="milho">Milho: a maior venda da safra, puxada pelo México</h2>
  <p class="abp-p">Os EUA venderam <b>{br(Mi['net'], 0)} mil toneladas de milho</b> na semana, mais que o dobro das {br(Mi['net_ant'], 0)} mil toneladas da semana anterior e bem acima da média das quatro semanas anteriores ({br(Mi['net4'], 0)} mil t). É a maior venda semanal desde o início do ano-safra, em setembro, e supera a média de {br(Mi['net5'], 0)} mil toneladas das cinco safras anteriores na mesma semana.</p>
  <p class="abp-p">O México respondeu por {br(sem_m['México']['net'], 0)} mil toneladas, cerca de {br(sem_m['México']['net'] / Mi['net'] * 100, 0)}% do total. Colômbia ({br(sem_m['Colômbia']['net'], 0)} mil t) e Coreia do Sul ({br(sem_m['Coreia do Sul']['net'], 0)} mil t) completam a lista dos principais compradores.</p>
{g_milho}  <p class="abp-p">Apesar da semana forte, o retrato acumulado continua mais fraco que o do ano passado. O compromisso de milho soma {br(Mi['comp'] / 1000)} milhões de toneladas, {br(-pc(Mi['comp_ant'], Mi['comp']), 0)}% abaixo de 2025/26, quando os EUA exportaram {br(M['milho']['d']['anos'][-2]['projecao_usda'] / 1000)} milhões de toneladas no ano-safra. Isso representa {br(Mi['pct'], 0)}% da projeção do USDA ({br(Mi['proj'] / 1000)} milhões), contra {br(Mi['pct5'], 0)}% na média histórica.</p>
  <p class="abp-p">Os embarques são o ponto fraco. Nas últimas quatro semanas, a média foi de {br(Mi['emb4'], 0)} mil toneladas por semana. Para cumprir a projeção, os EUA precisam embarcar {br(Mi['need'], 0)} mil toneladas por semana até o fim de agosto. É uma diferença grande. Parte dela é sazonal, porque os embarques de milho dos EUA costumam ganhar ritmo no primeiro semestre, mas o número precisa melhorar nas próximas semanas para sustentar a projeção.</p>

  <div class="abp-cta-box">
    <h3>Vendas semanais dos EUA, atualizadas a cada relatório</h3>
    <p>Compromisso acumulado contra as últimas 5 safras, destinos, compradores da semana e ritmo necessário para cumprir a projeção do USDA.</p>
    <a href="/dashboards/exportacoes-eua-usda/" class="abp-cta-btn">Acessar o dashboard <i data-lucide="arrow-right"></i></a>
  </div>

  <h2 class="abp-h2" id="soja">Soja: a China sustenta o ritmo</h2>
  <p class="abp-p">A venda semanal de soja foi de <b>{br(S['net'], 0)} mil toneladas</b>, abaixo das {br(S['net_ant'], 0)} mil t da semana anterior e da média de {br(S['net5'], 0)} mil t das cinco safras anteriores na mesma semana. Os embarques somaram {br(S['emb'], 0)} mil toneladas. É um ritmo de desaceleração, depois de duas semanas em outubro com vendas acima de 2,5 milhões de toneladas.</p>
  <p class="abp-p">O acumulado, porém, é o melhor dos últimos anos em relação à meta. O compromisso chega a <b>{br(S['comp'] / 1000)} milhões de toneladas</b>, {br(S['pct'], 0)}% da exportação projetada pelo USDA ({br(S['proj'] / 1000)} milhões), contra {br(S['pct5'], 0)}% na média das cinco safras anteriores. Para cumprir a projeção, bastam embarques de {br(S['need'], 0)} mil toneladas por semana até o fim de agosto, bem abaixo dos {br(S['emb4'], 0)} mil t por semana das últimas quatro semanas.</p>
{g_china}  <p class="abp-p">A explicação está na China. O país tem {br(china['comp'] / 1000)} milhões de toneladas de soja americana contratadas, contra apenas {br(china['comp_ant'], 0)} mil toneladas no mesmo ponto da safra passada, quando ficou praticamente fora do mercado dos EUA. Só nesta semana, foram {br(sem_s['China']['net'], 0)} mil toneladas vendidas e {br(sem_s['China']['emb'], 0)} mil embarcadas para o destino chinês. A China responde por {br(china['comp'] / S['comp'] * 100, 0)}% de todo o compromisso.</p>
  <p class="abp-p">Fora da China, o quadro é outro. Os demais destinos somam {br(sx_at / 1000)} milhões de toneladas, {br(-pc(sx_ant, sx_at), 0)}% abaixo do ano passado. México e Egito, por exemplo, compraram menos que em 2025/26. A demanda pela soja americana está concentrada em um único comprador, o que torna o número sensível a qualquer mudança na relação comercial entre Washington e Pequim.</p>
  <div class="abp-note">Destino a definir: {br(S['dest']['Destino a definir']['comp'] / 1000)} milhões de toneladas de soja ainda não têm país declarado. Nesta semana, {br(-sem_s['Destino a definir']['net'], 0)} mil toneladas saíram dessa conta, em geral porque o destino foi confirmado. Parte desse volume tende a aparecer como China nas próximas semanas.</div>

  <h2 class="abp-h2" id="trigo-farelo">Trigo, farelo e óleo</h2>
  <p class="abp-p"><b>Trigo:</b> semana fraca, com {br(T['net'], 0)} mil toneladas vendidas, ante {br(T['net_ant'], 0)} mil na semana anterior. O compromisso soma {br(T['comp'] / 1000)} milhões de toneladas, {br(-pc(T['comp_ant'], T['comp']), 0)}% abaixo de 2025/26 e {br(T['pct'], 0)}% da projeção, perto da média de {br(T['pct5'], 0)}%. México, Japão e Indonésia lideraram as compras.</p>
  <p class="abp-p"><b>Farelo de soja:</b> {br(F['net'], 0)} mil toneladas vendidas, acima da média das quatro semanas anteriores. O compromisso de {br(F['comp'] / 1000, 2)} milhões de toneladas é {br(pc(F['comp_ant'], F['comp']), 0)}% maior que o do ano passado, com destaque para Filipinas, México, Colômbia e Vietnã. A projeção do USDA, de {br(F['proj'] / 1000)} milhões de toneladas, supera a exportação de todas as safras recentes e exige um ritmo forte daqui para frente.</p>
  <p class="abp-p"><b>Óleo de soja:</b> as exportações seguem residuais, com {br(O['comp'], 0)} mil toneladas contratadas, quase tudo para o Canadá. Com o mandato de biocombustíveis absorvendo o óleo dentro dos EUA, o país praticamente saiu do mercado externo.</p>

  <h2 class="abp-h2" id="brasil">O que isso significa para o Brasil</h2>
  <h3 class="abp-h3">Soja: China dividida entre EUA e Brasil</h3>
  <p class="abp-p">As compras chinesas nos EUA reduzem a demanda pela soja brasileira justamente na janela em que o Brasil ainda tem pouco grão para vender, antes da colheita de 2026/27. O efeito para o produtor brasileiro aparece mais no prêmio de exportação nos portos do que na cotação de Chicago. Quando a safra brasileira chegar, a partir de fevereiro, a China volta a ter no Brasil a origem mais competitiva.</p>
  <h3 class="abp-h3">Milho: concorrência maior na exportação</h3>
  <p class="abp-p">O milho americano segue muito competitivo no México e na América Latina, mercados em que disputa espaço com o Brasil. O dado conversa com o 2º levantamento da Conab, divulgado no mesmo dia, que cortou a exportação brasileira de milho da safra 2025/26 para 40,9 milhões de toneladas e citou a colheita americana como um dos motivos. Menos exportação significa mais milho no mercado interno brasileiro, o que pesa sobre os preços no físico. A análise completa está no artigo <a href="/analises/conab-novembro-2026-safra-graos-2026-27/" style="color:#1E4812;font-weight:600">Conab novembro 2026</a>.</p>

  <div class="abp-pullquote">Em resumo: o milho americano mostrou força na semana, a soja segue apoiada em um único comprador e o trigo continua fraco. Para o Brasil, o recado é concorrência mais dura no milho e uma China dividida na soja até a nossa colheita.</div>

  <h2 class="abp-h2" id="faq">Perguntas frequentes</h2>
{faq_html}

  <div class="abp-sources">
    <b>Fontes consultadas para este artigo:</b> USDA FAS, Export Sales Reporting, relatório de 13/11/2026 (semana encerrada em {DDMM}/2026) e histórico das safras 2021/22 a 2025/26; USDA WASDE, novembro de 2026; Conab, 2º levantamento da safra de grãos 2026/27.
  </div>

  <div class="abp-author-box">
    <div class="abp-author-icon"><i data-lucide="pen-line"></i></div>
    <div class="abp-author-text"><b>Equipe AgroBasis</b><br>Inteligência de mercado para o agronegócio: dashboards, análises e conteúdo educacional com dados oficiais.</div>
  </div>

  <div class="abp-disclaimer">
    Fonte dos dados: USDA FAS e Conab. Conteúdo referencial para acompanhamento de mercado, elaborado pela equipe AgroBasis. Não constitui recomendação de investimento, compra ou venda.
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
saida = Path(__file__).with_name("export-sales-2026-11-05.html")
saida.write_text(html)
print("ok", len(html), "| div", html.count("<div"), html.count("</div>"), "| faq", len(FAQ))
print(TITULO, len(TITULO)); print(DESC, len(DESC))
print("milho max anterior", mi_max, "| ex-China", sx_at, sx_ant)
