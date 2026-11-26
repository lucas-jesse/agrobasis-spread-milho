import requests, re
UA={"User-Agent":"Mozilla/5.0 (AgroBasis; agrobasis.com.br)"}
t=requests.get("https://monitordesecas.ana.gov.br/main-es2015.ce70a5b5f644ae7bc49e.js",headers=UA,timeout=60).text
for m in sorted(set(re.findall(r'["\'`]([^"\'`]{0,40}(?:data/|\.json|\.geojson|\.zip|\.shp|\.kml)[^"\'`]{0,100})["\'`]',t)))[:150]: print("S:",m)
for m in re.finditer(r'.{150}ana-monitor-secas-files[^"\']*["\'].{250}',t): print("CTX:",m.group(0)[:420])
