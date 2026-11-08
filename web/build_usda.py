import json
from pathlib import Path
T = Path("usda-template.html").read_text()
PAGS = {
 "soja": dict(titulo="Soja", slug="usda-complexo-soja", desc="Oferta e demanda mundial do complexo soja (grão, farelo e óleo) pelo USDA: produção, esmagamento, exportação, estoques e ranking de países.",
   faq=[("O que mostra este painel?","O balanço mundial de oferta e demanda da soja em grão, do farelo e do óleo de soja segundo o USDA, por país e por safra, desde 2000/01."),
        ("De onde vêm os números?","Do PSD Online do USDA/FAS, a mesma base do relatório WASDE. Os dados são atualizados automaticamente no dia de cada novo relatório."),
        ("Por que a última safra aparece mais clara?","Porque é a projeção atual do USDA, que ainda pode ser revisada nos próximos relatórios."),
        ("Como ler a relação estoque/consumo?","É o estoque final dividido pelo consumo do ano. Quanto mais baixa, mais apertado o balanço e maior a sensibilidade do preço a problemas de oferta."),
        ("Como o Mundo é calculado?","Pela soma de todos os países do PSD, mesmo critério usado pelo USDA nos totais mundiais.")]),
 "milho": dict(titulo="Milho", slug="usda-milho", desc="Oferta e demanda mundial de milho pelo USDA: produção, consumo, exportação, estoques, relação estoque/consumo e ranking de países.",
   faq=[("O que mostra este painel?","O balanço mundial de oferta e demanda de milho segundo o USDA, por país e por safra, desde 2000/01."),
        ("De onde vêm os números?","Do PSD Online do USDA/FAS, a mesma base do relatório WASDE. Os dados são atualizados automaticamente no dia de cada novo relatório."),
        ("Por que a última safra aparece mais clara?","Porque é a projeção atual do USDA, que ainda pode ser revisada nos próximos relatórios."),
        ("Como ler a relação estoque/consumo?","É o estoque final dividido pelo consumo do ano. Quanto mais baixa, mais apertado o balanço e maior a sensibilidade do preço a problemas de oferta."),
        ("A safra do Brasil segue o ano-safra brasileiro?","O USDA usa um ano comercial próprio para cada país. Para o Brasil, a safra 26/27 do USDA corresponde ao milho colhido em 2027.")]),
 "trigo": dict(titulo="Trigo", slug="usda-trigo", desc="Oferta e demanda mundial de trigo pelo USDA: produção, consumo, exportação, estoques, relação estoque/consumo e ranking de países.",
   faq=[("O que mostra este painel?","O balanço mundial de oferta e demanda de trigo segundo o USDA, por país e por safra, desde 2000/01."),
        ("De onde vêm os números?","Do PSD Online do USDA/FAS, a mesma base do relatório WASDE. Os dados são atualizados automaticamente no dia de cada novo relatório."),
        ("Por que a última safra aparece mais clara?","Porque é a projeção atual do USDA, que ainda pode ser revisada nos próximos relatórios."),
        ("Como ler a relação estoque/consumo?","É o estoque final dividido pelo consumo do ano. Quanto mais baixa, mais apertado o balanço e maior a sensibilidade do preço a problemas de oferta."),
        ("Por que a China pesa tanto nos estoques mundiais?","A China concentra uma parte grande dos estoques mundiais de trigo, que em geral não chegam ao mercado internacional. Vale olhar também o balanço sem a China.")]),
}
LINKS = {"soja": [("/dashboards/usda-milho/","USDA Milho"),("/dashboards/usda-trigo/","USDA Trigo"),("/dashboards/basis-soja-brasil/","Basis Soja"),("/simulador-de-soja/","Simulador de Soja")],
         "milho": [("/dashboards/usda-complexo-soja/","USDA Soja"),("/dashboards/usda-trigo/","USDA Trigo"),("/dashboards/spread-milho-b3/","Spread Milho B3"),("/simulador-de-milho/","Simulador de Milho")],
         "trigo": [("/dashboards/usda-complexo-soja/","USDA Soja"),("/dashboards/usda-milho/","USDA Milho"),("/dashboards/posicao-fundos-cftc/","Posição dos Fundos"),("/agenda/","Agenda do Agro")]}
for pag, c in PAGS.items():
    faq = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in c["faq"])
    links = "".join(f'<a href="{h}">{t}</a>' for h, t in LINKS[pag] + [("/agenda/","Agenda do Agro") if pag!="trigo" else ("/dashboards/","Todos os dashboards"), ("/dashboards/","Todos os dashboards")][:2 if pag!="trigo" else 1])
    ld = {"@context":"https://schema.org","@graph":[{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in c["faq"]]},
          {"@type":"WebApplication","name":f"USDA {c['titulo']} · AgroBasis","applicationCategory":"FinanceApplication","operatingSystem":"Web","url":f"https://agrobasis.com.br/dashboards/{c['slug']}/","description":c["desc"],"offers":{"@type":"Offer","price":"0","priceCurrency":"BRL"},"publisher":{"@type":"Organization","name":"AgroBasis","url":"https://agrobasis.com.br"}}]}
    h = T.replace("__TITULO__", c["titulo"]).replace("__PAGINA__", pag).replace("__FAQ__", faq).replace("__LINKS__", links).replace("__LD__", json.dumps(ld, ensure_ascii=False))
    Path(f"usda-{pag}.html").write_text(h)
    print(pag, len(h), h.count("__"))
