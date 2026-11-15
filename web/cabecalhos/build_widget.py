"""Monta o HTML do widget global do cabeçalho (id ab0menu no template 24 do Elementor):
CSS do menu responsivo + menu fixo ao rolar + troca do bloco antigo de comunidade pela faixa do WhatsApp."""
import json
from pathlib import Path
css = Path("menu-responsivo.css").read_text()
faixa = Path("cta-whatsapp.html").read_text().split("-->", 1)[1].strip()
js = """<script>(function(){var b=document.documentElement,on=false;function f(){var s=window.scrollY>8;if(s!==on){on=s;b.classList.toggle("ab-rolou",s);}}window.addEventListener("scroll",f,{passive:true});f();
var FAIXA=%s;
function troca(){[].slice.call(document.querySelectorAll(".elementor-widget-heading,.elementor-widget-icon-box")).filter(function(w){return /Junte-se a produtores/.test(w.textContent);}).forEach(function(w){
var c=w.closest(".e-con");if(!c||c.dataset.abw)return;
while(c.parentElement){var p=c.parentElement.closest(".e-con");if(!p)break;var filhos=p.querySelectorAll(":scope>.e-con,:scope>.e-con-inner>.e-con,:scope>.elementor-element,:scope>.e-con-inner>.elementor-element");if(filhos.length!==1)break;c=p;}
var s=document.createElement("section");s.className="abw-sec";s.innerHTML=FAIXA;c.dataset.abw="1";c.replaceWith(s);});
// páginas sem o bloco antigo (painéis, ferramentas, clima, artigos): a faixa entra logo antes do rodapé
if(!document.querySelector(".abw-sec")&&location.pathname!=="/"&&!/\/wp-admin|preview=|elementor-preview/.test(location.href)){var ft=document.querySelector("[data-elementor-type=footer],footer");if(ft&&ft.parentNode){var s2=document.createElement("section");s2.className="abw-sec";s2.innerHTML=FAIXA;ft.parentNode.insertBefore(s2,ft);}}}
if(document.readyState!=="loading")troca();else document.addEventListener("DOMContentLoaded",troca);})();</script>""" % json.dumps(faixa, ensure_ascii=False).replace("</", "<\\/")
html = ('<style id="ab-menu-resp">\n' + css +
        ".elementor-24 .elementor-element-ab0menu{position:absolute!important;width:0!important;height:0!important;overflow:hidden!important;margin:0!important;padding:0!important}\n</style>\n" + js)
Path("widget-cabecalho.html").write_text(html)
print(len(html))
