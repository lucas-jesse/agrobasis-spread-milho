import json
from pathlib import Path
faq=[("Por que as opções de soja aparecem em dólares por bushel?","Porque é assim que a CBOT negocia: futuro, strike e prêmio em dólares (ou centavos) por bushel, num contrato de 5.000 bushels. Usar a mesma unidade da tela da corretora evita erro na hora de comparar. O simulador converte o resultado para reais por saca de 60 kg com o dólar futuro da data de vencimento."),
("De onde vêm o preço do futuro, o vencimento e o dólar?","São preenchidos com o fechamento mais recente coletado pelo AgroBasis: curva da soja na CBOT, milho e trigo da CBOT, milho da B3 e dólar futuro da B3. A data de vencimento da opção segue a regra de cada bolsa. Todos os campos podem ser editados."),
("Quando vence a opção de soja da CBOT?","Na última sexta-feira que antecede, em pelo menos dois dias úteis, o último dia útil do mês anterior ao do contrato. A opção de janeiro, por exemplo, vence no fim de dezembro. Na B3, a opção de milho vence no dia 15 do mês do contrato. O simulador calcula a data, mas vale conferir no calendário da bolsa por causa dos feriados."),
("Preciso informar a volatilidade?","Ela já vem com um valor típico para cada produto. Se você tiver o prêmio de tela da corretora, digite no campo prêmio de mercado: o simulador passa a usar esse prêmio e calcula a volatilidade implícita, que é a forma mais fiel de refletir o mercado do dia."),
("O que é o preço mínimo garantido?","É o menor preço que a combinação de futuro com opções entrega no vencimento. Numa put de proteção, é o strike menos o prêmio pago. No collar, existe também um preço máximo, porque a call vendida entrega a alta acima do strike dela. O valor não inclui o basis da sua praça nem custos de corretagem."),
("Qual a diferença entre o gráfico no vencimento e o de hoje?","No vencimento, a opção vale só o que estiver dentro do dinheiro. Hoje, ela ainda tem valor de tempo, que depende do prazo e da volatilidade. A linha tracejada mostra quanto a posição valeria se o futuro mudasse agora."),
("Por que preciso informar meus dados para ver o resultado?","O cadastro é pedido uma única vez por aparelho, na hora de ver o resultado. Ele permite que a equipe AgroBasis acompanhe quem usa as ferramentas do site e, quando fizer sentido, ofereça conteúdo e contato relevantes."),
("O resultado é uma recomendação?","Não. É uma simulação educacional com base nos números informados e nos preços de fechamento. Não constitui recomendação de investimento, compra ou venda. Decisões de hedge devem considerar a operação completa e a orientação de um profissional qualificado.")]
fh="".join(f'<details class="abp-faq-item"><summary>{q} <i data-lucide="chevron-down"></i></summary><p class="abp-faq-a">{a}</p></details>\n  ' for q,a in faq)
ld={"@context":"https://schema.org","@graph":[{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faq]},
 {"@type":"SoftwareApplication","name":"Simulador de Opções Agrícolas · AgroBasis","applicationCategory":"BusinessApplication","operatingSystem":"Web","url":"https://agrobasis.com.br/simulador-de-opcoes-agricolas/",
  "description":"Simulador de opções sobre futuros agrícolas da CBOT (soja, milho e trigo em US$/bushel) e da B3 (milho, boi gordo e café) pelo modelo Black-76, com preço mínimo garantido em R$ por saca, gráfico no vencimento, cenários e gregas.",
  "offers":{"@type":"Offer","price":"0","priceCurrency":"BRL"},"publisher":{"@type":"Organization","name":"AgroBasis","url":"https://agrobasis.com.br"}}]}
head='''<!--
AgroBasis · Simulador de Opções Agrícolas (Black-76), versão 2
CBOT em US$/bushel (soja, milho, trigo) e B3 (milho, boi, café). Preços de fechamento, vencimentos e dólar
vêm dos JSON do repositório agrobasis-spread-milho (dados/curva_soja.json, curva_ccm.json, manha.json, cambio.json).
Cadastro pelo mesmo Google Forms dos simuladores de milho e soja, pedido só na hora do resultado.
Publicar dentro de um widget HTML do Elementor, layout "Elementor largura total".
-->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800&amp;family=Sora:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/lucide@latest/dist/umd/lucide.js" defer=""></script>
'''
html=head+"<style>\n"+Path("abp.css").read_text()+"\n"+Path("sop.css").read_text()+"</style>\n"+Path("corpo.html").read_text().replace("__FAQ__",fh)+'<script type="application/ld+json">'+json.dumps(ld,ensure_ascii=False)+"</script>\n<script>\n"+Path("app.js").read_text()+"</script>\n"
Path("simulador-opcoes.html").write_text(html); print(len(html))
