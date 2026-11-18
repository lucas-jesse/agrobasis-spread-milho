"""Basis de balcão: preço pago ao produtor em praças selecionadas, contra a CBOT (soja) e a B3 (milho).

Duas etapas, ambas idempotentes:
  1. coleta (opcional): se a variável de ambiente FONTE_BALCAO existir, busca as cotações de balcão dos
     últimos dias e acrescenta em dados/basis/balcao_hist.json. FONTE_BALCAO é um modelo de URL com
     {produto} e {data} (AAAA-MM-DD), guardado como segredo do repositório.
  2. exportação: cruza o histórico de balcão com as séries de referência que já alimentam os painéis
     de basis (dados/basis/soja.json: PTAX e CBOT do contrato de referência; dados/basis/milho.json:
     B3 do contrato de referência) e grava dados/basis/balcao_soja.json e balcao_milho.json no mesmo
     formato lido pelo template dos painéis de basis.

Basis da soja (cents de dólar por bushel) = balcão (R$/sc) ÷ PTAX × 27,2155/60 × 100 − CBOT de referência.
Basis do milho (R$/sc) = balcão (R$/sc) − B3 de referência.
"""
import json
import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PASTA = Path("dados/basis")
HIST = PASTA / "balcao_hist.json"
KG_BUSHEL_SOJA = 27.2155

# praça exibida -> (início do rótulo na tabela de origem, trecho obrigatório no rótulo ou None)
PRACAS = {
    "Não-Me-Toque RS": ("Não-Me-Toque/RS", None),
    "Palma Sola SC": ("Palma Sola/SC", None),
    "Pato Branco PR": ("Pato Branco/PR", None),
    "Marechal Cândido Rondon PR": ("Marechal Cândido Rondon/PR", None),
    "Londrina PR": ("Londrina/PR", None),
    "Castro PR": ("Castro/PR", None),
    "Cândido Mota SP": ("Cândido Mota/SP", None),
    "Maracaju MS": ("Maracaju/MS", None),
    "São Gabriel do Oeste MS": ("São Gabriel do Oeste/MS", None),
    "Sorriso MT": ("Sorriso/MT", "Balcão"),
    "Rondonópolis MT": ("Rondonópolis/MT", None),
    "Campo Novo do Parecis MT": ("Campo Novo do Parecis/MT", None),
    "Rio Verde GO": ("Rio Verde/GO", None),
    "Brasília DF": ("Brasília/DF", None),
    "Luís Eduardo Magalhães BA": ("Luís Eduardo Magalhães/BA", None),
    "Santa Rosa RS": ("\x00", None),  # vem da segunda fonte (FONTE_BALCAO_SR), não da tabela geral
}
PRODUTOS = {"soja": "soja", "milho": "milho"}


def praca_do_rotulo(rotulo):
    """Devolve a praça exibida para um rótulo da tabela, ou None se não for uma praça acompanhada."""
    for nome, (inicio, obrig) in PRACAS.items():
        if not rotulo.startswith(inicio):
            continue
        if obrig:
            if obrig in rotulo:
                return nome
        elif "Disponível" not in rotulo:
            return nome
    return None


def num_br(txt):
    txt = txt.strip().replace(".", "").replace(",", ".")
    try:
        v = float(txt)
    except ValueError:
        return None
    return v if 5 < v < 400 else None


def ler_tabela(html):
    """Primeira tabela de cotações da página: (data de fechamento, {rótulo: preço})."""
    bloco = re.search(r'class="cotacao".*?</table>', html, re.S)
    if not bloco:
        return None, {}
    b = bloco.group(0)
    m = re.search(r"Fechamento:\s*(\d{2})/(\d{2})/(\d{4})", b)
    fech = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
    linhas = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", b, re.S):
        tds = [re.sub(r"<[^>]+>", "", t) for t in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        tds = [re.sub(r"\s+", " ", t).strip() for t in tds]
        if len(tds) >= 2:
            v = num_br(tds[1])
            if v is not None:
                linhas[tds[0]] = v
    return fech, linhas


def coletar(hist):
    modelo = os.environ.get("FONTE_BALCAO", "").strip()
    if not modelo:
        print("coleta: segredo FONTE_BALCAO ausente, só exporta")
        return False
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    ultimo = max((d for prod in hist.values() for serie in prod.values() for d in serie), default="2019-11-01")
    ini = max(date.fromisoformat(ultimo) + timedelta(days=1), hoje - timedelta(days=21))
    novos = 0
    d = ini
    while d <= hoje:
        if d.weekday() < 5:
            for prod, slug in PRODUTOS.items():
                try:
                    r = s.get(modelo.format(produto=slug, data=d.isoformat()), timeout=40)
                    fech, linhas = ler_tabela(r.text) if r.ok else (None, {})
                except Exception as e:
                    print(f"coleta {prod} {d}: falhou ({type(e).__name__})")
                    continue
                if not fech or fech != d.isoformat():
                    continue  # feriado ou dia sem fechamento: a página devolve o último fechamento
                for rot, v in linhas.items():
                    p = praca_do_rotulo(rot)
                    if p and fech not in hist[prod].setdefault(p, {}):
                        hist[prod][p][fech] = v
                        novos += 1
                time.sleep(1)
        d += timedelta(days=1)
    print(f"coleta: {novos} preços novos")
    return novos > 0


def coletar_sr(hist):
    """Santa Rosa RS: histórico mensal publicado num formulário (ASP.NET) cuja URL fica no segredo FONTE_BALCAO_SR.
    Na primeira vez busca desde nov/2019; depois, só o mês corrente e o anterior. Vale a última cotação de cada dia."""
    url = os.environ.get("FONTE_BALCAO_SR", "").strip()
    if not url:
        print("coleta SR: segredo FONTE_BALCAO_SR ausente")
        return 0
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    ja = len(hist["soja"].get("Santa Rosa RS", {}))
    ini = date(2019, 11, 1) if ja < 300 else date(hoje.year, hoje.month, 1) - timedelta(days=1)
    meses, d = [], date(ini.year, ini.month, 1)
    while d <= hoje:
        meses.append((d.month, d.year))
        d = (d + timedelta(days=32)).replace(day=1)
    novos = 0
    for mes, ano in meses:
        try:
            h = s.get(url, timeout=40).text
            f = dict(re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', h))
            f.update({"ddlMes": str(mes), "ddlAno": str(ano), "btnSend": "Consultar"})
            h = s.post(url, data=f, timeout=40).text
        except Exception as e:
            print(f"coleta SR {mes}/{ano}: {e}")
            continue
        for bloco in re.findall(r'<div class="cotacoes">(.*?)</ul>', h, re.S):
            m = re.search(r"<h2>\s*([^<]+?)\s*</h2>", bloco)
            prod = {"milho": "milho", "soja": "soja"}.get(m.group(1).strip().lower()) if m else None
            if not prod:
                continue
            serie = hist[prod].setdefault("Santa Rosa RS", {})
            for dt, val in re.findall(r'class="indice">\s*(\d{2}/\d{2}/\d{4})\s*</div>\s*<div class="valor">\s*R\$\s*([\d.,]+)', bloco):
                v = num_br(val)
                if v is None:
                    continue
                k = datetime.strptime(dt, "%d/%m/%Y").strftime("%Y-%m-%d")
                if serie.get(k) != v:  # várias cotações no dia: fica a última (tarde)
                    serie[k] = v
                    novos += 1
        time.sleep(1.5)
    print(f"coleta SR: {len(meses)} meses, {novos} valores novos ou alterados")
    return novos


def ref_por_data(datas, *cols):
    return {d: tuple(c[i] for c in cols) for i, d in enumerate(datas)}


def ref_proxima(mapa, d, ate=4):
    """Referência do próprio dia ou, se não houver pregão, do último dia útil anterior (até 4 dias)."""
    t = date.fromisoformat(d)
    for k in range(ate + 1):
        x = (t - timedelta(days=k)).isoformat()
        if x in mapa:
            return mapa[x]
    return None


def exportar(hist):
    agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    soja = json.loads((PASTA / "soja.json").read_text(encoding="utf-8"))
    milho = json.loads((PASTA / "milho.json").read_text(encoding="utf-8"))
    refs = {
        "soja": ref_por_data(soja["datas"], soja["ptax"], soja["contrato_ref"], soja["cbot_ref_cents"]),
        "milho": ref_por_data(milho["datas"], milho["b3"], milho["contrato_ref"]),
    }
    for prod in ("soja", "milho"):
        series = {p: v for p, v in hist[prod].items() if p in PRACAS and v}
        datas = sorted({d for v in series.values() for d in v if ref_proxima(refs[prod], d)})
        out = {"atualizado_em": agora, "fonte": "Preços de balcão coletados pelo AgroBasis · " + ("CBOT · PTAX/BCB" if prod == "soja" else "B3"),
               "unidade_basis": "cents/bushel" if prod == "soja" else "R$/saca", "datas": datas, "contrato_ref": [], "pracas": {}}
        if prod == "soja":
            out["ptax"], out["cbot_ref_cents"] = [], []
        else:
            out["b3"] = []
        for d in datas:
            rf = ref_proxima(refs[prod], d)
            if prod == "soja":
                out["ptax"].append(rf[0]); out["contrato_ref"].append(rf[1]); out["cbot_ref_cents"].append(rf[2])
            else:
                out["b3"].append(rf[0]); out["contrato_ref"].append(rf[1])
        for p in sorted(series, key=lambda x: x.split()[-1] + x):
            fis, bas = [], []
            for i, d in enumerate(datas):
                f = series[p].get(d)
                if f is None:
                    fis.append(None); bas.append(None); continue
                if prod == "soja":
                    b = f / out["ptax"][i] * (KG_BUSHEL_SOJA / 60) * 100 - out["cbot_ref_cents"][i]
                    fis.append(round(f, 2)); bas.append(round(b, 1))
                else:
                    fis.append(round(f, 2)); bas.append(round(f - out["b3"][i], 2))
            out["pracas"][p] = {"fisico": fis, "basis": bas}
        arq = PASTA / f"balcao_{prod}.json"
        arq.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{arq}: {len(datas)} datas, {len(out['pracas'])} praças, de {datas[0]} a {datas[-1]}")


def main():
    hist = json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else {"soja": {}, "milho": {}}
    n = coletar(hist)
    n += coletar_sr(hist)
    if n:
        HIST.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    exportar(hist)


if __name__ == "__main__":
    main()
