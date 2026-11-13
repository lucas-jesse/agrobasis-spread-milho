"""Monta o dashboard "Clima e El Niño nas regiões produtoras" (clima.html). CSS base do painel COT + extras."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.cl-status{display:flex;flex-direction:column;align-items:flex-end;gap:4px;align-self:flex-end}
.cl-badge{display:inline-flex;align-items:center;gap:6px;background:#FBEDE7;color:#A33E20;border:1px solid #F1CFC2;border-radius:999px;padding:5px 12px;font:600 12.5px Geist,sans-serif}
.cl-badge:before{content:"";width:7px;height:7px;border-radius:50%;background:#C0502E;box-shadow:0 0 0 3px rgba(192,80,46,.18)}
.cl-status small{font-size:11.5px;color:var(--mt)}
.abc-chart.cl-sm{height:340px}
.cl-sec{font-family:Sora,sans-serif;font-size:21px;font-weight:700;color:var(--tx);margin:34px 0 14px;padding-top:6px}
.cl-sec:before{content:"";display:block;width:32px;height:3px;border-radius:2px;background:var(--vc);margin-bottom:12px}
.cl-mapa{grid-template-columns:1.1fr 1fr}
.cl-mapa .abc-chart{height:520px}
.cl-local{background:#F6F8F4;border:1px solid var(--ln);border-radius:16px;padding:16px;margin:4px 0 8px}
.cl-local .abc-k{background:#fff}
.cl-lh{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.cl-ln{font-family:Sora,sans-serif;font-size:22px;font-weight:700;color:var(--vd)}
.cl-lm{font-size:13px;color:var(--mt);margin-top:3px}
.cl-sel select,#abcUf select{font:500 13px Geist,sans-serif;border:1px solid var(--ln);border-radius:8px;padding:7px 10px;background:#fff;color:var(--tx);cursor:pointer}
.cl-sel{padding:0;border:0;background:none}
#abcUf{padding:0;border:0;background:none}
.cn-scroll{overflow-x:auto;margin:0 -4px 8px;-webkit-overflow-scrolling:touch}
.cn-t{width:100%;border-collapse:collapse;font-size:13px;min-width:560px}
.cn-t th{font-weight:600;color:var(--mt);font-size:11.5px;padding:7px 8px;text-align:right;border-bottom:1px solid var(--ln);white-space:nowrap}
.cn-t td{padding:6px 8px;text-align:right;border-bottom:1px solid #F0F3F0;white-space:nowrap}
.cn-t td small{color:var(--mt);font-size:11px}
.cn-t .l{text-align:left}
.cn-t tr.uf{cursor:pointer}.cn-t tr.uf:hover td{background:#F7FAF5}
.cn-t tr.sel td{background:#FFF6DF}
.cn-t tr.tot td{font-weight:700;border-bottom:1px solid #cfd9d1}
.cl-cel{display:inline-block;min-width:54px;padding:3px 6px;border-radius:6px;font-weight:600;text-align:center}
@media (max-width:860px){.cl-mapa{grid-template-columns:1fr}}
@media (max-width:560px){.cl-mapa .abc-chart{height:430px}.cl-status{align-self:flex-start;align-items:flex-start;margin-top:8px}.cl-local{padding:12px;margin:0 -6px}.cl-ln{font-size:19px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Clima e El Niño nas regiões produtoras · dashboard em HTML\n"
       "     Dados: dados/clima/*.json no GitHub, gerados por exporta_clima.py (NOAA CPC, ERA5, ECMWF, Conab). -->\n")
faq = [("O que é o El Niño e por que ele importa para a safra?", "É o aquecimento anormal das águas do Pacífico equatorial, que muda a circulação da atmosfera e o regime de chuvas em várias partes do mundo. No Brasil, o padrão típico é chuva acima da média no Sul e chuva irregular ou abaixo da média no Norte, no Nordeste e em parte do Matopiba, o que mexe com a produtividade de soja, milho e trigo."),
       ("Qual índice o painel usa para medir o El Niño?", "Dois índices da NOAA. O Niño 3.4 semanal mostra a anomalia da temperatura do mar na região central do Pacífico, semana a semana. O RONI (Relative Oceanic Niño Index), adotado pela NOAA como índice oficial de intensidade, compara essa região com a média dos trópicos, em médias de três meses. Acima de +0,5 °C há El Niño; acima de +1,5 °C, El Niño forte."),
       ("De onde vêm os dados de chuva?", "A chuva observada vem da reanálise ERA5 do Copernicus, produzida pelo centro europeu ECMWF, com dados diários desde 1980 no ponto de cada município. A normal climatológica é a média de 1991 a 2020 do mesmo ponto. A previsão de 15 dias é o conjunto de 51 cenários do modelo do ECMWF. Os dados chegam pela plataforma Open-Meteo."),
       ("Como foi calculado o efeito do El Niño na produtividade?", "Com a série histórica da Conab por estado, desde a safra 1990/91. Para cada estado e cultura, o painel calcula a tendência de produtividade (que cresce com a tecnologia) e mede quanto cada safra ficou acima ou abaixo dela. Depois agrupa as safras pela fase do ENSO no verão, medida pelo RONI de dezembro a fevereiro. Para o trigo, vale a fase de agosto a outubro do ano da colheita."),
       ("O El Niño garante quebra no Matopiba e safra cheia no Sul?", "Não. Ele aumenta a chance desses resultados, mas cada evento é diferente e outros fatores pesam, como o Atlântico, a distribuição da chuva ao longo do ciclo e o manejo. Por isso o painel mostra a chuva observada e a previsão para cada região, além da média histórica. Há poucas safras de El Niño forte na série, e as médias por fase devem ser lidas como tendência."),
       ("Com que frequência o painel é atualizado?", "Duas vezes por dia. A chuva observada e a previsão de 15 dias são atualizadas de manhã e à noite. Os índices da NOAA entram assim que são publicados: o Niño 3.4 toda segunda-feira, o RONI e as probabilidades uma vez por mês, na segunda quinta-feira.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Clima e El Niño nas regiões produtoras · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/clima-el-nino/",
       "description": "El Niño em tempo real, chuva observada e prevista em 16 polos produtores de grãos e o efeito histórico do ENSO na produtividade de soja, milho e trigo por estado.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("clima-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("clima.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
