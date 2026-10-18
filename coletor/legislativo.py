"""Projetos de lei em andamento na Câmara dos Deputados sobre mulheres e crianças (API de Dados Abertos).

Busca por palavras-chave as proposições (PL, PLP, PEC) que tiveram tramitação nos últimos 120 dias, lê a
situação atual de cada uma e grava a lista com link para a ficha, o texto e a enquete pública da Câmara,
onde qualquer pessoa pode votar. Roda a cada rodada, chamado por extrair.py (não precisa de chave).

Saída: data/legislativo.json

Uso: uv run coletor/legislativo.py
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

from coletar import DATA, baixar

API = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
TERMOS = ["violência contra a mulher", "Lei Maria da Penha", "feminicídio", "violência doméstica", "medida protetiva",
          "estupro", "abuso sexual", "importunação sexual", "misoginia", "violência obstétrica", "igualdade salarial",
          "Estatuto da Criança e do Adolescente", "criança e adolescente", "exploração sexual", "trabalho infantil",
          "Casa da Mulher Brasileira", "violência política de gênero", "pensão alimentícia"]
DIAS = 120
CRIANCA = re.compile(r"crian[cç]a|adolescen|\bECA\b|8\.069|infantil|menor(es)? de", re.I)
FORA = re.compile(r"arquivad|transformad[oa] em norma|retirad[oa] pelo autor|devolvid|prejudicad", re.I)


def _json(url):
    corpo = baixar(url)
    try:
        return json.loads(corpo or b"{}").get("dados") or []
    except ValueError:
        return []


def candidatas() -> dict[int, dict]:
    inicio = (date.today() - timedelta(days=DIAS)).isoformat()
    achadas = {}
    for termo in TERMOS:
        for pagina in range(1, 4):
            url = (f"{API}?keywords={quote(termo)}&siglaTipo=PL,PLP,PEC&dataInicio={inicio}"
                   f"&ordem=DESC&ordenarPor=id&itens=100&pagina={pagina}")
            itens = _json(url)
            for p in itens:
                achadas[p["id"]] = p
            if len(itens) < 100:
                break
    return achadas


def detalhe(pid: int) -> dict | None:
    d = _json(f"{API}/{pid}")
    return d if isinstance(d, dict) else None


def etapa(st: dict) -> str:
    sit, org = st.get("descricaoSituacao") or "", st.get("siglaOrgao") or ""
    if re.search(r"pronta para pauta", sit, re.I):
        return "Pronto para votação no Plenário" if org == "PLEN" else "Pronto para votação na comissão"
    if re.search(r"aguardando (san[cç][aã]o|envio ao senado|remessa)|remetid", sit, re.I):
        return "Aprovado na Câmara"
    if re.search(r"parecer|relator|comiss[aã]o", sit, re.I) or org not in ("PLEN", "MESA", ""):
        return "Em análise nas comissões"
    return "Em tramitação"


def main() -> None:
    cand = candidatas()
    with ThreadPoolExecutor(max_workers=8) as ex:
        detalhes = list(ex.map(detalhe, cand))
    projetos = []
    for d in detalhes:
        if not d:
            continue
        st = d.get("statusProposicao") or {}
        if FORA.search(st.get("descricaoSituacao") or ""):
            continue
        pid = d["id"]
        projetos.append({
            "id": pid, "sigla": f'{d["siglaTipo"]} {d["numero"]}/{d["ano"]}', "ementa": d.get("ementa", ""),
            "apresentacao": (d.get("dataApresentacao") or "")[:10], "situacao": st.get("descricaoSituacao") or "",
            "orgao": st.get("siglaOrgao") or "", "data_situacao": (st.get("dataHora") or "")[:10],
            "andamento": (st.get("despacho") or st.get("descricaoTramitacao") or "")[:300], "regime": st.get("regime") or "",
            "etapa": etapa(st), "tema": "criancas" if CRIANCA.search(d.get("ementa", "")) else "mulheres",
            "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={pid}",
            "enquete": f"https://www.camara.leg.br/enquetes/{pid}", "teor": d.get("urlInteiroTeor") or ""})
    if not projetos and (DATA / "legislativo.json").exists():
        print("legislativo: API da Câmara sem resposta; mantida a lista anterior")
        return
    ordem = {"Pronto para votação no Plenário": 0, "Aprovado na Câmara": 1, "Pronto para votação na comissão": 2,
             "Em análise nas comissões": 3, "Em tramitação": 4}
    projetos.sort(key=lambda p: p["data_situacao"], reverse=True)  # mais recente primeiro dentro de cada etapa
    projetos.sort(key=lambda p: ordem.get(p["etapa"], 9))
    (DATA / "legislativo.json").write_text(json.dumps(
        {"gerado_em": datetime.now(timezone.utc).isoformat(), "fonte": "Câmara dos Deputados, API de Dados Abertos",
         "projetos": projetos}, ensure_ascii=False, indent=1), encoding="utf-8")
    cont = {}
    for p in projetos:
        cont[p["etapa"]] = cont.get(p["etapa"], 0) + 1
    print(f"legislativo: {len(cand)} candidatas, {len(projetos)} em andamento · {cont}")


if __name__ == "__main__":
    main()
