"""Monta a página "Relação entre culturas" (interculturas.html). CSS base do painel COT + extras."""
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
extra = """#abc .abc-chart{height:340px}#abc .abc-chart.ic-g{height:400px}#abc #icG3{height:320px}
#abc .abc-card{min-width:0}
.abc-ch .abc-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ic-leit{border:1px solid var(--ln);border-left:4px solid var(--vc);border-radius:12px;padding:14px 18px;margin:0 0 14px;background:#FAFBF8}
.ic-leit h3{font:700 15px Sora,sans-serif;margin:0 0 8px;color:var(--tx)}
.ic-leit ul{margin:0;padding-left:18px}.ic-leit li{font-size:14px;line-height:1.55;color:#33403a;margin:0 0 6px}
.ic-leit p{margin:8px 0 0;font-size:11.5px;color:var(--mt)}
.ic-tw{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:6px}
.ic-t{width:100%;border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums;white-space:nowrap}
.ic-t th,.ic-t td{padding:8px 10px;border-bottom:1px solid var(--ln);text-align:right}
.ic-t th:first-child,.ic-t td:first-child{text-align:left}
.ic-t thead th{font-size:12px;color:var(--mt);font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.ic-t tbody tr{cursor:pointer}.ic-t tbody tr:hover{background:#F6F8F4}.ic-t tbody tr.on{background:#EEF4E8}
.ic-mt{color:var(--mt);font-size:11.5px}
@media (max-width:560px){#abc .abc-chart,#abc .abc-chart.ic-g{height:300px}#abc #icG3{height:280px}.ic-t{font-size:12.5px}.ic-t th,.ic-t td{padding:7px 6px}
#icTab th:nth-child(2),#icTab td:nth-child(2),#icTab th:nth-child(3),#icTab td:nth-child(3),#icTab th:nth-child(4),#icTab td:nth-child(4){display:none}.ic-leit li{font-size:13.5px}}"""
css = "\n".join(cot[ini:fim]) + "\n" + extra + "\n</style>"
cab = ("<!-- AgroBasis · Relação entre culturas (soja, milho e trigo na CBOT) · painel em HTML\n"
       "     Dados: dados/interculturas.json no GitHub, gerado por exporta_interculturas.py. -->\n")
corpo = Path("interculturas-corpo.html").read_text()
Path("interculturas.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
