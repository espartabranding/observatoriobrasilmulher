"""Dados tirados das notícias coletadas: programas e recursos públicos, decisões da Justiça e iniciativas
com resultado na proteção de mulheres e crianças. Também acompanha a tramitação dos projetos de lei na Câmara.

O Claude (Haiku) lê só título e chamada de cada notícia candidata e devolve campos estruturados; o que não
estiver no material fica vazio. Cada notícia é lida uma vez (ids guardados em data/inteligencia.json).

Saídas:
  data/inteligencia.json    programas, decisões, iniciativas (com fonte e link de cada item)
  data/tramitacoes.json     últimos andamentos dos projetos de lei com camara_id em data/leis.json

Uso: uv run coletor/extrair.py
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

from coletar import DATA, baixar

ARQ = DATA / "inteligencia.json"
MODELO = os.environ.get("IAB_MODELO", "claude-haiku-5-5")
DIAS = 45        # só notícias recentes viram candidatas
POR_CHAMADA = 40
MAX_RODADA = 200  # teto de notícias analisadas por rodada (a primeira leitura pega o atraso aos poucos)

CANDIDATA = re.compile(
    r"lan[cç]a|programa|inaugur|investe|investimento|recursos|r\$|milh[õo]es|edital|amplia|cria|implanta|instala|"
    r"decide|decis[ãa]o|julga|julgamento|condena|absolv|\bSTF\b|\bSTJ\b|tribunal|\bTJ|tese|entendimento|garante|reconhece|"
    r"iniciativa|projeto|campanha|parceria|reduz|aumenta|resultado|atendid|atende|capacita|forma[çc][ãa]o", re.I)

INSTRUCOES = """Você classifica notícias sobre a proteção de mulheres e crianças no Brasil para um banco de dados público.
Para cada item numerado (título e chamada), responda com UM tipo e os campos dele, usando SOMENTE o que está escrito.
Não invente valores, nomes, órgãos ou resultados; deixe "" ou [] quando o material não disser.
Nunca registre nome de vítima, de criança ou de adolescente.
Tipos:
- "programa": governo, prefeitura, órgão público ou Legislativo lançou, ampliou ou financiou um programa, serviço,
  equipamento (ex. Casa da Mulher Brasileira, delegacia, abrigo) ou política de proteção. Campos: orgao, nome
  (nome do programa ou equipamento), valor (texto como está, ex. "R$ 5 milhões", ou ""), valor_mi (número em milhões de reais
  ou null), publico ("mulheres"|"crianças e adolescentes"|"ambos"), descricao (até 140 caracteres: o que faz), cidade (ou "").
- "decisao": decisão de tribunal, juiz ou do Ministério Público que firma um entendimento ou tem efeito além do caso
  (não registre simples condenações de um réu sem tese nova). Campos: tribunal, tema (até 80 caracteres),
  decisao (até 160 caracteres: o que foi decidido), efeito (até 140 caracteres: o que muda na prática, ou "").
- "iniciativa": órgão, empresa, escola ou organização da sociedade civil com uma ação concreta de proteção, com público
  atendido ou resultado divulgado. Campos: responsavel, setor ("segurança"|"saúde"|"educação"|"assistência"|"trabalho"|
  "Justiça"|"tecnologia"|"sociedade civil"), descricao (até 140 caracteres), resultado (até 140 caracteres, com números se houver, ou "").
- "nenhum": nada disso (crime isolado, opinião, evento, notícia internacional sem relação com o Brasil).
Escreva em português do Brasil. Responda só com JSON: {"itens": [{"i": 0, "tipo": "...", ...}, ...]}"""


def classificar(lote: list[dict]) -> list[dict]:
    from anthropic import Anthropic
    material = "\n\n".join(f"{i}. TÍTULO: {n['titulo']}\nCHAMADA: {n.get('resumo', '')[:300]}\nVEÍCULO: {n['fonte']}"
                           for i, n in enumerate(lote))
    r = Anthropic().messages.create(model=MODELO, max_tokens=16000, system=INSTRUCOES,
                                    messages=[{"role": "user", "content": material}])
    m = re.search(r"\{.*\}", "".join(b.text for b in r.content if b.type == "text"), re.S)
    return json.loads(m.group(0)).get("itens", []) if m else []


def tramitacoes() -> None:
    """Andamentos recentes na Câmara (API de Dados Abertos) dos projetos marcados em data/leis.json."""
    reg = DATA / "leis.json"
    if not reg.exists():
        return
    saida = {}
    for n in json.loads(reg.read_text(encoding="utf-8")).get("normas", []):
        if not n.get("camara_id"):
            continue
        corpo = baixar(f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{n['camara_id']}/tramitacoes")
        try:
            dados = json.loads(corpo or b"{}").get("dados", [])
        except ValueError:
            continue
        dados.sort(key=lambda t: t.get("dataHora") or "", reverse=True)
        saida[n["id"]] = [{"data": (t.get("dataHora") or "")[:10], "orgao": t.get("siglaOrgao", ""),
                           "situacao": t.get("descricaoSituacao") or "", "despacho": (t.get("despacho") or t.get("descricaoTramitacao") or "")[:300]}
                          for t in dados[:12]]
    if saida:
        (DATA / "tramitacoes.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
        print("tramitações:", {k: len(v) for k, v in saida.items()})


def main() -> None:
    tramitacoes()
    import legislativo  # projetos em andamento na Câmara (não precisa de chave)
    try:
        legislativo.main()
    except Exception as e:  # API fora do ar não derruba a rodada
        print("legislativo falhou:", e)
    import parlamentares  # quem propõe leis do tema (autoria na Câmara)
    try:
        parlamentares.main()
    except Exception as e:
        print("parlamentares falhou:", e)
    base = json.loads(ARQ.read_text(encoding="utf-8")) if ARQ.exists() else {}
    base = {"processados": base.get("processados", []), "programas": base.get("programas", []),
            "decisoes": base.get("decisoes", []), "iniciativas": base.get("iniciativas", [])}
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("sem ANTHROPIC_API_KEY: extração pulada")
        return
    feitos = set(base["processados"])
    noticias = json.loads((DATA / "noticias_completo.json").read_text(encoding="utf-8"))["noticias"]
    corte = (datetime.now(timezone.utc) - timedelta(days=DIAS)).isoformat()
    cand = [n for n in noticias if n["id"] not in feitos and n["data"] >= corte
            and n.get("brasil") and CANDIDATA.search(n["titulo"] + " " + n.get("resumo", ""))]
    cand = cand[:MAX_RODADA]
    chaves = {"programa": "programas", "decisao": "decisoes", "iniciativa": "iniciativas"}
    novos = {k: 0 for k in chaves.values()}
    for i in range(0, len(cand), POR_CHAMADA):
        lote = cand[i:i + POR_CHAMADA]
        try:
            res = classificar(lote)
        except Exception as e:
            print("extração falhou:", e)
            break
        for r in res:
            if not isinstance(r.get("i"), int) or not 0 <= r["i"] < len(lote) or r.get("tipo") not in chaves:
                continue
            n = lote[r["i"]]
            item = {k: v for k, v in r.items() if k not in ("i", "tipo")}
            item.update(id=n["id"], titulo=n["titulo"], link=n["link"], fonte=n["fonte"], data=n["data"][:10],
                        ufs=n.get("ufs", []))
            base[chaves[r["tipo"]]].append(item)
            novos[chaves[r["tipo"]]] += 1
        base["processados"] += [n["id"] for n in lote]
    for k in chaves.values():  # mais recentes primeiro, sem repetir a mesma notícia
        vistos, lista = set(), []
        for it in sorted(base[k], key=lambda x: x["data"], reverse=True):
            if it["id"] not in vistos:
                vistos.add(it["id"])
                lista.append(it)
        base[k] = lista
    base["processados"] = base["processados"][-6000:]
    base["gerado_em"] = datetime.now(timezone.utc).isoformat()
    ARQ.write_text(json.dumps(base, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(cand)} candidatas · novos: {novos}")


if __name__ == "__main__":
    main()
