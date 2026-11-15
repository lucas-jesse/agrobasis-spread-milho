"""Sondagem das fontes argentinas a partir do GitHub Actions: status, tamanho e conteúdo bruto em argentina/sonda/."""
import json, re, time
from pathlib import Path
from urllib.parse import quote
import requests

OUT = Path(__file__).with_name("sonda"); OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (compatible; AgroBasisBot/1.0; +https://agrobasis.com.br)"}
M = "https://www.magyp.gob.ar/sitio/areas/estimaciones"
ALVO = {
    "sagyp_lista": f"{M}/estimaciones/informes/",
    "sagyp_pdf": M + "/_archivos/estimaciones/260000_2026/261100_Noviembre/" + quote("261112_Informe Semanal al 12_11_2026.pdf"),
    "sagyp_series": f"{M}/series/",
    "sagyp_csv": "https://datos.magyp.gob.ar/dataset/9e1e77ba-267e-4eaa-a59f-3296e86b5f36/resource/95d066e6-8a0f-4a80-b59d-6f28f88eacd5/download/estimaciones-agricolas-2026-03.csv",
    "sagyp_robots": "https://www.magyp.gob.ar/robots.txt",
    "bcr_estim": "https://www.bcr.com.ar/es/mercados/gea/estimaciones-nacionales-de-produccion/estimaciones",
    "bcr_semanal": "https://www.bcr.com.ar/es/mercados/gea/seguimiento-de-cultivos/informe-semanal-zona-nucleo",
    "bcr_lluvias": "https://www.bcr.com.ar/es/mercados/gea/clima/clima-gea/lluvias",
    "bcr_robots": "https://www.bcr.com.ar/robots.txt",
    "bcba_pas": "https://www.bolsadecereales.com/estimaciones-informes",
    "bcba_robots": "https://www.bolsadecereales.com/robots.txt",
    "tableau_estado": "https://public.tableau.com/views/EstadoyHumedaddelosCultivos/Dashboard1?:showVizHome=no",
}
res = {}
for k, u in ALVO.items():
    try:
        r = requests.get(u, headers=UA, timeout=60)
        ext = "pdf" if "pdf" in r.headers.get("content-type", "") else ("csv" if k.endswith("csv") else "html")
        (OUT / f"{k}.{ext}").write_bytes(r.content)
        res[k] = {"status": r.status_code, "tipo": r.headers.get("content-type"), "bytes": len(r.content),
                  "cloudflare": "cf-ray" in r.headers or "Just a moment" in r.text[:3000]}
        if ext == "pdf" and r.ok:
            import pdfplumber
            with pdfplumber.open(OUT / f"{k}.pdf") as pdf:
                res[k]["paginas"] = len(pdf.pages)
                txt, tabs = [], []
                for i, pg in enumerate(pdf.pages):
                    txt.append(f"=== PAGINA {i+1}\n" + (pg.extract_text() or ""))
                    for t in pg.extract_tables():
                        tabs.append({"pagina": i + 1, "linhas": t})
                (OUT / f"{k}.txt").write_text("\n".join(txt))
                (OUT / f"{k}_tabelas.json").write_text(json.dumps(tabs, ensure_ascii=False, indent=1))
                res[k]["tabelas"] = len(tabs)
    except Exception as e:
        res[k] = {"erro": repr(e)[:300]}
    time.sleep(2)
(OUT / "resumo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False, indent=1))
