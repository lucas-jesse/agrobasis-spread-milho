"""Monta o dashboard de vendas semanais de exportação dos EUA (exportacoes-eua.html).
CSS: o mesmo do painel COT (cot-template.html), com o painel de produtos em 5 colunas."""
import json
from pathlib import Path
cot = Path("cot-template.html").read_text().split("\n")
ini = next(i for i, l in enumerate(cot) if l.startswith("<link"))
fim = next(i for i, l in enumerate(cot) if l.startswith("</style>"))
css = "\n".join(cot[ini:fim + 1]).replace("grid-template-columns:repeat(7,minmax(0,1fr))", "grid-template-columns:repeat(5,minmax(0,1fr))").replace("</style>", "@media (max-width:560px){.abc-k em{white-space:normal}}\n</style>")
cab = ("<!-- AgroBasis · Vendas semanais de exportação dos EUA (USDA FAS Export Sales) · dashboard em HTML\n"
       "     Dados: dados/export_sales/*.json no GitHub, gerados por exporta_export_sales.py às quintas, após a divulgação do USDA. -->\n")
faq = [("O que é o relatório de vendas semanais de exportação do USDA?", "É o Export Sales Report, publicado toda quinta-feira pelo Serviço Agrícola Estrangeiro (FAS) do USDA. Os exportadores dos EUA são obrigados a informar as vendas e os embarques da semana anterior, por país de destino. É o termômetro mais rápido da demanda externa pelos grãos americanos."),
       ("Qual a diferença entre vendas líquidas, embarques e compromisso?", "Vendas líquidas são os novos negócios da semana menos os cancelamentos. Embarques são o que efetivamente saiu dos portos. Compromisso é a soma do que já foi embarcado com o que está vendido e ainda falta embarcar no ano-safra."),
       ("Por que comparar com a projeção do USDA?", "O relatório de oferta e demanda (WASDE) projeta quanto os EUA vão exportar no ano-safra. Comparar o volume já vendido com essa projeção, e com o que era normal na mesma semana dos anos anteriores, mostra se a demanda está adiantada ou atrasada. Ritmo fraco aumenta a chance de corte na exportação e de estoques maiores."),
       ("O que é o destino a definir?", "São vendas cujo país de destino ainda não foi declarado pelo comprador, registradas como Unknown. Na prática, boa parte costuma ir para a China, que muitas vezes compra por meio de tradings sem informar o destino final na hora da venda."),
       ("Quando começa o ano-safra nos EUA?", "Para soja e milho, em 1º de setembro; para o trigo, em 1º de junho; para farelo e óleo de soja, em 1º de outubro. Cada linha do gráfico acumulado começa do zero no início do ano-safra."),
       ("Quando o painel é atualizado?", "O USDA divulga às quintas, às 8h30 de Washington (10h30 de Brasília, 9h30 no horário de verão dos EUA), com a semana encerrada na quinta anterior. O painel atualiza sozinho logo depois. Em semanas com feriado nos EUA, a divulgação passa para sexta.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Vendas de Exportação dos EUA · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
       "url": "https://agrobasis.com.br/dashboards/exportacoes-eua-usda/",
       "description": "Vendas semanais de exportação dos EUA de soja, milho, trigo, farelo e óleo de soja (USDA Export Sales): ritmo contra os últimos 5 anos, % da projeção do USDA, destinos e compradores da semana.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
corpo = Path("exs-corpo.html").read_text().replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("exportacoes-eua.html").write_text(cab + css + "\n\n" + corpo)
print("ok", len(cab + css + corpo))
