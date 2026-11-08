"""Exporta o PSD Online do USDA (oferta e demanda mundial) para os dashboards HTML.

Baixa os CSV oficiais do USDA/FAS (atualizados a cada WASDE) e grava um JSON
enxuto por página em dados/usda/:
  - soja.json  : Oilseed, Soybean + Meal, Soybean + Oil, Soybean
  - milho.json : Corn
  - trigo.json : Wheat

Formato (mil toneladas, mil hectares, t/ha):
{
  "atualizado_em": "...", "fonte": "USDA/FAS PSD Online", "anos": [2000, ...],
  "produtos": {"grao": {"nome": "Soja em grão", "atributos": [...],
       "paises": {"WD": {"nome": "Mundo", "dados": {"producao": [...], ...}}, "BR": {...}}}}
}
Mundo = soma de todos os países do PSD (mesmo critério do USDA para totais mundiais).
Ficam no arquivo os 30 países mais relevantes por produto (produção, comércio e estoque).
"""
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

BASE = "https://apps.fas.usda.gov/psdonline/downloads/"
ARQUIVOS = {"oleaginosas": "psd_oilseeds_csv.zip", "graos": "psd_grains_pulses_csv.zip"}
ANO_INICIAL = 2000
TOP_PAISES = 30

# atributo PSD -> chave curta
ATRIB = {
    "Area Harvested": "area",
    "Yield": "produtividade",
    "Beginning Stocks": "estoque_inicial",
    "Production": "producao",
    "Imports": "importacao",
    "MY Imports": "importacao",
    "Exports": "exportacao",
    "MY Exports": "exportacao",
    "Crush": "esmagamento",
    "Feed Dom. Consumption": "consumo_racao",
    "Feed Waste Dom. Cons.": "consumo_racao",
    "Domestic Consumption": "consumo",
    "Total Dom. Cons.": "consumo",
    "Dom. Consumption": "consumo",
    "Ending Stocks": "estoque_final",
}
PAGINAS = {
    "soja": [("grao", "Oilseed, Soybean", "Soja em grão"), ("farelo", "Meal, Soybean", "Farelo de soja"),
             ("oleo", "Oil, Soybean", "Óleo de soja")],
    "milho": [("grao", "Corn", "Milho")],
    "trigo": [("grao", "Wheat", "Trigo")],
}
NOMES = {
    "United States": "Estados Unidos", "Brazil": "Brasil", "Argentina": "Argentina", "China": "China",
    "European Union": "União Europeia", "India": "Índia", "Paraguay": "Paraguai", "Canada": "Canadá",
    "Russia": "Rússia", "Ukraine": "Ucrânia", "Australia": "Austrália", "Mexico": "México", "Japan": "Japão",
    "Egypt": "Egito", "Indonesia": "Indonésia", "Turkey": "Turquia", "Iran": "Irã", "Pakistan": "Paquistão",
    "Bolivia": "Bolívia", "Uruguay": "Uruguai", "South Africa": "África do Sul", "Kazakhstan": "Cazaquistão",
    "Korea, South": "Coreia do Sul", "Vietnam": "Vietnã", "Thailand": "Tailândia", "Malaysia": "Malásia",
    "Bangladesh": "Bangladesh", "Philippines": "Filipinas", "Algeria": "Argélia", "Morocco": "Marrocos",
    "Saudi Arabia": "Arábia Saudita", "Nigeria": "Nigéria", "Ethiopia": "Etiópia", "Colombia": "Colômbia",
    "Peru": "Peru", "Chile": "Chile", "Venezuela": "Venezuela", "United Kingdom": "Reino Unido",
    "Taiwan": "Taiwan", "Serbia": "Sérvia", "Norway": "Noruega", "Switzerland": "Suíça", "Israel": "Israel",
    "Iraq": "Iraque", "Syria": "Síria", "Afghanistan": "Afeganistão", "Uzbekistan": "Uzbequistão",
    "Tanzania": "Tanzânia", "Kenya": "Quênia", "Zambia": "Zâmbia", "Nepal": "Nepal", "Burma": "Mianmar",
    "Sri Lanka": "Sri Lanka", "Ecuador": "Equador", "Guatemala": "Guatemala", "Cuba": "Cuba",
    "Dominican Republic": "República Dominicana", "Costa Rica": "Costa Rica", "Yemen": "Iêmen",
    "Tunisia": "Tunísia", "Libya": "Líbia", "Sudan": "Sudão", "Belarus": "Belarus", "Moldova": "Moldávia",
    "Mozambique": "Moçambique", "Zimbabwe": "Zimbábue", "Malawi": "Malawi", "Uganda": "Uganda",
    "Ghana": "Gana", "Cameroon": "Camarões", "Angola": "Angola", "Senegal": "Senegal", "Jordan": "Jordânia",
    "Lebanon": "Líbano", "United Arab Emirates": "Emirados Árabes", "Oman": "Omã", "Kuwait": "Kuwait",
    "New Zealand": "Nova Zelândia", "Hong Kong": "Hong Kong", "Singapore": "Cingapura",
}


def baixar(nome):
    r = requests.get(BASE + nome, timeout=120, headers={"User-Agent": "Mozilla/5.0 AgroBasis"})
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    return pd.read_csv(z.open(z.namelist()[0]), low_memory=False)


def montar_produto(df, commodity):
    d = df[(df["Commodity_Description"] == commodity) & (df["Market_Year"] >= ANO_INICIAL)].copy()
    atributos_psd = sorted(d["Attribute_Description"].unique())
    d["chave"] = d["Attribute_Description"].map(ATRIB)
    d = d.dropna(subset=["chave"])
    # um atributo PSD por chave (o primeiro da lista ATRIB que existir)
    escolhido = {}
    for nome_psd, chave in ATRIB.items():
        if chave not in escolhido and nome_psd in atributos_psd:
            escolhido[chave] = nome_psd
    d = d[d.apply(lambda r: escolhido.get(r["chave"]) == r["Attribute_Description"], axis=1)]
    unidades = d.groupby("chave")["Unit_Description"].first().to_dict()
    anos = list(range(ANO_INICIAL, int(d["Market_Year"].max()) + 1))
    tab = d.pivot_table(index=["Country_Name", "chave"], columns="Market_Year", values="Value", aggfunc="sum")
    tab = tab.reindex(columns=anos)
    paises = sorted(d["Country_Name"].unique())
    # relevância: média dos últimos 5 anos de produção, exportação, importação e estoque
    rel = {}
    ult = anos[-5:]
    for p in paises:
        s = 0.0
        for ch in ("producao", "exportacao", "importacao", "estoque_final", "consumo"):
            if (p, ch) in tab.index:
                s += float(tab.loc[(p, ch), ult].fillna(0).mean())
        rel[p] = s
    top = sorted(paises, key=lambda p: -rel[p])[:TOP_PAISES]
    saida = {}
    # Mundo: soma de todos os países (área, produção, comércio, consumo, estoques)
    mundo = {}
    for ch in escolhido:
        if ch == "produtividade":
            continue
        linhas = tab.xs(ch, level="chave") if ch in tab.index.get_level_values("chave") else None
        if linhas is not None:
            mundo[ch] = [round(float(v), 1) if pd.notna(v) else None for v in linhas.sum(min_count=1).values]
    if "area" in mundo and "producao" in mundo:
        mundo["produtividade"] = [round(p / a, 2) if a and p is not None else None for p, a in zip(mundo["producao"], mundo["area"])]
    saida["WD"] = {"nome": "Mundo", "dados": mundo}
    codigos = d.groupby("Country_Name")["Country_Code"].first().to_dict()
    for p in top:
        dados = {}
        for ch in escolhido:
            if (p, ch) in tab.index:
                dados[ch] = [round(float(v), 2 if ch == "produtividade" else 1) if pd.notna(v) else None for v in tab.loc[(p, ch)].values]
        saida[codigos[p]] = {"nome": NOMES.get(p, p), "dados": dados}
    return anos, saida, unidades, atributos_psd


def main():
    dfs = {k: baixar(v) for k, v in ARQUIVOS.items()}
    destino = Path("dados/usda")
    destino.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    for pagina, produtos in PAGINAS.items():
        out = {"atualizado_em": agora, "fonte": "USDA/FAS PSD Online", "produtos": {}}
        for chave, commodity, nome in produtos:
            df = dfs["oleaginosas"] if commodity in set(dfs["oleaginosas"]["Commodity_Description"]) else dfs["graos"]
            anos, paises, unidades, atrib = montar_produto(df, commodity)
            ref = df[df["Commodity_Description"] == commodity]
            ult = ref[ref["Market_Year"] == ref["Market_Year"].max()]
            out["anos"] = anos
            out["produtos"][chave] = {"nome": nome, "unidades": unidades, "atributos_psd": atrib,
                                      "mes_relatorio": int(ult["Month"].max()) if "Month" in ult else None,
                                      "paises": paises}
        arq = destino / f"{pagina}.json"
        arq.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(pagina, f"{arq.stat().st_size/1024:.0f} KB", {k: list(v["paises"]["WD"]["dados"].keys()) for k, v in out["produtos"].items()})


if __name__ == "__main__":
    main()
