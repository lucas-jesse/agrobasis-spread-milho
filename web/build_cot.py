import json
from pathlib import Path
T = Path("cot.html").read_text()
faq = [("O que é o relatório COT?", "O Commitments of Traders é publicado toda sexta pela CFTC, a reguladora dos mercados futuros dos EUA. Mostra quantos contratos cada grupo de participantes tinha comprado e vendido na terça-feira anterior."),
       ("Quem são os fundos neste painel?", "É a categoria Managed Money do relatório: gestores de recursos e fundos especulativos, como CTAs e fundos de commodities. Costumam seguir tendência e por isso movimentam preço no curto prazo."),
       ("O que significa posição líquida?", "É o número de contratos comprados menos o de vendidos. Positiva indica que o grupo aposta na alta; negativa, na queda. Um contrato de soja ou milho equivale a 5.000 bushels."),
       ("Como ler o percentil de 5 anos?", "Mostra onde a posição de hoje está em relação a todas as semanas dos últimos cinco anos. Perto de 100, os fundos estão entre os mais comprados do período; perto de 0, entre os mais vendidos. Extremos costumam anteceder correções, porque sobra pouco espaço para novas compras ou vendas."),
       ("Por que produtores e comerciais ficam do lado oposto?", "Produtores, tradings e processadoras usam a bolsa para proteger o preço da mercadoria física. Quando os fundos compram, normalmente são eles que vendem, por isso as posições se espelham."),
       ("Quando os dados são atualizados?", "A CFTC publica às sextas, às 15h30 de Nova York (17h30 de Brasília), com as posições da terça-feira. Em semanas com feriado nos EUA, a publicação passa para segunda. O painel atualiza sozinho logo depois.")]
fh = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Posição dos Fundos COT · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web", "url": "https://agrobasis.com.br/dashboards/posicao-fundos-cftc/",
       "description": "Posição dos fundos e demais participantes no COT da CFTC para soja, milho, farelo, óleo, trigo e algodão: posição líquida, percentil de 5 anos, sazonalidade e relação com o preço.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
Path("cot-final.html").write_text(T.replace("__FAQ__", fh).replace("__LD__", json.dumps(ld, ensure_ascii=False)))
print("ok")
