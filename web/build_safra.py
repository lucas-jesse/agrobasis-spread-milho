import json
from pathlib import Path
css = Path("comex-template.html").read_text()
css = css[css.index("<style>"):css.index("</style>") + 8]
DL = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12m0 0l-5-5m5 5l5-5M4 21h16"/></svg>'
faq = [("De onde vêm os dados?", "Do relatório semanal Crop Progress do Departamento de Agricultura dos Estados Unidos (USDA NASS), consultado direto na API oficial Quick Stats. Os números são nacionais e a série começa em 2010."),
       ("Quando o painel é atualizado?", "O USDA publica o Crop Progress às segundas-feiras, às 17h de Brasília, de abril a novembro (na terça quando há feriado nos EUA). O painel consulta a API logo depois e nos dias seguintes, e atualiza sozinho."),
       ("O que significa lavoura em condição boa ou excelente?", "O USDA classifica as lavouras em cinco notas: muito ruim, ruim, regular, boa e excelente. A soma de boa e excelente é o indicador mais acompanhado pelo mercado: quanto maior, maior a expectativa de produtividade."),
       ("Como funciona o índice de condição?", "É a média ponderada das cinco notas, de 1 (muito ruim) a 5 (excelente). Resume a distribuição inteira em um número e ajuda a comparar semanas e anos."),
       ("O que é a média de 5 anos?", "É a média das cinco safras anteriores na mesma época do ano. A faixa verde mostra o menor e o maior valor desses cinco anos, para indicar o que é normal para a semana."),
       ("Por que isso importa para o produtor brasileiro?", "Os EUA são o maior produtor de milho e o segundo de soja. Atraso no plantio, piora na condição ou colheita lenta mexem com a Bolsa de Chicago, que é a referência do preço da soja e do milho no Brasil.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Condição e Avanço das Lavouras dos EUA · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web", "url": "https://agrobasis.com.br/dashboards/condicao-de-safra-eua/",
       "description": "Condição das lavouras e avanço do plantio e da colheita de milho, soja e trigo nos Estados Unidos, com dados semanais do USDA Crop Progress, comparação com o ano anterior e com a média de 5 anos.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
head = '''<!-- AgroBasis · Condição e Avanço das Lavouras dos EUA (USDA NASS Crop Progress) · dashboard em HTML
     Dados: dados/safra_eua.json no GitHub, exportado da API Quick Stats pelo GitHub Actions. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Sora:wght@600;700&display=swap" rel="stylesheet">
'''
corpo = Path("safra-corpo.html").read_text().replace("__DL__", DL).replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False))
html = head + css + "\n" + corpo + "\n<script>\n" + Path("safra-app.js").read_text() + "</script>\n"
Path("safra-eua.html").write_text(html); print(len(html))
