"""Curadoria automática: escolhe no repositório as notícias que viram destaque na home.

Roda depois de coletar.py. Critério de escolha (sem IA): notícia sobre o Brasil, recente,
repercutida por mais veículos, de fonte oficial ou especializada, variando as editorias.

Com ANTHROPIC_API_KEY no ambiente, o Claude escreve título, resumo, análise em parágrafos,
pontos principais, "por que importa" e "o que observar" com palavras próprias, só a partir do material das fontes (título, chamada do feed e,
quando o robots.txt do site permite, o texto da matéria lido com trafilatura). Esse texto
não é publicado: serve só de base para o resumo. Sem a chave, o destaque usa o título
original com crédito e link para a fonte.

Saída: data/destaques.json (lido por main.py e injetado na página como IAB_AUTO).

Uso: uv run coletor/curar.py
     uv run coletor/curar.py --semear   # só na primeira carga: até 24 destaques das últimas duas semanas
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import coletar
from coletar import DATA, REGIAO, baixar, robots_permite, sobre_tema

POR_RODADA = 3        # destaques novos por rodada (a coleta roda de hora em hora, 7h às 22h)
REESCREVE = 6         # destaques antigos sem texto da IA reescritos por rodada (quando há chave)
POR_DIA = 12          # teto de destaques novos em 24 horas
JANELA_H = 48         # só notícias publicadas nas últimas 48 horas viram destaque
GUARDA_DIAS = 45      # destaques ficam na home/arquivo por 45 dias
if "--semear" in sys.argv:  # primeira carga do portal: capa cheia com as notícias das últimas duas semanas
    POR_RODADA, POR_DIA, JANELA_H = 24, 60, 24 * 14
MODELO = os.environ.get("IAB_MODELO", "claude-haiku-5-5")  # o mais barato; resumo por menos de US$ 0,01
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

# fotos de cada editoria (src/fotos.json, o mesmo arquivo que a capa usa para não repetir foto)
RAIZ = Path(__file__).resolve().parent.parent
FOTOS = json.loads((RAIZ / "src" / "fotos.json").read_text(encoding="utf-8"))
# foto pelo assunto da notícia (vale antes da foto genérica da editoria); todas brasileiras, sem pessoas
FOTO_ASSUNTO = [
    (r"casa da mulher brasileira|abrigo|acolhiment|centro de refer[eê]ncia", "cmb-fachada-df"),
    (r"delegacia|\bDEAM|boletim de ocorr|medidas? protetivas?|patrulha", "deam-viatura-df"),
    (r"maternidade|parto|gestante|obst[eé]tric|gr[aá]vida|pr[eé]-natal", "hmib-maternidade"),
    (r"sa[uú]de|\bSUS\b|hospital|m[eé]dic|paciente", "uti"),
    (r"elei[cç]|\bTSE\b|candidat|urna", "tse"),
    (r"\bSTF\b|\bSTJ\b|tribunal|justi[cç]a|judici|j[uú]ri|condena", "stf"),
    (r"internet|online|redes sociais|deepfake|nudes|[ií]ntim|aplicativo|digital", "dados-rede"),
    (r"c[aâ]mara|senado|congresso|\bPL\b|projeto de lei|deputad|senador", "congresso-noite"),
    (r"\bescola|educa[cç]|\balun[oa]s?\b|professor|creche|estudante", "f-escola-estadual"),
    (r"crian[cç]a|infantil|inf[aâ]ncia|conselho tutelar|\bECA\b", "parquinho-praca"),
    (r"trabalho|emprego|sal[aá]ri|renda|empresa", "f-paulista-edificio"),
    (r"prefeitura|cidade|transporte|[oô]nibus|metr[oô]|urban", "cidade"),
    (r"governo|minist[eé]rio|planalto|presidente|lula", "congresso"),
]
FOTO_REGIAO = {"Norte": "r-norte", "Nordeste": "r-nordeste", "Centro-Oeste": "r-co", "Sul": "r-sul"}
PESO_TIPO = {"Governo federal": 3, "Legislativo": 3, "Judiciário": 3, "Ministério Público": 3, "Defensoria Pública": 3,
             "Controle": 3, "Governo estadual": 2, "Estatística oficial": 2, "Agência pública de notícias": 2,
             "Academia e pesquisa": 2, "Pesquisa pública": 2, "Observatório": 2, "Organismo internacional": 2,
             "Terceiro setor": 2, "Imprensa especializada": 1, "Imprensa jurídica": 1}


# chamada de evento, patrocínio e autopromoção: perde prioridade (a IA também descarta)
PROMO = re.compile(r"summit|webinar|evento|inscri[cç]|palestra|aborda|participa|patrocin|parceria com|"
                   r"promove|convida|\?$|lan[cç]a (curso|e-?book)|confira|saiba como|dicas", re.I)


def pontos(n: dict, agora: datetime) -> float:
    horas = (agora - datetime.fromisoformat(n["data"])).total_seconds() / 3600
    return (-6 if PROMO.search(n["titulo"]) else 0) + (n.get("n_fontes", 1) - 1) * 4 + PESO_TIPO.get(n.get("tipo", ""), 0) + (2 if n.get("ufs") else 0) \
        + max(0, 24 - horas) / 8 + (1 if n.get("empresas") else 0)


def _dominio(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


# veículos com paywall: a matéria é produto pago, então a IA só vê título e chamada do feed
PAYWALL = {_dominio(f["url"]) for f in json.loads((DATA / "fontes.json").read_text(encoding="utf-8"))
           if f.get("acesso") == "Paywall"}
# se o robots.txt bloqueia algum destes, o site recusou uso por IA: não lemos o texto da matéria
ROBOS_IA = ["ClaudeBot", "anthropic-ai", "Claude-User", "GPTBot", "Google-Extended", "CCBot"]


def recusa_ia(url: str) -> bool:
    if not robots_permite(url):
        return True
    p = urlparse(url)
    rp = coletar._ROBOTS.get(f"{p.scheme}://{p.netloc}")
    return rp is not None and not all(rp.can_fetch(r, url) for r in ROBOS_IA)


def texto_da_materia(url: str) -> str:
    """Texto da matéria só como insumo do resumo (não é publicado). Respeita o robots.txt,
    a recusa a robôs de IA e o paywall."""
    try:
        import trafilatura
        d = _dominio(url)
        if any(d == x or d.endswith("." + x) for x in PAYWALL) or recusa_ia(url):
            return ""
        html = baixar(url)
        return (trafilatura.extract(html, include_comments=False, include_tables=False) or "")[:12000] if html else ""
    except Exception:
        return ""


INSTRUCOES = """Você é editor do Observatório Brasil Mulher, portal de notícias e dados sobre a defesa de mulheres e crianças no Brasil:
violência contra a mulher, leis, rede de amparo e proteção da infância.
Escreva em português do Brasil, com suas palavras, a partir SOMENTE do material abaixo. Regras:
- Não invente fatos, números, datas, nomes ou citações. Se o material não diz, não escreva.
- Não copie frases do material: no máximo 6 palavras seguidas iguais às da fonte.
- Tom sóbrio e respeitoso de jornalismo de serviço. Sem sensacionalismo, sem detalhes gráficos da violência,
  sem culpar a vítima ("crime passional", "por ciúmes", "ela provocou") e sem romantizar o agressor.
- Proteja as vítimas: não escreva nome, endereço, escola ou qualquer dado que identifique vítima de violência sexual,
  criança ou adolescente (ECA, art. 17 e 143), mesmo que o material traga. Pode citar autoridades, órgãos e agressores condenados.
- Seu texto deve se sustentar sozinho, mas é contexto e análise, não substituto da matéria: não siga a ordem
  nem a estrutura da reportagem, não reproduza citações longas e credite o veículo como autor da apuração.
- Se só um veículo trouxe a notícia (apuração exclusiva), escreva no máximo 2 parágrafos de análise.
- Se a proteção de mulheres ou crianças não for o assunto central da notícia (só citada de passagem ou num anúncio), responda com "publicar": false.
- Não comente o próprio material ("a reportagem não informa", "o texto não detalha"): se falta um dado, simplesmente não fale dele.
- Responda só com um objeto JSON, sem comentários, com as chaves:
  "titulo": título próprio, informativo, até 100 caracteres;
  "resumo": 2 ou 3 frases, até 330 caracteres, com o fato principal (é a chamada do destaque; não repita o título);
  "analise": lista de 3 a 5 parágrafos (2 a 4 frases cada, 900 a 1.800 caracteres no total) que aprofundam o fato:
    o que aconteceu, números e prazos, quem está envolvido, a lei ou política pública aplicável, antecedentes e
    contexto no Brasil, divergências entre as fontes e próximos passos. Cite o veículo quando atribuir uma informação,
    sem repetir "segundo a matéria" a cada frase. Se o material for curto, escreva menos, sem encher;
  "pontos": lista de 3 a 5 fatos-chave curtos (até 140 caracteres cada), com números quando houver;
  "por_que_importa": 1 ou 2 frases, até 280 caracteres, sobre o que muda para mulheres, crianças, famílias ou para a rede de proteção;
  "observar": 1 frase, até 200 caracteres, sobre o próximo marco ou decisão a acompanhar ("" se o material não indicar);
  "editoria": uma letra entre P (política e políticas públicas), E (trabalho e renda), S (sociedade), T (violência digital),
    A (infância: crianças e adolescentes), L (leis e Justiça), H (saúde), N (segurança: feminicídio, polícia, medidas protetivas),
    I (amparo: rede de acolhimento e atendimento), G (diversidade: mulheres negras, indígenas, do campo, LBT, com deficiência);
  "ufs": lista de siglas de estados brasileiros citados como local do fato (pode ser vazia);
  "publicar": false se o material for fraco, promocional, repetido ou não for sobre a proteção de mulheres ou crianças no Brasil; senão true."""


def redigir(grupo: list[dict]) -> dict | None:
    from anthropic import Anthropic
    principal = grupo[0]
    material = "\n\n".join(
        f"FONTE: {n['fonte']} ({n['data'][:10]})\nTÍTULO: {n['titulo']}\nCHAMADA: {n.get('resumo', '')}" for n in grupo[:5])
    lidos = 0
    for n in grupo[:4]:  # texto de até duas matérias (as que o robots.txt deixa ler)
        corpo = texto_da_materia(n["link"])
        if corpo:
            material += f"\n\nTEXTO DA MATÉRIA ({n['fonte']}):\n{corpo}"
            lidos += 1
        if lidos == 2:
            break
    r = Anthropic().messages.create(model=MODELO, max_tokens=16000, system=INSTRUCOES,
                                    output_config={"effort": "medium"},
                                    messages=[{"role": "user", "content": material}])
    txt = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    d = json.loads(m.group(0))
    if not d.get("publicar", True) or d.get("editoria") not in FOTOS:
        return None
    return d


def escolher_foto(texto: str, e: str, ufs: list[str], evitar: list[str], usos: dict | None = None) -> str:
    """Foto que combina com o assunto; se não houver, a da região; por fim, a foto da editoria menos usada
    nos destaques atuais (para a capa não repetir imagem)."""
    usos = usos or {}
    for padrao, foto in FOTO_ASSUNTO:
        if not (RAIZ / "src" / "img" / f"{foto}.jpg").exists():
            continue
        if re.search(padrao, texto, re.I) and foto not in evitar and usos.get(foto, 0) < 2:
            return foto
    regioes = {REGIAO[u] for u in ufs}
    if len(regioes) == 1 and FOTO_REGIAO.get(next(iter(regioes))) not in (None, *evitar):
        return FOTO_REGIAO[next(iter(regioes))]
    livres = [f for f in FOTOS[e] if f not in evitar] or FOTOS[e]
    return min(livres, key=lambda f: (usos.get(f, 0), FOTOS[e].index(f)))


def main() -> None:
    agora = datetime.now(timezone.utc)
    repo = json.loads((DATA / "noticias_completo.json").read_text(encoding="utf-8"))["noticias"]
    caminho = DATA / "destaques.json"
    destaques = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else []
    corte = (agora - timedelta(days=GUARDA_DIAS)).isoformat()
    destaques = [d for d in destaques if d["iso"] >= corte]
    usados = {d["grupo"] for d in destaques}
    recentes = sum(1 for d in destaques if d["criado_em"] >= (agora - timedelta(hours=24)).isoformat())
    vagas = max(0, min(POR_RODADA, POR_DIA - recentes))
    com_ia = bool(os.environ.get("ANTHROPIC_API_KEY"))

    grupos: dict[str, list[dict]] = {}
    for n in repo:
        grupos.setdefault(n["grupo"], []).append(n)
    limite = (agora - timedelta(hours=JANELA_H)).isoformat()
    candidatos = [n for n in repo if n["id"] == n["grupo"] and n["brasil"] and n["data"] >= limite and n["grupo"] not in usados]
    candidatos.sort(key=lambda n: pontos(n, agora), reverse=True)
    eds_hoje = [d["e"] for d in destaques if d["criado_em"] >= (agora - timedelta(hours=24)).isoformat()]

    def aplicar(item: dict, texto: dict) -> None:
        item.update(h=texto["titulo"], t=texto["resumo"], w=texto.get("por_que_importa", ""), ia=1)
        paragrafos = [p.strip() for p in texto.get("analise") or [] if p.strip()]
        if paragrafos:
            item["a"] = paragrafos
        x = {}
        pontos = [p.strip() for p in texto.get("pontos") or [] if p.strip()]
        if pontos:
            x["bl"] = pontos[:5]
        if (texto.get("observar") or "").strip():
            x["nx"] = texto["observar"].strip()
        if x:
            item["x"] = x

    # destaques no ar que saíram sem a IA (modo reserva) ganham o texto aprofundado
    if com_ia:
        refeitos = 0
        semana = (agora - timedelta(days=7)).isoformat()
        for item in destaques:
            if refeitos >= REESCREVE:
                break
            if item.get("ia") or item["iso"] < semana or item["grupo"] not in grupos:
                continue
            grupo = sorted(grupos[item["grupo"]], key=lambda x: PESO_TIPO.get(x.get("tipo", ""), 0), reverse=True)
            try:
                texto = redigir(grupo)
            except Exception as e:  # falha da API não derruba a atualização do site
                print("reescrita com IA falhou:", type(e).__name__, str(e)[:200])
                com_ia = False
                break
            refeitos += 1
            if texto:
                aplicar(item, texto)
            else:
                item["ia"] = -1  # o Claude achou o material fraco ou fora do tema: sai do ar abaixo
        if refeitos:
            print(f"{refeitos} destaques antigos reescritos pelo Claude")

    antes = len(destaques)
    destaques = [d for d in destaques if d.get("ia") != -1 and sobre_tema(d["h"] + " " + d.get("t", "")[:400])]
    if len(destaques) < antes:
        print(f"{antes - len(destaques)} destaques fora do tema retirados")
    novos = []
    for n in candidatos:
        if len(novos) >= vagas:
            break
        if eds_hoje.count(n["editoria"]) >= 3:  # variedade: no máximo 3 por editoria em 24 h
            continue
        if not sobre_tema(n["titulo"]):  # destaque precisa ser do tema já no título
            continue
        grupo = sorted(grupos[n["grupo"]], key=lambda x: PESO_TIPO.get(x.get("tipo", ""), 0), reverse=True)
        texto = None
        if com_ia:
            try:
                texto = redigir(grupo)
            except Exception as e:  # falha da API não derruba a atualização do site
                print("curadoria com IA falhou:", type(e).__name__, str(e)[:200])
                com_ia = False
            if com_ia and texto is None:
                usados.add(n["grupo"])  # a IA descartou: não tenta de novo
                continue
        e = (texto or {}).get("editoria") or n["editoria"]
        ufs = sorted(set((texto or {}).get("ufs") or n.get("ufs") or []) & set(REGIAO))
        d = datetime.fromisoformat(n["data"]).astimezone(timezone(timedelta(hours=-3)))
        h = texto["titulo"] if texto else n["titulo"]
        ultimas = [x["img"] for x in destaques[:4] + novos]
        usos = {}
        for x in destaques + novos:
            usos[x.get("img")] = usos.get(x.get("img"), 0) + 1
        foto = escolher_foto(f"{h} {n['titulo']}", e, ufs, ultimas, usos)
        fontes = []
        for x in grupo:
            if x["fonte"] not in [f[0] for f in fontes]:
                fontes.append([x["fonte"], x["link"]])
        if texto:
            h, t, w = texto["titulo"], texto["resumo"], texto.get("por_que_importa", "")
        else:
            outros = len(fontes) - 1
            h = n["titulo"]
            t = (f"Notícia publicada por {n['fonte']} em {d.day} {MESES[d.month - 1]} {d.year}"
                 + (f" e repercutida por mais {outros} veículo{'s' if outros > 1 else ''}" if outros else "")
                 + ". Leia a matéria completa na fonte.")
            w = ""
        item = {"id": "a" + n["grupo"][:9], "grupo": n["grupo"], "e": e, "img": foto, "iso": n["data"],
                "date": f"{d.day} {MESES[d.month - 1]} {d.year}", "h": h, "t": t, "w": w, "s": fontes[:4],
                "auto": 1, "ia": 1 if texto else 0, "criado_em": agora.isoformat()}
        if ufs:
            item["uf"] = ufs
        if texto:
            aplicar(item, texto)
        novos.append(item)
        usados.add(n["grupo"])
        eds_hoje.append(e)

    destaques = sorted(destaques + novos, key=lambda d: d["iso"], reverse=True)
    caminho.write_text(json.dumps(destaques, ensure_ascii=False, indent=1), encoding="utf-8")
    modo = "redigidos pelo Claude" if com_ia else "título original + link (sem ANTHROPIC_API_KEY)"
    print(f"{len(novos)} destaques novos ({modo}) · {len(destaques)} no ar · {len(candidatos)} candidatos")


if __name__ == "__main__":
    main()
