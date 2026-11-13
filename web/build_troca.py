"""Monta o dashboard "Relação de Troca: grãos x fertilizantes" (troca.html). CSS base do painel COT + extras."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.tr-graos{align-self:flex-end}
.abc-chart.tr-sm{height:340px}
.tr-board{grid-template-columns:repeat(5,minmax(0,1fr))}
.abc-c .tr-g{background:linear-gradient(90deg,#9cc77a,#eef1ef 50%,#d9b48d)}
.abc-c .v small{white-space:nowrap}
.cn-scroll{overflow-x:auto;margin:0 -4px 8px;-webkit-overflow-scrolling:touch}
.cn-t{width:100%;border-collapse:separate;border-spacing:0 3px;font-size:13px;min-width:640px}
.cn-t th{font-weight:600;color:var(--mt);font-size:11.5px;padding:7px 8px;text-align:right;border-bottom:1px solid var(--ln);white-space:nowrap;vertical-align:bottom}
.cn-t th small{font-weight:500;color:#98a29a}
.cn-t td{padding:8px 10px;text-align:right;white-space:nowrap}
.cn-t .l{text-align:left}
.cn-t .cn-n{color:var(--mt);font-size:11.5px;margin-left:4px;font-weight:500}
.tr-t td.tr-c{cursor:pointer;border-radius:7px;transition:box-shadow .15s}
.tr-t td.tr-c small{opacity:.75;font-size:11px;margin-left:3px}
.tr-t td.tr-c:hover{box-shadow:0 0 0 2px #1d2420 inset}
.tr-t td.tr-c.sel{box-shadow:0 0 0 2px #E3A72F inset}
@media (max-width:900px){.tr-board{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:560px){.tr-board{grid-template-columns:repeat(2,minmax(0,1fr))}.cn-t .cn-n{display:none}.tr-graos{align-self:flex-start;margin-top:8px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Relação de troca grãos x fertilizantes · dashboard em HTML\n"
       "     Dados: dados/troca/troca.json no GitHub, gerado por exporta_troca.py (Comex Stat, Cepea, Banco Central). -->\n")
faq = [("O que é a relação de troca entre grãos e fertilizantes?", "É quantas sacas de grão o produtor precisa vender para pagar uma tonelada de fertilizante. Quanto menor o número, mais favorável o momento de compra. O painel calcula a relação mês a mês para soja, milho e trigo contra ureia, cloreto de potássio, MAP, sulfato de amônio e superfosfato simples."),
       ("De onde vêm os preços dos fertilizantes?", "Do Comex Stat, sistema oficial de comércio exterior do governo federal. O painel usa o preço médio de importação CIF, em dólares por tonelada, de cada fertilizante: o valor da mercadoria posta no porto brasileiro, com frete marítimo e seguro. O Brasil importa cerca de 85% dos fertilizantes que consome, então esse preço é a principal referência do mercado interno."),
       ("O preço CIF é o mesmo que o produtor paga na revenda?", "Não. Até chegar à fazenda, o adubo recebe custos de porto, frete rodoviário, mistura, impostos e a margem da revenda, que variam por região. Por isso o número absoluto de sacas no campo é maior. A relação no porto serve para comparar momentos: ela mostra se o adubo está caro ou barato em relação ao grão, frente à própria história."),
       ("Quais preços de grãos são usados?", "Os indicadores do Cepea/Esalq: soja em Paranaguá (PR), milho Esalq/B3 em Campinas (SP) e trigo no Paraná, convertido para sacas de 60 kg. O painel usa a média mensal em dólar, para que adubo e grão fiquem na mesma moeda."),
       ("Qual o melhor mês para comprar fertilizante?", "O gráfico de sazonalidade mostra, para cada par, em que meses a relação costuma ficar mais favorável que a média do ano. O padrão histórico ajuda no planejamento, mas não garante o comportamento do ano corrente, que depende do câmbio, do frete marítimo e da oferta mundial de nitrogenados, fosfatados e potássicos."),
       ("Quando o painel é atualizado?", "Os preços dos grãos são atualizados todo fim de tarde de dia útil. Os preços e volumes de fertilizantes saem uma vez por mês, quando o governo publica os dados de comércio exterior do mês anterior, em geral na primeira semana do mês.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Relação de Troca: grãos x fertilizantes · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/relacao-de-troca-fertilizantes/",
       "description": "Quantas sacas de soja, milho e trigo pagam uma tonelada de ureia, cloreto de potássio, MAP, sulfato de amônio e superfosfato, mês a mês desde 2010, com dados do Comex Stat e do Cepea.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("troca-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("troca.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
