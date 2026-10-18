# Observatório Brasil Mulher · site para publicar

Esta pasta é o site pronto. Suba **todo o conteúdo dela** na raiz do domínio `www.observatoriobrasilmulher.com.br`.

**NÃO EDITE ESTES ARQUIVOS À MÃO.** Eles são gerados por `main.py` (pasta `3-gerador`). A próxima geração desfaz qualquer edição manual.

## Como publicar

| Hospedagem | Como |
|---|---|
| **Cloudflare Pages** (recomendado) | Novo projeto → "Upload assets" → envie esta pasta. Os cabeçalhos de segurança e cache vêm do arquivo `_headers`. |
| **Netlify** | Arraste esta pasta em app.netlify.com/drop. Usa o `_headers`. |
| **Apache / cPanel** | Envie por FTP para `public_html`. Usa o `.htaccess` (HTTPS, www, cache, 404). |
| **Hostinger ou host com CDN** | Envie para `public_html`, mas ative HTTPS e o redirecionamento para `www` **pelo painel**: o `.htaccess` não vale atrás de CDN. |

Depois de publicar, teste: `http://observatoriobrasilmulher.com.br` precisa redirecionar para `https://www.observatoriobrasilmulher.com.br/`.

## O que está aqui

- `index.html` (home) e `norte/`, `nordeste/`, `centro-oeste/`, `sudeste/`, `sul/` (edições regionais), todos com o conteúdo já no HTML, legível sem JavaScript.
- `noticias/` com uma página por notícia (schema NewsArticle) e o índice de notícias.
- `sobre/`, `privacidade/`, `termos/`, `creditos/` e `404.html`.
- `robots.txt`, `sitemap.xml`, `llms.txt`, `feed.xml` (RSS), `site.webmanifest`, ícones e `og-image.jpg` (prévia de link 1200×630).
- `assets/` (CSS e fontes servidas pelo próprio domínio, sem chamar o Google), `img/` (fotos em WebP) e `data/noticias.json` (base do Radar).

## Lançamento (publicar não é lançar)

1. **Google Search Console**, propriedade de **domínio**, verificada por registro **TXT no DNS**. Cobre www, sem www, http e https de uma vez.
2. Envie `https://www.observatoriobrasilmulher.com.br/sitemap.xml`.
3. Inspeção de URL → **Solicitar indexação** da home, das 5 edições regionais e das principais notícias.
4. **Bing Webmaster Tools**: importe do Search Console. É de onde o Copilot e parte do ChatGPT buscam.
5. **Teste de resultados avançados** do Google na home e numa notícia (FAQ, NewsArticle, Breadcrumb).
6. **PageSpeed Insights**: guarde o número inicial.
7. Mande o link no WhatsApp para ver o card. O WhatsApp guarda a imagem em cache; para trocar, mude o nome do arquivo.

**Prazos honestos:** indexar leva dias depois do envio. Aparecer bem para termos disputados leva meses e depende de links, perfis e reputação, não de mais ajuste no código.

## Antes de lançar: preencha no gerador (bloco CFG de `main.py`)

- Razão social, CNPJ e endereço do controlador (Política de Privacidade e Schema).
- E-mail da redação e e-mail e nome do encarregado de dados (LGPD, art. 41).
- Plataforma de newsletter e a integração do formulário (hoje ele é um protótipo e não envia dados).
- Foro dos Termos de Uso.
- Perfis oficiais (LinkedIn, Instagram, YouTube) para o `sameAs`.
- Robôs de treino de IA: hoje **bloqueados** (`permitir_treino_ia`). Robôs de busca de IA ficam liberados.
- GA4, se quiser medir audiência: preencher liga sozinho o aviso de cookies com consentimento.

Campos vazios aparecem destacados em amarelo nas páginas legais e ficam fora do Schema. Rode `uv run main.py` de novo depois de preencher.
