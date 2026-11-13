"""Monta o dashboard "Armazenagem de grãos por estado" (armazenagem.html). CSS base do painel COT + extras."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.ar-loc{align-self:flex-end;display:flex;flex-direction:column;gap:4px}
.ar-loc label{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--mt)}
.ar-sel{appearance:none;-webkit-appearance:none;font:600 14px Geist,system-ui,sans-serif;color:var(--tx);background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%231E4812' stroke-width='2.5'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") no-repeat right 12px center;border:1px solid var(--ln);border-radius:10px;padding:9px 36px 9px 14px;min-width:210px;cursor:pointer}
.ar-sel:focus{outline:2px solid #E3A72F;outline-offset:1px}
.abc-chart.ar-map{height:470px}
.abc-chart.ar-sm{height:350px}
.cn-scroll{overflow-x:auto;margin:0 -4px 8px;-webkit-overflow-scrolling:touch}
.cn-t{width:100%;border-collapse:separate;border-spacing:0 3px;font-size:13px;min-width:760px}
.cn-t th{font-weight:600;color:var(--mt);font-size:11.5px;padding:7px 8px;text-align:right;border-bottom:1px solid var(--ln);white-space:nowrap;vertical-align:bottom}
.cn-t th small{font-weight:500;color:#98a29a}
.cn-t td{padding:7px 10px;text-align:right;white-space:nowrap}
.cn-t .l{text-align:left}
.ar-t tbody tr{cursor:pointer}
.ar-t tbody tr:hover td{background:#F6F8F6}
.ar-t tr.ar-br td{background:#EEF4EA;font-weight:600}
.ar-t tr.sel td{background:#FFF4D9}
.ar-t td.neg{color:#9C5B24}.ar-t td.pos{color:#2F6B1F}
#abc .abc-k span,#abc .abc-k em{white-space:normal;overflow:visible}
.ar-pill{display:inline-block;min-width:48px;padding:2px 8px;border-radius:999px;font-weight:600;text-align:center}
@media (max-width:560px){.ar-loc{align-self:stretch;margin-top:10px}.ar-sel{width:100%}.abc-chart.ar-map{height:390px}.abc-chart.ar-sm{height:320px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Armazenagem de grãos por estado · dashboard em HTML\n"
       "     Dados: dados/armazenagem/armazenagem.json no GitHub, gerado por exporta_armazenagem.py (IBGE SIDRA e Conab). -->\n")
faq = [("Quanto o Brasil consegue armazenar de grãos?", "Segundo a Pesquisa de Estoques do IBGE, o país tinha 214,7 milhões de toneladas de capacidade estática para grãos a granel no 1º semestre de 2026, somando silos e armazéns graneleiros. A safra 2025/26 foi de cerca de 362 milhões de toneladas pela Conab, então os armazéns comportam perto de 60% da produção de um ano. O painel atualiza esses números sempre que saem novos dados."),
       ("O que é capacidade estática?", "É quanto grão cabe nos armazéns de uma só vez. Como a soja e o milho são colhidos em épocas diferentes e parte da safra é embarcada logo após a colheita, o mesmo espaço é usado mais de uma vez no ano. Ainda assim, a capacidade estática é a medida mais usada para comparar a infraestrutura de armazenagem com o tamanho da safra."),
       ("Qual é a capacidade ideal de armazenagem?", "A referência mais citada no setor é ter capacidade estática 20% maior que a produção, ou 120% da safra. Com folga, o produtor consegue segurar o grão e vender quando o preço estiver melhor, em vez de vender na colheita, quando o basis costuma ser mais fraco e o frete mais caro."),
       ("Por que o déficit de armazenagem importa para o preço?", "Sem lugar para guardar, o produtor precisa vender ou embarcar o grão logo após a colheita. Isso pressiona o preço no interior, alarga o basis em relação a Chicago e encarece o frete no pico da safra. Estados com cobertura baixa, como Mato Grosso, sentem mais esse efeito."),
       ("De onde vêm os dados?", "A capacidade, o número de armazéns, os estoques por produto e o tipo de empresa vêm da Pesquisa de Estoques do IBGE (tabelas 5459 e 254 do SIDRA), que cobre as unidades armazenadoras do país duas vezes por ano, com referência em 30 de junho e 31 de dezembro. A produção vem da série histórica de grãos da Conab. A Conab também mantém o cadastro nacional de armazéns (SICARM), com números próximos aos do IBGE."),
       ("Por que alguns estados aparecem sem dado?", "O IBGE não divulga números que permitiriam identificar uma empresa, quando há poucos informantes no estado ou no município. Nesses casos, o painel mostra o campo vazio."),
       ("Quando o painel é atualizado?", "O IBGE publica a Pesquisa de Estoques duas vezes por ano: o 1º semestre sai em novembro e o 2º semestre em maio. A produção é atualizada a cada levantamento mensal da Conab. O painel verifica as fontes duas vezes por semana.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Armazenagem de grãos por estado · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/armazenagem-graos-brasil/",
       "description": "Capacidade estática de armazenagem de grãos por estado e município, comparada com a safra da Conab, com estoques de soja, milho e trigo e evolução desde 2007. Dados do IBGE e da Conab.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("armazenagem-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("armazenagem.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
