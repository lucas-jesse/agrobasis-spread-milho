"""Monta a página "Termômetro de venda AgroBasis" (termometro.html). CSS base do painel COT + extras."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.tm-ctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;align-self:flex-end}
.tm-ctl select{font:500 13.5px Geist,sans-serif;border:1px solid var(--ln);border-radius:9px;padding:7px 10px;background:#fff;color:var(--tx);cursor:pointer;max-width:220px}
.tm-ctl .abc-seg button{font-size:13.5px;padding:7px 14px}
.tm-topo{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:14px}
.tm-gauge-card{text-align:center;padding-bottom:16px}
.abc-chart.tm-gauge{height:260px}
.tm-faixa{font:700 19px Sora,sans-serif;margin-top:-10px}
.tm-frase{font-size:14.5px;line-height:1.6;color:#3f4842;margin:10px auto 14px;max-width:440px}
.tm-share{display:inline-flex;align-items:center;gap:8px;border:1px solid #25D366;color:#128C4B;background:#fff;border-radius:10px;padding:9px 16px;font:600 14px Geist,sans-serif;cursor:pointer}
.tm-share:hover{background:#F0FBF4}
.tm-comps{display:flex;flex-direction:column;gap:14px;padding:4px 2px 10px}
.tm-ct{display:flex;align-items:baseline;gap:8px}
.tm-ct b{font-size:14.5px;color:var(--tx)}.tm-ct span{font-size:12px;color:var(--mt)}.tm-ct em{margin-left:auto;font:700 18px Sora,sans-serif;font-style:normal}
.tm-bar{height:8px;border-radius:5px;background:#EEF1EE;margin:6px 0;overflow:hidden}.tm-bar i{display:block;height:100%;border-radius:5px;transition:width .5s}
.tm-c p{margin:0;font-size:13px;line-height:1.5;color:#4a544c}
.abc-chart.tm-sm{height:330px}
.tm-teste{display:flex;flex-direction:column;gap:10px;padding:6px 0 4px}
.tm-t{display:grid;grid-template-columns:110px auto 1fr;align-items:center;gap:12px;border:1px solid var(--ln);border-radius:12px;padding:12px 14px}
.tm-t span{font-size:13px;font-weight:600;border-left:4px solid;padding-left:8px}
.tm-t b{font:700 22px Sora,sans-serif}
.tm-t small{font-size:12.5px;color:var(--mt);text-align:right}
.tm-aviso{background:#FFF8EC;border:1px solid #F1E2C4;border-radius:12px;padding:12px 14px;font-size:13px;line-height:1.55;color:#6b5a3b;margin:4px 0 12px}
@media (max-width:900px){.tm-topo{grid-template-columns:1fr}}
@media (max-width:560px){.abc-chart.tm-gauge{height:220px}.tm-faixa{font-size:17px}.tm-ctl{width:100%}.tm-ctl select{flex:1;max-width:none}.tm-t{grid-template-columns:1fr auto;row-gap:2px}.tm-t small{grid-column:1/-1;text-align:left}.abc-chart.tm-sm{height:300px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Termômetro de venda (soja e milho por praça) · painel em HTML\n"
       "     Dados: dados/termometro.json no GitHub, gerado por exporta_termometro.py. -->\n")
faq = [("O que é o Termômetro de venda AgroBasis?", "É um indicador de 0 a 100 que resume, num número só, se o momento está mais ou menos favorável para vender a soja ou o milho disponível numa praça. Quanto maior, mais favorável à venda agora. Ele junta cinco informações que normalmente ficam espalhadas: o nível do preço, o basis, a sazonalidade, a posição dos fundos em Chicago e, no milho, o carrego da B3."),
       ("Como cada componente é calculado?", "Preço: onde o preço físico da praça está dentro dos preços dos últimos 3 anos. Basis: o basis de hoje comparado com o basis da mesma época nos 5 anos anteriores. Sazonalidade: o que o preço da praça costumou fazer nos 3 meses seguintes a esta época do ano. Fundos: a posição líquida dos fundos (managed money) na CBOT contra as últimas 3 safras; fundos muito comprados deixam o preço mais exposto a uma realização. Carrego: quanto a B3 paga a mais para vender cerca de 6 meses à frente; carrego alto favorece esperar."),
       ("Como chegar à nota final?", "Cada componente vira uma nota de 0 a 100 e entra com um peso fixo. Na soja: preço 35%, basis 25%, sazonalidade 25% e fundos 15%. No milho: preço 30%, basis 20%, sazonalidade 20%, carrego 15% e fundos 15%. As regras são as mesmas todos os dias e para todas as praças."),
       ("O termômetro funciona?", "O painel mostra o teste com os dados de cada praça desde novembro de 2021: para cada dia, o que o preço físico fez nos 3 meses seguintes, separado pela faixa do termômetro naquele dia. Nas praças analisadas, as leituras altas foram seguidas, em média, por preços menores, e as leituras baixas por preços maiores. É uma tendência média, e há períodos em que o mercado fez o contrário."),
       ("O termômetro diz quando eu devo vender?", "Não. Ele é um indicador educacional e não uma recomendação de compra ou venda. A decisão de cada produtor depende do custo de produção, das contas a pagar, do espaço para armazenar, do frete e do risco que ele aceita correr. Um uso comum é escalonar as vendas: vender lotes maiores quando o termômetro está alto e segurar mais quando está baixo."),
       ("Com que frequência é atualizado?", "Todo dia útil, depois do fechamento do mercado. O preço do dia é estimado com Chicago, o dólar e o último basis conhecido da praça (na soja) ou com o milho da B3 e o último basis (no milho). Os preços físicos de referência vêm da Conab e são semanais; a posição dos fundos é publicada pela CFTC uma vez por semana.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Termômetro de venda AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/termometro-de-venda/",
       "description": "Indicador de 0 a 100 que mostra se o momento está favorável para vender soja e milho em cada praça, com preço, basis, sazonalidade, fundos e carrego.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("termometro-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("termometro.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
