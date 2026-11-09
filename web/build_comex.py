import json
from pathlib import Path
T = Path("comex-template.html").read_text()
faq = [("De onde vêm os dados?", "Do Comex Stat, o sistema oficial de estatísticas de comércio exterior do Ministério do Desenvolvimento, Indústria, Comércio e Serviços (MDIC). Os números são consultados direto na API pública e somam todos os códigos NCM de cada produto."),
       ("Quando o painel é atualizado?", "O MDIC divulga o mês fechado nos primeiros dias úteis do mês seguinte. O painel consulta a API duas vezes por dia útil e atualiza sozinho assim que o novo mês aparece. O mês anterior também é reconsultado, porque o MDIC pode revisá-lo."),
       ("Por que comparar de janeiro até o último mês e não o ano inteiro?", "Porque o ano corrente ainda está incompleto. Comparar o mesmo intervalo de meses em todos os anos evita conclusões erradas, já que a soja, por exemplo, concentra o embarque entre março e julho."),
       ("O que é o preço médio FOB?", "É o valor exportado em dólares dividido pela quantidade embarcada, ou seja, o preço médio por tonelada posto no navio, sem frete marítimo e seguro. Serve como termômetro do preço efetivamente recebido nas vendas externas."),
       ("O que significa a concentração HHI?", "O índice Herfindahl-Hirschman soma o quadrado da participação de cada país. Acima de 2.500 indica mercado concentrado em poucos compradores, o que aumenta o risco comercial; abaixo de 1.500, compradores diversificados."),
       ("O estado de origem é onde o grão foi produzido?", "Não necessariamente. O Comex Stat registra a unidade da federação do produtor da mercadoria declarada na exportação, que em geral coincide com a região de produção, mas pode refletir a sede de quem exportou ou industrializou o produto.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Exportação e Importação de Grãos · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web", "url": "https://agrobasis.com.br/dashboards/exportacao-e-importacao-de-graos/",
       "description": "Exportações e importações brasileiras de soja, farelo, óleo, milho e trigo com dados oficiais do Comex Stat/MDIC: ritmo mensal, acumulado no ano, destinos, estados de origem e preço médio FOB.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
Path("comex.html").write_text(T.replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False)))
print("ok")
