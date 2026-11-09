import json
from pathlib import Path
T = Path("dolar.html").read_text()
faq = [("De onde vem a curva do dólar futuro?", "Dos contratos futuros de dólar comercial negociados na B3 (DOL), um para cada mês de vencimento. Entre um vencimento e outro, o valor é interpolado pela data. Os preços têm atraso de 10 a 15 minutos e são atualizados duas vezes por dia útil."),
       ("Por que o dólar futuro é mais caro que o dólar de hoje?", "Porque o preço futuro embute o carrego: a diferença entre o juro no Brasil e nos Estados Unidos no período. Com o DI bem acima do juro americano, cada mês à frente fica um pouco mais caro. Isso não é uma previsão de alta do dólar."),
       ("O que o Focus mostra no gráfico?", "A mediana das projeções de câmbio para o fim de cada ano, feita pelos economistas consultados semanalmente pelo Banco Central. A diferença entre o Focus e a curva da B3 mostra quanto do preço futuro é carrego e quanto é expectativa."),
       ("Como usar o simulador de trava?", "Escolha o mês em que vai receber pela venda e informe o valor em dólares. O painel mostra o dólar futuro para aquele mês, o prêmio sobre o spot e quanto a mais ou a menos a venda renderia em reais travando o câmbio. Numa operação real entram também custos, margem e o spread do banco."),
       ("O que é a volatilidade mostrada no histórico?", "É o desvio-padrão das variações diárias da PTAX nos últimos 21 pregões, anualizado. Picos de volatilidade indicam períodos de mais incerteza, quando travar o câmbio tende a fazer mais diferença no resultado.")]
ld = {"@context": "https://schema.org", "@graph": [{"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
      {"@type": "WebApplication", "name": "Curva do Dólar · AgroBasis", "applicationCategory": "FinanceApplication", "operatingSystem": "Web", "url": "https://agrobasis.com.br/dashboards/curva-do-dolar/",
       "description": "Curva do dólar futuro da B3 com dólar ao vivo, PTAX, Focus, juros futuros (DI), carrego anualizado e simulador de trava de câmbio por mês.",
       "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "publisher": {"@type": "Organization", "name": "AgroBasis", "url": "https://agrobasis.com.br"}}]}
h = T.replace("__FAQ__", "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)).replace("__LD__", json.dumps(ld, ensure_ascii=False))
Path("curva-dolar.html").write_text(h); print(len(h), h.count("__"))
