"""Versão do site para o GitHub Pages, que serve o portal numa subpasta (https://<conta>.github.io/<repositório>/).

O site é gerado com caminhos a partir da raiz ("/img/...", "/noticias/..."). Este script copia
entrega/1-site-para-publicar para entrega/github-pages e acrescenta o prefixo da subpasta a esses caminhos.
Quando o portal tiver domínio próprio, publique entrega/1-site-para-publicar direto e este passo deixa de ser usado.

Uso: uv run ferramentas/github_pages.py observatoriobrasilmulher
"""

import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "entrega" / "1-site-para-publicar"
DESTINO = RAIZ / "entrega" / "github-pages"


def prefixar(texto: str, base: str) -> str:
    texto = re.sub(r'((?:href|src|srcset|action)=["\'])/(?!/)', rf"\1{base}/", texto)  # href="/x", src='/x'
    texto = re.sub(r",\s*/(img|assets)/", rf", {base}/\1/", texto)                       # segunda imagem do srcset
    texto = re.sub(r"url\(/(?!/)", f"url({base}/", texto)                               # CSS: url(/assets/...)
    texto = texto.replace('fetch("/data/', f'fetch("{base}/data/')
    texto = texto.replace("new PagefindUI({", f'new PagefindUI({{baseUrl:"{base}/",')
    # links que o script da página monta depois de carregar ("/leis/", "/noticias/...") ganham o prefixo na hora
    corrige = ('<script>(function(){var B="' + base + '";function fix(r){(r.querySelectorAll?r:document).querySelectorAll('
               '\'a[href^="/"],img[src^="/"]\').forEach(function(e){var k=e.tagName==="A"?"href":"src",v=e.getAttribute(k);'
               'if(v&&v.indexOf("//")!==0&&v.indexOf(B+"/")!==0)e.setAttribute(k,B+v);});}fix(document);'
               'new MutationObserver(function(m){m.forEach(function(x){x.addedNodes.forEach(function(n){if(n.nodeType===1)fix(n);});});})'
               '.observe(document.documentElement,{childList:true,subtree:true});})();</script>')
    return texto.replace("</body>", corrige + "</body>", 1)


def main() -> None:
    base = "/" + (sys.argv[1] if len(sys.argv) > 1 else "observatoriobrasilmulher").strip("/")
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    shutil.copytree(ORIGEM, DESTINO)
    for arq in DESTINO.rglob("*"):
        if arq.suffix in (".html", ".css") and arq.is_file():
            arq.write_text(prefixar(arq.read_text(encoding="utf-8"), base), encoding="utf-8")
    (DESTINO / ".nojekyll").write_text("", encoding="utf-8")
    for extra in (".htaccess", "_headers", "LEIA-ME.md"):  # do servidor Apache/Netlify, não do Pages
        (DESTINO / extra).unlink(missing_ok=True)
    print(f"GitHub Pages: {DESTINO} com prefixo {base}")


if __name__ == "__main__":
    main()
