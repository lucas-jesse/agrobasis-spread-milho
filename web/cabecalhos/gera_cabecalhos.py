"""Cabeçalho enxuto das páginas de seção do site (substitui o banner com foto).
Gera um HTML por página, para colar como widget HTML no topo da página no Elementor."""
from pathlib import Path

CSS = """<style>
.abh{background:#F6F8F4;border-bottom:1px solid #E7ECE8;font-family:'Geist',Arial,sans-serif}
.abh-in{max-width:1180px;margin:0 auto;padding:30px 24px 28px;box-sizing:border-box}
.abh-bc{font-size:12.5px;color:#7a847c;margin:0 0 12px}
.abh-bc a{color:#1E4812;font-weight:600;text-decoration:none}.abh-bc a:hover{text-decoration:underline}
.abh-bc span{margin:0 7px;color:#b5beb7}
.abh h1{font-family:'Sora',Arial,sans-serif;font-size:34px;line-height:1.18;font-weight:700;color:#1d2420;margin:0;letter-spacing:-.01em}
.abh h1:before{content:"";display:block;width:36px;height:3px;border-radius:2px;background:#54931B;margin:0 0 14px}
.abh p{font-size:15.5px;line-height:1.65;color:#4a544c;margin:10px 0 0;max-width:760px}
.abh-meta{display:flex;flex-wrap:wrap;gap:6px 18px;margin:14px 0 0;font-size:12.5px;color:#6b756d}
.abh-meta b{color:#1E4812;font-weight:700}
.abh-meta i{display:inline-block;width:6px;height:6px;border-radius:50%;background:#54931B;margin-right:7px;vertical-align:1px}
@media (max-width:620px){.abh-in{padding:22px 16px 20px}.abh h1{font-size:26px}.abh p{font-size:14.5px}}
</style>"""
FONTES = """<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Sora:wght@600;700&display=swap" rel="stylesheet">"""

PAGINAS = {
    "dashboards": ("Dashboards", "Painéis de mercado agrícola",
                   "Soja, milho, trigo, câmbio, basis e posição dos fundos em painéis interativos, montados com dados oficiais da Conab, do USDA, do CFTC, da B3 e do Banco Central.",
                   '<span><i></i><b id="abhN">Painéis</b> interativos</span><span><i></i>Atualização automática</span><span><i></i>Gráficos exportáveis</span>'),
    "analises": ("Análises", "Análises e relatórios",
                 "Leitura técnica dos relatórios do USDA e da Conab, do câmbio e dos fundamentos que movem os preços de soja, milho e trigo, com o que muda para quem vende e compra grão.", ""),
    "educacional": ("Educacional", "Educacional", "", ""),
    "agenda": ("Agenda do Agro", "Agenda do Agro",
               "Datas e horários dos relatórios, indicadores e eventos que movimentam o mercado de grãos no Brasil e no mundo.", ""),
    "dados": ("Dados", "Dados históricos",
              "Séries históricas e levantamentos próprios sobre câmbio, oferta, demanda e preços, para análise de risco e tomada de decisão.", ""),
}
CONTA = """<script>(function(){function c(){var n=document.querySelectorAll('.agd-card:not([hidden])').length,e=document.getElementById('abhN');if(e&&n)e.textContent=n+' painéis';}
if(document.readyState!=='loading')setTimeout(c,1200);else document.addEventListener('DOMContentLoaded',function(){setTimeout(c,1200);});setTimeout(c,3500);})();</script>"""

for slug, (bc, h1, sub, meta) in PAGINAS.items():
    html = (f"<!-- AgroBasis · cabeçalho da página /{slug}/ (gerado por web/cabecalhos/gera_cabecalhos.py) -->\n{FONTES}\n{CSS}\n"
            f'<header class="abh"><div class="abh-in"><nav class="abh-bc" aria-label="Navegação"><a href="/">Início</a><span>/</span>{bc}</nav>'
            f"<h1>{h1}</h1>" + (f"<p>{sub}</p>" if sub else "") + (f'<div class="abh-meta">{meta}</div>' if meta else "") + "</div></header>"
            + (CONTA if slug == "dashboards" else ""))
    Path(f"{slug}.html").write_text(html)
print("ok")
