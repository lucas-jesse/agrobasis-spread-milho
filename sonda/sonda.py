import requests, json, os, re
UA={"User-Agent":"Mozilla/5.0 (AgroBasis; agrobasis.com.br)"}
def t(nome, url, **kw):
    try:
        r=requests.get(url,headers=UA,timeout=60,**kw); print("##",nome,r.status_code,len(r.content)); return r
    except Exception as e: print("##",nome,"ERRO",e)
# 1 multimodelos
mods="ecmwf_ifs025,ecmwf_aifs025_single,gfs_seamless,gfs_graphcast025,icon_seamless,gem_seamless,ukmo_seamless,jma_seamless,meteofrance_seamless,cma_grapes_global,bom_access_global,kma_seamless"
r=t("openmeteo","https://api.open-meteo.com/v1/forecast",params={"latitude":-12.09,"longitude":-45.8,"daily":"precipitation_sum","forecast_days":16,"models":mods,"timezone":"America/Sao_Paulo"})
if r is not None and r.ok:
    d=r.json()["daily"]
    for k,v in d.items():
        if k!="time": print(k, sum(1 for x in v if x is not None), round(sum(x for x in v if x is not None),1))
# 2 USDM
r=t("usdm_state","https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent",params={"aoi":"IA","startdate":"10/1/2026","enddate":"11/26/2026","statisticsType":"1"},)
if r is not None: print(r.headers.get("content-type"), r.text[:600])
r=t("usdm_json","https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent",params={"aoi":"IA","startdate":"10/1/2026","enddate":"11/26/2026","statisticsType":"1"},)
r=requests.get("https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent",params={"aoi":"19","startdate":"10/1/2026","enddate":"11/26/2026","statisticsType":"1"},headers=dict(UA,Accept="application/json"),timeout=60)
print("fips json", r.status_code, r.text[:600])
r=requests.get("https://usdmdataservices.unl.edu/api/USStatistics/GetDroughtSeverityStatisticsByAreaPercent",params={"aoi":"conus","startdate":"10/1/2026","enddate":"11/26/2026","statisticsType":"1"},headers=dict(UA,Accept="application/json"),timeout=60)
print("conus", r.status_code, r.text[:400])
# geojson atual
r=t("usdm_geojson","https://droughtmonitor.unl.edu/data/json/usdm_current.json")
if r is not None and r.ok: print(r.text[:300])
# 3 ANA
r=t("ana_home","https://monitordesecas.ana.gov.br/")
if r is not None: print(r.text[:1500]); print(sorted(set(re.findall(r'(?:src|href)="([^"]+)"',r.text)))[:60])
for u in ["https://monitordesecas.ana.gov.br/mapa","https://monitordesecas.ana.gov.br/api/mapa","https://monitordesecas.ana.gov.br/geoserver/wms?service=WMS&request=GetCapabilities","https://monitordesecas.ana.gov.br/geoserver/ows?service=WFS&request=GetCapabilities"]:
    r=t(u,u)
    if r is not None: print(r.text[:800])
# 4 NASS pesos
k=os.environ.get("NASS_API_KEY","")
for c in ("CORN","SOYBEANS"):
    r=requests.get("https://quickstats.nass.usda.gov/api/api_GET/",params={"key":k,"commodity_desc":c,"statisticcat_desc":"PRODUCTION","unit_desc":"BU","agg_level_desc":"STATE","year":"2025","reference_period_desc":"YEAR","source_desc":"SURVEY","format":"JSON"},timeout=120)
    try:
        dd=r.json()["data"]; print(c, len(dd), sorted([(x["state_alpha"],x["Value"],x.get("util_practice_desc"),x.get("class_desc")) for x in dd])[:60])
    except Exception as e: print(c,"erro",r.status_code,r.text[:300])
