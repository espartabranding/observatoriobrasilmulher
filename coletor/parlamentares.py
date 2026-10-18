"""Quem propõe leis para mulheres e crianças: autoria dos projetos de lei da legislatura atual na Câmara dos Deputados.

Critério objetivo e igual para todos os partidos: projetos (PL, PLP, PEC) apresentados desde fev/2023 cuja ementa
casa com os termos do tema (os mesmos de legislativo.py). Para cada projeto, guarda autores, situação e se virou lei;
para cada deputado autor, os dados oficiais (nome, partido, UF, foto). Tudo vem da API de Dados Abertos da Câmara.

O que já foi lido fica em data/autoria.json (projeto não muda de autor); a situação é relida aos poucos.
Chamado por extrair.py a cada rodada (não precisa de chave).

Saída: data/autoria.json

Uso: uv run coletor/parlamentares.py
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

from coletar import DATA, baixar
from legislativo import API, CRIANCA, TERMOS

ARQ = DATA / "autoria.json"
INICIO = "2023-02-01"          # começo da 57ª legislatura
DEP = "https://dadosabertos.camara.leg.br/api/v2/deputados"
POR_RODADA = 1500              # projetos novos lidos por rodada (a primeira carga vai aos poucos no GitHub)
RELER_DIAS = 7                 # situação de cada projeto relida a cada 7 dias
RELER_POR_RODADA = 300


def _json(url):
    corpo = baixar(url)
    try:
        return json.loads(corpo or b"{}").get("dados")
    except ValueError:
        return None


def projetos_do_tema() -> dict[int, dict]:
    achados = {}
    for termo in TERMOS:
        for pagina in range(1, 21):
            itens = _json(f"{API}?keywords={quote(termo)}&siglaTipo=PL,PLP,PEC&dataApresentacaoInicio={INICIO}"
                          f"&ordem=DESC&ordenarPor=id&itens=100&pagina={pagina}") or []
            for p in itens:
                achados[p["id"]] = p
            if len(itens) < 100:
                break
    return achados


def ler_projeto(pid: int) -> dict | None:
    d = _json(f"{API}/{pid}")
    if not isinstance(d, dict):
        return None
    autores = _json(f"{API}/{pid}/autores") or []
    st = d.get("statusProposicao") or {}
    deps = [a for a in autores if "/deputados/" in (a.get("uri") or "")]
    return {"sigla": f'{d["siglaTipo"]} {d["numero"]}/{d["ano"]}', "ementa": d.get("ementa", ""),
            "apresentacao": (d.get("dataApresentacao") or "")[:10], "situacao": st.get("descricaoSituacao") or "",
            "data_situacao": (st.get("dataHora") or "")[:10], "orgao": st.get("siglaOrgao") or "",
            "lei": "norma jur" in (st.get("descricaoSituacao") or "").lower(),
            "tema": "criancas" if CRIANCA.search(d.get("ementa", "")) else "mulheres",
            "autores": [int(a["uri"].rsplit("/", 1)[1]) for a in deps],
            "principal": [int(a["uri"].rsplit("/", 1)[1]) for a in deps if a.get("proponente") == 1 and a.get("ordemAssinatura") == 1],
            "lido_em": date.today().isoformat()}


def ler_deputado(did: int) -> dict | None:
    d = _json(f"{DEP}/{did}")
    if not isinstance(d, dict):
        return None
    u = d.get("ultimoStatus") or {}
    prof = _json(f"{DEP}/{did}/profissoes") or []
    return {"nome": u.get("nomeEleitoral") or d.get("nomeCivil", ""), "nome_civil": d.get("nomeCivil", ""),
            "partido": u.get("siglaPartido") or "", "uf": u.get("siglaUf") or "", "foto": u.get("urlFoto") or "",
            "situacao": u.get("situacao") or "", "sexo": d.get("sexo") or "", "nascimento": d.get("dataNascimento") or "",
            "naturalidade": " - ".join(x for x in (d.get("municipioNascimento"), d.get("ufNascimento")) if x),
            "escolaridade": d.get("escolaridade") or "", "email": (u.get("gabinete") or {}).get("email") or "",
            "profissoes": sorted({p["titulo"] for p in prof if p.get("titulo")}),
            "lido_em": date.today().isoformat()}


FOTOS = DATA / "parlamentares-fotos"
FOTOS_POR_RODADA = 150
LIMITE_FOTOS_S = 90      # tempo máximo baixando fotos por rodada


def baixar_fotos(deps: dict[int, dict]) -> int:
    """Fotos oficiais, uma a uma e devagar: o servidor da Câmara recusa (429) pedidos em sequência rápida."""
    import time
    import urllib.error
    import urllib.request
    FOTOS.mkdir(exist_ok=True)
    feitas, inicio = 0, time.time()
    for did, d in deps.items():
        arq = FOTOS / f"{did}.jpg"
        if arq.exists() or not d.get("foto"):
            continue
        if feitas >= FOTOS_POR_RODADA or time.time() - inicio > LIMITE_FOTOS_S:
            break  # o resto fica para as próximas rodadas
        time.sleep(0.8)
        try:
            req = urllib.request.Request(d["foto"], headers={"User-Agent": "Mozilla/5.0 (compatible; ObservatorioBrasilMulherBot/0.1)"})
            corpo = urllib.request.urlopen(req, timeout=15).read()
            if corpo[:3] == b"\xff\xd8\xff":  # JPEG de verdade
                arq.write_bytes(corpo)
                feitas += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:  # a Câmara pediu para esperar: para por aqui nesta rodada
                break
        except Exception:
            continue
    return feitas


def main() -> None:
    base = json.loads(ARQ.read_text(encoding="utf-8")) if ARQ.exists() else {}
    projs = {int(k): v for k, v in (base.get("projetos") or {}).items()}
    deps = {int(k): v for k, v in (base.get("deputados") or {}).items()}
    achados = projetos_do_tema()
    if not achados:
        print("parlamentares: API da Câmara sem resposta; mantida a lista anterior")
        return
    novos = [pid for pid in achados if pid not in projs][:POR_RODADA]
    velho = (date.today() - timedelta(days=RELER_DIAS)).isoformat()
    reler = sorted((pid for pid, p in projs.items() if p["lido_em"] < velho and not p.get("lei")),
                   key=lambda pid: projs[pid]["lido_em"])[:RELER_POR_RODADA]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for pid, p in zip(novos + reler, ex.map(ler_projeto, novos + reler)):
            if p:
                projs[pid] = p
    autores = {a for p in projs.values() for a in p["autores"]}
    velho_dep = (date.today() - timedelta(days=30)).isoformat()
    faltam = [a for a in autores if a not in deps or deps[a]["lido_em"] < velho_dep]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for did, d in zip(faltam, ex.map(ler_deputado, faltam)):
            if d:
                deps[did] = d
    ARQ.write_text(json.dumps({"gerado_em": datetime.now(timezone.utc).isoformat(), "desde": INICIO,
                               "fonte": "Câmara dos Deputados, API de Dados Abertos",
                               "projetos": {str(k): v for k, v in projs.items()},
                               "deputados": {str(k): v for k, v in deps.items()}}, ensure_ascii=False, indent=0), encoding="utf-8")
    com_proj = {a for p in projs.values() for a in p["principal"]}
    fotos = baixar_fotos({k: v for k, v in deps.items() if k in com_proj})
    print(f"parlamentares: {fotos} fotos novas baixadas")
    leis = sum(1 for p in projs.values() if p.get("lei"))
    print(f"parlamentares: {len(achados)} projetos do tema ({len(novos)} novos lidos, {len(reler)} relidos), "
          f"{len(projs)} no arquivo, {leis} viraram lei · {len(deps)} deputados autores")


if __name__ == "__main__":
    main()
