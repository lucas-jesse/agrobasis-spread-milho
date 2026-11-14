"""Vigia dos dados do AgroBasis.

Roda todo dia no GitHub Actions e confere duas coisas:
1. se cada arquivo de dados foi atualizado dentro do prazo esperado (pela data do último commit do arquivo);
2. se alguma rotina agendada falhou nas últimas 26 horas.
Se houver problema, abre (ou atualiza) uma issue "Vigia: dados com problema", o que gera aviso por e-mail
e no app do GitHub. Quando tudo volta ao normal, comenta e fecha a issue.

Prazos em "horas úteis": sábados e domingos não contam, para que o fim de semana não gere alarme falso.
"""
import os
import subprocess
from datetime import datetime, timedelta, timezone

import requests

REPO = os.environ.get("GITHUB_REPOSITORY", "lucas-jesse/agrobasis-spread-milho")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DONO = "lucas-jesse"
TITULO = "Vigia: dados com problema"
BRT = timezone(timedelta(hours=-3))

# caminho: (descrição, prazo em horas, conta só dias úteis?)
ARQUIVOS = {
    "dados/fechamento.json": ("Fechamento de mercado (página inicial e story)", 50, True),
    "dados/cotacoes_agora.json": ("Cotações durante o pregão (página inicial)", 50, True),
    "dados/manha.json": ("Coleta da manhã (áudio e painel)", 50, True),
    "dados/cambio.json": ("Câmbio e curva do dólar", 50, True),
    "dados/painel.json": ("Painel de cartões dos dashboards", 30, False),
    "dados/basis": ("Basis de soja e milho (preços semanais da Conab)", 9 * 24, False),
    "dados/curva_ccm.json": ("Curva do milho B3", 50, True),
    "dados/curva_soja.json": ("Curva da soja", 50, True),
    "dados/clima": ("Clima e El Niño (chuva e previsão)", 30, False),
    "dados/troca": ("Relação de troca", 50, True),
    "dados/cot": ("Posição dos fundos (CFTC)", 9 * 24, False),
    "dados/export_sales": ("Vendas semanais de exportação dos EUA", 9 * 24, False),
    "dados/usda": ("Relatório WASDE do USDA", 40 * 24, False),
    "dados/conab": ("Levantamento de safra da Conab", 40 * 24, False),
}


def horas(ini, fim, uteis):
    if not uteis:
        return (fim - ini).total_seconds() / 3600
    t, h = ini, 0.0
    while t < fim:
        prox = min(fim, (t + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0))
        if t.weekday() < 5:
            h += (prox - t).total_seconds() / 3600
        t = prox
    return h


def ultimo_commit(caminho):
    s = subprocess.run(["git", "log", "-1", "--format=%ct", "--", caminho], capture_output=True, text=True).stdout.strip()
    return datetime.fromtimestamp(int(s), BRT) if s else None


def api(metodo, url, **kw):
    r = requests.request(metodo, "https://api.github.com/repos/" + REPO + url, timeout=30,
                         headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json"}, **kw)
    r.raise_for_status()
    return r.json() if r.text else {}


def main():
    agora = datetime.now(BRT)
    problemas = []
    for caminho, (desc, prazo, uteis) in ARQUIVOS.items():
        t = ultimo_commit(caminho)
        if t is None:
            problemas.append(f"- **{desc}** (`{caminho}`): arquivo não encontrado")
            continue
        idade = horas(t, agora, uteis)
        if idade > prazo:
            problemas.append(f"- **{desc}** (`{caminho}`): última atualização em {t:%d/%m %H:%M}, há {idade / 24:.1f} dias{' úteis' if uteis else ''}")
    # rotinas agendadas que falharam nas últimas 26 horas (só a execução mais recente de cada uma)
    desde = (datetime.now(timezone.utc) - timedelta(hours=26)).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = api("GET", f"/actions/runs?event=schedule&per_page=100&created=>{desde}").get("workflow_runs", [])
    vistos = set()
    for r in runs:  # mais recentes primeiro
        if r["name"] in vistos or r["status"] != "completed":
            continue
        vistos.add(r["name"])
        if r["conclusion"] == "failure":
            problemas.append(f"- Rotina **{r['name']}** falhou na última execução ({r['html_url']})")
    abertas = [i for i in api("GET", "/issues?state=open&per_page=50") if i["title"] == TITULO and "pull_request" not in i]
    if problemas:
        corpo = (f"@{DONO}, o vigia encontrou problemas em {agora:%d/%m/%Y às %H:%M}:\n\n" + "\n".join(problemas) +
                 "\n\nAs páginas continuam no ar e mostram os últimos dados disponíveis, com a data. "
                 "Esta issue fecha sozinha quando tudo voltar ao normal.")
        if abertas:
            api("POST", f"/issues/{abertas[0]['number']}/comments", json={"body": corpo})
        else:
            api("POST", "/issues", json={"title": TITULO, "body": corpo})
        print("\n".join(problemas))
    else:
        for i in abertas:
            api("POST", f"/issues/{i['number']}/comments", json={"body": f"Tudo normalizado em {agora:%d/%m %H:%M}."})
            api("PATCH", f"/issues/{i['number']}", json={"state": "closed"})
        print("tudo em dia")


if __name__ == "__main__":
    main()
