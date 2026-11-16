"""Monta a página "Milho B3 x Dólar" (milho-dolar.html). CSS base do painel COT + extras."""
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """#abc .abc-chart{height:340px}#abc .abc-chart.md{height:380px}
.md-res{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:2px 0 12px}
.md-res div{border:1px solid var(--ln);border-radius:12px;padding:10px 12px}
.md-res b{display:block;font:700 22px Sora,sans-serif;color:var(--tx)}.md-res span{font-size:12.5px;color:var(--mt)}
#abc .abc-card{min-width:0}.md-tw{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
.md-t{width:100%;border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums;white-space:nowrap}
.md-t th,.md-t td{padding:8px 10px;border-bottom:1px solid var(--ln);text-align:right}
.md-t th:first-child,.md-t td:first-child{text-align:left}
.md-t thead th{font-size:12px;color:var(--mt);font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.md-t .md-up{color:#2E7D1E;font-weight:600}.md-t .md-dn{color:#B4441F;font-weight:600}.md-t .md-mt{color:var(--mt);text-align:center}
.md-in{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:4px 0 14px}
.md-in label{display:flex;flex-direction:column;gap:5px;font-size:12.5px;color:var(--mt);font-weight:600}
.md-in input,.md-in select{font:500 14.5px Geist,sans-serif;border:1px solid var(--ln);border-radius:9px;padding:9px 10px;background:#fff;color:var(--tx);min-width:0;width:100%;box-sizing:border-box}
.md-out{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}
.md-out div{background:#F6F8F4;border-radius:12px;padding:12px 14px}
.md-out span{display:block;font-size:12px;color:var(--mt);font-weight:600}.md-out b{display:block;font:700 22px Sora,sans-serif;margin:3px 0}.md-out em{font-style:normal;font-size:12.5px;color:var(--mt)}
.md-cen th{background:#F6F8F4}.md-cen td,.md-cen th{text-align:center!important}
.tm-aviso{background:#FFF8EC;border:1px solid #F1E2C4;border-radius:12px;padding:12px 14px;font-size:13px;line-height:1.55;color:#6b5a3b;margin:4px 0 12px}
@media (max-width:900px){.md-in{grid-template-columns:repeat(2,minmax(0,1fr))}.md-res{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:560px){#abc .abc-chart,#abc .abc-chart.md{height:300px}.md-out{grid-template-columns:1fr}.md-res b,.md-out b{font-size:19px}.md-t{font-size:12.5px}.md-t th,.md-t td{padding:7px 6px}#mdEp th:nth-child(2),#mdEp td:nth-child(2),#mdEp th:nth-child(4),#mdEp td:nth-child(4),#mdEp th:nth-child(5),#mdEp td:nth-child(5){display:none}.md-cen{font-size:11.5px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Milho B3 x Dólar (valor relativo) · painel em HTML\n"
       "     Dados: dados/milho_dolar.json no GitHub, gerado por exporta_milho_dolar.py. -->\n")
corpo = Path("milho-dolar-corpo.html").read_text()
Path("milho-dolar.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
