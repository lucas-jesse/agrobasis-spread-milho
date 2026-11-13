"""Monta o dashboard "Safra Brasil (Conab)" (conab.html). CSS base do painel COT + mapa e tabela."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.abc-board{grid-template-columns:repeat(5,minmax(0,1fr))}
.cn-mapa{grid-template-columns:1.12fr 1fr}
.cn-scroll{overflow-x:auto;margin:0 -4px 8px;-webkit-overflow-scrolling:touch}
.cn-t{width:100%;border-collapse:collapse;font-size:13px;min-width:860px}
.cn-t th{font-weight:600;color:var(--mt);font-size:11.5px;padding:7px 8px;text-align:right;border-bottom:1px solid var(--ln);white-space:nowrap}
.cn-t thead tr:first-child th{color:var(--tx);font-size:12px;text-align:center;border-bottom:0}
.cn-t td{padding:7px 8px;text-align:right;border-bottom:1px solid #F0F3F0;white-space:nowrap}
.cn-t .l{text-align:left}
.cn-t tr.uf{cursor:pointer}.cn-t tr.uf:hover td{background:#F7FAF5}
.cn-t tr.sel td{background:#FFF6DF}
.cn-t tr.reg td{background:#F6F8F4;font-weight:600}
.cn-t tr.tot td{background:#EEF4E8;font-weight:700;border-top:1px solid #cfd9d1}
.cn-t .cn-n{color:var(--mt);font-size:12px;margin-left:4px}
.cn-t td:nth-child(4),.cn-t td:nth-child(7){border-right:1px solid #F0F3F0}
@media (max-width:820px){.cn-mapa{grid-template-columns:1fr}}
@media (max-width:560px){#abcG0{height:430px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Safra Brasil (Conab): área, produtividade e produção por estado · dashboard em HTML\n"
       "     Dados: dados/conab/*.json no GitHub, gerados por exporta_conab.py a cada levantamento da Conab. -->\n")
faq = [("O que é o levantamento de safra da Conab?", "É a estimativa oficial da safra brasileira de grãos, publicada todo mês pela Companhia Nacional de Abastecimento. Cada ano-safra tem 12 levantamentos: o primeiro sai em outubro, antes do plantio da soja, e o último em setembro do ano seguinte, com a colheita encerrada. Os números são por estado e por cultura."),
       ("Como a Conab faz a estimativa?", "Combina pesquisa de campo com produtores, cooperativas e agentes do setor em todos os estados, imagens de satélite, modelos agrometeorológicos e estatísticos. No começo da safra a produtividade é projetada por tendência e clima; ela vai sendo ajustada conforme o plantio, o desenvolvimento das lavouras e a colheita avançam."),
       ("Por que as estimativas mudam ao longo da safra?", "Porque o clima e o andamento das lavouras só se confirmam com o tempo. O gráfico de revisões mostra como a produção estimada evoluiu de um levantamento para o outro nas últimas safras, o que ajuda a avaliar quanto a estimativa atual ainda pode mudar."),
       ("O que são milho 1ª e 2ª safra?", "O milho de 1ª safra (verão) é plantado entre setembro e dezembro, no Sul, Sudeste e parte do Nordeste. O de 2ª safra, a safrinha, é semeado logo após a colheita da soja, entre janeiro e março, principalmente em Mato Grosso, Paraná, Goiás e Mato Grosso do Sul, e responde pela maior parte do milho brasileiro."),
       ("Como converter produtividade em sacas por hectare?", "Divida a produtividade em kg/ha pelo peso da saca: 60 kg para soja, milho, trigo, sorgo e feijão, e 50 kg para arroz. Por exemplo, 3.600 kg/ha de soja equivalem a 60 sacas por hectare."),
       ("Quando o painel é atualizado?", "Sempre que a Conab publica um novo levantamento, em geral na segunda quinta-feira de cada mês, por volta das 9h. O painel verifica duas vezes por dia útil e atualiza sozinho.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Safra Brasil por Estado (Conab) · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/safra-brasil-conab/",
       "description": "Estimativas da Conab para a safra brasileira de grãos por estado: soja, milho 1ª e 2ª safra, trigo, algodão, arroz, feijão e sorgo, com mapa, ranking, série histórica e revisões de cada levantamento.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("conab-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("conab.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
