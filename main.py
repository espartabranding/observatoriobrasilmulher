"""Gerador do site Observatório Brasil Mulher (www.observatoriobrasilmulher.com.br).

FONTE DA VERDADE: este script + src/portal.html + data/. NÃO EDITE o HTML gerado em
entrega/1-site-para-publicar à mão: a próxima geração desfaz.

Uso:
    uv run coletor/coletar.py      # atualiza o repositório de notícias
    uv run coletor/curar.py        # escolhe (e, com ANTHROPIC_API_KEY, redige) os destaques da home
    uv run main.py                 # gera entrega/ completa
    uv run main.py --ci            # só o site (usado pela atualização automática no GitHub Actions)

Requer Node.js e `npm install` em ferramentas/ (pré-renderização com jsdom).
Campos marcados «PREENCHER» no CFG ficam fora do site até serem preenchidos.
"""

import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from email.utils import format_datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import secoes

# ============================================================================
# CFG: preencha aqui. Campo com «PREENCHER» é omitido do site e do Schema.
# ============================================================================
PENDENTE = "«PREENCHER»"
CFG = {
    # OBM_DOMINIO troca o endereço sem editar aqui (ex.: a versão de prévia no GitHub Pages)
    "dominio": os.environ.get("OBM_DOMINIO") or "https://www.observatoriobrasilmulher.com.br",
    "nome": "Observatório Brasil Mulher",
    "slogan": "Observatório da defesa de mulheres e crianças",
    "descricao": ("Observatório e repositório de notícias sobre a defesa de mulheres e crianças no Brasil: violência contra a mulher, "
                  "leis de proteção, rede de amparo e proteção da infância, com fonte em cada notícia, dez editorias, edições regionais, "
                  "canais de ajuda, dados e guias práticos."),
    # Controlador dos dados (LGPD) e contatos
    "razao_social": PENDENTE,
    "cnpj": PENDENTE,
    "endereco": PENDENTE,                  # endereço completo da sede, se houver
    "email_redacao": PENDENTE,             # correções, pautas, pedidos de remoção
    "email_privacidade": PENDENTE,         # canal do encarregado (DPO), LGPD art. 41
    "encarregado_nome": PENDENTE,          # nome do encarregado de dados
    "plataforma_newsletter": PENDENTE,     # ex.: Beehiiv, Ghost, Brevo (operador dos dados)
    "foro": PENDENTE,                      # cidade/UF do foro nos Termos de Uso
    # Perfis oficiais (entram no sameAs do Schema): URLs completas
    "redes": [],                           # ex.: ["https://www.instagram.com/observatoriobrasilmulher"]
    "whatsapp_canal": "",                  # link do Canal do WhatsApp do portal (https://whatsapp.com/channel/...): liga o botão "Siga no WhatsApp"
    # Medição: vazio = nenhum script de terceiros e nenhum banner de cookies
    "ga4": "",                             # ID da propriedade GA4 do Observatório (liga banner de consentimento)
    "google_site_verification": "",        # Search Console (meta tag)
    "bing_site_verification": "",
    # Robôs de IA de TREINO (GPTBot, ClaudeBot, CCBot, Google-Extended...). Robôs de BUSCA ficam sempre liberados.
    "permitir_treino_ia": False,
}

ROOT = Path(__file__).parent
SRC = ROOT / "src" / "portal.html"
IMG = ROOT / "src" / "img"
ENTREGA = ROOT / "entrega"
OUT = ENTREGA / "1-site-para-publicar"
HOJE = date.today()
CI = "--ci" in sys.argv
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
D = CFG["dominio"].rstrip("/")
HOST = D.split("://", 1)[-1]


def ok(v):
    return bool(v) and PENDENTE not in str(v)


def esc(s):
    return html.escape(str(s), quote=True)


def slug(t, n=80):
    t = unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:n].rstrip("-")


# ============================================================================
# 1. Pré-renderização (Node + jsdom)
# ============================================================================
def fonte_com_destaques():
    """src/portal.html + destaques automáticos (data/destaques.json) como window.IAB_AUTO."""
    html_src = SRC.read_text(encoding="utf-8")
    arq = ROOT / "data" / "destaques.json"
    auto = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []
    campos = ("id", "e", "img", "iso", "date", "h", "t", "w", "a", "x", "s", "uf", "auto")
    auto = [{k: d[k] for k in campos if k in d} for d in auto]
    js = json.dumps(auto, ensure_ascii=False).replace("</", "<\\/")
    fotos = (ROOT / "src" / "fotos.json").read_text(encoding="utf-8")  # pools da capa (foto repetida é trocada)
    html_src = html_src.replace("<script>", f"<script>window.IAB_FOTOS={fotos};</script>\n<script>", 1)
    ajuda = ROOT / "data" / "ajuda.json"  # canais de ajuda da capa
    if ajuda.exists():
        aj = json.dumps(json.loads(ajuda.read_text(encoding="utf-8")), ensure_ascii=False).replace("</", "<\\/")
        html_src = html_src.replace("<script>", f"<script>window.IAB_AJUDA={aj};</script>\n<script>", 1)
    return html_src.replace("<script>", f"<script>window.IAB_AUTO={js};</script>\n<script>", 1) if auto else html_src


def prerender():
    tmp = ROOT / "ferramentas" / "_pre.json"
    fonte = ROOT / "ferramentas" / "_src.html"
    fonte.write_text(fonte_com_destaques(), encoding="utf-8")
    subprocess.run(["node", str(ROOT / "ferramentas" / "prerender.js"), str(fonte),
                    str(ROOT / "data" / "noticias.json"), str(tmp), D], check=True)
    dados = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.unlink()
    fonte.unlink()
    return dados


def data_de(n):
    """Data ISO (AAAA-MM-DD) da notícia: a dos automáticos, ou deduzida de "13 ago 2026" / "set 2026"."""
    if n.get("iso"):
        return n["iso"][:10]
    m = re.search(r"(\d{1,2})?\s?(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\w*\s+(\d{4})", n.get("date", ""), re.I)
    if m:
        mes = [x[:3] for x in MESES].index(m.group(2).lower()[:3]) + 1
        return f"{m.group(3)}-{mes:02d}-{int(m.group(1) or 15):02d}"
    m = re.search(r"(\d{4})", n.get("date", ""))
    return f"{m.group(1)}-06-30" if m else HOJE.isoformat()


# ============================================================================
# 2. Recursos: imagens WebP, fontes locais, CSS, ícones, og-image
# ============================================================================
CACHE_IMG = ROOT / ".cache" / "img"  # WebP já convertidos (o GitHub Actions guarda entre rodadas)


def imagens():
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    CACHE_IMG.mkdir(parents=True, exist_ok=True)
    dims = {}
    for p in sorted(IMG.glob("*.jpg")):
        destino = OUT / "img" / (p.stem + ".webp")
        chave = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        pronto = CACHE_IMG / f"{p.stem}-{chave}.webp"
        if pronto.exists():  # foto que não mudou: reaproveita a conversão
            shutil.copy2(pronto, destino)
            with Image.open(pronto) as im:
                dims[p.stem] = im.size
            continue
        im = Image.open(p).convert("RGB")
        for q in (78, 70, 62, 55):  # foto muito detalhada: baixa a qualidade até caber em ~220 KB (celular em 4G)
            im.save(destino, "WEBP", quality=q, method=6)
            if destino.stat().st_size <= 220_000:
                break
        else:  # nem assim: reduz para 1280 px de largura (mesma proporção)
            im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
            im.save(destino, "WEBP", quality=70, method=6)
        dims[p.stem] = im.size
        shutil.copy2(destino, pronto)
    for p in IMG.glob("logo*.png"):
        if p.name != "logo-full.png":
            shutil.copy2(p, OUT / "img" / p.name)
    (OUT / "img" / "logos").mkdir()
    for p in [*(IMG / "logos").glob("*.svg"), *(IMG / "logos").glob("*.png")]:  # logotipos (Wikimedia Commons)
        shutil.copy2(p, OUT / "img" / "logos" / p.name)
    return dims


FONTES = Path(__file__).parent / "src" / "fontes"  # cópia local: o build não depende do Google Fonts


def fontes():
    pasta = OUT / "assets" / "fonts"
    pasta.mkdir(parents=True, exist_ok=True)
    if (FONTES / "fontes.css").exists():
        for f in FONTES.glob("*.woff2"):
            shutil.copy2(f, pasta / f.name)
        return (FONTES / "fontes.css").read_text(encoding="utf-8")
    url = ("https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@300;500;700;800;900"
           "&family=Red+Hat+Text:wght@400;500;600&family=Red+Hat+Mono:wght@400&display=swap")
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
    css = urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=30).read().decode()
    FONTES.mkdir(parents=True, exist_ok=True)
    blocos = re.findall(r"/\* ([\w-]+) \*/\s*(@font-face\s*{[^}]+})", css)
    saida = []
    for subset, bloco in blocos:
        m = re.search(r"url\((https://[^)]+\.woff2)\)", bloco)
        if subset not in ("latin", "latin-ext") or not m:  # português
            continue
        fonte = m.group(1)
        nome = hashlib.md5(fonte.encode()).hexdigest()[:10] + ".woff2"
        if not (FONTES / nome).exists():
            (FONTES / nome).write_bytes(urllib.request.urlopen(urllib.request.Request(fonte, headers=ua), timeout=30).read())
        shutil.copy2(FONTES / nome, pasta / nome)
        saida.append(bloco.replace(fonte, "/assets/fonts/" + nome))
    if not saida:
        raise RuntimeError("Google Fonts não devolveu fontes woff2; tente de novo")
    (FONTES / "fontes.css").write_text("\n".join(saida), encoding="utf-8")
    return "\n".join(saida)


ARTIGO_CSS = """
/* ---------- páginas internas (notícias e institucionais) ---------- */
.subnav{display:flex;gap:4px;flex:1;overflow-x:auto;scrollbar-width:none}
.subnav a{padding:8px 12px;font-size:14px;color:var(--text-2);white-space:nowrap}
.subnav a:hover{color:var(--text)}
.art{max-width:880px;margin-inline:auto;padding-block:40px 80px}
.crumbs{font-size:13px;color:var(--text-3);margin-bottom:20px;display:flex;gap:8px;flex-wrap:wrap}
.crumbs a:hover{color:var(--link);text-decoration:underline}
.art h1{font-family:var(--display);font-size:clamp(30px,4vw,48px);font-weight:300;line-height:1.15;letter-spacing:-.02em;margin:14px 0 18px}
.art .lead{font-size:clamp(18px,1.6vw,21px);color:var(--text-2);line-height:1.6}
.ran p{font-size:17px;line-height:1.7;margin:0 0 18px;max-width:70ch}
.share{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 22px}
.share a,.share button{font:600 13.5px var(--font,inherit);padding:8px 14px;border-radius:999px;border:1px solid var(--border-strong,#bbb);background:var(--bg,#fff);color:var(--text,#161616);cursor:pointer;text-decoration:none}
.share a:hover,.share button:hover{border-color:var(--text,#161616)}
.art figure{margin:28px 0}
.art figure img{width:100%;height:auto;border-radius:16px;display:block}
.art figcaption{font-size:12px;color:var(--text-3);margin-top:8px}
.art figcaption a{text-decoration:underline}
.art .rbody{padding:0}
.art aside{margin-top:48px;border-top:2px solid var(--blue);padding-top:20px}
.art aside h2{font-family:var(--display);font-size:22px;font-weight:700;margin-bottom:8px}
.prose h2{font-family:var(--display);font-size:24px;font-weight:700;margin:36px 0 10px}
.prose p,.prose li{font-size:16.5px;line-height:1.7;color:var(--text-2);margin:0 0 12px}
.prose ul{padding-left:20px}
.prose a{color:var(--link);text-decoration:underline}
.pend{background:#FFF1C2;color:#5C4300;padding:1px 6px;border-radius:4px;font-size:.9em}
.lista-noticias{list-style:none;margin:0;padding:0}
.lista-noticias li{padding:16px 0;border-bottom:1px solid var(--border)}
.lista-noticias a{font-family:var(--display);font-size:18px;font-weight:700}
.lista-noticias a:hover{color:var(--link)}
.lista-noticias p{font-size:14.5px;color:var(--text-2);margin-top:4px}
#cookies{position:fixed;left:16px;right:16px;bottom:16px;z-index:70;max-width:640px;margin-inline:auto;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:16px;padding:18px;box-shadow:0 12px 40px rgba(0,0,0,.25);display:flex;flex-direction:column;gap:12px;font-size:14px}
#cookies[hidden]{display:none}
""" + secoes.CSS


def css_site(src_html, css_fontes):
    css = re.search(r"<style>(.*?)</style>", src_html, re.S).group(1)
    css = css_fontes + "\n" + css + ARTIGO_CSS
    h = hashlib.md5(css.encode()).hexdigest()[:10]
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "assets" / f"site.{h}.css").write_text(css, encoding="utf-8")
    return f"/assets/site.{h}.css"


def icones():
    full = Image.open(IMG / "logo-full.png").convert("RGBA")
    ic = full.crop((0, 0, 529, full.height))
    ic = ic.crop(ic.getchannel("A").getbbox())
    lado = max(ic.size)
    sq = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    sq.alpha_composite(ic, ((lado - ic.width) // 2, (lado - ic.height) // 2))
    for s in (16, 32, 180, 192, 512):
        sq.resize((s, s), Image.LANCZOS).save(OUT / f"icon-{s}.png", optimize=True)
    sq.resize((48, 48), Image.LANCZOS).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    shutil.copy2(OUT / "icon-180.png", OUT / "apple-touch-icon.png")
    (OUT / "site.webmanifest").write_text(json.dumps({
        "name": CFG["nome"], "short_name": CFG["nome"], "description": CFG["descricao"], "lang": "pt-BR",
        "start_url": "/", "display": "browser", "theme_color": "#8A3FFC", "background_color": "#FFFFFF",
        "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, ensure_ascii=False, indent=1),
        encoding="utf-8")


def fonte_sis(nome, tam):
    for f in (f"C:/Windows/Fonts/{nome}", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def og_image(nome_arq, foto, titulo, sub):
    cache = IMG / "_og" / (hashlib.md5(f"{foto}|{titulo}|{sub}".encode()).hexdigest()[:12] + ".jpg")
    if cache.exists():
        shutil.copy2(cache, OUT / nome_arq)
        return
    _og_desenhar(nome_arq, foto, titulo, sub)
    cache.parent.mkdir(exist_ok=True)
    shutil.copy2(OUT / nome_arq, cache)


def _og_desenhar(nome_arq, foto, titulo, sub):
    W, H = 1200, 630
    im = Image.open(IMG / f"{foto}.jpg").convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x0, y0, x0 + W, y0 + H)).convert("RGBA")
    sombra = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(sombra)
    for x in range(W):
        d.line([(x, 0), (x, H)], fill=(10, 8, 20, int(230 - 150 * x / W)))
    im = Image.alpha_composite(im, sombra)
    logo = Image.open(IMG / "logo-light-lg.png").convert("RGBA")
    logo = logo.resize((round(logo.width * 96 / logo.height), 96), Image.LANCZOS)
    im.alpha_composite(logo, (64, 60))
    d = ImageDraw.Draw(im)
    f1, f2 = fonte_sis("segoeuil.ttf", 58), fonte_sis("segoeui.ttf", 28)
    linhas, atual = [], ""
    for p in titulo.split():
        if atual and d.textlength(atual + " " + p, font=f1) > 900:
            linhas.append(atual)
            atual = p
        else:
            atual = (atual + " " + p).strip()
    linhas.append(atual)
    y = 250
    for ln in linhas[:3]:
        d.text((64, y), ln, font=f1, fill=(255, 255, 255))
        y += 70
    d.rectangle([64, H - 84, 160, H - 80], fill=(138, 63, 252))
    d.text((64, H - 70), sub, font=f2, fill=(214, 190, 255))
    im.convert("RGB").save(OUT / nome_arq, "JPEG", quality=86, optimize=True)


# ============================================================================
# 3. HTML: cabeçalho, JSON-LD e ajustes do corpo
# ============================================================================
def head(titulo, desc, caminho, css, og="/og-image.jpg", og_dim=(1200, 630), tipo="website", jsonld=None, extra="", robots="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"):
    url = D + caminho
    v = []
    if ok(CFG["google_site_verification"]):
        v.append(f'<meta name="google-site-verification" content="{esc(CFG["google_site_verification"])}">')
    if ok(CFG["bing_site_verification"]):
        v.append(f'<meta name="msvalidate.01" content="{esc(CFG["bing_site_verification"])}">')
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="pt-BR" data-pre>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="{robots}">
<meta property="og:type" content="{tipo}">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="{esc(CFG['nome'])}">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{D}{og}">
<meta property="og:image:width" content="{og_dim[0]}">
<meta property="og:image:height" content="{og_dim[1]}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#8A3FFC">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/icon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="{esc(CFG['nome'])}" href="/feed.xml">
{chr(10).join(v)}
<link rel="stylesheet" href="{css}">
{extra}
{ld}
</head>
<body>
"""


def org_ld():
    o = {"@type": "NewsMediaOrganization", "@id": D + "/#org", "name": CFG["nome"], "url": D + "/",
         "slogan": CFG["slogan"], "description": CFG["descricao"],
         "logo": {"@type": "ImageObject", "url": D + "/img/logo-lg.png", "width": 338, "height": 128},
         "publishingPrinciples": D + "/sobre/", "correctionsPolicy": D + "/sobre/#correcoes",
         "ethicsPolicy": D + "/sobre/#principios", "actionableFeedbackPolicy": D + "/sobre/#correcoes",
         "areaServed": {"@type": "Country", "name": "Brasil"},
         "knowsAbout": ["Violência contra a mulher", "Lei Maria da Penha (Lei 11.340/2006)", "Feminicídio", "Medidas protetivas de urgência",
                        "Estatuto da Criança e do Adolescente (Lei 8.069/1990)", "Violência sexual contra crianças e adolescentes",
                        "Casa da Mulher Brasileira", "Ligue 180", "Disque 100", "Violência digital", "Igualdade de gênero",
                        "Rede de proteção", "Políticas públicas para mulheres"]}
    if CFG["redes"]:
        o["sameAs"] = CFG["redes"]
    if ok(CFG["email_redacao"]):
        o["email"] = CFG["email_redacao"]
    if ok(CFG["razao_social"]):
        o["legalName"] = CFG["razao_social"]
    if ok(CFG["cnpj"]):
        o["taxID"] = CFG["cnpj"]
    if ok(CFG["endereco"]):
        o["address"] = CFG["endereco"]
    return o


def site_ld():
    return {"@type": "WebSite", "@id": D + "/#website", "url": D + "/", "name": CFG["nome"],
            "description": CFG["descricao"], "inLanguage": "pt-BR", "publisher": {"@id": D + "/#org"}}


def migalhas(itens):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": D + u} for i, (n, u) in enumerate(itens)]}


SLUGIFY_JS = ('  function slugify(t){return t.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase()'
              '.replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,80).replace(/-+$/,"");}\n')


def ajustar_corpo(body, mapa_slug):
    # o que vai para o <head>: título, metas, fontes e estilo inline
    body = re.sub(r"<title>.*?</title>", "", body, count=1, flags=re.S)
    body = re.sub(r"<style>.*?</style>", "", body, count=1, flags=re.S)
    body = re.sub(r'<meta name="(?:claude:[^"]+|description)"[^>]*>\s*', "", body)
    body = re.sub(r'<link rel="(?:preconnect|stylesheet)"[^>]*>\s*', "", body)
    # caminhos absolutos (funcionam em /norte/, /noticias/...) e JPEG -> WebP
    body = re.sub(r'(src|srcset)="img/', r'\1="/img/', body)
    body = body.replace(", img/logo", ", /img/logo").replace("'img/'+", "'/img/'+")
    body = re.sub(r"(/img/[\w-]+)\.jpg", r"\1.webp", body)
    body = body.replace("+'.jpg", "+'.webp")
    body = body.replace('fetch("data/noticias.json")', 'fetch("/data/noticias.json")')
    # cartões que abrem o leitor viram links reais para a página da notícia (robôs seguem links)
    def link(m):
        abre, nid, miolo = m.group(1), m.group(2), m.group(3)
        if nid not in mapa_slug:
            return m.group(0)
        abre = abre.replace("<button", f'<a href="/noticias/{mapa_slug[nid]}/"', 1).replace(' type="button"', "")
        return abre + miolo + "</a>"
    body = re.sub(r'(<button[^>]*data-open="(\w+)"[^>]*>)(.*?)</button>', link, body, flags=re.S)
    # leitor ganha botão para a página permanente da notícia
    body = body.replace("  var NEW=' target=\"_blank\" rel=\"noopener\"';\n", "  var NEW=' target=\"_blank\" rel=\"noopener\"';\n" + SLUGIFY_JS, 1)
    body = body.replace("'<div class=\"btns\"><a class=\"btn ghost\" href=\"#'+d.id+'\" data-close>",
                        "'<div class=\"btns\"><a class=\"btn\" href=\"/noticias/'+slugify(n.h)+'/\">Página da notícia '+ARROW+'</a><a class=\"btn ghost\" href=\"#'+d.id+'\" data-close>")
    return body


def medicao():
    """Só com GA4 no CFG: aviso de cookies (LGPD) e carregamento após o aceite."""
    if not ok(CFG["ga4"]):
        return ""
    gid = esc(CFG["ga4"])
    return f"""<div id="cookies" hidden role="dialog" aria-label="Preferências de cookies">
<p>Usamos cookies para melhorar sua experiência e entender como o site é usado. Você pode aceitar ou recusar. Saiba mais na <a href="/privacidade/">Política de Privacidade</a>.</p>
<div class="btns"><button class="btn" type="button" id="ckSim">Aceitar cookies</button><button class="btn ghost" type="button" id="ckNao">Recusar</button></div></div>
<script>
(function(){{var k="iab-consent",v=null;try{{v=localStorage.getItem(k)}}catch(e){{}}
function load(){{var s=document.createElement("script");s.async=1;s.src="https://www.googletagmanager.com/gtag/js?id={gid}";document.head.appendChild(s);
window.dataLayer=window.dataLayer||[];function g(){{dataLayer.push(arguments)}}window.gtag=g;g("js",new Date());
g("consent","default",{{ad_storage:"denied",ad_user_data:"denied",ad_personalization:"denied",analytics_storage:"granted"}});g("config","{gid}");}}
if(v==="sim")load();else if(v!=="nao")document.getElementById("cookies").hidden=false;
function set(x){{try{{localStorage.setItem(k,x)}}catch(e){{}}document.getElementById("cookies").hidden=true;if(x==="sim")load();}}
document.getElementById("ckSim").onclick=function(){{set("sim")}};document.getElementById("ckNao").onclick=function(){{set("nao")}};}})();
</script>"""


# "Ouvir": lê a página em voz alta com a voz do próprio navegador (Web Speech API), sem serviço externo
OUVIR = """<script>(function(){var bs=document.querySelectorAll("[data-ouvir]");if(!bs.length||!("speechSynthesis" in window))return;
var lang=document.documentElement.lang||"pt-BR",fala=false;
function texto(){var m=document.querySelector("main");if(!m)return "";var out=[];
m.querySelectorAll("h1,h2,h3,p,li").forEach(function(e){if(e.closest(".share,.crumbs,nav,.dados-nav,figcaption"))return;
var t=e.innerText.trim();if(t&&!/^(Fontes?|Sources?):/.test(t))out.push(t);});return out.join(". ");}
function parar(){speechSynthesis.cancel();fala=false;bs.forEach(function(b){b.textContent=b.getAttribute("data-ouvir")||"▶ Ouvir";});}
bs.forEach(function(b){b.hidden=false;b.addEventListener("click",function(){if(fala){parar();return;}
var partes=texto().match(/[^.!?]+[.!?]*/g)||[];speechSynthesis.cancel();
partes.forEach(function(p,i){var u=new SpeechSynthesisUtterance(p);u.lang=lang;u.rate=1.05;if(i===partes.length-1)u.onend=parar;speechSynthesis.speak(u);});
fala=true;bs.forEach(function(x){x.textContent="■ Parar";});});});
window.addEventListener("pagehide",parar);})();</script>"""
# fundo animado em rede (pontos e conexões em roxo, pulsos azuis) para todo canvas.techbg da página
REDE = """<script>(function(){var red=window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches;
document.querySelectorAll("canvas.techbg").forEach(function(cv){var ctx=cv.getContext&&cv.getContext("2d");if(!ctx)return;
var W,H,P=[],pulses=[],vis=false,dpr=Math.min(2,window.devicePixelRatio||1);
function size(){W=cv.clientWidth;H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
var n=Math.round(Math.min(90,W*H/9000));P=[];for(var i=0;i<n;i++)P.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.18,vy:(Math.random()-.5)*.18});}
function frame(){ctx.clearRect(0,0,W,H);var L=130;
for(var i=0;i<P.length;i++){var a=P[i];a.x+=a.vx;a.y+=a.vy;if(a.x<0||a.x>W)a.vx*=-1;if(a.y<0||a.y>H)a.vy*=-1;
for(var j=i+1;j<P.length;j++){var b=P[j],dx=a.x-b.x,dy=a.y-b.y,d=Math.sqrt(dx*dx+dy*dy);
if(d<L){ctx.strokeStyle="rgba(190,149,255,"+(0.16*(1-d/L))+")";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}}}
ctx.fillStyle="rgba(212,187,255,.55)";P.forEach(function(a){ctx.fillRect(a.x-1,a.y-1,2,2);});
if(Math.random()<.04&&P.length>1){pulses.push({a:P[Math.random()*P.length|0],b:P[Math.random()*P.length|0],t:0});}
pulses=pulses.filter(function(q){q.t+=.012;var x=q.a.x+(q.b.x-q.a.x)*q.t,y=q.a.y+(q.b.y-q.a.y)*q.t;
ctx.fillStyle="rgba(69,137,255,"+(1-q.t)+")";ctx.beginPath();ctx.arc(x,y,2.2,0,6.29);ctx.fill();return q.t<1;});
if(vis&&!red)requestAnimationFrame(frame);}
size();window.addEventListener("resize",size);
if("IntersectionObserver" in window){new IntersectionObserver(function(es){var v=es[0].isIntersecting;if(v&&!vis){vis=true;frame();}else vis=v;}).observe(cv);}
else{vis=true;frame();}
if(red){vis=true;frame();vis=false;}});})();</script>"""
FIM = "\n" + OUVIR + "\n" + REDE + "\n</body>\n</html>\n"


# ============================================================================
# 4. Páginas internas
# ============================================================================

def topo_sub(ed):
    links = "".join(f'<a href="/#{d["id"]}">{esc(d["tag"])}</a>' for d in ed)
    n = esc(CFG["nome"])
    return f"""<header class="mast"><div class="wrap">
<a class="brand" href="/" aria-label="{n}, início"><img class="logo-img lg-on-light" src="/img/logo.png" srcset="/img/logo.png 1x, /img/logo-lg.png 2x" width="127" height="48" alt="{n}"><img class="logo-img lg-on-dark" src="/img/logo-light.png" srcset="/img/logo-light.png 1x, /img/logo-light-lg.png 2x" width="127" height="48" alt="{n}"></a>
<nav class="subnav" aria-label="Editorias">{links}<a href="/noticias/">Todas as notícias</a><a href="/#radar">Radar</a></nav>
<a class="btn" href="/ajuda/">Buscar ajuda</a></div></header>"""


def credito_html(cr, lic, k):
    c = cr.get(k)
    if not c:
        return ""
    l = f'<a href="{esc(lic[c[1]])}" rel="noopener">{esc(c[1])}</a>' if c[1] in lic else esc(c[1])
    return f'Foto: <a href="{esc(c[2])}" rel="noopener">{esc(c[0])}</a> / {l}, via Wikimedia Commons'


def pagina_noticia(n, dados, mapa, css, topo, rodape, dims):
    ed = {d["k"]: d for d in dados["ED"]}[n["e"]]
    x = dados["X"].get(n["id"], {})
    url = f"/noticias/{mapa[n['id']]}/"
    titulo = n["h"]
    desc = (n["t"][:155].rsplit(" ", 1)[0] + "…") if len(n["t"]) > 158 else n["t"]
    w, h = dims.get(n["img"], (1100, 733))
    b = []
    if x.get("k"):
        b.append('<div class="rk">' + "".join(f'<div><b>{esc(a)}</b><span>{esc(c)}</span></div>' for a, c in x["k"]) + "</div>")
    if x.get("bl"):
        b.append('<h2 class="rh">Pontos principais</h2><ul class="rbl">' + "".join(f"<li>{esc(i)}</li>" for i in x["bl"]) + "</ul>")
    if x.get("of"):
        o = x["of"]
        b.append('<div class="rof"><span class="rh">Na fonte oficial</span>' + (f'<blockquote>“{esc(o["q"])}…”</blockquote>' if o.get("q") else "")
                 + f'<p>{esc(o.get("extra", ""))}</p><a class="lnkp" href="{esc(o["u"])}" rel="noopener">{esc(o["ref"])}</a></div>')
    if x.get("tl"):
        b.append('<h2 class="rh">Linha do tempo</h2><ol class="rtl">' + "".join(f"<li><b>{esc(a)}</b><span>{esc(c)}</span></li>" for a, c in x["tl"]) + "</ol>")
    if x.get("nx"):
        b.append(f'<div class="rnx"><b>O que observar</b>{esc(x["nx"])}</div>')
    fontes_html = "".join(f'<a href="{esc(u)}" rel="noopener">{esc(nm)}</a>' for nm, u in n["s"])
    nota = ("Resumo e análise próprios do " + esc(CFG["nome"]) + ", escritos com apoio de IA a partir das fontes acima e publicados pela curadoria automática do portal."
            if n.get("auto") and n.get("w") else
            "Destaque selecionado pela curadoria automática do " + esc(CFG["nome"]) + ". O título e o conteúdo pertencem ao veículo de origem."
            if n.get("auto") else
            "Resumo e análise próprios do " + esc(CFG["nome"]) + ". Trechos de atos oficiais reproduzidos com base no art. 8º, IV, da Lei 9.610/98.")
    rel = [m for m in dados["N"] if m["e"] == n["e"] and m["id"] != n["id"]][:5]
    rel_html = "".join(f'<li><a href="/noticias/{mapa[m["id"]]}/">{esc(m["h"])}</a></li>' for m in rel)
    ld = {"@context": "https://schema.org", "@graph": [org_ld(), site_ld(), {
        "@type": "NewsArticle", "@id": D + url + "#artigo", "headline": titulo[:110], "description": desc,
        "image": [D + f"/img/{n['img']}.webp"], "datePublished": data_de(n), "dateModified": data_de(n),
        "author": {"@type": "Organization", "name": "Redação " + CFG["nome"], "url": D + "/sobre/"},
        "publisher": {"@id": D + "/#org"}, "mainEntityOfPage": D + url, "isPartOf": {"@id": D + "/#website"},
        "articleSection": (ed.get("h") or ed["name"]), "inLanguage": "pt-BR", "isAccessibleForFree": True,
        "citation": [u for _, u in n["s"]]},
        migalhas([("Início", "/"), ((ed.get("h") or ed["name"]), "/#" + ed["id"]), (titulo, url)])]}
    corte = esc(titulo[:60]) + ("…" if len(titulo) > 60 else "")
    data_html = f'<span class="when">{esc(n["date"])}</span>' if n.get("date") else ""
    why = f'<div class="why"><b>Por que importa</b>{esc(n["w"])}</div>' if n.get("w") else ""
    analise = '<div class="ran">' + "".join(f"<p>{esc(p)}</p>" for p in n["a"]) + "</div>" if n.get("a") else ""
    aside = f'<aside><h2>Mais em {esc(ed["tag"])}</h2><ul class="lista-noticias">{rel_html}</ul></aside>' if rel_html else ""
    titulo_tag = titulo if len(titulo) > 48 else f"{titulo} | {CFG['nome']}"
    return (head(titulo_tag, desc, url, css, og=f"/img/{n['img']}.webp", og_dim=(w, h), tipo="article", jsonld=ld)
            + f"""<div class="sub">{topo}
<main class="wrap art" data-pagefind-body>
<nav class="crumbs" aria-label="Você está em"><a href="/">Início</a>›<a href="/#{ed['id']}">{esc(ed['tag'])}</a>›<span>{corte}</span></nav>
<article>
<div class="meta"><span class="tag solid" style="--c:var({ed['c']})">{esc(ed['tag'])}</span>{data_html}</div>
<h1>{esc(titulo)}</h1>
<p class="lead">{esc(n['t'])}</p>
{compartilhar(D + url, titulo)}
<figure><img src="/img/{n['img']}.webp" width="{w}" height="{h}" alt="" fetchpriority="high"><figcaption>{credito_html(dados['CR'], dados['LIC'], n['img'])}</figcaption></figure>
<div class="rbody">
{analise}
{why}
{''.join(b)}
<h2 class="rh">Leia nas fontes originais</h2><div class="rsrc">{fontes_html}</div>
<p class="rlegal">{nota} Para o texto completo, acesse os veículos acima.</p>
<div class="why"><b>Precisa de ajuda?</b>Em perigo agora, ligue 190. Violência contra a mulher: Ligue 180 (24 horas, gratuito). Crianças e adolescentes: Disque 100. <a href="/ajuda/">Veja todos os canais</a>.</div>
</div>
</article>
{aside}
</main>
{rodape}</div>
<script>document.addEventListener("click",function(e){{var b=e.target.closest("[data-copy]");if(!b)return;
navigator.clipboard&&navigator.clipboard.writeText(b.getAttribute("data-copy")).then(function(){{b.textContent="Link copiado";}});}});</script>
{medicao()}""" + FIM)


def pagina_simples(caminho, titulo, desc, corpo, css, topo, rodape, crumbs, robots=None, largo=False, ld_extra=None, fundo=None):
    ld = {"@context": "https://schema.org", "@graph": [org_ld(), site_ld(),
          {"@type": "WebPage", "@id": D + caminho, "url": D + caminho, "name": titulo, "description": desc,
           "isPartOf": {"@id": D + "/#website"}, "inLanguage": "pt-BR", "dateModified": HOJE.isoformat()},
          migalhas(crumbs)] + (ld_extra or [])}
    nav = "›".join(f'<a href="{u}">{esc(n)}</a>' for n, u in crumbs[:-1]) + f"›<span>{esc(crumbs[-1][0])}</span>"
    kw = {"robots": robots} if robots else {}
    return (head(f"{titulo} | {CFG['nome']}", desc, caminho, css, jsonld=ld, **kw)
            + f"""<div class="sub">{topo}
{f'<div class="{fundo} pagina-fundo"><canvas class="techbg" aria-hidden="true"></canvas>' if fundo else ''}<main class="wrap art prose{' largo' if largo else ''}" data-pagefind-body><nav class="crumbs" aria-label="Você está em">{nav}</nav>
<h1>{esc(titulo)}</h1>
{corpo}
</main>{'</div>' if fundo else ''}
{rodape}</div>
{medicao()}""" + FIM)


def p(v, rotulo):
    return esc(v) if ok(v) else f'<span class="pend">{rotulo}</span>'


def corpo_privacidade():
    medir = ('<li><b>Medição de audiência.</b> Google Analytics 4, carregado só depois do seu aceite no aviso de cookies. '
             'Base legal: consentimento (art. 7º, I).</li>' if ok(CFG["ga4"]) else
             '<li><b>Medição de audiência.</b> Hoje o site não usa cookies nem ferramentas de rastreamento. Se isso mudar, '
             'você verá um aviso pedindo consentimento antes de qualquer coleta.</li>')
    return f"""<p class="lead">Como o {esc(CFG['nome'])} trata dados pessoais, conforme a Lei Geral de Proteção de Dados (Lei 13.709/2018, LGPD). Última atualização: {HOJE.strftime('%d/%m/%Y')}.</p>
<h2>1. Quem é o controlador</h2>
<p>{p(CFG['razao_social'], 'razão social a preencher')}, CNPJ {p(CFG['cnpj'], 'a preencher')}, responsável pelo portal {esc(HOST)}.</p>
<p>Encarregado pelo tratamento de dados pessoais (art. 41): {p(CFG['encarregado_nome'], 'nome a preencher')}, pelo e-mail {p(CFG['email_privacidade'], 'e-mail a preencher')}.</p>
<h2>2. Que dados tratamos e por quê</h2>
<ul>
<li><b>Registros de acesso.</b> Endereço IP, data e hora de acesso, guardados pelo provedor de hospedagem. Finalidade: segurança e cumprimento do Marco Civil da Internet (Lei 12.965/2014, art. 15), que obriga a manter esses registros por 6 meses. Base legal: cumprimento de obrigação legal (art. 7º, II).</li>
<li><b>Preferência de região.</b> Ao escolher uma edição regional, o site guarda essa escolha no armazenamento local do seu próprio navegador (localStorage). Esse dado não é enviado a nós nem a terceiros e pode ser apagado limpando os dados do site no navegador.</li>
{medir}
</ul>
<p>Na navegação, o site não carrega fontes, imagens ou scripts de servidores de terceiros: tudo é servido pelo próprio domínio. Os links para veículos externos levam a sites com políticas próprias.</p>
<h2>3. Com quem compartilhamos</h2>
<p>Só com operadores que nos ajudam a prestar o serviço: o provedor de hospedagem e, se você aceitar os cookies, o Google Analytics. Não vendemos dados. Se algum operador armazenar dados fora do Brasil, a transferência segue o art. 33 da LGPD.</p>
<h2>4. Por quanto tempo guardamos</h2>
<p>Registros de acesso: 6 meses, conforme o Marco Civil da Internet. Dados de medição de audiência: pelo prazo configurado no Google Analytics.</p>
<h2>5. Seus direitos</h2>
<p>Pelo art. 18 da LGPD, você pode pedir: confirmação de que tratamos seus dados, acesso, correção, anonimização, bloqueio ou eliminação de dados desnecessários, portabilidade, informação sobre compartilhamento, revogação do consentimento e eliminação dos dados tratados com base nele. Envie o pedido para {p(CFG['email_privacidade'], 'e-mail do encarregado a preencher')}. Você também pode reclamar à Autoridade Nacional de Proteção de Dados (ANPD), em <a href="https://www.gov.br/anpd" rel="noopener">gov.br/anpd</a>.</p>
<h2>6. Segurança</h2>
<p>O site é servido só por HTTPS, com cabeçalhos de segurança, e não tem formulários que coletem dados pessoais.</p>
<h2>7. Crianças e adolescentes</h2>
<p>O portal é informativo, não tem cadastro e não coleta intencionalmente dados de menores de 18 anos. As notícias não identificam crianças e adolescentes vítimas de violência (ECA, arts. 17 e 143).</p>
<h2>8. Mudanças nesta política</h2>
<p>Quando esta política mudar, a data no topo será atualizada, e mudanças relevantes serão avisadas no site.</p>"""


def corpo_termos():
    return f"""<p class="lead">Regras de uso do portal {esc(CFG['nome'])} ({esc(HOST)}). Última atualização: {HOJE.strftime('%d/%m/%Y')}.</p>
<h2>1. O que é o portal</h2><p>Um observatório jornalístico sobre a defesa de mulheres e crianças no Brasil, com notícias resumidas e analisadas pela redação, links para as fontes originais, dados, canais de ajuda e uma base de notícias coletadas automaticamente de fontes públicas.</p>
<h2>2. Conteúdo próprio</h2><p>Textos, análises e o desenho do portal pertencem ao {esc(CFG['nome'])}. Você pode citar trechos com crédito e link para a página original. A reprodução integral depende de autorização.</p>
<h2>3. Conteúdo de terceiros</h2><p>Títulos e links do Radar da rede levam a matérias de outros veículos, que são titulares desse conteúdo. As fotos vêm do Wikimedia Commons e são usadas conforme as licenças indicadas em <a href="/creditos/">Créditos das imagens</a>. Atos oficiais, como leis, projetos e resoluções, não têm proteção autoral (Lei 9.610/98, art. 8º, IV).</p>
<h2>4. Não substitui atendimento</h2><p>O conteúdo é informativo. Nada aqui substitui orientação jurídica, atendimento de saúde ou os serviços de proteção. Em perigo, ligue 190; para orientação sobre violência contra a mulher, Ligue 180; para crianças e adolescentes, Disque 100.</p>
<h2>5. Correções e remoção</h2><p>Erros e pedidos de remoção podem ser enviados para {p(CFG['email_redacao'], 'e-mail da redação a preencher')}. Veja a <a href="/sobre/#correcoes">política de correções</a>.</p>
<h2>6. Privacidade</h2><p>O tratamento de dados pessoais segue a <a href="/privacidade/">Política de Privacidade</a>.</p>
<h2>7. Lei e foro</h2><p>Valem as leis brasileiras. Fica eleito o foro de {p(CFG['foro'], 'cidade/UF a preencher')}, ressalvado o direito do consumidor de demandar no próprio domicílio.</p>"""


def corpo_sobre():
    n_fontes = len(json.loads((ROOT / "data" / "fontes.json").read_text(encoding="utf-8")))
    contato = ""
    if ok(CFG["email_redacao"]):  # sem e-mail definido, a seção não aparece
        contato = f"<h2>Contato</h2><p>Redação, correções e sugestões de pauta: {esc(CFG['email_redacao'])}.</p>"
    return f'''<p class="lead">O {esc(CFG['nome'])} é um observatório aberto de notícias e dados sobre a defesa de mulheres e crianças no Brasil. Reunimos, num só lugar e de hora em hora, o que governos, Justiça, Ministério Público, Defensorias, polícias, pesquisadores, organizações da sociedade civil e a imprensa de todas as regiões publicam sobre violência contra a mulher, leis de proteção, rede de amparo e proteção da infância, sempre com a fonte original.</p>
<h2 id="missao">Nossa missão</h2>
<p>Informar para proteger. Acreditamos que informação clara e confiável salva vidas: ajuda quem sofre violência a conhecer seus direitos e os caminhos de ajuda, ajuda quem está perto a agir e ajuda gestores, legisladores e a sociedade a cobrar e construir políticas que funcionem.</p>
<p>Por isso o portal acompanha as leis e sua aplicação, os números da violência, os programas públicos, as decisões da Justiça e as iniciativas que dão resultado, em todo o país e não só nas capitais.</p>
<h2>O que você encontra aqui</h2>
<ul>
<li><b>Onde buscar ajuda.</b> <a href="/ajuda/">Canais de emergência, serviços e organizações</a>, com contatos conferidos nas fontes oficiais.</li>
<li><b>Repositório de notícias.</b> Mais de {n_fontes // 10 * 10} fontes acompanhadas automaticamente, com busca, filtros por editoria e região e arquivo mês a mês. Cada título leva à matéria no veículo que a publicou.</li>
<li><b>Destaques com análise.</b> As notícias mais relevantes ganham resumo próprio, contexto e o que muda para mulheres, crianças e a rede de proteção.</li>
<li><b>Dez editorias.</b> Política, trabalho e renda, sociedade, violência digital, infância, leis e Justiça, saúde, segurança, amparo e diversidade, além de edições para cada região do país.</li>
<li><b>Dados e guias.</b> <a href="/leis/">Leis</a>, <a href="/programas/">programas e recursos</a>, <a href="/decisoes/">decisões da Justiça</a>, <a href="/iniciativas/">iniciativas</a>, <a href="/instituicoes/">quem protege</a>, <a href="/indicadores/">indicadores</a>, <a href="/eventos/">agenda</a>, <a href="/guias/">guias práticos</a> e <a href="/glossario/">glossário</a>.</li>
</ul>
<h2>Para quem</h2>
<p>Para mulheres, mães, pais e cuidadores, educadores, profissionais de saúde, assistência social, segurança e Justiça, gestores públicos, empresas, pesquisadores, jornalistas e organizações da sociedade civil, e para quem quer acompanhar o tema com fontes confiáveis.</p>
<h2 id="principios">Como trabalhamos</h2>
<ul><li><b>Fonte em toda notícia.</b> Cada item traz link para o documento original ou para a reportagem citada.</li>
<li><b>Proteção das vítimas.</b> Não identificamos vítimas de violência sexual nem crianças e adolescentes, não usamos fotos de pessoas, evitamos detalhes gráficos e não tratamos violência como "crime passional".</li>
<li><b>Texto próprio.</b> Resumos e análises são escritos com nossas palavras; não reproduzimos matérias de outros veículos e respeitamos quem não autoriza robôs de IA.</li>
<li><b>Uso de IA declarado.</b> A coleta, a classificação, os resumos dos destaques e a extração de dados são feitos com apoio de inteligência artificial, sob regras editoriais públicas, e cada texto avisa quando foi escrito com IA.</li>
<li><b>Independência.</b> Notícia, análise e qualquer conteúdo patrocinado ficam sempre separados e identificados.</li></ul>
<h2 id="correcoes">Correções</h2>
<p>Corrigimos erros assim que confirmados e indicamos o que mudou. Pedidos de correção ou de remoção são atendidos com prioridade.</p>
<h2>Fotos e marcas</h2>
<p>As fotos vêm do Wikimedia Commons, sob licenças livres, com autores e licenças em <a href="/creditos/">créditos das fotos</a>. Mostram lugares e instituições, nunca pessoas.</p>
{contato}'''


def corpo_creditos(cr, lic):
    vistos, linhas = set(), []
    for k, c in cr.items():
        if k.startswith("s-") or tuple(c) in vistos:
            continue
        vistos.add(tuple(c))
        l = f'<a href="{esc(lic[c[1]])}" rel="noopener">{esc(c[1])}</a>' if c[1] in lic else esc(c[1])
        linhas.append(f'<li><a href="{esc(c[2])}" rel="noopener">{esc(c[0])}</a> · {l}</li>')
    arq_logos = IMG / "logos" / "logos.json"
    logos = json.loads(arq_logos.read_text(encoding="utf-8")) if arq_logos.exists() else {}
    linhas_logos = "".join(f'<li>{esc(k)} · <a href="{esc(v["origem"])}" rel="noopener">arquivo no Wikimedia Commons</a> ({esc(v["licenca"])})</li>'
                           for k, v in logos.items())
    return ('<p class="lead">As fotos do portal vêm do Wikimedia Commons e são usadas conforme as licenças livres de cada autor. '
            'Mostram lugares e instituições, nunca pessoas. Foram redimensionadas, comprimidas e recortadas para exibição. '
            'O logotipo é propriedade do ' + esc(CFG["nome"]) + '.</p><ul>'
            + "".join(linhas) + "</ul>"
            + ('<h2>Logotipos</h2><p>Os logotipos são marcas de seus titulares, usados só para identificar as instituições citadas nas notícias. '
               'Não indicam patrocínio nem parceria com o ' + esc(CFG["nome"]) + '.</p><ul>' + linhas_logos + "</ul>" if linhas_logos else ""))


# ============================================================================
# 5. Arquivos de descoberta
# ============================================================================
BUSCA_IA = ["OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Perplexity-User", "Claude-SearchBot",
            "Claude-User", "Applebot", "DuckAssistBot", "Googlebot", "Bingbot"]
TREINO_IA = ["GPTBot", "ClaudeBot", "anthropic-ai", "CCBot", "Google-Extended", "Applebot-Extended",
             "meta-externalagent", "Bytespider", "cohere-ai"]
RASPADORES = ["AhrefsBot", "SemrushBot", "MJ12bot", "DotBot", "DataForSeoBot", "BLEXBot"]


def robots():
    t = [f"# robots.txt · {CFG['nome']}", "User-agent: *", "Allow: /", "",
         "# Buscadores e assistentes de IA que citam fontes e trazem visitas: liberados"]
    for b in BUSCA_IA:
        t += [f"User-agent: {b}", "Allow: /", ""]
    t.append("# Robôs de TREINO de IA: " + ("liberados" if CFG["permitir_treino_ia"] else
             "bloqueados por padrão (decisão do dono: mude permitir_treino_ia no gerador)"))
    for b in TREINO_IA:
        t += [f"User-agent: {b}", "Allow: /" if CFG["permitir_treino_ia"] else "Disallow: /", ""]
    t.append("# Raspadores comerciais de SEO: consomem banda sem trazer leitores")
    for b in RASPADORES:
        t += [f"User-agent: {b}", "Disallow: /", ""]
    t.append(f"Sitemap: {D}/sitemap.xml")
    t.append(f"Sitemap: {D}/sitemap-noticias.xml")
    return "\n".join(t) + "\n"


def compartilhar(link, titulo):
    """Botões de compartilhar (sem script de terceiros: só links) + copiar link."""
    t, u = quote(f"{titulo} {link}", safe=""), quote(link, safe="")
    return ('<div class="share" aria-label="Compartilhar">'
            f'<a href="https://wa.me/?text={t}" rel="noopener" target="_blank">WhatsApp</a>'
            f'<a href="https://www.linkedin.com/sharing/share-offsite/?url={u}" rel="noopener" target="_blank">LinkedIn</a>'
            f'<a href="mailto:?subject={quote(titulo)}&amp;body={u}">E-mail</a>'
            f'<button type="button" data-copy="{esc(link)}">Copiar link</button>'
            '<button type="button" data-ouvir="▶ Ouvir" hidden>▶ Ouvir</button>'
            + (f'<a href="{esc(CFG["whatsapp_canal"])}" rel="noopener" target="_blank">Siga no WhatsApp</a>' if ok(CFG["whatsapp_canal"]) else "")
            + '</div>')


def sitemap_noticias(noticias, mapa):
    """Sitemap do Google News: só as notícias das últimas 48 horas."""
    corte = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">']
    for n in noticias:
        if n.get("iso", "") < corte:
            continue
        linhas.append(f"  <url><loc>{D}/noticias/{mapa[n['id']]}/</loc><news:news><news:publication>"
                      f"<news:name>{esc(CFG['nome'])}</news:name><news:language>pt</news:language></news:publication>"
                      f"<news:publication_date>{n['iso']}</news:publication_date><news:title>{esc(n['h'])}</news:title>"
                      "</news:news></url>")
    return "\n".join(linhas + ["</urlset>"]) + "\n"


def sitemap(urls):
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for item in urls:
        u, prio, img = item[:3]
        quando = item[3] if len(item) > 3 else HOJE.isoformat()
        linhas.append(f"  <url><loc>{D}{u}</loc><lastmod>{quando}</lastmod><priority>{prio}</priority>"
                      + (f"<image:image><image:loc>{D}{img}</image:loc></image:image>" if img else "") + "</url>")
    return "\n".join(linhas + ["</urlset>"]) + "\n"


def rss(noticias, mapa, edk):
    agora = format_datetime(datetime.now(timezone.utc))

    def pub(n):
        return format_datetime(datetime.fromisoformat(data_de(n)).replace(hour=12, tzinfo=timezone.utc))
    itens = "".join(
        f"<item><title>{esc(n['h'])}</title><link>{D}/noticias/{mapa[n['id']]}/</link><guid>{D}/noticias/{mapa[n['id']]}/</guid>"
        f"<category>{esc(edk[n['e']]['tag'])}</category><description>{esc(n['t'])}</description><pubDate>{pub(n)}</pubDate></item>"
        for n in noticias)
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{esc(CFG["nome"])}</title>'
            f"<link>{D}/</link><description>{esc(CFG['descricao'])}</description><language>pt-BR</language>"
            f"<lastBuildDate>{agora}</lastBuildDate>{itens}</channel></rss>\n")


REGIOES = [("norte", "Norte", "r-norte"), ("nordeste", "Nordeste", "r-nordeste"), ("centro-oeste", "Centro-Oeste", "r-co"),
           ("sudeste", "Sudeste", "s-leis"), ("sul", "Sul", "r-sul")]


def llms(dados, mapa, faq):
    t = [f"# {CFG['nome']}", "", f"> {CFG['descricao']}", "",
         f"Site: {D}/ · Idioma: português do Brasil · Atualizado em {HOJE.strftime('%d/%m/%Y')}.",
         "Cada notícia é um resumo próprio da redação, com links para as fontes originais.",
         "Em perigo no Brasil: ligue 190. Violência contra a mulher: Ligue 180. Crianças e adolescentes: Disque 100.", "", "## Editorias"]
    t += [f"- [{d['tag']} · {d['name']}]({D}/#{d['id']}): {d['desc']}" for d in dados["ED"]]
    t += ["", "## Edições regionais"] + [f"- [Edição {nm}]({D}/{s}/)" for s, nm, _ in REGIOES]
    t += ["", "## Notícias"] + [f"- [{n['h']}]({D}/noticias/{mapa[n['id']]}/): {n['t'].split('. ')[0]}." for n in dados["N"]]
    t += ["", "## Repositório de notícias", f"- [Arquivo completo, mês a mês]({D}/arquivo/): todas as notícias coletadas sobre a proteção de mulheres e crianças no Brasil, com fonte e link para o original."]
    t += ["", "## Dados e guias"] + [f"- [{nome}]({D}{u})" for u, nome in secoes.SECOES]
    t += ["", "## Perguntas frequentes"]
    for q, a in faq:
        t += [f"### {q}", a, ""]
    t += ["## Sobre", f"- [Princípios editoriais e política de correções]({D}/sobre/)", f"- [Política de Privacidade]({D}/privacidade/)"]
    if ok(CFG["email_redacao"]):
        t.append(f"- Contato da redação: {CFG['email_redacao']}")
    return "\n".join(t) + "\n"


def cabecalhos():
    ga = ok(CFG["ga4"])
    csp = ("default-src 'self'; img-src 'self' data:" + (" https://*.google-analytics.com https://*.googletagmanager.com" if ga else "") + "; style-src 'self' 'unsafe-inline'; font-src 'self'; "
           "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'" + (" https://*.googletagmanager.com" if ga else "") + "; "
           "connect-src 'self'" + (" https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com" if ga else "") + "; "
           "frame-ancestors 'self'; base-uri 'self'; form-action 'self'; object-src 'none'")
    seg = [("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "strict-origin-when-cross-origin"),
           ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), browsing-topics=()"),
           ("X-Frame-Options", "SAMEORIGIN"), ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
           ("Content-Security-Policy", csp)]
    netlify = ("/*\n" + "".join(f"  {k}: {v}\n" for k, v in seg)
               + "\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n"
               + "\n/img/*\n  Cache-Control: public, max-age=2592000\n"
               + "\n/data/*\n  Cache-Control: public, max-age=600\n")
    raiz = HOST[4:] if HOST.startswith("www.") else HOST
    apache = ("# .htaccess (Apache). Em host com CDN (ex.: Hostinger hcdn), HTTPS e www saem pelo painel.\n"
              "Options -Indexes\nDirectoryIndex index.html\nErrorDocument 404 /404.html\n\n"
              "<IfModule mod_rewrite.c>\nRewriteEngine On\n"
              "RewriteCond %{HTTPS} off [OR]\nRewriteCond %{HTTP_HOST} !^www\\. [NC]\n"
              f"RewriteRule ^ https://www.{raiz}%{{REQUEST_URI}} [L,R=301]\n"
              "RewriteRule ^(.*/)?index\\.html$ /$1 [L,R=301]\n</IfModule>\n\n"
              "<IfModule mod_headers.c>\n" + "".join(f'Header always set {k} "{v}"\n' for k, v in seg)
              + '<FilesMatch "\\.(css|woff2)$">\nHeader set Cache-Control "public, max-age=31536000, immutable"\n</FilesMatch>\n'
              + '<FilesMatch "\\.(webp|png|jpg|ico)$">\nHeader set Cache-Control "public, max-age=2592000"\n</FilesMatch>\n'
              # o site se atualiza a cada 2 horas: HTML e dados sempre revalidados, para ninguém ver a versão velha
              + '<FilesMatch "\\.(html|xml|txt|json)$">\nHeader set Cache-Control "no-cache"\n</FilesMatch>\n</IfModule>\n\n'
              + "<IfModule mod_deflate.c>\nAddOutputFilterByType DEFLATE text/html text/css application/javascript application/json "
              + "text/plain application/xml application/rss+xml\n</IfModule>\nAddType application/manifest+json .webmanifest\n")
    return netlify, apache


# ============================================================================
# 6. Montagem
# ============================================================================
def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    src_html = SRC.read_text(encoding="utf-8")

    print("1/7 pré-renderizando a página...")
    pre = prerender()
    dados = pre["dados"]
    N, ED = dados["N"], dados["ED"]
    mapa, usados = {}, set()
    for n in N:  # endereço único por notícia (títulos automáticos podem coincidir)
        sl = slug(n["h"])
        mapa[n["id"]] = sl if sl not in usados else f"{sl[:70]}-{n['id'].lower()}"
        usados.add(mapa[n["id"]])
    edk = {d["k"]: d for d in ED}

    print("2/7 imagens WebP, fontes locais, ícones, imagens de compartilhamento...")
    dims = imagens()
    css = css_site(src_html, fontes())
    icones()
    og_image("og-image.jpg", "s-leis", CFG["slogan"] + ".", f"Notícias, leis e canais de ajuda · {HOST}")
    for s, nm, foto in REGIOES:
        og_image(f"og-{s}.jpg", foto, f"Mulheres e crianças no {nm}: edição regional.", f"{HOST}/{s}/")

    faq = [(html.unescape(re.sub("<[^>]+>", "", q)), html.unescape(re.sub("<[^>]+>", "", a)))
           for q, a in re.findall(r"<summary>(.*?)</summary><p>(.*?)</p>", src_html, re.S)]
    footer = re.search(r"<footer>.*?</footer>", pre["paginas"][""], re.S).group(0).replace('href="#', 'href="/#')
    topo = topo_sub(ED)

    print("3/7 home e edições regionais...")
    painel = secoes.painel({"ROOT": ROOT, "esc": esc})
    for k in pre["paginas"]:
        pre["paginas"][k] = pre["paginas"][k].replace("<!--PAINEL-->", painel)
    verts = secoes.verticais_capa({"ROOT": ROOT, "esc": esc})
    for k in pre["paginas"]:
        pre["paginas"][k] = pre["paginas"][k].replace("<!--VERTICAIS-->", verts)
    rede_prot = secoes.instituicoes_hero({"ROOT": ROOT, "esc": esc, "CR": dados["CR"]})
    numeros = secoes.numeros_capa({"ROOT": ROOT, "esc": esc})
    parl = secoes.parlamentares_capa({"ROOT": ROOT, "esc": esc})
    for k in pre["paginas"]:
        pre["paginas"][k] = pre["paginas"][k].replace("<!--INSTITUICOES-->", rede_prot).replace("<!--NUMEROS-->", numeros).replace("<!--PARLAMENTARES-->", parl)
        if ok(CFG["whatsapp_canal"]):  # faixa de emergência ganha o convite para o canal do portal
            pre["paginas"][k] = pre["paginas"][k].replace(
                '<a href="/ajuda/">Todos os canais de ajuda →</a>',
                f'<a href="/ajuda/">Todos os canais de ajuda →</a><a href="{esc(CFG["whatsapp_canal"])}" rel="noopener" target="_blank" style="margin-left:0">Siga no WhatsApp</a>', 1)
    titulo_home = f"{CFG['nome']} · Defesa de mulheres e crianças"
    desc_home = ("Notícias, leis, dados e canais de ajuda sobre a defesa de mulheres e crianças no Brasil: violência contra a mulher, "
                 "Lei Maria da Penha, rede de amparo e infância, com fonte.")
    ld_home = {"@context": "https://schema.org", "@graph": [
        org_ld(), site_ld(),
        {"@type": "CollectionPage", "@id": D + "/#webpage", "url": D + "/", "name": titulo_home, "description": desc_home,
         "isPartOf": {"@id": D + "/#website"}, "about": {"@id": D + "/#org"}, "inLanguage": "pt-BR",
         "primaryImageOfPage": D + "/og-image.jpg", "dateModified": HOJE.isoformat()},
        {"@type": "FAQPage", "@id": D + "/#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
        {"@type": "ItemList", "@id": D + "/#noticias", "name": "Notícias em destaque", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": f"{D}/noticias/{mapa[n['id']]}/"} for i, n in enumerate(N)]}]}
    (OUT / "index.html").write_text(
        head(titulo_home, desc_home, "/", css, jsonld=ld_home,
             extra=f'<link rel="preload" as="image" href="/img/{dados["SL"][0][1]}.webp" fetchpriority="high">')
        + ajustar_corpo(pre["paginas"][""], mapa) + medicao() + FIM, encoding="utf-8")
    for s, nm, foto in REGIOES:
        t = f"Mulheres e crianças no {nm} · Edição {nm} | {CFG['nome']}"
        d_ = (f"Notícias sobre a proteção de mulheres e crianças no {nm}: violência, leis, rede de amparo, Justiça e políticas públicas "
              "na região, com fonte em cada notícia.")
        ld = {"@context": "https://schema.org", "@graph": [org_ld(), site_ld(),
              {"@type": "CollectionPage", "@id": f"{D}/{s}/#webpage", "url": f"{D}/{s}/", "name": t, "description": d_,
               "isPartOf": {"@id": D + "/#website"}, "inLanguage": "pt-BR", "about": {"@type": "Place", "name": f"Região {nm}, Brasil"}},
              migalhas([("Início", "/"), (f"Edição {nm}", f"/{s}/")])]}
        (OUT / s).mkdir()
        (OUT / s / "index.html").write_text(
            head(t, d_, f"/{s}/", css, og=f"/og-{s}.jpg", jsonld=ld,
                 extra=f'<link rel="preload" as="image" href="/img/{foto}.webp" fetchpriority="high">')
            + ajustar_corpo(pre["paginas"][s], mapa) + medicao() + FIM, encoding="utf-8")

    print("4/7 páginas de notícia...")
    for n in N:
        pasta = OUT / "noticias" / mapa[n["id"]]
        pasta.mkdir(parents=True)
        (pasta / "index.html").write_text(pagina_noticia(n, dados, mapa, css, topo, footer, dims), encoding="utf-8")
    lista = "".join(f'<li><span class="tag" style="--c:var({edk[n["e"]]["c"]})">{esc(edk[n["e"]]["tag"])}</span><br>'
                    f'<a href="/noticias/{mapa[n["id"]]}/">{esc(n["h"])}</a><p>{esc(n["t"][:180])}…</p></li>' for n in N)
    (OUT / "noticias" / "index.html").write_text(pagina_simples(
        "/noticias/", "Todas as notícias: mulheres e crianças no Brasil", "Todas as notícias do Observatório Brasil Mulher sobre violência contra a mulher, leis, amparo e proteção da infância, com resumo próprio e fontes.",
        f'<p class="lead">Notícias sobre a defesa de mulheres e crianças no Brasil com resumo da redação e links para as fontes originais.</p><ul class="lista-noticias">{lista}</ul>',
        css, topo, footer, [("Início", "/"), ("Notícias", "/noticias/")]), encoding="utf-8")

    print("5/7 páginas institucionais e LGPD...")
    for caminho, titulo, desc, corpo in [
        ("/sobre/", "Sobre nós: o Observatório Brasil Mulher", "O Observatório Brasil Mulher reúne notícias, leis, dados e canais de ajuda sobre a defesa de mulheres e crianças no Brasil, com a missão de informar para proteger.", corpo_sobre()),
        ("/privacidade/", "Política de Privacidade", "Como o Observatório Brasil Mulher trata dados pessoais conforme a LGPD: dados coletados, bases legais, direitos do titular e contato do encarregado.", corpo_privacidade()),
        ("/termos/", "Termos de Uso do portal", "Regras de uso do Observatório Brasil Mulher: conteúdo próprio, conteúdo de terceiros e fotos, correções, privacidade, lei e foro aplicáveis.", corpo_termos()),
        ("/creditos/", "Créditos das imagens", "Autores e licenças Creative Commons das fotos usadas no Observatório Brasil Mulher, todas do Wikimedia Commons, com links para as obras e licenças.", corpo_creditos(dados["CR"], dados["LIC"]))]:
        (OUT / caminho.strip("/")).mkdir()
        (OUT / caminho.strip("/") / "index.html").write_text(
            pagina_simples(caminho, titulo, desc, corpo, css, topo, footer, [("Início", "/"), (titulo, caminho)]), encoding="utf-8")
    (OUT / "404.html").write_text(pagina_simples(
        "/404.html", "Página não encontrada", "Página não encontrada no Observatório Brasil Mulher.",
        '<p class="lead">Este endereço não existe ou mudou. <a href="/">Voltar ao início</a> ou ver <a href="/noticias/">todas as notícias</a>.</p>',
        css, topo, footer, [("Início", "/"), ("Página não encontrada", "/404.html")], robots="noindex"), encoding="utf-8")

    print("   repositório: arquivo mês a mês...")
    meses = paginas_arquivo(css, topo, footer, edk)
    print("   instituições: uma página por instituição citada...")
    empresas = paginas_empresas(css, topo, footer, edk, N, mapa)
    print("   seções de dados e guias...")
    extras = secoes.gerar({"pagina_simples": pagina_simples, "esc": esc, "OUT": OUT, "ROOT": ROOT, "D": D, "MESES": MESES,
                           "css": css, "topo": topo, "footer": footer, "edk": edk, "N": N, "mapa": mapa})

    print("6/7 robots, sitemap, llms.txt, RSS, cabeçalhos...")
    (OUT / "data").mkdir()
    shutil.copy2(ROOT / "data" / "noticias.json", OUT / "data" / "noticias.json")
    urls = ([("/", "1.0", "/og-image.jpg")] + [(f"/{s}/", "0.8", f"/og-{s}.jpg") for s, _, _ in REGIOES]
            + [("/noticias/", "0.7", None), ("/arquivo/", "0.7", None), ("/orgaos/", "0.6", None)]
            + [(f"/orgaos/{s}/", "0.5", None, ult) for s, ult in empresas]
            + [(u, "0.6" if u.count("/") == 2 else "0.4", None) for u in extras]
            + [(f"/arquivo/{m}/", "0.5", None, ult) for m, ult in meses]
            + [(f"/noticias/{mapa[n['id']]}/", "0.7", f"/img/{n['img']}.webp", data_de(n)) for n in N]
            + [(u, "0.3", None) for u in ("/sobre/", "/privacidade/", "/termos/", "/creditos/")])
    (OUT / "sitemap.xml").write_text(sitemap(urls), encoding="utf-8")
    (OUT / "sitemap-noticias.xml").write_text(sitemap_noticias(N, mapa), encoding="utf-8")
    (OUT / "robots.txt").write_text(robots(), encoding="utf-8")
    (OUT / "llms.txt").write_text(llms(dados, mapa, faq), encoding="utf-8")
    (OUT / "feed.xml").write_text(rss(N, mapa, edk), encoding="utf-8")
    netlify, apache = cabecalhos()
    (OUT / "_headers").write_text(netlify, encoding="utf-8")
    (OUT / ".htaccess").write_text(apache, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copy2(ROOT / "ferramentas" / "LEIA-ME-site.md", OUT / "LEIA-ME.md")

    if CI:
        print(f"Pronto (modo CI, só o site): {OUT}  ·  {len(urls)} URLs no sitemap")
        return
    print("7/7 pastas de entrega...")
    entrega_extra(pre, mapa, css)
    print(f"Pronto: {OUT}  ·  {len(urls)} URLs no sitemap")


def paginas_empresas(css, topo, footer, edk, noticias, mapa):
    """/orgaos/ e /orgaos/<nome>/: tudo o que o Radar e os destaques trouxeram sobre cada instituição (mínimo 3 notícias)."""
    repo = json.loads((ROOT / "data" / "noticias_completo.json").read_text(encoding="utf-8"))["noticias"]
    por_empresa = {}
    for n in repo:
        for e in n.get("empresas") or []:
            por_empresa.setdefault(e, []).append(n)
    saida, linhas_idx = [], []
    for nome, itens in sorted(por_empresa.items(), key=lambda kv: -len(kv[1])):
        if len(itens) < 3:
            continue
        itens.sort(key=lambda n: n["data"], reverse=True)
        s = slug(nome.split("/")[0], 40)
        termo = re.compile(r"\b" + re.escape(nome.split("/")[0]) + r"\b", re.I)
        nossos = [n for n in noticias if termo.search(n["h"] + " " + n["t"])][:6]
        corpo = []
        if nossos:
            corpo.append('<h2>Nos destaques do Observatório</h2><ul class="lista-noticias">' + "".join(
                f'<li><a href="/noticias/{mapa[n["id"]]}/">{esc(n["h"])}</a><p>{esc(n.get("date", ""))}</p></li>' for n in nossos) + "</ul>")
        corpo.append('<h2>Na rede</h2><ul class="lista-noticias">')
        for n in itens[:60]:
            ed = edk.get(n["editoria"])
            tag = f'<span class="tag" style="--c:var({ed["c"]})">{esc(ed["tag"])}</span> ' if ed else ""
            d = date.fromisoformat(n["data"][:10])
            corpo.append(f'<li>{tag}<a href="{esc(n["link"])}" rel="noopener" target="_blank">{esc(n["titulo"])}</a>'
                         f'<p>{esc(n["fonte"])} · {d.day} {MESES[d.month - 1]} {d.year}</p></li>')
        corpo.append("</ul>")
        br = sum(1 for n in itens if n.get("brasil"))
        titulo = f"{nome}: notícias sobre a proteção de mulheres e crianças"
        desc = (f"Notícias sobre {nome} e a proteção de mulheres e crianças reunidas pelo Observatório: {len(itens)} matérias, "
                f"{br} sobre o Brasil, com fonte e link para o original.")
        (OUT / "orgaos" / s).mkdir(parents=True)
        (OUT / "orgaos" / s / "index.html").write_text(pagina_simples(
            f"/orgaos/{s}/", titulo, desc,
            f'<p class="lead">{len(itens)} notícias sobre {esc(nome)} e a proteção de mulheres e crianças ({br} sobre o Brasil), '
            'coletadas pelo Radar da rede. Cada título leva à matéria no veículo que a publicou.</p>' + "".join(corpo),
            css, topo, footer, [("Início", "/"), ("Instituições", "/orgaos/"), (nome, f"/orgaos/{s}/")]), encoding="utf-8")
        linhas_idx.append(f'<li><a href="/orgaos/{s}/">{esc(nome)}</a><p>{len(itens)} notícias · {br} sobre o Brasil</p></li>')
        saida.append((s, itens[0]["data"][:10]))
    (OUT / "orgaos").mkdir(exist_ok=True)
    (OUT / "orgaos" / "index.html").write_text(pagina_simples(
        "/orgaos/", "Instituições nas notícias sobre mulheres e crianças",
        "Ministérios, tribunais, Ministério Público, polícias, organismos internacionais e plataformas: as notícias de cada instituição, com fonte e link.",
        '<p class="lead">As instituições que mais aparecem nas notícias sobre a proteção de mulheres e crianças coletadas pelo Observatório.</p>'
        f'<ul class="lista-noticias">{"".join(linhas_idx)}</ul>',
        css, topo, footer, [("Início", "/"), ("Instituições", "/orgaos/")]), encoding="utf-8")
    return saida


def paginas_arquivo(css, topo, footer, edk):
    """O repositório em páginas estáticas: /arquivo/ (meses) e /arquivo/AAAA-MM/ (todas as notícias do mês, por dia)."""
    pasta = ROOT / "data" / "arquivo"
    meses = sorted((p.stem for p in pasta.glob("*.json")), reverse=True) if pasta.exists() else []
    saida, linhas_idx = [], []
    for m in meses:
        itens = json.loads((pasta / f"{m}.json").read_text(encoding="utf-8"))["noticias"]
        ano, mes = m.split("-")
        nome = f"{MESES[int(mes) - 1]} de {ano}"
        por_dia = {}
        for n in itens:
            por_dia.setdefault(n["data"][:10], []).append(n)
        corpo = []
        for dia in sorted(por_dia, reverse=True):
            d = date.fromisoformat(dia)
            corpo.append(f'<h2>{d.day} de {MESES[d.month - 1]}</h2><ul class="lista-noticias">')
            for n in por_dia[dia]:
                ed = edk.get(n["editoria"])
                tag = f'<span class="tag" style="--c:var({ed["c"]})">{esc(ed["tag"])}</span> ' if ed else ""
                extra = f' · mais {n["n_fontes"] - 1} veículo(s)' if (n.get("n_fontes") or 1) > 1 and n.get("grupo") == n.get("id") else ""
                ufs = f' · {", ".join(n["ufs"])}' if n.get("ufs") else ""
                corpo.append(f'<li>{tag}<a href="{esc(n["link"])}" rel="noopener" target="_blank">{esc(n["titulo"])}</a>'
                             f'<p>{esc(n["fonte"])}{ufs}{extra}</p></li>')
            corpo.append("</ul>")
        br = sum(1 for n in itens if n.get("brasil"))
        titulo = f"Notícias sobre mulheres e crianças em {nome}"
        desc = (f"Repositório do Observatório Brasil Mulher: {len(itens)} notícias sobre mulheres e crianças coletadas em {nome}, "
                f"{br} sobre o Brasil, com fonte, editoria e link para o original.")
        (OUT / "arquivo" / m).mkdir(parents=True)
        (OUT / "arquivo" / m / "index.html").write_text(pagina_simples(
            f"/arquivo/{m}/", titulo, desc,
            f'<p class="lead">{len(itens)} notícias reunidas em {nome} pelo Radar da rede ({br} sobre o Brasil). '
            f'Cada título leva à matéria no veículo que a publicou.</p>' + "".join(corpo),
            css, topo, footer, [("Início", "/"), ("Repositório", "/arquivo/"), (nome.capitalize(), f"/arquivo/{m}/")]),
            encoding="utf-8")
        linhas_idx.append(f'<li><a href="/arquivo/{m}/">{nome.capitalize()}</a><p>{len(itens)} notícias · {br} sobre o Brasil</p></li>')
        saida.append((m, max(n["data"][:10] for n in itens)))
    total = sum(int(re.search(r"<p>(\d+)", x).group(1)) for x in linhas_idx)
    (OUT / "arquivo").mkdir(exist_ok=True)
    (OUT / "arquivo" / "index.html").write_text(pagina_simples(
        "/arquivo/", "Repositório de notícias sobre mulheres e crianças",
        f"Arquivo completo do Observatório Brasil Mulher: {total} notícias sobre a proteção de mulheres e crianças coletadas de centenas de fontes, "
        "organizadas mês a mês, com fonte e link para o original.",
        f'<p class="lead">Todas as notícias coletadas pelo Radar da rede, atualizado de hora em hora: '
        f'{total} itens de centenas de fontes. Para buscar e filtrar, use o <a href="/#radar">Repositório na página inicial</a>.</p>'
        f'<ul class="lista-noticias">{"".join(linhas_idx)}</ul>',
        css, topo, footer, [("Início", "/"), ("Repositório", "/arquivo/")]), encoding="utf-8")
    return saida


def entrega_extra(pre, mapa, css_url):
    # 2 · arquivo único com imagens embutidas, para WhatsApp/e-mail. NÃO é para hospedar.
    d2 = ENTREGA / "2-para-enviar"
    shutil.rmtree(d2, ignore_errors=True)
    d2.mkdir(parents=True)
    corpo = re.sub(r"<script>.*?</script>", "", ajustar_corpo(pre["paginas"][""], mapa), flags=re.S)

    def emb(m):
        arq = OUT / m.group(1).lstrip("/")
        if not arq.exists():
            return m.group(0)
        tipo = "image/webp" if arq.suffix == ".webp" else "image/png"
        return f'src="data:{tipo};base64,{base64.b64encode(arq.read_bytes()).decode()}"'
    corpo = re.sub(r'src="(/img/[\w.-]+)"', emb, corpo)
    corpo = re.sub(r'\ssrcset="[^"]*"', "", corpo)
    css = re.sub(r"@font-face\s*{[^}]+}", "", (OUT / css_url.lstrip("/")).read_text(encoding="utf-8"))
    (d2 / "observatorio-portal.html").write_text(
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{esc(CFG["nome"])} · prévia</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@300;500;700;800;900&family=Red+Hat+Text:wght@400;500;600&display=swap">'
        f"<style>{css}</style></head><body>{corpo}</body></html>", encoding="utf-8")
    # 3 · gerador (fonte da verdade)
    d3 = ENTREGA / "3-gerador"
    shutil.rmtree(d3, ignore_errors=True)
    d3.mkdir()
    for item in ("main.py", "pyproject.toml", "src", "data", "coletor"):
        o = ROOT / item
        (shutil.copytree(o, d3 / item) if o.is_dir() else shutil.copy2(o, d3 / item))
    shutil.copytree(ROOT / "ferramentas", d3 / "ferramentas", ignore=shutil.ignore_patterns("node_modules", "_pre.json"))
    # 4 · imagens soltas
    d4 = ENTREGA / "4-imagens"
    shutil.rmtree(d4, ignore_errors=True)
    shutil.copytree(OUT / "img", d4)
    shutil.copy2(OUT / "og-image.jpg", d4 / "og-image.jpg")
    shutil.copy2(ROOT / "ferramentas" / "LEIA-ME-entrega.md", ENTREGA / "LEIA-ME.md")
    # .zip do site (inclui .htaccess) para subir pelo gerenciador de arquivos da Hostinger e extrair em public_html
    zip_base = ENTREGA / "observatorio-site-para-hostinger"
    Path(str(zip_base) + ".zip").unlink(missing_ok=True)
    shutil.make_archive(str(zip_base), "zip", OUT)


if __name__ == "__main__":
    build()
