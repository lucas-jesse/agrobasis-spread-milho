"""Monta a página "Previsão do tempo por município" (tempo.html), publicada em /clima/. CSS base do painel COT + extras."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """.tp-busca{display:flex;gap:10px;align-items:stretch;margin:6px 0 10px;flex-wrap:wrap}
.tp-campo{position:relative;flex:1 1 320px;display:flex;align-items:center;gap:8px;background:#fff;border:1.5px solid var(--ln);border-radius:12px;padding:0 14px;color:var(--mt);transition:border-color .15s,box-shadow .15s}
.tp-campo:focus-within{border-color:var(--vc);box-shadow:0 0 0 4px rgba(84,147,27,.12)}
.tp-campo input{flex:1;border:0;outline:0;font:500 16px Geist,sans-serif;color:var(--tx);padding:13px 0;background:transparent;min-width:0}
.tp-sug{display:none;position:absolute;left:-1px;right:-1px;top:calc(100% + 6px);background:#fff;border:1px solid var(--ln);border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,.1);z-index:30;overflow:hidden}
.tp-sug div{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;cursor:pointer;font-size:14.5px;color:var(--tx)}
.tp-sug div small{color:var(--mt);font-weight:600}
.tp-sug div:hover,.tp-sug div.ativo{background:#F3F7EF}
.tp-gps{display:inline-flex;align-items:center;gap:8px;border:1.5px solid var(--vd);background:var(--vd);color:#fff;border-radius:12px;padding:0 16px;font:600 14px Geist,sans-serif;cursor:pointer;min-height:48px}
.tp-gps:hover{background:#163a0d}.tp-gps.on{opacity:.6;pointer-events:none}
.tp-chips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}
.tp-chips button{border:1px solid var(--ln);background:#fff;border-radius:999px;padding:6px 12px;font:500 13px Geist,sans-serif;color:var(--tx);cursor:pointer}
.tp-chips button:hover{border-color:var(--vc);color:var(--vd);background:#F6FAF2}
.abc-k b small{font-size:.55em;font-weight:600;margin-left:3px;color:var(--mt)}
.abc-k em i.pos{color:#2F6DB5;font-weight:600}.abc-k em i.neg{color:#A35A1E;font-weight:600}
.tp-dias{border-top:1px solid var(--ln)}
.tp-dia{border-bottom:1px solid var(--ln)}
.tp-dia summary{list-style:none;display:grid;grid-template-columns:72px 56px 150px 1fr 28px;align-items:center;gap:8px;padding:10px 4px;cursor:pointer}
.tp-dia summary::-webkit-details-marker{display:none}
.tp-dia summary:hover{background:#F8FAF6}
.tp-d{display:flex;flex-direction:column;line-height:1.15}.tp-d b{font:700 20px Sora,sans-serif;color:var(--tx);display:flex;align-items:center;gap:4px}.tp-d small{font-size:13px;color:var(--mt)}
.tp-al{font-style:normal;display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#D2694A;color:#fff;font:700 11px Geist,sans-serif}
.tp-ic svg{display:block}
.tp-t{display:flex;gap:12px;font:600 18px Sora,sans-serif}.tp-t i{font-style:normal}.tp-t .mn{color:#2F6DB5}.tp-t .mx{color:#C0502E}
.tp-c{display:flex;align-items:center;gap:8px;justify-content:flex-start}.tp-g{display:inline-flex;gap:2px}.tp-c b{font:600 17px Sora,sans-serif;color:var(--tx);white-space:nowrap}
.tp-x{width:26px;height:26px;border-radius:7px;background:#EEF2EE;position:relative}
.tp-x:before,.tp-x:after{content:"";position:absolute;left:7px;right:7px;top:12px;height:2px;background:var(--tx);border-radius:1px}
.tp-x:after{transform:rotate(90deg);transition:transform .15s}
.tp-dia[open] .tp-x:after{transform:rotate(0)}
.tp-det{display:grid;grid-template-columns:repeat(3,1fr);gap:10px 18px;padding:4px 8px 14px 8px;font-size:13px}
.tp-det span{display:block;color:var(--mt);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em}.tp-det b{font-weight:600;color:var(--tx)}
.tp-per{grid-column:1/-1;display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.tp-per span{background:#F3F7FB;border-radius:8px;padding:6px 8px;text-transform:none;letter-spacing:0;color:var(--tx);font-size:13px}.tp-per small{display:block;color:var(--mt);font-size:11px}
.tp-dias .tp-ext{display:none}.tp-dias.todos .tp-ext{display:block}
.tp-mais{display:block;margin:14px auto 2px;border:0;background:var(--vd);color:#fff;border-radius:10px;padding:11px 30px;font:600 15px Geist,sans-serif;cursor:pointer}
.tp-mais:hover{background:#163a0d}
.abc-chart.tp-sm{height:300px}
.tp-polos{display:grid;grid-template-columns:1.15fr 1fr;gap:12px;align-items:center}
.abc-chart.tp-mapa{height:520px}.abc-chart.tp-rank{height:470px}
.tp-leg{display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--mt)}
.tp-leg i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-left:8px}
.tp-leg i.b,.tp-jc.c0{background:#4C9A2A}.tp-leg i.a,.tp-jc.c1{background:#E8B84A}.tp-leg i.r,.tp-jc.c2{background:#D2694A}
.tp-jan{overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:4px}
.tp-jt{display:grid;grid-template-columns:78px repeat(17,minmax(26px,1fr));gap:3px;margin-bottom:3px;min-width:560px}
.tp-jl{font-size:12.5px;font-weight:600;color:var(--tx);display:flex;align-items:center;position:sticky;left:0;background:#fff;z-index:1}
.tp-jh{font-size:10.5px;color:var(--mt);text-align:center}
.tp-jc{height:26px;border-radius:4px;cursor:pointer;transition:transform .1s}
.tp-jc:hover{transform:scale(1.12)}.tp-jc.x{background:#F1F3F1;cursor:default}.tp-jc.x:hover{transform:none}
.tp-jinfo{font-size:13px;color:var(--tx);background:#F6F8F4;border-radius:8px;padding:8px 12px;margin-top:8px;min-height:20px}
.abc-lead{display:flex;gap:10px;align-items:flex-start}.abc-lead svg{flex:0 0 auto;margin-top:4px;color:var(--az,#2F6DB5)}
#tpTit,.tp-coord{display:none}
@media (min-width:900px){#tpConteudo:not([hidden]){display:grid;grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);column-gap:14px;align-items:start;grid-template-rows:auto auto 1fr}
#tpConteudo>*{grid-column:1/-1;min-width:0}
#tpConteudo>.tp-dias-card{grid-column:1;grid-row:1/span 3;margin-bottom:14px}
#tpConteudo>.abc-lead{grid-column:2;grid-row:1;margin-top:0}
#tpConteudo>.abc-kpis{grid-column:2;grid-row:2;grid-template-columns:1fr 1fr;align-self:start}
#tpConteudo>.abc-kpis .abc-k{padding:16px}#tpConteudo>.abc-kpis .abc-k span,#tpConteudo>.abc-kpis .abc-k em{white-space:normal;overflow:visible;text-overflow:clip}
.tp-dia summary{grid-template-columns:66px 52px 120px 1fr 28px}}
.tp-wy{position:relative;width:100%;height:560px;border-radius:12px;overflow:hidden;background:#e9eeea;margin:6px 0 4px}
.tp-wy iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
#ao-vivo .abc-tools{display:flex;gap:8px;flex-wrap:wrap}
@media (max-width:860px){.tp-polos{grid-template-columns:1fr}}
@media (max-width:560px){.tp-wy{height:440px}#abc .abc-h{margin-bottom:10px}.tp-busca{flex-wrap:nowrap;gap:8px}.tp-campo{flex:1 1 auto}.tp-gps{flex:0 0 50px;min-height:50px;padding:0;justify-content:center}.tp-gps span{display:none}.tp-gps svg{width:20px;height:20px}.tp-chips{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;margin:0 0 14px;padding:0}.tp-chips::-webkit-scrollbar{display:none}.tp-chips button{flex:0 0 auto;white-space:nowrap}#tpConteudo:not([hidden]){display:flex;flex-direction:column}#tpConteudo>*{order:2}#tpConteudo>.tp-dias-card{order:0;scroll-margin-top:90px}#tpConteudo>.abc-lead{order:1;margin-top:4px}#tpConteudo>.abc-kpis{order:1}.tp-dia summary{grid-template-columns:50px 44px 76px 1fr 26px;gap:6px;padding:10px 0}.tp-d b{font-size:18px}.tp-t{gap:8px;font-size:16px}.tp-c b{font-size:15px}.tp-ic svg{width:40px;height:40px}.tp-det{grid-template-columns:1fr 1fr;padding:2px 0 12px}.tp-per{grid-template-columns:repeat(2,1fr)}.tp-dias-card{padding-left:12px!important;padding-right:12px!important}.abc-k span,.abc-k em{white-space:normal!important;overflow:visible!important;text-overflow:clip!important}.abc-k span{font-size:10.5px;line-height:1.3}.abc-chart.tp-mapa{height:420px}.abc-chart.tp-sm{height:260px}.tp-jt{grid-template-columns:58px repeat(17,26px)}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Previsão do tempo por município · página /clima/\n"
       "     Previsão no navegador via Open-Meteo (CC BY 4.0). Municípios: dados/geo/municipios.json. Polos: dados/clima/clima.json. -->\n")
faq = [("De onde vem a previsão do tempo desta página?", "Da plataforma Open-Meteo, que combina os principais modelos meteorológicos do mundo, como o europeu ECMWF e o americano GFS, e escolhe a melhor combinação para cada ponto. A previsão é calculada para a coordenada da sede de cada município, com dados publicados sob a licença CC BY 4.0."),
       ("O que é o normal de chuva usado na comparação?", "É a média de chuva de cada dia do ano entre 1991 e 2020, no mesmo ponto do município, calculada com a reanálise ERA5 do Copernicus. Para não comparar a previsão com um único dia histórico, a página usa a média móvel de 15 dias em torno de cada data. Assim dá para saber se a previsão está acima ou abaixo do que costuma chover na época."),
       ("Até quantos dias a previsão é confiável?", "Nos primeiros 5 a 7 dias a previsão costuma ser boa para dizer se vai chover e em que volume aproximado. Da segunda semana em diante, ela indica tendência: período mais seco ou mais chuvoso que o normal, e não o dia exato da chuva. Por isso a página destaca o acumulado e a comparação com o normal."),
       ("Como funciona a janela de pulverização?", "Para cada hora dos próximos 5 dias, entre 5h e 21h, a página cruza vento, umidade relativa, temperatura e chuva prevista. A hora é boa quando o vento fica entre 3 e 10 km/h, a umidade está em 55% ou mais, a temperatura não passa de 30 °C e não há chuva prevista. Fora dessas faixas a hora vira atenção ou evitar. É uma referência de boas práticas: a bula do produto e o agrônomo têm a palavra final."),
       ("Por que a previsão da minha cidade é diferente da de outro site?", "Cada serviço usa modelos, resoluções e ajustes diferentes, e a chuva de verão é muito localizada. Diferenças de alguns milímetros são normais. O mais útil é acompanhar a tendência: se vários dias seguidos aparecem com chuva baixa e o acumulado fica abaixo do normal, o sinal é de período mais seco."),
       ("O que mostra o mapa ao vivo?", "Três camadas do Windy: a imagem de satélite das nuvens, os radares meteorológicos que mostram onde está chovendo agora e a chuva acumulada prevista pelo modelo europeu ECMWF para as próximas horas e dias. O mapa abre centrado no município escolhido e tem uma linha do tempo para animar a imagem."),
       ("Com que frequência a previsão é atualizada?", "Os modelos rodam várias vezes por dia e a página busca a rodada mais recente sempre que você abre ou troca de município. A sua última cidade fica salva no navegador para abrir direto na próxima visita.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Previsão do tempo para o produtor · AgroBasis", "applicationCategory": "WeatherApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/clima/",
       "description": "Previsão do tempo por município para o produtor rural: chuva de 16 dias contra o normal, chuva dos últimos 30 dias, temperatura e janela de pulverização hora a hora.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("tempo-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("tempo.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
