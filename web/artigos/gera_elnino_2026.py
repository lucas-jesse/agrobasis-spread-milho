"""Gera o artigo 'El Niño 2026/27: o que a história diz para a safra brasileira' (el-nino-2026-safra.html).
Números de dados/clima/clima.json (NOAA CPC, ERA5, ECMWF) e dados/clima/enso_produtividade.json (Conab x RONI)."""
import json
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
C = json.loads((RAIZ / "dados/clima/clima.json").read_text())
E = json.loads((RAIZ / "dados/clima/enso_produtividade.json").read_text())
CSS = Path(__file__).with_name("usda-novembro-2026.html").read_text()
CSS = CSS[CSS.index("<link rel=\"preconnect\""):CSS.index("</style>") + 8]
VD, VC, MR, CZ, TX, MT, EN, LA = "#1E4812", "#54931B", "#A17149", "#C9D1CB", "#222222", "#7a7a7a", "#C0502E", "#2F6FA8"
NUF = {"BR": "Brasil", "MT": "Mato Grosso", "PR": "Paraná", "RS": "Rio Grande do Sul", "GO": "Goiás", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
       "BA": "Bahia", "SP": "São Paulo", "SC": "Santa Catarina", "TO": "Tocantins", "MA": "Maranhão", "PI": "Piauí"}


def br(v, c=1):
    s = f"{v:,.{c}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def sinal(v, c=1):
    v = round(v, c)
    return ("+" if v > 0 else "−" if v < 0 else "") + br(abs(v), c)


# ---------------------------------------------------------------- números
en = C["enso"]; n34 = en["nino34"]; ult = n34["ultimo"]; roni = en["roni"][-1]
pico = {a: max(v for _, v in n34["comparacao"][a]) for a in ("1997", "2015", "2023")}
djf = next(x for x in en["prob"] if x["s"] == "DJF"); neu = next((x for x in en["prob"] if x["n"] >= 50), None)
TRI = {"DJF": "dezembro a fevereiro", "JFM": "janeiro a março", "FMA": "fevereiro a abril", "MAM": "março a maio", "AMJ": "abril a junho", "MJJ": "maio a julho", "JJA": "junho a agosto", "ASO": "agosto a outubro"}
fortes = [(r[1], r[2]) for r in en["roni"] if r[0] == "DJF" and r[2] >= 1.5]
S = E["culturas"]["soja"]["ufs"]; M1 = E["culturas"]["milho1"]["ufs"]; M2 = E["culturas"]["milho2"]["ufs"]; T = E["culturas"]["trigo"]["ufs"]
P = {p["id"]: p for p in C["pontos"]}


def djf_en(p, f="en_forte"):
    v = P[p]["enso_mes"][f][3:6]
    return sum(v) / 3


def pct(p, k="safra"):
    a = P[p]["acc"][k]; return a[0] / a[1] * 100


def safras(uf, cult="soja"):
    return {s["safra"]: s["desvio"] for s in E["culturas"][cult]["ufs"][uf]["safras"] if s["fase"] == "en_forte"}


# ---------------------------------------------------------------- SVG
def svg_linhas(series, aria, w=640, h=300):
    esq, dir_, topo, base = 46, 20, 16, h - 34
    x0, x1, y0, y1 = 0, 546, -1.5, 4.0
    X = lambda d: esq + (d - x0) / (x1 - x0) * (w - esq - dir_)
    Y = lambda v: base - (v - y0) / (y1 - y0) * (base - topo)
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{aria}">']
    s.append(f'<rect x="{esq}" y="{Y(4.0):.1f}" width="{w - esq - dir_}" height="{Y(1.5) - Y(4.0):.1f}" fill="rgba(192,80,46,.06)"/>')
    for v in [-1, 0, 1, 2, 3, 4]:
        s.append(f'<line x1="{esq}" x2="{w - dir_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#EEF1ED"/>')
        s.append(f'<text x="{esq - 8}" y="{Y(v) + 4:.1f}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="end">{sinal(v, 0) if v else "0"}</text>')
    for v in (0.5, 1.5):
        s.append(f'<line x1="{esq}" x2="{w - dir_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#bbb" stroke-dasharray="4 4"/>')
    meses = ["jan", "mar", "mai", "jul", "set", "nov", "jan+1", "mar+1", "mai+1"]
    for i, m in enumerate(meses):
        d = i * 61
        s.append(f'<text x="{X(d):.1f}" y="{base + 18}" font-family="Geist,Arial" font-size="11" fill="{MT}" text-anchor="middle">{m}</text>')
    for nome, pts, cor, larg in series:
        path = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in pts)
        s.append(f'<polyline points="{path}" fill="none" stroke="{cor}" stroke-width="{larg}" stroke-linejoin="round"/>')
    d, v = series[-1][1][-1]
    s.append(f'<circle cx="{X(d):.1f}" cy="{Y(v):.1f}" r="4.5" fill="{EN}" stroke="#fff" stroke-width="2"/>')
    s.append(f'<text x="{X(d):.1f}" y="{Y(v) - 10:.1f}" font-family="Geist,Arial" font-size="12.5" font-weight="700" fill="{EN}" text-anchor="middle">{sinal(v, 1)} °C</text>')
    s.append("</svg>")
    return "".join(s)


def svg_hbar(itens, aria, sufixo="%", centro=None, w=640, cor_fn=None):
    lh = 30; h = 16 + lh * len(itens) + 10
    esq = 190; dir_ = 60
    vals = [v for _, v in itens]; lo = min(0, min(vals)); hi = max(vals)
    if centro is not None:
        lo = min(lo, centro)
    folga = (hi - lo) * 0.12; lo -= folga if lo < 0 else 0; hi += folga
    X = lambda v: esq + (v - lo) / (hi - lo) * (w - esq - dir_)
    zero = X(centro if centro is not None else 0)
    s = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;" role="img" aria-label="{aria}">']
    s.append(f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="6" y2="{h - 6}" stroke="#999" stroke-dasharray="3 3"/>')
    for i, (rot, v) in enumerate(itens):
        y = 12 + i * lh
        cor = cor_fn(v) if cor_fn else (VD if v >= 0 else MR)
        a, b = sorted([zero, X(v)])
        s.append(f'<text x="{esq - 10}" y="{y + 15}" font-family="Geist,Arial" font-size="12.5" font-weight="600" fill="{TX}" text-anchor="end">{rot}</text>')
        s.append(f'<rect x="{a:.1f}" y="{y}" width="{max(b - a, 1.5):.1f}" height="21" rx="4" fill="{cor}"/>')
        tx = X(v) + (8 if X(v) >= zero else -8)
        s.append(f'<text x="{tx:.1f}" y="{y + 15}" font-family="Geist,Arial" font-size="12" font-weight="700" fill="{cor}" text-anchor="{"start" if X(v) >= zero else "end"}">{(sinal(v, 0) if centro is None else br(v, 0))}{sufixo}</text>')
    s.append("</svg>")
    return "".join(s)


def grafico(titulo, sub, corpo, fonte, leg=None):
    lg = ('<div class="abp-legend">' + "".join(f'<span class="abp-legend-item"><span class="abp-legend-dot" style="background:{c};"></span> {t}</span>' for t, c in leg) + "</div>\n    ") if leg else ""
    return f'  <div class="abp-chart-card">\n    <div class="abp-chart-title">{titulo}</div>\n    <div class="abp-chart-sub">{sub}</div>\n    {lg}{corpo}\n    <div class="abp-chart-caption">{fonte} · Elaboração: AgroBasis</div>\n  </div>\n'


cores = {"1997": "#C9A27E", "2015": "#AEB7B0", "2023": "#8FB27A"}
ser = [(f"{a}/{str(int(a) + 1)[2:]}", n34["comparacao"][a], cores[a], 1.8) for a in ("1997", "2015", "2023")]
atual = max(n34["comparacao"]); ser.append((f"{atual}/{str(int(atual) + 1)[2:]}", n34["comparacao"][atual], EN, 3.2))
g_n34 = grafico("2026 contra os grandes El Niños", "Anomalia semanal da temperatura do mar no Niño 3.4, °C, de janeiro de cada ano a junho do ano seguinte",
                svg_linhas(ser, "Niño 3.4 semanal: 2026 contra 1997, 2015 e 2023"),
                f"Fonte: NOAA Climate Prediction Center, semana até {ult[0][8:10]}/{ult[0][5:7]}/{ult[0][:4]}",
                [("1997/98", cores["1997"]), ("2015/16", cores["2015"]), ("2023/24", cores["2023"]), (f"{atual}/{str(int(atual) + 1)[2:]}", EN)])

ufs_s = [u for u in S if u != "BR" and S[u]["fases"]["en_forte"]["n"] >= 2]
ufs_s.sort(key=lambda u: -S[u]["fases"]["en_forte"]["media"])
g_soja = grafico("Soja: produtividade nas safras de El Niño forte", "Desvio médio em relação à tendência, por estado, safras 1991/92, 1997/98 e 2015/16",
                 svg_hbar([(NUF[u], S[u]["fases"]["en_forte"]["media"]) for u in ufs_s], "Desvio da produtividade da soja em El Niño forte",
                          cor_fn=lambda v: VD if v >= 5 else ("#8FB27A" if v >= 0 else ("#D9B48D" if v > -10 else MR))),
                 "Fonte: Conab (série histórica por UF) e NOAA (RONI de dezembro a fevereiro)")

pts = sorted(C["pontos"], key=lambda p: -pct(p["id"]))
g_chuva = grafico("Chuva desde 1º de setembro, em % da normal", f"Polos produtores, até {P['santarosa']['ultimo'][8:10]}/{P['santarosa']['ultimo'][5:7]}/2026; normal = média 1991-2020",
                  svg_hbar([(f"{p['nome']} ({p['uf']})", pct(p["id"])) for p in pts], "Chuva desde setembro em percentual da normal", centro=100,
                           cor_fn=lambda v: LA if v >= 130 else ("#8CBADE" if v >= 105 else ("#C9C9C0" if v >= 95 else ("#D9B48D" if v >= 75 else MR)))),
                  "Fonte: Copernicus ERA5 (ECMWF), via Open-Meteo")


def linha_reg(pid):
    p = P[pid]
    return (f"<tr><td>{p['nome']} ({p['uf']})</td><td>{sinal(sum(p['enso_mes']['en_forte'][1:3]) / 2, 0)}%</td><td><b>{sinal(djf_en(pid), 0)}%</b></td>"
            f"<td>{sinal(djf_en(pid, 'ln'), 0)}%</td><td>{br(pct(pid), 0)}%</td></tr>")


REG = ["santarosa", "passofundo", "cruzalta", "chapeco", "cascavel", "londrina", "dourados", "rioverde", "sorriso", "primavera", "unai", "lem", "portonacional", "balsas", "urucui"]
tab_chuva = ('  <table class="abp-table">\n    <thead><tr><th>Polo</th><th>Out-nov em El Niño forte</th><th>Dez-fev em El Niño forte</th><th>Dez-fev em La Niña</th><th>Safra 2026/27 até agora</th></tr></thead>\n    <tbody>\n'
             + "\n".join("      " + linha_reg(r) for r in REG) + "\n    </tbody>\n  </table>\n")


def linha_cult(u):
    def c(x):
        return f"{sinal(x[u]['fases']['en_forte']['media'], 0)}%" if u in x and x[u]["fases"]["en_forte"]["n"] >= 2 else "-"
    return f"<tr><td>{NUF[u]}</td><td>{c(S)}</td><td>{c(M1)}</td><td>{c(M2)}</td><td>{c(T)}</td></tr>"


tab_cult = ('  <table class="abp-table">\n    <thead><tr><th>Estado</th><th>Soja</th><th>Milho 1ª safra</th><th>Milho 2ª safra</th><th>Trigo</th></tr></thead>\n    <tbody>\n'
            + "\n".join("      " + linha_cult(u) for u in ["RS", "SC", "PR", "MS", "MT", "GO", "MG", "BA", "TO", "MA", "PI", "BR"]) + "\n    </tbody>\n  </table>\n")

rs = safras("RS"); ma = safras("MA"); pi = safras("PI"); ba = safras("BA"); mt = safras("MT")

FAQ = [
    ("O El Niño de 2026/27 é forte?",
     f"Sim. A NOAA mantém o alerta de El Niño e prevê um evento forte a muito forte até o trimestre de janeiro a março de 2027. O índice oficial de intensidade (RONI) chegou a {sinal(roni[2], 2)} °C em agosto a outubro, e a anomalia semanal do Niño 3.4 está em {sinal(ult[1], 1)} °C, acima do pico dos El Niños de 1997/98 ({sinal(pico['1997'], 1)} °C) e 2015/16 ({sinal(pico['2015'], 1)} °C)."),
    ("Como o El Niño afeta a soja no Brasil?",
     f"Ele tende a dividir o país. Nas três safras de El Niño forte desde 1990, a produtividade da soja ficou em média {sinal(S['RS']['fases']['en_forte']['media'], 0)}% acima da tendência no Rio Grande do Sul e {sinal(S['MA']['fases']['en_forte']['media'], 0)}% no Maranhão, {sinal(S['PI']['fases']['en_forte']['media'], 0)}% no Piauí e {sinal(S['BA']['fases']['en_forte']['media'], 0)}% na Bahia. No Brasil como um todo, o efeito médio foi de {sinal(S['BR']['fases']['en_forte']['media'], 1)}%, porque as perdas e os ganhos regionais se compensam."),
    ("O El Niño é bom para o Rio Grande do Sul?",
     "Para a soja e o milho de verão, historicamente sim: chove mais no Sul, e as safras gaúchas de El Niño forte ficaram acima da tendência. Para o trigo, o efeito é o contrário: o excesso de chuva na primavera, perto da colheita, derrubou a produtividade gaúcha em média 13% nessas safras. O excesso de chuva também traz risco de doenças, atraso de plantio e enchentes."),
    ("Quando o El Niño de 2026/27 deve terminar?",
     f"Pelas probabilidades da NOAA, o El Niño segue dominante até o início de 2027, e a neutralidade passa a ser o cenário mais provável a partir de {TRI.get(neu['s'], neu['s']) if neu else 'meados de 2027'} ({neu['n'] if neu else '-'}% de chance)."),
    ("Como foi feito o estudo de produtividade?",
     "Com a série histórica da Conab por estado, desde a safra 1990/91. Para cada estado e cultura, calculamos a tendência de produtividade, que cresce com a tecnologia, e quanto cada safra ficou acima ou abaixo dela. Depois agrupamos as safras pela fase do ENSO no verão, medida pelo RONI de dezembro a fevereiro. Para o trigo, vale a fase de agosto a outubro do ano da colheita. Os resultados estão no painel Clima e El Niño do AgroBasis."),
]
faq_html = "\n".join(f'  <details class="abp-faq-item">\n    <summary>{q} <i data-lucide="chevron-down"></i></summary>\n    <p class="abp-faq-a">{a}</p>\n  </details>' for q, a in FAQ)
faq_ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}, ensure_ascii=False, indent=2)

SLUG = "el-nino-2026-27-safra-soja-milho-trigo"
TITULO = "El Niño 2026/27: o que a história diz para a safra de soja, milho e trigo"
DESC = f"El Niño forte em curso. Nas safras de El Niño forte, a soja do RS ficou {br(S['RS']['fases']['en_forte']['media'], 0)}% acima da tendência e a do MA, {br(-S['MA']['fases']['en_forte']['media'], 0)}% abaixo. Estudo por estado e chuva atual."
art_ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": TITULO, "description": DESC, "author": {"@type": "Organization", "name": "AgroBasis"},
                     "publisher": {"@type": "Organization", "name": "AgroBasis"}, "datePublished": date.today().isoformat(), "dateModified": date.today().isoformat(),
                     "mainEntityOfPage": f"https://agrobasis.com.br/analises/{SLUG}/"}, ensure_ascii=False, indent=2)

html = f"""<!--
============================================================
AGROBASIS · ANÁLISE: EL NIÑO 2026/27 E A SAFRA BRASILEIRA
============================================================
URL: /analises/{SLUG}/

CONFIGURAÇÃO NO PLUGIN DE SEO:
  Title (SEO): El Niño 2026/27: o que esperar para soja, milho e trigo | AgroBasis
  Meta description: {DESC}
  Slug: {SLUG}
  Frase-chave de foco: El Niño 2026 safra

NOTA DE DADOS (conferidos em {date.today().strftime('%d/%m/%Y')}):
  ENSO: NOAA Climate Prediction Center. RONI trimestral (RONI.ascii.txt), Niño 3.4 semanal (wksst9120.for),
  probabilidades oficiais por trimestre e discussão diagnóstica de {en['emitida']}.
  Chuva: reanálise ERA5 (Copernicus/ECMWF) no ponto de cada polo, via Open-Meteo, diária desde 1980; normal 1991-2020.
  Previsão: ensemble ECMWF IFS (51 membros), 15 dias.
  Produtividade: Conab, SerieHistoricaGraos por UF, safras 1990/91 a 2025/26; desvio da tendência quadrática;
  fase pelo RONI de dez-fev (trigo: ago-out do ano da colheita). El Niño forte = RONI de dez-fev de +1,5 °C ou mais.
  Arquivos: dados/clima/clima.json e dados/clima/enso_produtividade.json do repositório AgroBasis.

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
    El Niño 2026/27
  </div>

  <div class="abp-badge"><i data-lucide="cloud-sun-rain"></i> Análise · Clima e safra</div>
  <h1 class="abp-h1">{TITULO}</h1>
  <p class="abp-lead">O Pacífico vive um dos El Niños mais intensos já medidos. Cruzamos 35 anos de produtividade da Conab com o índice oficial da NOAA para responder à pergunta que importa: o que costuma acontecer com a safra brasileira quando o fenômeno chega forte? A resposta é um país dividido, com o Sul de um lado e o Matopiba do outro.</p>
  <div class="abp-meta">Por Equipe AgroBasis · Atualizado em {date.today().day} de novembro de {date.today().year} · Leitura de 8 min</div>

  <div class="abp-toc">
    <div class="abp-toc-title">Neste artigo</div>
    <ol>
      <li><a href="#forca">Um El Niño acima de 1997 e 2015</a></li>
      <li><a href="#padrao">O padrão de chuva no Brasil</a></li>
      <li><a href="#soja">Soja: Sul ganha, Matopiba perde</a></li>
      <li><a href="#milho-trigo">Milho e trigo</a></li>
      <li><a href="#agora">Como está a chuva nesta safra</a></li>
      <li><a href="#mercado">O que isso significa para o mercado</a></li>
      <li><a href="#faq">Perguntas frequentes</a></li>
    </ol>
  </div>

  <h2 class="abp-h2" id="forca">Um El Niño acima de 1997 e 2015</h2>
  <p class="abp-p">O Climate Prediction Center da NOAA, o centro de previsão climática do governo americano, mantém o <b>alerta de El Niño</b> e, na discussão de {en['emitida'][8:10]}/{en['emitida'][5:7]}, descreveu um fenômeno que continua se fortalecendo, com um evento forte a muito forte provável até o trimestre de janeiro a março de 2027. A probabilidade de El Niño no verão brasileiro, de dezembro a fevereiro, é de <b>{djf['en']}%</b>.</p>
  <p class="abp-p">Os números confirmam a dimensão. A anomalia semanal da temperatura do mar na região Niño 3.4, termômetro clássico do fenômeno, está em <b>{sinal(ult[1], 1)} °C</b> na semana até {ult[0][8:10]}/{ult[0][5:7]}. É mais do que o pico dos dois maiores eventos recentes: {sinal(pico['1997'], 1)} °C em 1997 e {sinal(pico['2015'], 1)} °C em 2015. O RONI, índice trimestral que a NOAA adotou como medida oficial de intensidade, chegou a {sinal(roni[2], 2)} °C em agosto a outubro, já na faixa de El Niño forte (acima de +1,5 °C).</p>
{g_n34}  <div class="abp-note">Desde 1950, só {len(fortes)} verões tiveram El Niño forte pelo RONI: {", ".join(f"{a - 1}/{str(a)[2:]}" for a, _ in fortes)}. A NOAA considera alta a chance de o evento atual superar todos eles.</div>

  <h2 class="abp-h2" id="padrao">O padrão de chuva no Brasil</h2>
  <p class="abp-p">O El Niño muda a circulação da atmosfera e, no Brasil, costuma produzir um efeito em gangorra. O Sul recebe mais chuva, com frentes frias que ficam paradas sobre a região. O Norte e parte do Nordeste, incluindo o Matopiba, tendem a ter chuva irregular e veranicos. O Centro-Oeste fica no meio do caminho, com efeito menos definido.</p>
  <p class="abp-p">Para medir isso nos polos produtores, calculamos a chuva de cada mês nas safras de El Niño forte desde 1980, comparada à normal de 1991 a 2020 do próprio local. O resultado aparece na tabela abaixo. Em Santa Rosa (RS), a chuva de dezembro a fevereiro ficou em média {br(djf_en('santarosa'), 0)}% acima da normal nessas safras; em Passo Fundo, {br(djf_en('passofundo'), 0)}% acima. Em La Niña, o sinal se inverte: {sinal(djf_en('santarosa', 'ln'), 0)}% em Santa Rosa.</p>
{tab_chuva}  <p class="abp-p">No Matopiba, o sinal mais claro aparece no início da temporada. Em Balsas (MA) e Uruçuí (PI), outubro e novembro tiveram chuva {sinal(sum(P['balsas']['enso_mes']['en_forte'][1:3]) / 2, 0)}% e {sinal(sum(P['urucui']['enso_mes']['en_forte'][1:3]) / 2, 0)}% frente à normal nas safras de El Niño forte, um atraso no estabelecimento das chuvas que costuma comprometer a janela de plantio. Com só quatro safras de El Niño forte na série de chuva, as médias mensais indicam tendência, não previsão.</p>

  <h2 class="abp-h2" id="soja">Soja: Sul ganha, Matopiba perde</h2>
  <p class="abp-p">O efeito na produtividade segue o mapa da chuva. Nas três safras de El Niño forte desde 1990 (1991/92, 1997/98 e 2015/16), a soja do <b>Rio Grande do Sul</b> ficou em média <b>{br(S['RS']['fases']['en_forte']['media'], 1)}%</b> acima da tendência, com ganhos em todas elas ({", ".join(f"{k}: {sinal(v, 0)}%" for k, v in rs.items())}). Santa Catarina também ganhou ({sinal(S['SC']['fases']['en_forte']['media'], 1)}%).</p>
  <p class="abp-p">Na outra ponta estão os estados do Norte e do Nordeste. O <b>Piauí</b> teve produtividade {sinal(S['PI']['fases']['en_forte']['media'], 1)}% frente à tendência, o <b>Maranhão</b> {sinal(S['MA']['fases']['en_forte']['media'], 1)}%, o Tocantins {sinal(S['TO']['fases']['en_forte']['media'], 1)}% e a Bahia {sinal(S['BA']['fases']['en_forte']['media'], 1)}%. O caso mais duro foi 2015/16, quando a soja do Piauí ficou {sinal(pi.get('2015/16', 0), 0)}% abaixo da tendência e a do Maranhão {sinal(ma.get('2015/16', 0), 0)}%.</p>
{g_soja}  <p class="abp-p">Mato Grosso, maior produtor, sentiu pouco na média ({sinal(S['MT']['fases']['en_forte']['media'], 1)}%), mas ficou {br(-mt.get('2015/16', 0), 0)}% abaixo da tendência em 2015/16, ano de chuva irregular no início do plantio. O Paraná, apesar de estar no Sul, ficou {sinal(S['PR']['fases']['en_forte']['media'], 1)}%: o excesso de chuva no norte e no oeste paranaense também atrapalha, com doenças e dificuldade de colheita.</p>
  <p class="abp-p">No agregado nacional, o efeito médio foi de apenas <b>{sinal(S['BR']['fases']['en_forte']['media'], 1)}%</b>. Os ganhos do Sul compensam as perdas do Norte e do Nordeste, e é por isso que o El Niño raramente aparece como quebra na safra brasileira total, mesmo quando muda bastante o resultado de cada região.</p>

  <div class="abp-cta-box">
    <h3>El Niño, chuva e produtividade em tempo real</h3>
    <p>Índices da NOAA, chuva observada e prevista em 16 polos produtores e o estudo de produtividade por estado e cultura.</p>
    <a href="/dashboards/clima-el-nino/" class="abp-cta-btn">Acessar o dashboard <i data-lucide="arrow-right"></i></a>
  </div>

  <h2 class="abp-h2" id="milho-trigo">Milho e trigo</h2>
  <p class="abp-p">O <b>milho de verão</b> repete o padrão da soja, com ganho expressivo no Rio Grande do Sul ({sinal(M1['RS']['fases']['en_forte']['media'], 0)}% em El Niño forte) e perdas no Piauí ({sinal(M1['PI']['fases']['en_forte']['media'], 0)}%) e no Maranhão ({sinal(M1['MA']['fases']['en_forte']['media'], 0)}%). Na <b>2ª safra</b>, o Paraná se destaca positivamente ({sinal(M2['PR']['fases']['en_forte']['media'], 0)}%), favorecido pela umidade que se estende até o outono, enquanto Goiás ({sinal(M2['GO']['fases']['en_forte']['media'], 0)}%), Minas Gerais ({sinal(M2['MG']['fases']['en_forte']['media'], 0)}%) e Bahia ({sinal(M2['BA']['fases']['en_forte']['media'], 0)}%) perderam. No Brasil, a safrinha ficou {br(M2['BR']['fases']['en_forte']['media'], 0)}% acima da tendência nessas safras.</p>
  <p class="abp-p">O <b>trigo gaúcho</b> é a exceção no Sul. Como a colheita acontece na primavera, o excesso de chuva chega na pior hora. Nas safras de El Niño forte, a produtividade do trigo gaúcho ficou {sinal(T['RS']['fases']['en_forte']['media'], 0)}% frente à tendência. O dado conversa com a safra de 2026: a Conab cortou a estimativa de trigo para 5,26 milhões de toneladas em novembro, com perdas no Paraná e no Rio Grande do Sul.</p>
{tab_cult}  <p class="abp-p">A tabela resume o desvio médio da produtividade em relação à tendência nas safras de El Niño forte, por cultura e estado. Traço indica estado com menos de duas safras de El Niño forte na série da Conab para aquela cultura.</p>

  <h2 class="abp-h2" id="agora">Como está a chuva nesta safra</h2>
  <p class="abp-p">Até agora, a safra 2026/27 segue o roteiro do El Niño no Sul. Desde 1º de setembro, choveu {br(pct('londrina'), 0)}% da normal em Londrina, {br(pct('pontagrossa'), 0)}% em Ponta Grossa, {br(pct('cascavel'), 0)}% em Cascavel e {br(pct('chapeco'), 0)}% em Chapecó. No Rio Grande do Sul, Cruz Alta acumula {br(pct('cruzalta'), 0)}% e Santa Rosa {br(pct('santarosa'), 0)}%.</p>
  <p class="abp-p">O ponto de atenção está no Centro-Oeste e no Tocantins. Sorriso (MT) recebeu só {br(pct('sorriso'), 0)}% da normal desde setembro, Porto Nacional (TO) {br(pct('portonacional'), 0)}% e Primavera do Leste (MT) {br(pct('primavera'), 0)}%. No Matopiba, os percentuais altos de Balsas e Uruçuí refletem chuvas pontuais sobre uma normal muito baixa no fim da estação seca, e não uma temporada regular. A previsão do modelo europeu para os próximos 15 dias indica volumes acima da normal na maior parte dos polos, o que pode aliviar o atraso no Mato Grosso.</p>
{g_chuva}
  <h2 class="abp-h2" id="mercado">O que isso significa para o mercado</h2>
  <h3 class="abp-h3">Um risco regional, não nacional</h3>
  <p class="abp-p">A história mostra que o El Niño forte não costuma derrubar a safra brasileira como um todo, mas redistribui a produção. Para o mercado, isso significa prêmios e basis diferentes por região: mais oferta no Sul e menos no Norte e no Nordeste, onde as tradings dependem do grão local para abastecer os portos do Arco Norte.</p>
  <h3 class="abp-h3">Safrinha e trigo no radar</h3>
  <p class="abp-p">No milho, o plantio adiantado da soja no Paraná e a umidade do El Niño favorecem a safrinha paranaense, mas o atraso das chuvas em Mato Grosso pode encurtar a janela de plantio do maior produtor de milho 2ª safra. No trigo, a safra de 2026 já sofreu com o excesso de chuva, e o país deve depender mais da importação em 2027.</p>
  <h3 class="abp-h3">Acompanhar, não antecipar</h3>
  <p class="abp-p">Cada El Niño é diferente, e o Atlântico, a distribuição das chuvas e o manejo pesam tanto quanto a intensidade no Pacífico. Com poucas safras de El Niño forte na série, as médias históricas devem ser lidas como tendência. O monitoramento da chuva e da previsão em cada região, semana a semana, é o que vai mostrar se 2026/27 segue o roteiro.</p>

  <div class="abp-pullquote">Em resumo: o El Niño de 2026/27 é um dos mais fortes já medidos. A história aponta chuva e produtividade acima da tendência no Sul, risco no Matopiba e efeito pequeno no total do Brasil, com exceção do trigo gaúcho.</div>

  <h2 class="abp-h2" id="faq">Perguntas frequentes</h2>
{faq_html}

  <div class="abp-sources">
    <b>Fontes consultadas para este artigo:</b> NOAA Climate Prediction Center (ENSO Diagnostic Discussion de {en['emitida'][8:10]}/{en['emitida'][5:7]}/{en['emitida'][:4]}, RONI, Niño 3.4 semanal e probabilidades oficiais); Copernicus ERA5 e ECMWF IFS, via Open-Meteo; Conab, série histórica de área, produção e produtividade por UF e 2º levantamento da safra 2026/27.
  </div>

  <div class="abp-author-box">
    <div class="abp-author-icon"><i data-lucide="pen-line"></i></div>
    <div class="abp-author-text"><b>Equipe AgroBasis</b><br>Inteligência de mercado para o agronegócio: dashboards, análises e conteúdo educacional com dados oficiais.</div>
  </div>

  <div class="abp-disclaimer">
    Fonte dos dados: NOAA, Copernicus/ECMWF e Conab. Conteúdo referencial para acompanhamento de mercado, elaborado pela equipe AgroBasis. Não constitui recomendação de investimento, compra ou venda.
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
Path(__file__).with_name("el-nino-2026-safra.html").write_text(html)
print("ok", len(html), "| div", html.count("<div"), html.count("</div>"))
print(DESC, len(DESC))
