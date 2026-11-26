import requests, re
UA={"User-Agent":"Mozilla/5.0 (AgroBasis; agrobasis.com.br)"}
B="https://monitordesecas.ana.gov.br/"
for js in ["main-es2015.ce70a5b5f644ae7bc49e.js","scripts.0523905a50962b053e9a.js"]:
    t=requests.get(B+js,headers=UA,timeout=60).text
    print("##",js,len(t))
    urls=sorted(set(re.findall(r'https?://[^"\'\s\\)]+',t)))
    print("\n".join(u for u in urls if "w3.org" not in u and "angular" not in u)[:6000])
    for m in re.finditer(r'(api|geoserver|wfs|wms|shp|zip|kml|json)[^"\']{0,80}',t,re.I):
        pass
    rel=sorted(set(re.findall(r'["\'](/?(?:api|geoserver|monitor|mapa|arquivos|download)[^"\']{0,100})["\']',t)))
    print("REL:", rel[:200])
