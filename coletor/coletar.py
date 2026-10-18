"""Coleta notícias sobre a defesa de mulheres e crianças no Brasil e mantém o repositório (arquivo acumulado).

Fontes: os feeds RSS/Atom de data/fontes.json (respeitando o robots.txt de cada site),
a página de notícias de órgãos que não têm feed (campo "pagina")
e, como descoberta extra, a API aberta do GDELT (imprensa brasileira).
Fica só com itens sobre o tema (violência contra a mulher, leis, amparo, proteção da infância),
classifica cada um por editoria, estado, região e instituição citada, junta duplicados
(mesma notícia em vários veículos) e ACUMULA: o que já estava no arquivo continua lá,
mesmo depois de sair do feed.

Saídas:
  data/noticias_completo.json   arquivo interno (inclui o resumo do feed, texto do veículo)
  data/noticias.json            público, as mais recentes (home e Radar)
  data/arquivo/AAAA-MM.json     público, o repositório completo por mês

Uso: uv run coletor/coletar.py
"""

import hashlib
import json
import re
import time
import unicodedata
import ssl
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
UA = "Mozilla/5.0 (compatible; ObservatorioBrasilMulherBot/0.1; +https://www.observatoriobrasilmulher.com.br)"
DIAS_NOVAS = 30    # item do feed mais velho que isso é ignorado (o arquivo já guarda os antigos)
DIAS_ARQUIVO = 730 # o repositório guarda até 2 anos
LIMITE_HOME = 800  # itens em data/noticias.json (o que a home e o Radar carregam)
GDELT = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
         + quote('("violência contra a mulher" OR feminicídio OR "Maria da Penha" OR "medida protetiva" '
                 'OR "violência doméstica" OR "abuso sexual infantil" OR "estupro de vulnerável")')
         + "%20sourcecountry:brazil&mode=artlist&maxrecords=150&format=json&timespan=3d&sort=datedesc")

# Instituições acompanhadas: nome exibido -> padrão de busca (o campo se chama "empresas" nos dados).
EMPRESAS = {
    "Ministério das Mulheres": r"minist[eé]rio das mulheres|ministra das mulheres",
    "Ministério dos Direitos Humanos": r"minist[eé]rio dos direitos humanos|\bMDHC\b",
    "Ministério da Justiça": r"minist[eé]rio da justi[cç]a|\bMJSP\b", "Ministério da Saúde": r"minist[eé]rio da sa[uú]de",
    "STF": r"\bSTF\b|supremo tribunal federal|\bsupremo\b", "STJ": r"\bSTJ\b|superior tribunal de justi[cç]a",
    "CNJ": r"\bCNJ\b|conselho nacional de justi[cç]a", "TSE": r"\bTSE\b|tribunal superior eleitoral",
    "Ministério Público": r"minist[eé]rio p[uú]blico|\bMP[A-Z]{0,2}\b|promotoria", "Defensoria Pública": r"defensoria",
    "Polícia Civil": r"pol[ií]cia civil|delegacia", "Polícia Militar": r"pol[ií]cia militar|\bPM\b|patrulha maria da penha",
    "Polícia Federal": r"pol[ií]cia federal|\bPF\b", "Senado": r"\bsenado\b", "Câmara dos Deputados": r"c[aâ]mara dos deputados",
    "ONU Mulheres": r"onu mulheres|un women", "UNICEF": r"unicef", "Instituto Maria da Penha": r"instituto maria da penha",
    "Fórum Brasileiro de Segurança Pública": r"f[oó]rum brasileiro de seguran[cç]a|anu[aá]rio brasileiro de seguran[cç]a",
    "Conselho Tutelar": r"conselho tutelar|conselhos tutelares", "Casa da Mulher Brasileira": r"casa da mulher brasileira",
    "Meta": r"\bmeta\b|instagram|facebook|whatsapp", "Google": r"google|youtube", "TikTok": r"tiktok",
    "X (Twitter)": r"\btwitter\b|\bX\b \(antigo twitter\)", "Telegram": r"telegram", "Discord": r"discord",
}
EMPRESAS_RE = {k: re.compile(v, re.I) for k, v in EMPRESAS.items()}

# Estados: nome, capital e cidades/gentílicos sem ambiguidade. Siglas só entre parênteses ou após hífen, ex. "(CE)".
UF_TERMOS = {
    "AC": r"\bAcre\b|Rio Branco", "AL": r"Alagoas|Macei[oó]", "AP": r"Amap[aá]|Macap[aá]", "AM": r"\bAmazonas\b|Manaus",
    "BA": r"\bBahia\b|baian|Salvador \(|Cama[cç]ari|Feira de Santana", "CE": r"Cear[aá]|Fortaleza|Caucaia|Juazeiro do Norte",
    "DF": r"Distrito Federal|\bGDF\b", "ES": r"Esp[ií]rito Santo|capixaba|Vila Velha", "GO": r"Goi[aá]s|Goi[aâ]nia|An[aá]polis",
    "MA": r"Maranh[aã]o|S[aã]o Lu[ií]s", "MT": r"Mato Grosso(?! do Sul)|Cuiab[aá]", "MS": r"Mato Grosso do Sul|Campo Grande",
    "MG": r"Minas Gerais|mineir[ao]|Belo Horizonte|Uberl[aâ]ndia|Juiz de Fora", "PA": r"\bPará\b|\bBel[eé]m\b|paraense",
    "PB": r"Para[ií]ba|Jo[aã]o Pessoa|Campina Grande", "PR": r"Paran[aá]\b|Curitiba|Londrina|Maring[aá]|paranaense",
    "PE": r"Pernambuco\b|Recife", "PI": r"Piau[ií]|Teresina", "RJ": r"Rio de Janeiro|carioca|Niter[oó]i",
    "RN": r"Rio Grande do Norte|potiguar|Mossor[oó]", "RS": r"Rio Grande do Sul|Porto Alegre|ga[uú]ch|Caxias do Sul",
    "RO": r"Rond[oô]nia|Porto Velho", "RR": r"Roraima|Boa Vista", "SC": r"Santa Catarina|Florian[oó]polis|Joinville|Blumenau|catarinense",
    "SP": r"S[aã]o Paulo|paulista|Campinas|Ribeir[aã]o Preto|S[aã]o Jos[eé] dos Campos|Sorocaba", "SE": r"Sergipe|Aracaju",
    "TO": r"Tocantins|Palmas \(",
}
UF_RE = {k: re.compile(v, re.I) for k, v in UF_TERMOS.items()}
SIGLA_RE = re.compile(r"[(\-–]\s?(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\)?\b")
REGIAO = {**dict.fromkeys(["AC", "AM", "AP", "PA", "RO", "RR", "TO"], "Norte"),
          **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
          **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
          **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
          **dict.fromkeys(["PR", "RS", "SC"], "Sul")}


def estados(texto: str) -> list[str]:
    achados = {uf for uf, r in UF_RE.items() if r.search(texto)}
    achados.update(SIGLA_RE.findall(texto))
    return sorted(achados)
SEM_VERIFICACAO = ssl._create_unverified_context()

# Termos que, sozinhos, já colocam a notícia no tema.
TEMA_FORTE = re.compile(
    r"viol[eê]ncia (contra (a |as )?(mulher|mulheres|meninas?|crian[cç]as?|adolescentes?)|dom[eé]stica|de g[eê]nero|"
    r"obst[eé]trica|sexual|psicol[oó]gica|vic[aá]ria|pol[ií]tica de g[eê]nero|infantil)|"
    r"feminic[ií]dio|femic[ií]dio|maria da penha|medidas? protetivas?|estupro|estuprad[ao]|abuso sexual|abusad[ao] sexualmente|"
    r"ass[eé]dio sexual|importuna[cç][aã]o sexual|explora[cç][aã]o sexual|pedofil|misogin|machismo|"
    r"casa da mulher brasileira|ligue 180|disque 100|delegacias? (da|de defesa da) mulher|\bDEAMs?\b|"
    r"minist[eé]rio das mulheres|direitos das mulheres|igualdade de g[eê]nero|igualdade salarial|"
    r"estatuto da crian[cç]a|\bECA\b|conselhos? tutelar(es)?|trabalho infantil|abuso infantil|maus-tratos|"
    r"aborto legal|dignidade menstrual|sextors[aã]o|aliciamento (de|online)|grooming|nudes|imagens? [ií]ntimas?|"
    r"v[ií]deos? [ií]ntimos?|tr[aá]fico de (pessoas|mulheres|crian[cç]as)|casamento infantil|gravidez na adolesc[eê]ncia|"
    r"stalking|crime de persegui[cç][aã]o|sinal vermelho|patrulha maria da penha|lei henry borel|escuta especializada|"
    r"depoimento especial|viol[eê]ncia contra a pessoa idosa|leg[ií]tima defesa da honra|lei do minuto seguinte|n[aã]o [eé] n[aã]o",
    re.I,
)
# Sujeito + dano: "mulher é morta", "criança vítima de agressão", "menina desaparecida"...
SUJEITO = re.compile(r"\bmulher(es)?\b|\bm[aã]es?\b|\bgestantes?\b|\bmeninas?\b|\bcrian[cç]as?\b|\badolescentes?\b|\bbeb[eê]s?\b|"
                     r"\bmenor(es)? de idade\b|\besposa\b|\bnamorada\b|\bex-companheira\b|\bcompanheira\b|\bvi[uú]va\b|\binf[aâ]ncia\b|\bg[eê]nero\b", re.I)
DANO = re.compile(r"viol[eê]ncia|agress|agredid|espancad|abus|ass[eé]di|estupr|mort[ao]s?\b|matou|assassin|esfaquead|baleada|"
                  r"amea[cç]|desaparecid|sequestr|v[ií]tima|prote[cç]|protetiv|amparo|acolh|abrigo|den[uú]nci|"
                  r"\blei\b|igualdade|desigualdade|discrimina|preconceito|racis|maus-tratos|neglig|explora|"
                  r"tornozeleira|delegacia", re.I)
# Vagas e oportunidades para mulheres e jovens: "inscrições abertas para curso gratuito para mulheres"...
OPORTUNIDADE = re.compile(r"\bvagas?\b|inscri[cç][oõ]es|\bedita(l|is)\b|cursos? (gratuito|de capacita|de qualifica|profissionaliz)|"
                          r"capacita[cç][aã]o|qualifica[cç][aã]o profissional|\bbolsas?\b|empregabilidade|mercado de trabalho|"
                          r"jovem aprendiz|primeiro emprego|empreendedor|microcr[eé]dito|cr[eé]dito para|feira de emprego|mutir[aã]o de emprego|\bsine\b", re.I)
PUBLICO_OP = re.compile(r"\bmulher(es)?\b|\bm[aã]es\b|\bmeninas\b|\bjovens\b|\badolescentes\b|\bv[ií]timas de viol[eê]ncia\b|\bfeminin[oa]s?\b", re.I)

# ordem = desempate: editorias específicas antes das genéricas
EDITORIAS = {
    "I": r"casa da mulher brasileira|abrigo|acolhiment|casa-abrigo|centro de refer[eê]ncia|\bCRAM\b|\bCREAS\b|\bCRAS\b|ligue 180|"
         r"disque 100|rede de (prote[cç][aã]o|atendimento|enfrentamento)|assist[eê]ncia social|amparo|aux[ií]lio|benef[ií]cio|atendimento",
    "T": r"internet|online|redes sociais|digital|deepfake|nudes|imagens? [ií]ntimas?|v[ií]deos? [ií]ntimos?|sextors|perfil falso|"
         r"aplicativo|\bapps?\b|instagram|tiktok|whatsapp|telegram|discord|cibern|virtual|intelig[eê]ncia artificial|golpe",
    "A": r"crian[cç]a|infantil|inf[aâ]ncia|adolescen|menor de idade|menina|menino|beb[eê]|escola|estudante|\bECA\b|conselho tutelar|"
         r"estupro de vulner[aá]vel|pedofil|explora[cç][aã]o sexual|trabalho infantil|bullying|creche",
    "H": r"sa[uú]de|\bSUS\b|hospital|m[eé]dic|maternidade|gestante|gravidez|gr[aá]vida|parto|obst[eé]tric|aborto|anticoncep|"
         r"c[aâ]ncer de mama|mamografia|sa[uú]de mental|pr[eé]-natal|mortalidade materna|menstrua|vacina",
    "G": r"\bnegras?\b|racis|ind[ií]genas?|quilombol|LGBT|l[eé]sbica|\btrans\b|transexua|travesti|com defici[eê]ncia|\bPcD\b|"
         r"idosa|rural|do campo|ribeirinh|periferia|imigrante|refugiad",
    "N": r"feminic[ií]d|femic[ií]d|assassin|mort[ao]\b|matou|homic[ií]d|pol[ií]cia|delegacia|\bDEAM|pris[aã]o|pres[ao]\b|flagrante|"
         r"boletim de ocorr|medidas? protetivas?|tornozeleira|patrulha|seguran[cç]a p[uú]blica|agress|espancad|esfaque|baleada|tiros?\b",
    "L": r"\blei\b|leis\b|legisla|projeto de lei|\bPL \d|\bSTF\b|\bSTJ\b|\bTJ[A-Z]{0,2}\b|tribunal|justi[cç]a|\bju[ií]z[a]?\b|"
         r"condena|senten[cç]a|julgament|\br[eé]u\b|minist[eé]rio p[uú]blico|promotor|defensoria|\bCNJ\b|supremo|j[uú]ri|decis[aã]o",
    "E": r"trabalho|emprego|sal[aá]ri|renda|mercado de trabalho|empreend|economia|desemprego|aposentad|previd[eê]n|ass[eé]dio moral|"
         r"\bCLT\b|licen[cç]a-maternidade|cuidados?\b|empresas?\b",
    "P": r"governo|minist[eé]rio|ministra|presidente|congresso|senado|c[aâ]mara|deputad|senador|prefeit|vereador|elei[cç]|"
         r"pol[ií]tica p[uú]blica|or[cç]amento|plano nacional|pacto nacional|programa federal|candidat",
    "S": r"educa[cç][aã]o|cultura|campanha|m[ií]dia|novela|filme|comportamento|machismo|misogin|igualdade de g[eê]nero|feminis|"
         r"sociedade|pesquisa|levantamento|estudo|religi",
}
EDITORIAS_RE = {k: re.compile(v, re.I) for k, v in EDITORIAS.items()}

# Pistas de que a notícia é sobre o Brasil.
BRASIL = re.compile(
    r"brasil|brasileir|\bBR\b|S[aã]o Paulo|Rio de Janeiro|Bras[ií]lia|Minas Gerais|Bahia|Pernambuco|Cear[aá]|"
    r"Goi[aá]s|Paran[aá]|Santa Catarina|Rio Grande do Sul|Amaz[oô]nia|Nordeste|\bSUS\b|Maria da Penha|Ligue 180|Disque 100|"
    r"Lula|Congresso Nacional|C[aâ]mara dos Deputados|Senado Federal|\bSTF\b|\bSTJ\b|\bCNJ\b|\bECA\b|Conselho Tutelar|"
    r"Casa da Mulher Brasileira|Minist[eé]rio das Mulheres|Delegacia da Mulher|\bDEAM|R\$",
    re.I,
)
# Fontes estrangeiras: só entram notícias que citam o Brasil.
SO_COM_BRASIL = {"Internacional"}
TAG = re.compile(r"<[^>]+>")


def limpar(t: str | None) -> str:
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", unescape(TAG.sub(" ", t or "")))).strip()


def data_iso(txt: str | None) -> str | None:
    if not txt:
        return None
    txt = txt.strip()
    try:
        d = parsedate_to_datetime(txt)
    except Exception:
        try:
            d = datetime.fromisoformat(txt.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat()


def filho(el, *nomes):
    for n in nomes:
        for c in el:
            if c.tag.split("}")[-1] == n:
                return c
    return None


def itens_feedparser(xml: bytes) -> list[dict]:
    """Plano B para feed malformado: o feedparser tolera XML quebrado."""
    import feedparser
    f = feedparser.parse(xml)
    return [{"titulo": limpar(e.get("title")), "link": (e.get("link") or "").strip(),
             "resumo": limpar(e.get("summary"))[:400],
             "data": data_iso(e.get("published") or e.get("updated"))} for e in f.entries]


def itens_do_feed(xml: bytes) -> list[dict]:
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        if len(xml) > 1_500_000 or b"<rss" not in xml[:2000].lower() and b"<feed" not in xml[:2000].lower():
            return []  # não é feed (página de erro, HTML, binário)
        try:
            return itens_feedparser(xml)
        except Exception:
            return []
    saida = []
    for el in raiz.iter():
        nome = el.tag.split("}")[-1]
        if nome not in ("item", "entry"):
            continue
        titulo = filho(el, "title")
        link = filho(el, "link")
        href = (link.get("href") or link.text) if link is not None else None
        resumo = filho(el, "description", "summary", "content", "encoded")
        quando = filho(el, "pubDate", "published", "updated", "date")
        saida.append({
            "titulo": limpar(titulo.text if titulo is not None else ""),
            "link": (href or "").strip(),
            "resumo": limpar(resumo.text if resumo is not None else "")[:400],
            "data": data_iso(quando.text if quando is not None else None),
        })
    return saida


# Idioma do título: o portal publica só manchetes em português.
_PT = set("e o a os as um uma de do da dos das em no na nos nas por para com que não é ao à se seu sua mais como entre sobre após já".split())
_EN = set("the of and to in for on with is are how why what new its at by from this that will can it as be has have".split())
_ES = set("el los las del y en con para por que es una un su sus como más según ya entre sobre al lo".split())


def em_portugues(titulo: str) -> bool:
    w = re.findall(r"[a-záéíóúâêôãõçñ]+", titulo.lower())
    pt, en, es = (sum(x in c for x in w) for c in (_PT, _EN, _ES))
    if en >= 2 and en > pt:
        return False
    # espanhol: palavras exclusivas (el, los, las, del, y, ya, según, más, su/sus) acima das portuguesas
    so_es = sum(x in {"el", "los", "las", "del", "la", "y", "ya", "según", "más", "su", "sus", "lo", "al", "una", "es", "cómo", "con", "pero", "hasta"} for x in w)
    so_es += len(re.findall(r"ci[oó]n(es)?\b|[ñ¿¡]", titulo.lower()))
    return not (so_es >= 2 and so_es > pt)


# legenda de foto no resumo do feed ("Foto: Fulano/Agência X") não conta para o tema
LEGENDA = re.compile(r"(imagem|foto|ilustra\w*|arte|cr[eé]dito)s?\s*:[^|]{0,160}?(?=\||$)", re.I)


def relevante(titulo: str, resumo: str) -> bool:
    """Notícia do tema: o título trata do tema, ou o resumo trata (sem contar legenda de imagem)."""
    return sobre_tema(titulo) or sobre_tema(LEGENDA.sub(" ", resumo or "")) or oportunidade(titulo)


def sobre_tema(texto: str) -> bool:
    if TEMA_FORTE.search(texto):
        return True
    return bool(SUJEITO.search(texto) and DANO.search(texto))


def oportunidade(titulo: str) -> bool:
    """Vaga, curso, edital ou bolsa voltado a mulheres ou jovens (só pelo título, para não pegar anúncio genérico)."""
    return bool(OPORTUNIDADE.search(titulo) and PUBLICO_OP.search(titulo))


def editoria(texto: str, padrao: str) -> str:
    pontos = {k: len(r.findall(texto)) for k, r in EDITORIAS_RE.items()}
    melhor = max(pontos, key=lambda k: (pontos[k], k in padrao))
    return melhor if pontos[melhor] else (padrao[0] if padrao else "S")


def baixar(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for ctx in (None, SEM_VERIFICACAO):
        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                return r.read(3_000_000)
        except (ssl.SSLError, urllib.error.URLError) as e:
            # só vale tentar sem verificar o certificado se o erro foi de certificado
            if isinstance(e, ssl.SSLError) or isinstance(getattr(e, "reason", None), ssl.SSLError):
                continue
            return None
        except Exception:
            return None
    return None


_ROBOTS: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def robots_permite(url: str) -> bool:
    """Respeita o robots.txt do site: se ele proíbe o feed, não coletamos."""
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        corpo = baixar(base + "/robots.txt")
        if corpo is None:
            _ROBOTS[base] = None  # sem robots.txt acessível: liberado
        else:
            rp.parse(corpo.decode("utf-8", "replace").splitlines())
            _ROBOTS[base] = rp
    rp = _ROBOTS[base]
    return rp is None or rp.can_fetch(UA, url)


def feeds_tematicos(feed: str) -> list[str]:
    """Sites WordPress publicam feeds por tag e por busca; pedimos os do tema."""
    if "/feed" not in feed:
        return []
    base = feed.split("/feed")[0].rstrip("/")
    return [base + "/tag/violencia-contra-a-mulher/feed/",
            base + "/?s=viol%C3%AAncia+contra+a+mulher&feed=rss2"]


# páginas de notícias já lidas: link -> {titulo, data} (ou None, sem data/título), para não baixar de novo
VISTAS_ARQ = DATA / "paginas_vistas.json"
VISTAS: dict[str, dict | None] = json.loads(VISTAS_ARQ.read_text(encoding="utf-8")) if VISTAS_ARQ.exists() else {}
NOVAS_POR_PAGINA = 8  # matérias novas abertas por página a cada rodada
META = {k: re.compile(v, re.I) for k, v in {
    "titulo": r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"|<title>([^<]+)</title>|<h1[^>]*>(.*?)</h1>',
    "data": r'article:published_time"[^>]+content="([^"]+)"|"datePublished"\s*:\s*"([^"]+)"|<time[^>]+datetime="([^"]+)"',
}.items()}
MESES_TXT = {m: i + 1 for i, ms in enumerate(zip(
    "january february march april may june july august september october november december".split(),
    "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split())) for m in ms}
DATA_TXT = re.compile(r"\b([A-Z][a-z]+) (\d{1,2}), (20\d\d)\b|\b(\d{1,2}) de ([a-zç]+) de (20\d\d)\b")


def data_do_texto(html: str) -> str | None:
    """Página sem metadado de data: primeira data escrita por extenso ("June 29, 2026" ou "29 de junho de 2026")."""
    for m in DATA_TXT.finditer(html):
        mes, dia, ano = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(5), m.group(4), m.group(6))
        if mes.lower() in MESES_TXT:
            return datetime(int(ano), MESES_TXT[mes.lower()], int(dia), 12, tzinfo=timezone.utc).isoformat()
    return None


def coletar_pagina(f: dict) -> tuple[str, list[dict], str | None]:
    """Sites sem feed: lê a lista de notícias da página e abre só as matérias novas (título e data do HTML)."""
    if not robots_permite(f["pagina"]):
        return f["id"], [], "robots.txt não permite"
    corpo = baixar(f["pagina"])
    if not corpo:
        return f["id"], [], "não respondeu"
    p = urlparse(f["pagina"])
    links = []
    for h in re.findall(f["padrao"], corpo.decode("utf-8", "replace")):
        u = h if h.startswith("http") else f"{p.scheme}://{p.netloc}{h}"
        if u not in links and u.rstrip("/") != f["pagina"].rstrip("/"):
            links.append(u)
    if f.get("data_vista") and not any(u in VISTAS for u in links):
        # site sem data nas matérias: na primeira leitura só anota o que já existe; o que aparecer depois
        # entra com a data em que foi visto
        VISTAS.update((u, None) for u in links)
        return f["id"], [], None
    abertas = 0
    for u in links:
        if u in VISTAS or abertas >= NOVAS_POR_PAGINA or not robots_permite(u):
            continue
        abertas += 1
        html = (baixar(u) or b"").decode("utf-8", "replace")
        t, d = META["titulo"].search(html), META["data"].search(html)
        titulo = limpar(next((g for g in t.groups() if g), "")) if t else ""
        titulo = re.split(r"\s+[|\\]\s+", titulo)[0].strip()  # tira " | Órgão"
        titulo = re.sub(r"\s+[–—]\s+[^–—]{2,30}$", "", titulo)  # e " – Órgão"
        quando = data_iso(next((g for g in d.groups() if g), None)) if d else None
        if not quando and f.get("data_url") and (m := re.search(f["data_url"], u)):  # data no endereço (aa/mm/dd)
            quando = datetime(2000 + int(m[1]), int(m[2]), int(m[3]), 12, tzinfo=timezone.utc).isoformat()
        quando = quando or data_do_texto(html)
        if not quando and f.get("data_vista"):
            quando = datetime.now(timezone.utc).isoformat()
        VISTAS[u] = {"titulo": titulo, "data": quando} if titulo and quando else None
    itens = [{"titulo": v["titulo"], "link": u, "resumo": "", "data": v["data"]}
             for u in links if (v := VISTAS.get(u))]
    return f["id"], filtrar(itens, f), None


def coletar_fonte(f: dict) -> tuple[str, list[dict], str | None]:
    if f.get("pagina"):
        return coletar_pagina(f)
    if not robots_permite(f["feed"]):
        return f["id"], [], "robots.txt não permite"
    corpo = baixar(f["feed"])
    if not corpo:
        return f["id"], [], "não respondeu"
    itens = itens_do_feed(corpo)
    if not itens and b"<item" not in corpo and b"<entry" not in corpo:
        return f["id"], [], "feed inválido"
    for extra in feeds_tematicos(f["feed"]):
        if not robots_permite(extra):
            continue
        c = baixar(extra)
        if c and c.lstrip()[:600].lower().find(b"<rss") > -1:
            itens += itens_do_feed(c)
    return f["id"], filtrar(itens, f), None


def filtrar(itens: list[dict], f: dict) -> list[dict]:
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_NOVAS)
    bons = []
    for it in itens:
        texto = f"{it['titulo']} {it['resumo']}"
        if not it["titulo"] or not it["link"] or not (relevante(it["titulo"], it["resumo"]) and em_portugues(it["titulo"])):
            continue
        if it["data"] and datetime.fromisoformat(it["data"]) < limite:
            continue
        brasil = bool(BRASIL.search(texto))
        if not brasil and f["setor"] in SO_COM_BRASIL:
            continue
        empresas = [k for k, r in EMPRESAS_RE.items() if r.search(it["titulo"])]
        ufs = estados(texto)
        regioes = sorted({REGIAO[u] for u in ufs})
        brasil = brasil or bool(ufs) or f["setor"] != "Internacional"  # fonte brasileira fala do Brasil
        it.update(fonte=f["nome"], fonte_id=f["id"], tipo=f["tipo"], setor=f["setor"], brasil=brasil, empresas=empresas,
                  ufs=ufs, regioes=regioes, fonte_uf=f.get("uf"), fonte_regiao=REGIAO.get(f.get("uf")),
                  editoria=editoria(texto, f.get("editorias", "")))
        if oportunidade(it["titulo"]):
            it.update(oport=True, editoria="E")
        bons.append(it)
    return bons


def coletar_gdelt(fontes: list[dict]) -> list[dict]:
    """Descoberta extra: imprensa brasileira indexada pelo GDELT (API aberta, 1 consulta por rodada)."""
    corpo = baixar(GDELT)
    try:
        arts = json.loads(corpo or b"{}").get("articles", [])
    except ValueError:
        return []  # o GDELT responde texto quando limita a taxa; segue sem ele
    por_dominio = {}
    for f in fontes:
        dom = urlparse(f.get("site") or f.get("feed") or "").netloc.removeprefix("www.")
        if dom:
            por_dominio[dom] = f
    itens = []
    for a in arts:
        dom = (a.get("domain") or "").removeprefix("www.")
        f = por_dominio.get(dom, {"id": "gdelt:" + dom, "nome": dom, "tipo": "Imprensa", "setor": "Imprensa", "editorias": ""})
        try:
            quando = datetime.strptime(a.get("seendate", ""), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            quando = None
        itens += filtrar([{"titulo": limpar(a.get("title")), "link": a.get("url", ""), "resumo": "", "data": quando}], f)
    return itens


PALAVRA = re.compile(r"[a-z0-9]{4,}")


def assinatura(titulo: str) -> set[str]:
    t = unicodedata.normalize("NFD", titulo.lower()).encode("ascii", "ignore").decode()
    return set(PALAVRA.findall(t))


def _dias(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 99
    return (datetime.fromisoformat(a) - datetime.fromisoformat(b)).total_seconds() / 86400


def agrupar(noticias: list[dict]) -> None:
    """Mesma notícia em vários veículos: títulos com 60%+ das palavras em comum, até 3 dias de distância.
    Cada item ganha 'grupo' (id do primeiro) e 'n_fontes' (quantos veículos deram a notícia)."""
    base: list[tuple[set[str], dict]] = []
    for n in sorted(noticias, key=lambda n: n["data"] or ""):
        a = assinatura(n["titulo"])
        n["grupo"] = n["id"]
        if len(a) >= 4:
            for b, ref in reversed(base[-400:]):
                if len(a & b) / len(a | b) >= 0.6 and abs(_dias(ref["data"], n["data"])) <= 3:
                    n["grupo"] = ref["grupo"]
                    break
        base.append((a, n))
    fontes: dict[str, set[str]] = {}
    for n in noticias:
        fontes.setdefault(n["grupo"], set()).add(n["fonte"])
    for n in noticias:
        n["n_fontes"] = len(fontes[n["grupo"]])


PUBLICOS = ("id", "titulo", "link", "data", "fonte", "tipo", "editoria", "brasil", "empresas", "ufs", "regioes",
            "fonte_uf", "fonte_regiao", "grupo", "n_fontes", "oport")


def chave_titulo(t: str) -> str:
    return re.sub(r"\W+", "", t.lower())[:80]


def main() -> None:
    t0 = time.time()
    fontes_todas = json.loads((DATA / "fontes.json").read_text(encoding="utf-8"))
    fontes = [f for f in fontes_todas if f.get("feed") or f.get("pagina")]
    with ThreadPoolExecutor(max_workers=32) as ex:
        resultados = list(ex.map(coletar_fonte, fontes))
    gdelt = coletar_gdelt(fontes_todas)
    resultados.append(("gdelt", gdelt, None))

    # o repositório acumula: começa pelo que já está no arquivo
    arq = DATA / "noticias_completo.json"
    antes = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    anteriores = antes.get("noticias", [])
    anteriores = [n for n in anteriores if em_portugues(n["titulo"]) and relevante(n["titulo"], n.get("resumo", ""))]
    for n in anteriores:  # vagas e oportunidades: marca também o que já estava no arquivo
        if oportunidade(n["titulo"]):
            n.update(oport=True, editoria="E")
    for n in anteriores:  # sem data no feed: vale a data em que entrou no arquivo
        n["data"] = n.get("data") or n.get("coletado_em") or antes["gerado_em"]
    vistos, noticias, por_fonte, novas = set(), [], {}, 0
    for n in anteriores:
        n.setdefault("id", hashlib.sha1(n["link"].encode()).hexdigest()[:12])
        vistos.update((n["link"], chave_titulo(n["titulo"])))
        noticias.append(n)
    agora = datetime.now(timezone.utc).isoformat()
    for n in noticias:
        n["data"] = min(n["data"], agora)
    VISTAS_ARQ.write_text(json.dumps(VISTAS, ensure_ascii=False, indent=0), encoding="utf-8")
    for fid, itens, erro in resultados:
        por_fonte[fid] = erro or len(itens)
        for it in itens:
            chave = chave_titulo(it["titulo"])
            if it["link"] in vistos or chave in vistos:
                continue
            vistos.update((it["link"], chave))
            it["id"] = hashlib.sha1(it["link"].encode()).hexdigest()[:12]
            it["data"] = min(it["data"] or agora, agora)  # data no futuro (fuso errado no feed) vira agora
            it["coletado_em"] = agora
            noticias.append(it)
            novas += 1
    corte = (datetime.now(timezone.utc) - timedelta(days=DIAS_ARQUIVO)).isoformat()
    noticias = [n for n in noticias if n["data"] >= corte]
    noticias.sort(key=lambda n: n["data"], reverse=True)
    agrupar(noticias)

    arq.write_text(json.dumps({"gerado_em": agora, "total": len(noticias), "fontes_lidas": len(fontes), "novas": novas,
                               "por_fonte": por_fonte, "noticias": noticias}, ensure_ascii=False, indent=1), encoding="utf-8")
    # Público: só título, link, fonte e metadados, sem reproduzir o texto dos veículos.
    publico = [{k: n.get(k) for k in PUBLICOS} for n in noticias]
    (DATA / "noticias.json").write_text(json.dumps(
        {"gerado_em": agora, "total": len(publico), "noticias": publico[:LIMITE_HOME]},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pasta = DATA / "arquivo"
    pasta.mkdir(exist_ok=True)
    meses: dict[str, list[dict]] = {}
    for n in publico:
        meses.setdefault(n["data"][:7], []).append(n)
    for velho in pasta.glob("*.json"):  # mês que ficou vazio (saiu da janela ou data corrigida)
        if velho.stem not in meses:
            velho.unlink()
    for m, itens in meses.items():
        (pasta / f"{m}.json").write_text(json.dumps({"mes": m, "total": len(itens), "noticias": itens},
                                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    contagem = {k: sum(1 for n in noticias if n["editoria"] == k) for k in EDITORIAS}
    br = sum(1 for n in noticias if n["brasil"])
    print(f"{novas} novas ({len(gdelt)} via GDELT) · repositório: {len(noticias)} notícias, {br} citam o Brasil, "
          f"{len(meses)} meses · por editoria: {contagem} · {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
