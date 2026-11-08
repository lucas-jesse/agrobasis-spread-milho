import json
from pathlib import Path
T = Path("basis-template.html").read_text()
FAQ_COMUM = [("Por que o basis daqui é diferente do que eu vejo na cooperativa ou na cerealista?", "Porque o painel usa preços do mercado disponível, negociados entre empresas nas praças de referência. O preço de balcão pago ao produtor desconta frete, armazenagem, quebra e a margem de quem compra, então o basis de balcão costuma ser mais fraco que o mostrado aqui."),
             ("Com que frequência os dados são atualizados?", "O painel lê a planilha de preços físicos do AgroBasis de hora em hora, das 8h às 20h nos dias úteis. A data do último preço aparece no topo."),
             ("O preço projetado é um preço negociável?", "Não. É uma referência teórica que combina a curva futura de hoje com o basis médio dos últimos cinco anos para o mesmo período. Serve para comparar cenários, não como cotação de compra ou venda.")]
PAGS = {
 "soja": dict(produto="Soja", slug="basis-soja-brasil", curva="dados/curva_soja.json", fonte="Fonte: preços físicos AgroBasis · CBOT · PTAX/BCB", curta="Fonte: físico AgroBasis · CBOT · PTAX",
   un="c/bu", unLongo="cents de dólar por bushel", dec=1, padrao="Santa Rosa",
   desc="Basis da soja por praça no Brasil: preço físico convertido contra a CBOT, comparação com a média de 5 anos, percentil histórico e preço projetado.",
   faq=[("O que é o basis da soja?", "É a diferença entre o preço físico da soja numa praça, convertido para dólares por bushel pela PTAX, e o contrato de referência da CBOT. Basis positivo indica físico valorizado frente a Chicago; negativo, descontado."),
        ("Qual contrato da CBOT é usado como referência?", "O primeiro vencimento seguinte ao mês corrente, sem usar o contrato que vence no próprio mês. Em outubro, por exemplo, a referência é novembro; em dezembro, janeiro do ano seguinte."),
        ("Como ler o percentil de 5 anos?", "Mostra em que posição o basis de hoje está entre todas as observações dos últimos cinco anos daquela praça. Perto de 100 é um basis historicamente forte; perto de 0, fraco.")] + FAQ_COMUM,
   links=[("/simulador-de-soja/","Simulador de Soja"),("/dashboards/basis-milho-brasil/","Basis Milho"),("/dashboards/usda-complexo-soja/","USDA Soja"),("/dashboards/curva-do-dolar/","Curva do Dólar"),("/dashboards/","Todos os dashboards")]),
 "milho": dict(produto="Milho", slug="basis-milho-brasil", curva="dados/curva_ccm.json", fonte="Fonte: preços físicos AgroBasis e Conab · B3", curta="Fonte: físico AgroBasis/Conab · B3",
   un="R$/sc", unLongo="reais por saca", dec=2, padrao="Santa Rosa RS",
   desc="Basis do milho por praça no Brasil: preço físico contra o contrato CCM da B3, comparação com a média de 5 anos, percentil histórico e preço projetado.",
   faq=[("O que é o basis do milho?", "É a diferença, em reais por saca, entre o preço físico do milho numa praça e o contrato de referência do milho na B3 (CCM). Basis negativo indica físico abaixo da bolsa, o mais comum no interior."),
        ("De onde vêm os preços físicos?", "Da série diária do AgroBasis, complementada pela pesquisa semanal de preços por município da Conab. Nas semanas da Conab, o basis usa a média da B3 na mesma semana."),
        ("Como ler o percentil de 5 anos?", "Mostra em que posição o basis de hoje está entre todas as observações dos últimos cinco anos daquela praça. Perto de 100 é um basis historicamente forte; perto de 0, fraco.")] + FAQ_COMUM,
   links=[("/simulador-de-milho/","Simulador de Milho"),("/dashboards/spread-milho-b3/","Spread Milho B3"),("/dashboards/basis-soja-brasil/","Basis Soja"),("/dashboards/usda-milho/","USDA Milho"),("/dashboards/","Todos os dashboards")]),
}
for pag, c in PAGS.items():
    cfg = {"pagina": pag, "produto": c["produto"], "curva": c["curva"], "un": c["un"], "unLongo": c["unLongo"], "dec": c["dec"], "padrao": c["padrao"], "fonteCurta": c["curta"]}
    faq = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in c["faq"])
    links = "".join(f'<a href="{h}">{t}</a>' for h, t in c["links"])
    ld = {"@context":"https://schema.org","@graph":[{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in c["faq"]]},
          {"@type":"WebApplication","name":f"Basis {c['produto']} Brasil · AgroBasis","applicationCategory":"FinanceApplication","operatingSystem":"Web","url":f"https://agrobasis.com.br/dashboards/{c['slug']}/","description":c["desc"],"offers":{"@type":"Offer","price":"0","priceCurrency":"BRL"},"publisher":{"@type":"Organization","name":"AgroBasis","url":"https://agrobasis.com.br"}}]}
    h = (T.replace("__CFG__", json.dumps(cfg, ensure_ascii=False)).replace("__PRODUTO__", c["produto"]).replace("__PAGINA__", pag).replace("__CURVA__", c["curva"])
          .replace("__FONTE__", c["fonte"]).replace("__FAQ__", faq).replace("__LINKS__", links).replace("__LD__", json.dumps(ld, ensure_ascii=False)))
    Path(f"basis-{pag}.html").write_text(h); print(pag, len(h), h.count("__"))
