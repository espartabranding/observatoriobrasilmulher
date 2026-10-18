"""Auditoria do site gerado (entrega/1-site-para-publicar): SEO técnico, schema, links e arquivos de descoberta.

Uso: uv run ferramentas/auditar.py
"""
import json
import re
import sys
import xml.dom.minidom
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "entrega" / "1-site-para-publicar"
DOM = __import__("os").environ.get("OBM_DOMINIO") or "https://www.observatoriobrasilmulher.com.br"
erros, avisos = [], []


def texto_visivel(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


paginas = sorted(SITE.rglob("*.html"))
for arq in paginas:
    rel = "/" + arq.relative_to(SITE).as_posix().replace("index.html", "")
    h = arq.read_text(encoding="utf-8")
    h1 = len(re.findall(r"<h1[\s>]", h))
    if h1 != 1:
        erros.append(f"{rel}: {h1} H1 (esperado 1)")
    t = re.search(r"<title>(.*?)</title>", h, re.S)
    if not t:
        erros.append(f"{rel}: sem <title>")
    elif not 30 <= len(t.group(1)) <= 70:
        avisos.append(f"{rel}: título com {len(t.group(1))} caracteres")
    dsc = re.search(r'<meta name="description" content="([^"]*)"', h)
    if not dsc:
        erros.append(f"{rel}: sem meta description")
    elif not 110 <= len(dsc.group(1)) <= 170:
        avisos.append(f"{rel}: description com {len(dsc.group(1))} caracteres")
    can = re.search(r'<link rel="canonical" href="([^"]+)"', h)
    if not can or not can.group(1).startswith(DOM):
        erros.append(f"{rel}: canonical ausente ou não absoluto")
    elif arq.name != "404.html" and can.group(1) != DOM + rel:
        erros.append(f"{rel}: canonical {can.group(1)} não é autorreferente")
    for bloco in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            json.loads(bloco)
        except json.JSONDecodeError as e:
            erros.append(f"{rel}: JSON-LD inválido ({e})")
    if "base64," in h:
        erros.append(f"{rel}: imagem em base64 no HTML")
    if "«PREENCHER»" in h:
        avisos.append(f"{rel}: contém «PREENCHER» visível")
    for src in set(re.findall(r"""(?:src|href)="(/(?:img|assets)/[^"']+)\"""", h)):
        if not (SITE / src.lstrip("/")).exists():
            erros.append(f"{rel}: arquivo inexistente {src}")
    for href in set(re.findall(r'href="(/[a-z0-9\-/]*)"', h)):
        alvo = SITE / href.strip("/") / "index.html" if href.endswith("/") else SITE / href.lstrip("/")
        if href != "/" and not alvo.exists():
            erros.append(f"{rel}: link interno quebrado {href}")
    if len(texto_visivel(h)) < 1500 and arq.name != "404.html":
        avisos.append(f"{rel}: pouco texto sem JavaScript ({len(texto_visivel(h))} caracteres)")

for nome in ("robots.txt", "sitemap.xml", "llms.txt", "feed.xml", "site.webmanifest", "og-image.jpg",
             "favicon.ico", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "_headers", ".htaccess", "404.html"):
    if not (SITE / nome).exists():
        erros.append(f"falta {nome}")
for nome in ("sitemap.xml", "feed.xml"):
    try:
        xml.dom.minidom.parse(str(SITE / nome))
    except Exception as e:
        erros.append(f"{nome} inválido: {e}")
locs = re.findall(r"<loc>(.*?)</loc>", (SITE / "sitemap.xml").read_text(encoding="utf-8"))
for u in locs:
    caminho = u.replace(DOM, "").strip("/")
    if not (SITE / caminho / "index.html").exists() and caminho:
        erros.append(f"sitemap aponta para página inexistente: {u}")
if "Disallow: /\n" in (SITE / "robots.txt").read_text(encoding="utf-8").split("# Buscadores")[0]:
    erros.append("robots.txt bloqueia todo o site")

print(f"{len(paginas)} páginas · {len(locs)} URLs no sitemap")
print("ERROS:" if erros else "ERROS: nenhum")
for e in erros:
    print("  -", e)
print("AVISOS:" if avisos else "AVISOS: nenhum")
for a in avisos:
    print("  -", a)
sys.exit(1 if erros else 0)
