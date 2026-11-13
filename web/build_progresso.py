"""Monta o dashboard "Plantio e Colheita no Brasil (Conab)" (progresso.html). CSS base do painel COT + extras."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.pg-ops{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.abc-c .pg-g{background:#EEF1EF;overflow:hidden}
.abc-c .pg-g i{left:0;top:0;height:5px;border-radius:3px;background:var(--vc);transform:none}
.abc-c[aria-pressed=true] .pg-g i{background:var(--vd)}
.abc-c .p span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pg-mapa{grid-template-columns:1.12fr 1fr}
.cn-scroll{overflow-x:auto;margin:0 -4px 8px;-webkit-overflow-scrolling:touch}
.cn-t{width:100%;border-collapse:collapse;font-size:13px;min-width:720px}
.cn-t th{font-weight:600;color:var(--mt);font-size:11.5px;padding:7px 8px;text-align:right;border-bottom:1px solid var(--ln);white-space:nowrap;vertical-align:bottom}
.cn-t th small{font-weight:500;color:#98a29a}
.cn-t td{padding:7px 8px;text-align:right;border-bottom:1px solid #F0F3F0;white-space:nowrap}
.cn-t .l{text-align:left}
.cn-t tr.uf{cursor:pointer}.cn-t tr.uf:hover td{background:#F7FAF5}
.cn-t tr.sel td{background:#FFF6DF}
.cn-t tr.tot td{background:#EEF4E8;font-weight:700;border-top:1px solid #cfd9d1}
.cn-t .cn-n{color:var(--mt);font-size:12px;margin-left:4px;font-weight:500}
.pg-bar{display:inline-block;width:70px;height:6px;border-radius:3px;background:#EEF1EF;margin-right:8px;vertical-align:middle;overflow:hidden}
.pg-bar i{display:block;height:100%;background:var(--vc);border-radius:3px}
@media (max-width:1100px){.abc-board{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media (max-width:820px){.pg-mapa{grid-template-columns:1fr}}
@media (max-width:560px){.cn-t .cn-n{display:none}.abc-board{grid-template-columns:repeat(2,minmax(0,1fr))}#abcG1{height:430px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Plantio e Colheita no Brasil (Conab, semanal) · dashboard em HTML\n"
       "     Dados: dados/progresso/progresso.json no GitHub, gerado por exporta_progresso.py a cada boletim semanal da Conab. -->\n")
faq = [("O que é o Progresso de Safra da Conab?", "É o boletim semanal em que a Companhia Nacional de Abastecimento informa quanto da área de cada cultura já foi plantada ou colhida, estado por estado. Ele acompanha soja, milho 1ª e 2ª safra, algodão, arroz, feijão e trigo nos estados que concentram quase toda a área de cada cultura."),
       ("Como o percentual do Brasil é calculado?", "A Conab pondera o percentual de cada estado acompanhado pela área que ele tem na cultura. O número do Brasil, portanto, se refere aos estados acompanhados, que somam entre 87% e 99% da área nacional, conforme a cultura. A cobertura aparece no topo do painel."),
       ("Por que comparar com o ano passado e com a média de 5 anos?", "O ritmo de plantio e colheita depende do clima, sobretudo das chuvas. A comparação com a mesma semana do ano anterior e com a média de cinco anos mostra se a safra está adiantada ou atrasada, o que afeta a janela da safrinha de milho, o risco de perdas e o fluxo de oferta para o mercado."),
       ("Atraso no plantio da soja afeta o milho safrinha?", "Sim. O milho 2ª safra é semeado logo depois da colheita da soja, e quanto mais tarde ele entra, maior o risco de pegar o fim das chuvas e geadas na fase final. Por isso o ritmo da soja em Mato Grosso, Paraná, Goiás e Mato Grosso do Sul é acompanhado de perto pelo mercado de milho."),
       ("Quando o painel é atualizado?", "A Conab publica o boletim toda semana, em geral na segunda-feira à tarde, com dados até a sexta ou o sábado anterior. O painel verifica na segunda, na terça e na quarta e atualiza sozinho.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Plantio e Colheita no Brasil (Conab) · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/plantio-e-colheita-brasil/",
       "description": "Andamento semanal do plantio e da colheita de soja, milho, algodão, arroz, feijão e trigo no Brasil, por estado, comparado ao ano passado e à média de 5 anos, com dados da Conab.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("progresso-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("progresso.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
