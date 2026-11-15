"""Monta a página "Safra Argentina" (argentina.html). CSS base do painel COT + extras."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.ar-tab{overflow-x:auto;margin:2px 0 6px}
.ar-tab table{width:100%;border-collapse:collapse;font-size:13.5px}
.ar-tab th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--mt);font-weight:600;text-align:left;padding:8px 10px;border-bottom:1px solid var(--ln);white-space:nowrap}
.ar-tab td{padding:9px 10px;border-bottom:1px solid #F0F3F0;white-space:nowrap}
.ar-tab tr:last-child td{border-bottom:0}
.ar-tab .n{text-align:right}.ar-tab .b{width:34%;min-width:140px}.ar-tab .b2{background:#F7FAF5}
.ar-tab td small{font-size:11.5px;color:var(--mt);margin-left:4px}
.ar-tab td b+small{display:block;margin:1px 0 0}
.ar-tab td em{font-style:normal;font-weight:600;font-size:12.5px;margin-left:4px}
.ar-bar{position:relative;height:20px;background:#EEF2EE;border-radius:5px;overflow:hidden}
.ar-bar i{position:absolute;left:0;top:0;bottom:0;background:#54931B;border-radius:5px}
.ar-bar span{position:relative;font-size:12px;font-weight:600;padding-left:7px;line-height:20px;color:#1d2420}
.ar-up{color:#2E7D1E!important;font-style:normal}.ar-dn{color:#B4441F!important;font-style:normal}
.ar-est{display:flex;height:22px;border-radius:6px;overflow:hidden;background:#EEF2EE}
.ar-est i{display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-style:normal;font-weight:600}
.ar-estn{display:grid;grid-template-columns:150px 1fr;gap:12px;align-items:center;margin:6px 0 8px}
.ar-estl b{display:block;font-size:14.5px}.ar-estl small{font-size:12px;color:var(--mt)}
.ar-leg{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--mt);margin:0 0 10px}
.ar-leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.ar-um{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12.5px;margin:0 0 10px;padding:9px 10px;background:#F7FAF5;border-radius:10px}
.ar-um span{color:var(--mt);margin-right:4px}.ar-um b{font-weight:600}.ar-um .s{color:#A35A1E}.ar-um .a{color:#1E4812}.ar-um .e{color:#2F6FA8}
.ar-estp{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px}.ar-estp td{padding:5px 0}.ar-estp td:first-child{width:130px;padding-right:10px;white-space:nowrap}
.ar-bcr{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:4px 0 10px}
.ar-bcri{display:block;border:1px solid var(--ln);border-radius:12px;padding:12px 14px;text-decoration:none!important;color:var(--tx)!important}
.ar-bcri:hover{border-color:var(--vc)}.ar-bcri span{display:block;font-size:11.5px;color:var(--mt);text-transform:uppercase;letter-spacing:.05em;font-weight:600;margin-bottom:4px}.ar-bcri b{font-size:14.5px;font-weight:600;line-height:1.4}
.ar-pc{margin-top:4px}
@media (max-width:560px){.ar-estn{grid-template-columns:1fr;gap:4px}.ar-bcr{grid-template-columns:1fr}.ar-tab table{font-size:12.5px}.ar-tab td,.ar-tab th{padding:8px 6px}.ar-estp td:first-child{width:96px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Safra Argentina · painel em HTML\n"
       "     Dados: dados/argentina/argentina.json no GitHub, gerado por exporta_argentina.py. -->\n")
faq = [("Qual a fonte dos dados da safra argentina?", "O avanço do plantio e da colheita, a condição das lavouras e a umidade do solo vêm do Informe Semanal de Estimaciones Agrícolas da Secretaría de Agricultura, Ganadería y Pesca da Argentina, publicado às quintas-feiras com dados de cerca de 40 delegações regionais. As estimativas de produção vêm do próprio governo, da Bolsa de Comercio de Rosario (GEA) e do USDA. A chuva vem da reanálise ERA5 e do modelo europeu ECMWF."),
       ("Quando a Argentina planta e colhe soja e milho?", "O milho começa a ser plantado em setembro, com uma parte em dezembro e janeiro (milho tardio). A soja de primeira é plantada de outubro a dezembro e a de segunda, depois do trigo, até janeiro. A colheita de soja e milho vai de março a julho. O trigo é plantado de maio a julho e colhido de novembro a janeiro."),
       ("Por que a safra argentina importa para o produtor brasileiro?", "A Argentina é o maior exportador mundial de farelo e óleo de soja e um dos maiores exportadores de milho e trigo. Uma safra cheia lá aumenta a concorrência com o Brasil na exportação a partir de março e pesa nos prêmios dos portos brasileiros e na Bolsa de Chicago. Uma quebra, como a de 2022/23, faz o contrário."),
       ("Como é medida a condição das lavouras?", "Cada delegação do governo argentino informa a porcentagem da área em estado muito bom, bom, regular ou ruim, além da fase da lavoura e da umidade do solo. O AgroBasis pondera essas porcentagens pela área de cada delegação para chegar ao número da Argentina e de cada província. O quadro de soja e milho aparece quando as lavouras já emergiram, em geral a partir de dezembro."),
       ("O El Niño é bom para a safra argentina?", "Em geral, sim. O El Niño costuma trazer mais chuva para a região pampeana no verão, e as safras de El Niño tendem a ficar acima da tendência de produtividade, como mostra o gráfico do painel. A La Niña costuma trazer seca, como em 2008/09, 2017/18 e 2022/23. O excesso de chuva, porém, também pode atrasar o plantio e a colheita."),
       ("Com que frequência o painel é atualizado?", "O avanço, a condição e as estimativas são atualizados toda quinta e sexta-feira à noite, depois da publicação do governo argentino e da Bolsa de Rosario. A chuva e a previsão são atualizadas todo dia de manhã.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Safra Argentina: plantio, colheita e condição das lavouras", "applicationCategory": "BusinessApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/safra-argentina/",
       "description": "Avanço do plantio e da colheita de soja, milho e trigo na Argentina, condição das lavouras por província, estimativas de produção, chuva nos polos e produtividade por fase do El Niño.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("argentina-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
html = cab + css + "\n\n" + corpo
assert "—" not in html
Path("argentina.html").write_text(html)
print("ok", len(html))
