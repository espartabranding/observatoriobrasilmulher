"""Verifica cada fonte de data/fontes.json e descobre o feed RSS/Atom.

Para cada fonte: confere se o site responde, procura <link rel="alternate">
no HTML e, se não achar, testa caminhos comuns (/feed, /rss, /RSS do gov.br...).
Grava de volta em data/fontes.json os campos status, feed e verificado_em.

Uso: uv run coletor/descobrir_feeds.py
"""

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

FONTES = Path(__file__).resolve().parent.parent / "data" / "fontes.json"
UA = "Mozilla/5.0 (compatible; IAnoBrasilBot/0.1; +https://www.ianobrasil.com.br)"
TIMEOUT = 20
CAMINHOS = ["feed/", "feed", "rss", "rss.xml", "feed.xml", "index.xml", "atom.xml", "RSS", "rss/", "noticias/RSS"]
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)


SEM_VERIFICACAO = ssl._create_unverified_context()


def baixar(url: str, limite: int = 600_000, _tentativa: int = 0) -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    ctx = SEM_VERIFICACAO if _tentativa else None
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            corpo = r.read(limite).decode(r.headers.get_content_charset() or "utf-8", "replace")
            return r.status, r.geturl(), corpo
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception:
        # Vários sites públicos têm cadeia de certificados incompleta; só lemos conteúdo público.
        return baixar(url, limite, 1) if not _tentativa else (0, url, "")


def eh_feed(texto: str) -> bool:
    inicio = texto.lstrip()[:2000].lower()
    return "<rss" in inicio or "<feed" in inicio or "<rdf:rdf" in inicio


def feeds_no_html(html: str, base: str) -> list[str]:
    achados = []
    for tag in LINK_RE.findall(html):
        t = tag.lower()
        if "alternate" in t and ("rss+xml" in t or "atom+xml" in t):
            m = re.search(r'href=["\']([^"\']+)', tag, re.I)
            if m:
                href = unescape(m.group(1))
                if "comments" not in href.lower():
                    achados.append(urljoin(base, href))
    return achados


def verificar(fonte: dict) -> dict:
    status, final, html = baixar(fonte["url"])
    fonte["status"] = status
    fonte["verificado_em"] = date.today().isoformat()
    candidatos = feeds_no_html(html, final) if html else []
    base = final if final.endswith("/") else final + "/"
    raiz = f"{urlparse(final).scheme}://{urlparse(final).netloc}/"
    candidatos += [urljoin(base, c) for c in CAMINHOS] + [urljoin(raiz, c) for c in CAMINHOS[:5]]
    vistos = set()
    for c in candidatos:
        if c in vistos:
            continue
        vistos.add(c)
        st, _, corpo = baixar(c, 200_000)
        if st == 200 and eh_feed(corpo):
            fonte["feed"] = c
            break
    else:
        fonte.setdefault("feed", None)
    return fonte


def main() -> None:
    fontes = json.loads(FONTES.read_text(encoding="utf-8"))
    so = set(sys.argv[1:])  # opcional: verificar só alguns ids
    alvo = [f for f in fontes if not so or f["id"] in so]
    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(verificar, alvo))
    FONTES.write_text(json.dumps(fontes, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for f in fontes if f["status"] == 200)
    com_feed = sum(1 for f in fontes if f.get("feed"))
    print(f"{len(fontes)} fontes · {ok} respondem 200 · {com_feed} com feed")
    for f in fontes:
        if f["status"] != 200:
            print(f"  [{f['status']}] {f['id']}  {f['url']}")


if __name__ == "__main__":
    main()
