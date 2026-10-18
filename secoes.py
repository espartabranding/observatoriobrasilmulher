"""Seções de dados e guias do Observatório Brasil Mulher, geradas pelo main.py:

  /ajuda/          onde buscar ajuda: canais de emergência, serviços e organizações (data/ajuda.json)
  /leis/           leis de proteção, tramitação dos projetos e linha do tempo        (data/leis.json, tramitacoes.json)
  /programas/      programas, equipamentos e recursos públicos anunciados          (data/inteligencia.json)
  /decisoes/       decisões da Justiça que firmam entendimento                     (data/inteligencia.json)
  /iniciativas/    iniciativas com resultado, por setor                            (data/inteligencia.json)
  /instituicoes/   quem protege: as instituições da rede de proteção               (data/instituicoes.json)
  /indicadores/    números da violência contra mulheres e crianças, com fonte     (data/indicadores.json)
  /eventos/        agenda de datas, campanhas e eventos + eventos.ics             (data/eventos.json)
  /glossario/      glossário, uma página por termo                                (data/glossario.json)
  /guias/          guias práticos por público                                     (data/guias.json)
  /briefing/       o briefing do dia
  /relatorio/      relatório mensal, pronto para imprimir/PDF
  /busca/          busca em todo o site (Pagefind, índice gerado no GitHub Actions)
  /en/             os destaques traduzidos para o inglês                          (cache em data/en.json)
  /infancia/, /seguranca/, /amparo/, /saude/   verticais com notícias, programas, iniciativas e leis

Cada gerador devolve a lista de URLs para o sitemap. Arquivo de dados ausente = seção não gerada.
"""

import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone

CSS = """
/* ---------- seções de dados ---------- */
.art.largo{max-width:1180px}
.tabela{width:100%;overflow-x:auto;margin:20px 0 8px;border:1px solid var(--border);border-radius:12px}
.tabela table{width:100%;border-collapse:collapse;font-size:14.5px;min-width:720px}
.tabela th{background:var(--layer);text-align:left;font-weight:600;padding:10px 12px;white-space:nowrap;color:var(--text)}
.tabela td{padding:10px 12px;border-top:1px solid var(--border);vertical-align:top;color:var(--text-2);line-height:1.5}
.tabela td b{color:var(--text)}
.tabela td.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.cards-d{columns:3 280px;column-gap:16px;margin:20px 0}
.cards-d > div{background:var(--layer);border-radius:14px;padding:18px 18px 16px;break-inside:avoid;margin:0 0 16px;display:inline-block;width:100%}
.lg{width:48px;height:48px;border-radius:12px;background:#fff;border:1px solid var(--border);display:inline-flex;align-items:center;justify-content:center;
  overflow:hidden;flex:none;font:700 17px var(--display);color:#fff}
.lg img{width:100%;height:100%;object-fit:contain;padding:6px}
.lg.ini{border:0}
.cab-lg{display:flex;gap:12px;align-items:center;margin-bottom:8px}
.cab-lg h3{margin:0!important}
.valor{font-family:var(--display);font-size:28px;font-weight:300;color:var(--text);line-height:1.1;margin:6px 0 2px}
.etq{display:inline-block;font-size:12px;font-weight:600;padding:2px 10px;border-radius:999px;background:var(--bg);border:1px solid var(--border-strong);margin:0 4px 6px 0}
.cards-d h3{font-family:var(--display);font-size:17px;font-weight:700;margin:6px 0 6px;color:var(--text)}
.cards-d p{font-size:14.5px;line-height:1.55;margin:0 0 8px;color:var(--text-2)}
.cards-d .num{font-family:var(--display);font-size:30px;font-weight:300;color:var(--text);line-height:1.1}
.cards-d small{font-size:12.5px;color:var(--text-3)}
.cards-d small a{color:var(--link)}
.sit{display:inline-block;font-size:12px;font-weight:600;padding:2px 10px;border-radius:999px;background:var(--bg);border:1px solid var(--border-strong)}
.sit.vig{border-color:#24a148;color:#198038}.sit.tra{border-color:#f1c21b;color:#8e6a00}.sit.arq{color:var(--text-3)}
.linha{list-style:none;padding:0;margin:20px 0;border-left:2px solid var(--blue)}
.linha li{position:relative;padding:0 0 18px 20px;margin:0}
.linha li::before{content:"";position:absolute;left:-7px;top:6px;width:12px;height:12px;border-radius:50%;background:var(--blue)}
.linha time{font-size:13px;font-weight:600;color:var(--text-3);display:block}
.linha b{color:var(--text)}
.az{display:flex;flex-wrap:wrap;gap:6px;margin:16px 0}
.az a{padding:4px 10px;border:1px solid var(--border);border-radius:8px;text-decoration:none!important;font-weight:600}
.dados-nav{display:flex;flex-wrap:wrap;gap:8px;margin:28px 0 0;padding-top:20px;border-top:1px solid var(--border)}
.dados-nav a{font-size:13.5px;padding:6px 12px;border:1px solid var(--border-strong);border-radius:999px;text-decoration:none!important;color:var(--text)!important}
.imprimir{margin:8px 0 20px}
.cards-d.stats-d{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;columns:auto}
.stats-d > div{margin:0}
@media (max-width:600px){.cards-d.stats-d{grid-template-columns:minmax(0,1fr)}}
.sub{overflow-x:clip}
.banda{margin:28px calc(50% - 50vw) 8px;padding:44px max(16px,calc(50vw - 566px)) 36px}
.banda h2{margin-top:0!important;color:#fff}
.pagina-fundo .art h1,.pagina-fundo .prose h2{color:#fff}
.pagina-fundo .art .lead,.pagina-fundo .prose p{color:var(--text-2)}
.pagina-fundo .crumbs{color:var(--text-3)}
.pagina-fundo .dados-nav{border-top-color:var(--border)}
.pagina-fundo .dados-nav a{color:var(--text)!important;border-color:var(--border)}
.banda > p,.banda .nota{color:var(--text-2)}
.tech .cards-d > div{background:var(--card);border:1px solid var(--border);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);
  box-shadow:0 18px 40px rgba(0,0,0,.35);transition:border-color .25s,box-shadow .25s,transform .25s}
@media (hover:hover){.tech .cards-d > div:hover{border-color:rgba(190,149,255,.6);box-shadow:0 0 28px rgba(138,63,252,.28),0 18px 40px rgba(0,0,0,.4);transform:translateY(-2px)}}
.tech .cards-d h3{color:#fff}
.prose .valor{font-family:var(--display);font-size:28px;line-height:1.15;margin:4px 0 8px;color:var(--text)}
.tech .prose .valor{color:#BE95FF;font-weight:400}
.tech .etq{background:rgba(138,63,252,.14);border-color:rgba(190,149,255,.35);color:#E8DAFF}
.tech .cards-d small a,.tech a{color:var(--link)}
.tech .cards-d p b{color:#fff}
.urgente{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;background:#2A0F4A;color:#fff;border-radius:16px;padding:18px 22px;margin:20px 0}
.urgente b{font-family:var(--display);font-size:20px;font-weight:800}
.urgente span{color:#E8DAFF;font-size:15px}
.urgente a{color:#fff!important;font-weight:700;text-decoration:underline}
/* links externos em pílulas: fonte, texto oficial, site, enquete */
.prose .pill,.cards-d small a[target="_blank"],.cards-d p a[target="_blank"],.tabela a[target="_blank"],.linha a[target="_blank"],.prose li > a[target="_blank"] + small a{
  display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:999px;border:1.5px solid var(--link);color:var(--link)!important;
  font:700 13px/1.25 var(--display);text-decoration:none!important;margin:6px 6px 2px 0;transition:background .2s,color .2s;vertical-align:middle}
.prose .pill::after,.cards-d small a[target="_blank"]::after,.cards-d p a[target="_blank"]::after,.tabela a[target="_blank"]::after,.linha a[target="_blank"]::after{content:"↗";font-size:12px}
.prose .pill:hover,.cards-d small a[target="_blank"]:hover,.cards-d p a[target="_blank"]:hover,.tabela a[target="_blank"]:hover,.linha a[target="_blank"]:hover{background:var(--link);color:var(--bg)!important}
.prose .pill.cheia{background:var(--blue);border-color:var(--blue);color:#fff!important;font-size:14px;padding:8px 16px}
.prose .pill.cheia:hover{background:var(--blue-hover)}
.tabela a[target="_blank"]{white-space:nowrap}
.cards-d h3 a[target="_blank"],.lista-noticias a[target="_blank"]{text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:3px}
.cards-d h3 a[target="_blank"]::after,.lista-noticias a[target="_blank"]::after{content:" ↗";font-size:.8em;color:var(--link)}
/* quem propõe: cartões com foto oficial */
.parls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:16px 0 28px}
.parl{display:flex;gap:14px;align-items:center;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:12px;color:var(--text)!important;
  text-decoration:none!important;transition:border-color .2s,transform .2s}
.parl:hover{border-color:var(--blue);transform:translateY(-2px)}
.parl img,.parl-sem{width:64px;height:85px;object-fit:cover;border-radius:10px;flex:none;background:var(--layer)}
.parl-in{display:flex;flex-direction:column;gap:3px;min-width:0}
.parl-in b{font-family:var(--display);font-size:15.5px;line-height:1.25}
.parl-in small{font-size:12.5px;color:var(--text-3)}
.parl-n{font-size:13px;color:var(--text-2)}.parl-n em{font-style:normal;font-family:var(--display);font-weight:800;font-size:17px;color:var(--link)}
.parl-lei{align-self:flex-start;font:700 11.5px var(--display);color:#198038;border:1px solid #24a148;border-radius:999px;padding:1px 8px}
.parl-top{display:flex;gap:24px;align-items:flex-start;margin:8px 0 20px;flex-wrap:wrap}
.parl-top img{border-radius:14px;width:150px;height:200px;object-fit:cover}
.parl-top dl{display:grid;grid-template-columns:auto 1fr;gap:6px 16px;margin:0;font-size:15px}
.parl-top dt{color:var(--text-3)}.parl-top dd{margin:0;color:var(--text)}
@media (max-width:1100px){.parls{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:600px){.parls{grid-template-columns:minmax(0,1fr)}}
.contato{font-family:var(--display);font-size:22px;font-weight:700;color:var(--text);margin:4px 0 6px;line-height:1.2}
@media print{.banda{margin:0;padding:0;background:none!important;color:#000}.banda::before,.banda::after,.banda .scan{display:none}}
@media print{.sub > header,.sub > footer,.crumbs,.imprimir,.dados-nav,#cookies,.share{display:none!important}.art{padding:0;max-width:none}
  .tabela{border:0;overflow:visible}.tabela table{min-width:0}a{color:inherit!important;text-decoration:none!important}}
"""

MES_CURTO = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
SECOES = [("/ajuda/", "Onde buscar ajuda"), ("/oportunidades/", "Vagas e oportunidades"), ("/projetos/", "Projetos sociais"),("/briefing/", "Briefing do dia"),("/infancia/", "Infância"),
          ("/seguranca/", "Segurança"), ("/amparo/", "Amparo"), ("/saude/", "Saúde"),
          ("/leis/", "Leis"), ("/em-votacao/", "Em votação"), ("/participe/", "Participe"), ("/parlamentares/", "Quem propõe"), ("/programas/", "Programas e recursos"), ("/decisoes/", "Decisões da Justiça"),
          ("/iniciativas/", "Iniciativas"), ("/instituicoes/", "Quem protege"), ("/guias/", "Guias práticos"),
          ("/indicadores/", "Indicadores"), ("/eventos/", "Agenda"), ("/glossario/", "Glossário"),
          ("/relatorio/", "Relatório mensal"), ("/busca/", "Busca"), ("/en/", "English")]
URGENTE = ('<div class="urgente" role="note"><b>Em perigo agora? Ligue 190.</b>'
           '<span>Para orientação e denúncia sobre violência contra a mulher, Ligue 180 (24 horas, gratuito). '
           'Crianças e adolescentes: Disque 100. <a href="/ajuda/">Todos os canais de ajuda</a></span></div>')


def _ler(C, nome, padrao=None):
    arq = C["ROOT"] / "data" / nome
    try:
        return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else padrao
    except ValueError:
        return padrao


def _data(iso):
    try:
        d = date.fromisoformat((iso or "")[:10])
    except ValueError:
        return iso or ""
    return f"{d.day} {MES_CURTO[d.month - 1]} {d.year}"


def _link(C, url, texto):
    return f'<a href="{C["esc"](url)}" target="_blank" rel="noopener">{C["esc"](texto)}</a>'


def _nav(atual):
    return f"<!--DADOS-NAV:{atual}-->"  # preenchido no fim, só com as seções que foram geradas


def _preencher_nav(C, urls):
    existem = set(urls)
    for arq in C["OUT"].rglob("index.html"):
        h = arq.read_text(encoding="utf-8")
        if "<!--DADOS-NAV:" not in h:
            continue
        h = re.sub(r"<!--DADOS-NAV:([^>]*)-->", lambda m: '<nav class="dados-nav" aria-label="Dados e guias">' + "".join(
            f'<a href="{u}">{n}</a>' for u, n in SECOES if u != m.group(1) and u in existem) + "</nav>", h)
        arq.write_text(h, encoding="utf-8")


def _gravar(C, caminho, titulo, desc, corpo, crumb, largo=False, extra_head="", ld_extra=None, fundo=None):
    pasta = C["OUT"] / caminho.strip("/")
    pasta.mkdir(parents=True, exist_ok=True)
    h = C["pagina_simples"](caminho, titulo, desc, corpo + _nav(caminho), C["css"], C["topo"], C["footer"],
                            [("Início", "/")] + crumb, largo=largo, ld_extra=ld_extra, fundo=fundo)
    if extra_head:
        h = h.replace("</head>", extra_head + "</head>", 1)
    (pasta / "index.html").write_text(h, encoding="utf-8")


def _tabela(cab, linhas, numericas=()):
    th = "".join(f"<th>{c}</th>" for c in cab)
    tr = "".join("<tr>" + "".join(f'<td{" class=n" if i in numericas else ""}>{v}</td>' for i, v in enumerate(l)) + "</tr>"
                 for l in linhas)
    return f'<div class="tabela"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def logo(C, nome, tam=48):
    """Iniciais da instituição num círculo colorido (o portal não usa logotipos de terceiros)."""
    import unicodedata
    k = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", (nome or "").lower()).encode("ascii", "ignore").decode()).strip("-")[:50]
    ini = "".join(w[0] for w in re.findall(r"[A-Za-zÀ-ÿ0-9]+", nome or "?")[:2]).upper() or "?"
    cor = ["#0f62fe", "#8a3ffc", "#007d79", "#d02670", "#ba4e00", "#198038", "#1192e8", "#6929c4"][sum(map(ord, k)) % 8]
    return f'<span class="lg ini" style="background:{cor}{";width:%dpx;height:%dpx" % (tam, tam) if tam != 48 else ""}" aria-hidden="true">{C["esc"](ini)}</span>'


def _noticias_rede(C):
    return (_ler(C, "noticias.json", {}) or {}).get("noticias", [])


OFICIAIS = {"Governo federal", "Governo estadual", "Legislativo", "Judiciário", "Ministério Público", "Defensoria Pública",
            "Controle", "Agência pública de notícias", "Estatística oficial"}


# ---------------------------------------------------------------- leis
def leis(C):
    reg = _ler(C, "leis.json")
    if not reg:
        return []
    e = C["esc"]
    tram = _ler(C, "tramitacoes.json", {}) or {}
    classe = {"Em vigor": "vig", "Aprovado": "vig", "Em tramitação": "tra", "Em consulta": "tra", "Em andamento": "tra", "Arquivado": "arq"}
    nomes = {n["id"]: n["nome"] for n in reg["normas"]}
    publico = {"mulheres": "Mulheres", "criancas": "Crianças e adolescentes", "ambos": "Mulheres e crianças"}

    def cards(normas):
        return "".join(
            f'<div><span class="sit {classe.get(n["situacao"], "")}">{e(n["situacao"])}</span>'
            f'<h3>{e(n["nome"])}</h3><p>{e(n["resumo"])}</p>'
            + (f'<p><b>Próximo passo:</b> {e(n["proximo_passo"])}</p>' if n.get("proximo_passo") else "")
            + f'<small>{e(n["tipo"])} · {e(n["orgao"])} · {_link(C, n["url"], "texto oficial")}</small></div>'
            for n in normas)
    grupos = {}
    for n in reg["normas"]:
        grupos.setdefault(publico.get(n.get("publico"), "Mulheres e crianças"), []).append(n)
    corpo = [f'<p class="lead">As leis que protegem mulheres, crianças e adolescentes no Brasil, explicadas em linguagem simples: '
             f'{len(reg["normas"])} leis, projetos e decisões acompanhados, com link para o texto oficial. '
             f'Revisado em {_data(reg.get("atualizado_em"))}; a tramitação dos projetos na Câmara é atualizada automaticamente.</p>',
             '<p>Veja também os <a href="/em-votacao/">projetos de lei em votação</a>, com enquete oficial, e como '
             '<a href="/participe/">apoiar abaixo-assinados e ideias legislativas</a>.</p>', URGENTE]
    for g in ("Mulheres", "Crianças e adolescentes", "Mulheres e crianças"):
        if grupos.get(g):
            corpo += [f'<h2>{e(g)}</h2>', f'<div class="cards-d">{cards(grupos[g])}</div>']
    for nid, ts in tram.items():
        if ts:
            corpo.append(f'<h2>Últimos andamentos na Câmara: {e(nomes.get(nid, nid))}</h2><ul class="linha">' + "".join(
                f'<li><time>{_data(t["data"])} · {e(t["orgao"])}</time><b>{e(t["situacao"] or "Andamento")}</b>'
                f'<p>{e(t["despacho"])}</p></li>' for t in ts[:8]) + "</ul>")
    marcos = sorted(reg.get("marcos", []), key=lambda m: m["data"], reverse=True)
    corpo.append('<h2>Linha do tempo</h2><ul class="linha">' + "".join(
        f'<li><time>{_data(m["data"])}</time><b>{e(m["titulo"])}</b><p>{e(m["descricao"])} '
        f'{_link(C, m["url"], "Fonte")}</p></li>' for m in marcos) + "</ul>")
    leg = [n for n in _noticias_rede(C) if n.get("editoria") == "L" and n.get("brasil")][:15]
    if leg:
        corpo.append('<h2>Últimas notícias sobre leis e Justiça</h2><ul class="lista-noticias">' + "".join(
            f'<li>{_link(C, n["link"], n["titulo"])}<p>{e(n["fonte"])} · {_data(n["data"])}</p></li>' for n in leg) + "</ul>")
    corpo.append('<p><small>Este acompanhamento é informativo e não substitui orientação jurídica. A Defensoria Pública '
                 'oferece atendimento gratuito.</small></p>')
    _gravar(C, "/leis/", "Leis de proteção à mulher e à criança no Brasil",
            "Lei Maria da Penha, feminicídio, ECA, Lei Henry Borel e outras normas de proteção a mulheres e crianças, explicadas, com situação, linha do tempo e fonte oficial.",
            "".join(corpo), [("Leis", "/leis/")], largo=True)
    return ["/leis/"]


# ---------------------------------------------------------------- programas, iniciativas, decisões
def _fonte(C, it):
    return _link(C, it["link"], it["fonte"]) + f'<br><small>{_data(it["data"])}</small>'


def programas(C):
    intel = _ler(C, "inteligencia.json")
    if not intel or not intel.get("programas"):
        return []
    e = C["esc"]
    prog = intel["programas"]
    corte = (date.today() - timedelta(days=30)).isoformat()
    rec = [p for p in prog if p["data"] >= corte]
    soma = sum(p.get("valor_mi") or 0 for p in rec)
    resumo = f"{len(rec)} anúncios nos últimos 30 dias" + (f" (valores divulgados somam R$ {soma:,.0f} milhões)".replace(",", ".") if soma else "")
    cards = "".join(
        f'<div><div class="cab-lg">{logo(C, p.get("orgao"))}<h3>{e(p.get("nome") or p.get("orgao", ""))}</h3></div>'
        + (f'<p class="valor">{e(p["valor"])}</p>' if p.get("valor") else "")
        + "".join(f'<span class="etq">{e(x)}</span>' for x in (p.get("orgao"), p.get("publico"), p.get("cidade")) if x)
        + (f'<p>{e(p["descricao"])}</p>' if p.get("descricao") else "")
        + f'<small>{_link(C, p["link"], p["fonte"])} · {_data(p["data"])}</small></div>' for p in prog)
    corpo = [f'<p class="lead">Programas, serviços, equipamentos e recursos públicos para a proteção de mulheres e crianças anunciados no Brasil, '
             f'tirados automaticamente das notícias coletadas pelo Observatório, com link para a matéria de cada um. {resumo}.</p>',
             f'<div class="cards-d">{cards}</div>',
             '<p><small>Dados extraídos com apoio de IA a partir de título e chamada das notícias; valores e nomes '
             'como divulgados pelos órgãos ou pela imprensa. Confira na matéria original antes de usar. Encontrou um erro? Avise a redação.</small></p>']
    _gravar(C, "/programas/", "Programas e recursos para proteger mulheres e crianças",
            "Programas, Casas da Mulher Brasileira, delegacias, abrigos e recursos públicos anunciados no Brasil para proteger mulheres e crianças, com órgão, valor e fonte.",
            "".join(corpo), [("Programas e recursos", "/programas/")], largo=True, fundo="tech")
    return ["/programas/"]


def iniciativas(C):
    intel = _ler(C, "inteligencia.json")
    if not intel or not intel.get("iniciativas"):
        return []
    e = C["esc"]
    por_setor = {}
    for c in intel["iniciativas"]:
        por_setor.setdefault((c.get("setor") or "outros").strip().lower() or "outros", []).append(c)
    corpo = [f'<p class="lead">{len(intel["iniciativas"])} iniciativas de proteção a mulheres e crianças no Brasil, por setor: '
             'o que órgãos públicos, escolas, empresas e organizações da sociedade civil estão fazendo e que resultado foi divulgado, '
             'com link para a notícia.</p>']
    for setor, itens in sorted(por_setor.items(), key=lambda kv: -len(kv[1])):
        corpo.append(f'<h2>{e(setor.capitalize())} <small>({len(itens)})</small></h2><div class="cards-d">' + "".join(
            f'<div><div class="cab-lg">{logo(C, c.get("responsavel"))}<h3>{e(c.get("responsavel", ""))}</h3></div><p>{e(c.get("descricao", ""))}</p>'
            + (f'<p><b>Resultado:</b> {e(c["resultado"])}</p>' if c.get("resultado") else "")
            + f'<small>{_link(C, c["link"], c["fonte"])} · {_data(c["data"])}</small></div>' for c in itens[:30]) + "</div>")
    corpo.append('<p><small>Iniciativas identificadas com apoio de IA a partir das notícias coletadas; resultados como divulgados pelos responsáveis ou pela imprensa.</small></p>')
    _gravar(C, "/iniciativas/", "Iniciativas de proteção a mulheres e crianças",
            "O que órgãos públicos, escolas, empresas e a sociedade civil fazem para proteger mulheres e crianças no Brasil: iniciativas por setor, resultados e fonte.",
            "".join(corpo), [("Iniciativas", "/iniciativas/")], largo=True)
    return ["/iniciativas/"]


def decisoes(C):
    intel = _ler(C, "inteligencia.json")
    if not intel or not intel.get("decisoes"):
        return []
    e = C["esc"]
    linhas = [[f'<b>{e(x.get("tribunal", ""))}</b>', e(x.get("tema", "")), e(x.get("decisao", "")), e(x.get("efeito", "")), _fonte(C, x)]
              for x in intel["decisoes"]]
    corpo = [f'<p class="lead">Decisões de tribunais e do Ministério Público que firmam entendimentos sobre a proteção de mulheres, '
             f'crianças e adolescentes, segundo a imprensa e os próprios órgãos. {len(linhas)} decisões, com link para a notícia. '
             'Para as leis em vigor, veja <a href="/leis/">Leis</a>.</p>',
             _tabela(["Tribunal", "Tema", "Decisão", "O que muda", "Fonte"], linhas),
             '<p><small>Decisões identificadas com apoio de IA a partir das notícias coletadas. Consulte o processo no tribunal antes de citar.</small></p>']
    _gravar(C, "/decisoes/", "Decisões da Justiça sobre violência contra a mulher",
            "Decisões do STF, STJ, tribunais de Justiça e Ministério Público sobre violência contra a mulher e proteção da infância, com o que muda na prática e a fonte.",
            "".join(corpo), [("Decisões da Justiça", "/decisoes/")], largo=True)
    return ["/decisoes/"]


# ---------------------------------------------------------------- quem protege
def instituicoes(C):
    ins = _ler(C, "instituicoes.json")
    if not ins:
        return []
    e = C["esc"]
    por_esfera = {}
    for i in ins:
        por_esfera.setdefault(i.get("esfera") or "Outras", []).append(i)
    corpo = [f'<p class="lead">As {len(ins)} instituições centrais da rede de proteção a mulheres e crianças no Brasil: o que cada uma faz, '
             'como acionar e onde ficam as notícias oficiais. Cada item tem link para o site oficial.</p>', URGENTE]
    for esf, itens in por_esfera.items():
        corpo.append(f'<h2>{e(esf)}</h2><div class="cards-d">' + "".join(
            f'<div><div class="cab-lg">{logo(C, i.get("sigla") or i["nome"])}<h3>{e(i["nome"])}</h3></div>'
            + f'<p>{e(i.get("descricao", ""))}</p>'
            + ("<ul>" + "".join(f"<li>{e(a)}</li>" for a in i.get("atribuicoes", [])) + "</ul>" if i.get("atribuicoes") else "")
            + (f'<p><b>Como acionar:</b> {e(i["canal"])}</p>' if i.get("canal") else "")
            + f'<small>{e(i.get("tipo", ""))} · {e(i.get("abrangencia", ""))} · {_link(C, i["url"], "site oficial")}</small></div>'
            for i in itens) + "</div>")
    _gravar(C, "/instituicoes/", "Quem protege: a rede de proteção à mulher e à criança",
            "Ministério das Mulheres, Justiça, Ministério Público, Defensoria, delegacias, Conselho Tutelar e organizações: o que cada um faz e como acionar.",
            "".join(corpo), [("Quem protege", "/instituicoes/")], largo=True)
    return ["/instituicoes/"]


# ---------------------------------------------------------------- indicadores
def indicadores(C):
    ind = _ler(C, "indicadores.json")
    if not ind:
        return []
    e = C["esc"]
    grupos = {}
    for i in ind:
        grupos.setdefault(i["grupo"], []).append(i)
    corpo = [f'<p class="lead">{len(ind)} números para entender a violência contra mulheres, crianças e adolescentes no Brasil '
             'e a resposta do Estado: feminicídios, violência sexual e doméstica, infância, trabalho e renda e a rede de proteção. '
             'Cada número traz a fonte e o período.</p>']
    for g, itens in grupos.items():
        corpo.append(f'<h2>{e(g)}</h2><div class="cards-d">' + "".join(
            f'<div><span class="num">{e(i["valor"])}</span><h3>{e(i["rotulo"])}</h3><p>{e(i.get("detalhe", ""))}</p>'
            f'<small>{_link(C, i["url"], i["fonte"])} · {e(i.get("data", ""))}</small></div>' for i in itens) + "</div>")
    _gravar(C, "/indicadores/", "Indicadores da violência contra mulheres e crianças",
            "Os principais números da violência contra mulheres e crianças no Brasil: feminicídios, estupros, violência doméstica, infância e rede de proteção, com fonte.",
            "".join(corpo), [("Indicadores", "/indicadores/")], largo=True)
    return ["/indicadores/"]


# ---------------------------------------------------------------- agenda
def eventos(C):
    evs = _ler(C, "eventos.json")
    if not evs:
        return []
    e = C["esc"]
    hoje = date.today().isoformat()
    prox = sorted((v for v in evs if (v.get("fim") or v["inicio"]) >= hoje), key=lambda v: v["inicio"])

    def periodo(v):
        a, b = v["inicio"], v.get("fim") or v["inicio"]
        return _data(a) if a == b else f"{_data(a)} a {_data(b)}"

    def lugar(v):
        return v["cidade"] + (f' ({v["uf"]})' if v.get("uf") else "")

    linhas = [[f'<b>{_link(C, v["url"], v["nome"])}</b><br><small>{e(v.get("descricao", ""))}</small>', periodo(v),
               e(lugar(v)), e(v.get("formato", "")), e(v.get("organizador", ""))]
              for v in prox]
    corpo = [f'<p class="lead">Datas, campanhas e eventos sobre os direitos de mulheres e crianças no Brasil: {len(prox)} próximas datas, '
             'com período, local e link oficial. <a href="/eventos.ics">Adicione todas à sua agenda</a> (arquivo .ics para Google Agenda, Outlook e Apple).</p>',
             _tabela(["Data ou evento", "Quando", "Onde", "Formato", "Organizador"], linhas),
             '<p><small>Datas informadas pelos organizadores e em leis e calendários oficiais; confirme no site oficial. '
             'Quer incluir um evento? Envie para a redação.</small></p>']
    ld = [{"@type": "Event", "name": v["nome"], "startDate": v["inicio"], "endDate": v.get("fim") or v["inicio"], "url": v["url"],
           "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode" if v.get("formato") == "Online" else "https://schema.org/OfflineEventAttendanceMode",
           "location": {"@type": "VirtualLocation", "url": v["url"]} if v.get("formato") == "Online" else
           {"@type": "Place", "name": v["cidade"], "address": {"@type": "PostalAddress", "addressLocality": v["cidade"], "addressRegion": v.get("uf", ""), "addressCountry": "BR"}},
           "organizer": {"@type": "Organization", "name": v.get("organizador", "")}, "description": v.get("descricao", "")} for v in prox]
    _gravar(C, "/eventos/", "Agenda: datas e campanhas pelos direitos das mulheres",
            "Agosto Lilás, 21 Dias de Ativismo, 8 de março, 18 de maio e outros eventos sobre os direitos de mulheres e crianças, com datas e arquivo para a agenda.",
            "".join(corpo), [("Agenda", "/eventos/")], largo=True, ld_extra=ld)
    # arquivo de agenda (iCalendar)
    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    host = C["D"].split("://", 1)[-1]
    linhas_ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Observatorio Brasil Mulher//Agenda//PT-BR", "CALSCALE:GREGORIAN",
                  "X-WR-CALNAME:Agenda do Observatório Brasil Mulher"]
    for v in prox:
        fim = date.fromisoformat(v.get("fim") or v["inicio"]) + timedelta(days=1)
        txt = lambda s: re.sub(r"([,;\\])", r"\\\1", s or "").replace("\n", " ")
        linhas_ics += ["BEGIN:VEVENT", f"UID:{hashlib.md5((v['nome'] + v['inicio']).encode()).hexdigest()}@{host}",
                       f"DTSTAMP:{agora}", f"DTSTART;VALUE=DATE:{v['inicio'].replace('-', '')}", f"DTEND;VALUE=DATE:{fim.strftime('%Y%m%d')}",
                       f"SUMMARY:{txt(v['nome'])}", f"LOCATION:{txt(v['cidade'] + (' - ' + v['uf'] if v.get('uf') else ''))}",
                       f"DESCRIPTION:{txt(v.get('descricao', ''))} {v['url']}", f"URL:{v['url']}", "END:VEVENT"]
    linhas_ics.append("END:VCALENDAR")
    (C["OUT"] / "eventos.ics").write_text("\r\n".join(linhas_ics) + "\r\n", encoding="utf-8")
    return ["/eventos/"]


# ---------------------------------------------------------------- glossário
def glossario(C):
    gl = _ler(C, "glossario.json")
    if not gl:
        return []
    e = C["esc"]
    gl = sorted(gl, key=lambda g: g["termo"].lower())
    por_slug = {g["slug"]: g for g in gl}
    import unicodedata
    letra = lambda t: unicodedata.normalize("NFD", t[0]).encode("ascii", "ignore").decode().upper() or "#"
    letras = sorted({letra(g["termo"]) for g in gl})
    corpo = [f'<p class="lead">{len(gl)} termos sobre violência contra a mulher, proteção da infância, leis e rede de amparo, '
             'explicados em linguagem simples, cada um com o que significa na prática.</p>',
             '<nav class="az" aria-label="Letras">' + "".join(f'<a href="#l-{l}">{l}</a>' for l in letras) + "</nav>"]
    for l in letras:
        corpo.append(f'<h2 id="l-{l}">{l}</h2><ul class="lista-noticias">' + "".join(
            f'<li><a href="/glossario/{g["slug"]}/">{e(g["termo"])}</a><p>{e(g["definicao"][:170])}{"…" if len(g["definicao"]) > 170 else ""}</p></li>'
            for g in gl if letra(g["termo"]) == l) + "</ul>")
    ld = [{"@type": "DefinedTermSet", "@id": C["D"] + "/glossario/#set", "name": "Glossário de proteção à mulher e à criança",
           "hasDefinedTerm": [{"@type": "DefinedTerm", "name": g["termo"], "url": f'{C["D"]}/glossario/{g["slug"]}/'} for g in gl]}]
    _gravar(C, "/glossario/", "Glossário: violência contra a mulher e proteção",
            f"Glossário com {len(gl)} termos explicados: medida protetiva, feminicídio, violência psicológica, Conselho Tutelar, escuta especializada e mais.",
            "".join(corpo), [("Glossário", "/glossario/")], ld_extra=ld)
    urls = ["/glossario/"]
    for g in gl:
        rel = [por_slug[s] for s in g.get("relacionados", []) if s in por_slug]
        corpo = (f'<p class="lead">{e(g["definicao"])}</p>'
                 + (f'<h2>Na prática</h2><p>{e(g["na_pratica"])}</p>' if g.get("na_pratica") else "")
                 + (f'<h2>Termos relacionados</h2><ul>' + "".join(f'<li><a href="/glossario/{r["slug"]}/">{e(r["termo"])}</a></li>' for r in rel) + "</ul>" if rel else "")
                 + f'<p>Categoria: {e(g.get("categoria", ""))}. <a href="/glossario/">Ver todos os termos</a>. '
                 'Precisa de ajuda? Veja <a href="/ajuda/">onde buscar ajuda</a>.</p>')
        nome_curto = g["termo"].split(" (")[0]
        titulo = f"O que é {nome_curto}? Glossário"
        if len(titulo) > 66:
            titulo = f"{nome_curto[:52]}: glossário"
        if len(titulo) < 30:
            titulo = f"O que é {nome_curto}? Glossário de proteção"
        desc = (f"{nome_curto}: " + g["definicao"])[:155].rsplit(" ", 1)[0] + "…"
        if len(desc) < 110:
            desc = (desc[:-1] + " Explicação em linguagem simples no glossário do Observatório Brasil Mulher.")[:168]
        ld = [{"@type": "DefinedTerm", "name": g["termo"], "description": g["definicao"], "inDefinedTermSet": C["D"] + "/glossario/#set",
               "url": f'{C["D"]}/glossario/{g["slug"]}/'}]
        _gravar(C, f'/glossario/{g["slug"]}/', titulo, desc, corpo, [("Glossário", "/glossario/"), (nome_curto, f'/glossario/{g["slug"]}/')], ld_extra=ld)
        urls.append(f'/glossario/{g["slug"]}/')
    return urls


# ---------------------------------------------------------------- briefing do dia
def briefing(C):
    e, N, mapa = C["esc"], C["N"], C["mapa"]
    dest = sorted([n for n in N if n.get("iso")], key=lambda n: n["iso"], reverse=True)[:5] or N[:5]
    hoje = date.today()
    intel = _ler(C, "inteligencia.json", {}) or {}
    semana = (hoje - timedelta(days=7)).isoformat()
    corpo = [f'<p class="lead">O essencial sobre a proteção de mulheres e crianças no Brasil em {hoje.day} de {C["MESES"][hoje.month - 1]} de {hoje.year}, '
             'em cinco minutos: os destaques com o que muda, o que os órgãos oficiais anunciaram, programas e decisões da Justiça.</p>',
             '<div class="share"><button type="button" data-ouvir="▶ Ouvir o briefing" hidden>▶ Ouvir o briefing</button></div>',
             URGENTE, '<h2>Os destaques</h2>']
    for i, n in enumerate(dest, 1):
        corpo.append(f'<h3>{i}. <a href="/noticias/{mapa[n["id"]]}/">{e(n["h"])}</a></h3><p>{e(n["t"])}</p>'
                     + (f'<p><b>Por que importa:</b> {e(n["w"])}</p>' if n.get("w") else ""))
    ofi = [x for x in _noticias_rede(C) if x.get("tipo") in OFICIAIS][:6]
    if ofi:
        corpo.append('<h2>Das fontes oficiais</h2><ul>' + "".join(
            f'<li>{_link(C, x["link"], x["titulo"])} <small>({e(x["fonte"])})</small></li>' for x in ofi) + "</ul>")
    prog = [p for p in intel.get("programas", []) if p["data"] >= semana][:6]
    if prog:
        corpo.append('<h2>Programas e recursos</h2><ul>' + "".join(
            f'<li><b>{e(p.get("orgao", ""))}</b>: {e(p.get("nome") or p.get("descricao", ""))} {("· " + e(p["valor"])) if p.get("valor") else ""} '
            f'— {_link(C, p["link"], p["fonte"])}</li>' for p in prog) + "</ul>")
    dec = [x for x in intel.get("decisoes", []) if x["data"] >= semana][:5]
    if dec:
        corpo.append('<h2>Na Justiça</h2><ul>' + "".join(
            f'<li><b>{e(x.get("tribunal", ""))}</b>: {e(x.get("decisao", ""))} — {_link(C, x["link"], x["fonte"])}</li>' for x in dec) + "</ul>")
    _gravar(C, "/briefing/", "Briefing do dia: proteção de mulheres e crianças",
            "O briefing diário do Observatório Brasil Mulher: os destaques sobre violência contra a mulher e proteção da infância, fontes oficiais, programas e Justiça.",
            "".join(corpo), [("Briefing do dia", "/briefing/")])
    return ["/briefing/"]


# ---------------------------------------------------------------- relatório mensal
def relatorio(C):
    e, edk = C["esc"], C["edk"]
    pasta = C["ROOT"] / "data" / "arquivo"
    meses = sorted((p.stem for p in pasta.glob("*.json")), reverse=True) if pasta.exists() else []
    intel = _ler(C, "inteligencia.json", {}) or {}
    reg = _ler(C, "leis.json", {}) or {}
    urls, idx = [], []
    for m in meses[:12]:
        itens = json.loads((pasta / f"{m}.json").read_text(encoding="utf-8"))["noticias"]
        if len(itens) < 30:
            continue
        ano, mes = m.split("-")
        nome = f"{C['MESES'][int(mes) - 1]} de {ano}"
        br = [n for n in itens if n.get("brasil")]
        cont = {k: sum(1 for n in itens if n.get("editoria") == k) for k in edk}
        org = {}
        for n in itens:
            for x in n.get("empresas") or []:
                org[x] = org.get(x, 0) + 1
        top_org = sorted(org.items(), key=lambda kv: -kv[1])[:10]
        ufs = {}
        for n in itens:
            for u in n.get("ufs") or []:
                ufs[u] = ufs.get(u, 0) + 1
        top_uf = sorted(ufs.items(), key=lambda kv: -kv[1])[:8]
        no_mes = lambda lst: [x for x in lst if x["data"][:7] == m]
        prog, dec, ini = (no_mes(intel.get(k, [])) for k in ("programas", "decisoes", "iniciativas"))
        marcos = [x for x in reg.get("marcos", []) if x["data"][:7] == m]
        dest = [n for n in C["N"] if (n.get("iso") or "")[:7] == m]
        corpo = [f'<p class="lead">O mês da proteção de mulheres e crianças no Brasil em números e fatos: {len(itens)} notícias coletadas, '
                 f'{len(br)} sobre o Brasil, {len(prog)} programas e recursos anunciados, {len(dec)} decisões da Justiça e '
                 f'{len(ini)} iniciativas identificadas.</p>',
                 '<button type="button" class="btn ghost imprimir" onclick="window.print()">Salvar em PDF / imprimir</button>',
                 '<h2>Panorama por editoria</h2>',
                 _tabela(["Editoria", "Notícias"], [[e(edk[k]["tag"]), str(v)] for k, v in cont.items()], numericas=(1,))]
        if top_org:
            corpo += ['<h2>Instituições mais citadas</h2>', _tabela(["Instituição", "Notícias"], [[e(k), str(v)] for k, v in top_org], numericas=(1,))]
        if top_uf:
            corpo += ['<h2>Estados com mais notícias</h2>', _tabela(["Estado", "Notícias"], [[e(k), str(v)] for k, v in top_uf], numericas=(1,))]
        if dest:
            corpo.append('<h2>Destaques do Observatório</h2><ul>' + "".join(
                f'<li><a href="/noticias/{C["mapa"][n["id"]]}/">{e(n["h"])}</a></li>' for n in dest[:15]) + "</ul>")
        if marcos:
            corpo.append('<h2>Leis</h2><ul>' + "".join(f'<li><b>{_data(x["data"])}</b>: {e(x["titulo"])}</li>' for x in marcos) + "</ul>")
        if prog:
            corpo += ['<h2>Programas e recursos</h2>', _tabela(["Órgão", "Programa", "Valor", "Fonte"], [
                [f'<b>{e(p.get("orgao", ""))}</b>', e(p.get("nome", "")), e(p.get("valor", "")), _fonte(C, p)] for p in prog])]
        if dec:
            corpo.append('<h2>Decisões da Justiça</h2><ul>' + "".join(
                f'<li><b>{e(x.get("tribunal", ""))}</b>: {e(x.get("decisao", ""))} — {_link(C, x["link"], x["fonte"])}</li>' for x in dec) + "</ul>")
        if ini:
            corpo.append('<h2>Iniciativas</h2><ul>' + "".join(
                f'<li><b>{e(c.get("responsavel", ""))}</b>: {e(c.get("descricao", ""))}</li>' for c in ini[:20]) + "</ul>")
        corpo.append(f'<p>Todas as notícias do mês estão no <a href="/arquivo/{m}/">repositório de {nome}</a>.</p>')
        _gravar(C, f"/relatorio/{m}/", f"Relatório de {nome}: proteção de mulheres e crianças",
                f"Relatório mensal do Observatório Brasil Mulher sobre {nome}: notícias por editoria, instituições e estados mais citados, programas, decisões e iniciativas.",
                "".join(corpo), [("Relatório mensal", "/relatorio/"), (nome.capitalize(), f"/relatorio/{m}/")], largo=True)
        urls.append(f"/relatorio/{m}/")
        idx.append(f'<li><a href="/relatorio/{m}/">{nome.capitalize()}</a><p>{len(itens)} notícias · {len(prog)} programas · {len(dec)} decisões</p></li>')
    if not idx:
        return []
    _gravar(C, "/relatorio/", "Relatório mensal: mulheres e crianças no Brasil",
            "O relatório mensal do Observatório Brasil Mulher: a proteção de mulheres e crianças no país em números e fatos, mês a mês, pronto para salvar em PDF.",
            '<p class="lead">Todo mês, um retrato da proteção de mulheres e crianças no Brasil a partir das notícias coletadas pelo Observatório: '
            'editorias, instituições, estados, programas, decisões da Justiça e iniciativas. Cada relatório pode ser salvo em PDF.</p>'
            f'<ul class="lista-noticias">{"".join(idx)}</ul>', [("Relatório mensal", "/relatorio/")])
    return ["/relatorio/"] + urls


# ---------------------------------------------------------------- busca
def busca(C):
    corpo = ('<p class="lead">Busque em todas as páginas do Observatório Brasil Mulher: notícias com análise, leis, canais de ajuda, '
             'programas, decisões, glossário, guias e relatórios. Para os títulos de toda a rede de veículos, use o '
             '<a href="/#radar">Repositório na página inicial</a>.</p>'
             '<div id="busca"></div>'
             '<noscript><p>A busca precisa de JavaScript. Veja o <a href="/arquivo/">repositório mês a mês</a>.</p></noscript>'
             '<script src="/pagefind/pagefind-ui.js"></script>'
             '<script>window.addEventListener("DOMContentLoaded",function(){if(!window.PagefindUI){document.getElementById("busca").innerHTML='
             '\'<p>Índice de busca em preparação. Tente de novo em alguns minutos.</p>\';return;}'
             'new PagefindUI({element:"#busca",showSubResults:true,showImages:false,translations:{placeholder:"Buscar: medida protetiva, Lei Maria da Penha, Conselho Tutelar…",'
             'zero_results:"Nada encontrado para [SEARCH_TERM]",many_results:"[COUNT] resultados para [SEARCH_TERM]",one_result:"1 resultado para [SEARCH_TERM]",'
             'load_more:"Mostrar mais",search_label:"Buscar no Observatório"}});'
             'var q=new URLSearchParams(location.search).get("q");if(q){var i=document.querySelector("#busca input");if(i){i.value=q;i.dispatchEvent(new Event("input"));}}});</script>')
    _gravar(C, "/busca/", "Busca no Observatório Brasil Mulher: notícias e leis",
            "Busque em todo o Observatório Brasil Mulher: notícias com análise, leis, canais de ajuda, programas, decisões da Justiça, glossário, guias e relatórios.",
            corpo, [("Busca", "/busca/")], extra_head='<link rel="stylesheet" href="/pagefind/pagefind-ui.css">')
    return ["/busca/"]


# ---------------------------------------------------------------- English
EN_SYS = ("Translate this Brazilian news item about the protection of women and children from Portuguese into clear, concise "
          "US English for international readers, NGOs and researchers. Keep names, numbers, law names and facts exactly; "
          'do not add information. Answer only with JSON: {"h": "headline", "t": "summary", "w": "why it matters"}')


def _traduzir(item):
    from anthropic import Anthropic
    r = Anthropic().messages.create(model=os.environ.get("IAB_MODELO", "claude-haiku-5-5"), max_tokens=2000, system=EN_SYS,
                                    messages=[{"role": "user", "content": json.dumps({k: item.get(k, "") for k in ("h", "t", "w")}, ensure_ascii=False)}])
    m = re.search(r"\{.*\}", "".join(b.text for b in r.content if b.type == "text"), re.S)
    return json.loads(m.group(0)) if m else None


def ingles(C):
    e, N = C["esc"], C["N"]
    arq = C["ROOT"] / "data" / "en.json"
    cache = _ler(C, "en.json", {}) or {}
    tem_chave = bool(os.environ.get("ANTHROPIC_API_KEY"))
    feitos = 0
    itens = []
    for n in N:
        hsh = hashlib.md5((n["h"] + n["t"] + n.get("w", "")).encode()).hexdigest()[:10]
        c = cache.get(n["id"])
        if (not c or c.get("hash") != hsh) and tem_chave and feitos < 25:
            try:
                tr = _traduzir(n)
                if tr and tr.get("h"):
                    c = cache[n["id"]] = {"hash": hsh, **tr}
                    feitos += 1
            except Exception as ex:
                print("   tradução EN falhou:", ex)
                tem_chave = False
        if c:
            itens.append((n, c))
    if feitos:
        arq.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    if not itens:
        return []
    itens.sort(key=lambda nc: nc[0].get("iso") or "", reverse=True)
    corpo = ['<p class="lead">Observatório Brasil Mulher is a news and data portal about the protection of women and children in Brazil: '
             'violence against women, laws, support services and child protection. This page brings our latest analyses in English. '
             'Every item links to the original sources, mostly in Portuguese.</p>']
    for n, c in itens:
        fontes = " · ".join(_link(C, u, nome) for nome, u in (n.get("s") or [])[:3])
        corpo.append(f'<h2>{e(c["h"])}</h2><p><small>{e(n.get("date", ""))}</small></p><p>{e(c.get("t", ""))}</p>'
                     + (f'<p><b>Why it matters:</b> {e(c["w"])}</p>' if c.get("w") else "")
                     + f'<p><small>Sources: {fontes} · <a href="/noticias/{C["mapa"][n["id"]]}/" hreflang="pt-BR">Leia em português</a></small></p>')
    corpo.append('<p><small>Translated with the help of AI from the Portuguese edition. In Brazil, call 190 (police) in an emergency, '
                 '180 (women\'s helpline) or 100 (human rights and children). More data: <a href="/leis/">laws</a>, '
                 '<a href="/indicadores/">key figures</a> (in Portuguese).</small></p>')
    pasta = C["OUT"] / "en"
    pasta.mkdir(exist_ok=True)
    h = C["pagina_simples"]("/en/", "Women and children in Brazil: news and analysis",
                            "Violence against women and child protection in Brazil in English: the latest news, laws, public programs and why they matter, from Observatório Brasil Mulher.",
                            "".join(corpo), C["css"], C["topo"], C["footer"], [("Observatório", "/"), ("English", "/en/")])
    h = h.replace('<html lang="pt-BR"', '<html lang="en"', 1).replace('"inLanguage": "pt-BR"', '"inLanguage": "en"')
    h = h.replace("</head>", f'<link rel="alternate" hreflang="pt-BR" href="{C["D"]}/"><link rel="alternate" hreflang="en" href="{C["D"]}/en/"></head>', 1)
    (pasta / "index.html").write_text(h, encoding="utf-8")
    return ["/en/"]


# ---------------------------------------------------------------- onde buscar ajuda
def ajuda(C):
    fs = _ler(C, "ajuda.json")
    if not fs:
        return []
    e = C["esc"]
    cats = {}
    for f in fs:
        cats.setdefault(f["categoria"], []).append(f)
    corpo = [f'<p class="lead">{len(fs)} canais, serviços e organizações para quem sofre violência ou quer ajudar alguém, '
             'em todo o Brasil: o que cada um faz, como acionar e quando funciona. Todos os contatos foram conferidos nas fontes oficiais.</p>',
             URGENTE,
             '<nav class="az" aria-label="Categorias">' + "".join(
                 f'<a href="#c-{i}">{e(c)}</a>' for i, c in enumerate(cats)) + "</nav>"]
    for i, (c, itens) in enumerate(cats.items()):
        itens.sort(key=lambda f: (f.get("abrangencia") != "Nacional", f["nome"].lower()))
        corpo.append(f'<h2 id="c-{i}">{e(c)}</h2><div class="cards-d">' + "".join(
            f'<div><h3>{_link(C, f["url"], f["nome"])}</h3>'
            + (f'<p class="contato">{e(f["contato"])}</p>' if f.get("contato") else "")
            + f'<p>{e(f.get("descricao", ""))}</p>'
            + (f'<p><b>Para quem:</b> {e(f["para_quem"])}</p>' if f.get("para_quem") else "")
            + f'<small>{e(f.get("responsavel", ""))} · {e(f.get("abrangencia", ""))}'
            f'{(" · " + e(f["funciona"])) if f.get("funciona") else ""}{" · gratuito" if f.get("gratuito") else ""}</small></div>'
            for f in itens) + "</div>")
    corpo.append('<p><small>Lista editorial, conferida nas fontes oficiais. Horários e contatos podem mudar: em caso de dúvida, '
                 'ligue 180. Para sugerir um serviço da sua cidade, escreva para a redação.</small></p>')
    _gravar(C, "/ajuda/", "Onde buscar ajuda: Ligue 180, 190, Disque 100 e mais",
            "Canais de emergência e denúncia, serviços de atendimento, saúde e organizações para mulheres e crianças em situação de violência no Brasil.",
            "".join(corpo), [("Onde buscar ajuda", "/ajuda/")], largo=True)
    return ["/ajuda/"]


# ---------------------------------------------------------------- vagas e oportunidades
def _vagas(C, dias=45):
    corte = (date.today() - timedelta(days=dias)).isoformat()
    return [n for n in _noticias_rede(C) if n.get("oport") and n.get("brasil") and n["data"] >= corte]


def oportunidades(C):
    progs = _ler(C, "oportunidades.json", []) or []
    vagas = _vagas(C)
    if not progs and not vagas:
        return []
    e = C["esc"]
    corpo = [f'<p class="lead">Vagas de emprego, cursos gratuitos, editais, bolsas e crédito para mulheres e jovens no Brasil: '
             f'{len(vagas)} oportunidades divulgadas nos últimos 45 dias, coletadas automaticamente de órgãos públicos e da imprensa, '
             f'e {len(progs)} programas permanentes conferidos nos sites oficiais. Autonomia financeira é parte da proteção: '
             'com renda própria, sair de uma relação violenta fica mais possível.</p>',
             '<p><b>Atenção a golpes:</b> vaga ou curso de verdade não cobra taxa para inscrição nem pede senha ou dados bancários. '
             'Confira sempre no site oficial de quem oferece.</p>']
    if vagas:
        regs = {}
        for n in vagas:
            for r in (n.get("regioes") or [n.get("fonte_regiao") or "Nacional"]):
                regs.setdefault(r or "Nacional", []).append(n)
        corpo.append('<h2>Abertas agora</h2><nav class="az" aria-label="Regiões">' + "".join(
            f'<a href="#r-{i}">{e(r)} ({len(v)})</a>' for i, (r, v) in enumerate(sorted(regs.items()))) + "</nav>")
        for i, (r, itens) in enumerate(sorted(regs.items())):
            corpo.append(f'<h3 id="r-{i}">{e(r)}</h3><ul class="lista-noticias">' + "".join(
                f'<li>{_link(C, n["link"], n["titulo"])}<p>{e(n["fonte"])}{(" · " + ", ".join(n["ufs"])) if n.get("ufs") else ""} · {_data(n["data"])}</p></li>'
                for n in itens[:25]) + "</ul>")
    if progs:
        cats = {}
        for p in progs:
            cats.setdefault(p["categoria"], []).append(p)
        corpo.append("<h2>Programas permanentes</h2>")
        for c, itens in cats.items():
            corpo.append(f'<h3>{e(c)}</h3><div class="cards-d">' + "".join(
                f'<div><h3>{_link(C, p["url"], p["nome"])}</h3><p>{e(p.get("descricao", ""))}</p>'
                + (f'<p><b>Para quem:</b> {e(p["para_quem"])}</p>' if p.get("para_quem") else "")
                + (f'<p><b>Como acessar:</b> {e(p["como_acessar"])}</p>' if p.get("como_acessar") else "")
                + f'<small>{e(p.get("responsavel", ""))} · {e(p.get("abrangencia", ""))}{" · gratuito" if p.get("gratuito") else ""}</small></div>'
                for p in itens) + "</div>")
    corpo.append('<p><small>As vagas e cursos são divulgados pelos órgãos e veículos de origem; prazos e requisitos estão no link de cada um. '
                 'Para divulgar uma oportunidade para mulheres, escreva para a redação.</small></p>')
    _gravar(C, "/oportunidades/", "Vagas e oportunidades para mulheres e jovens",
            "Vagas de emprego, cursos gratuitos, editais, bolsas, crédito e programas de renda para mulheres e jovens no Brasil, atualizados de hora em hora, com link oficial.",
            "".join(corpo), [("Vagas e oportunidades", "/oportunidades/")], largo=True)
    return ["/oportunidades/"]


# ---------------------------------------------------------------- em votação e participe
ETAPAS = ["Pronto para votação no Plenário", "Aprovado na Câmara", "Pronto para votação na comissão",
          "Em análise nas comissões", "Em tramitação"]


def em_votacao(C):
    leg = _ler(C, "legislativo.json", {}) or {}
    ps = leg.get("projetos") or []
    if not ps:
        return []
    e = C["esc"]
    tema = {"mulheres": "Mulheres", "criancas": "Crianças"}
    cont = {t: sum(1 for p in ps if p["etapa"] == t) for t in ETAPAS}
    corpo = [f'<p class="lead">{len(ps)} projetos de lei sobre mulheres e crianças tiveram andamento na Câmara dos Deputados nos últimos '
             f'quatro meses. {cont["Pronto para votação no Plenário"] + cont["Pronto para votação na comissão"]} estão prontos para votação. '
             'Leia o texto, acompanhe a tramitação e dê a sua opinião na enquete oficial da Câmara: os deputados consultam o resultado. '
             f'Atualizado automaticamente em {_data(leg.get("gerado_em"))}.</p>',
             '<p>Quer propor uma lei ou apoiar uma ideia? Veja <a href="/participe/">Participe: abaixo-assinados e consultas</a>. '
             'As leis que já valem estão em <a href="/leis/">Leis</a>.</p>',
             '<nav class="az" aria-label="Etapas">' + "".join(f'<a href="#e-{i}">{e(t)} ({cont[t]})</a>' for i, t in enumerate(ETAPAS) if cont[t]) + "</nav>"]
    for i, t in enumerate(ETAPAS):
        itens = [p for p in ps if p["etapa"] == t]
        if not itens:
            continue
        limite = 150
        corpo.append(f'<h2 id="e-{i}">{e(t)} <small>({len(itens)})</small></h2>' + _tabela(
            ["Projeto", "O que propõe", "Onde está", "Participe"],
            [[f'<b>{_link(C, p["url"], p["sigla"])}</b><br><small>{tema.get(p["tema"], "")}</small>',
              e(p["ementa"][:260]) + ("…" if len(p["ementa"]) > 260 else ""),
              f'{e(p["situacao"])}<br><small>{e(p["orgao"])} · {_data(p["data_situacao"])}{(" · " + e(p["regime"])) if "rg" in p["regime"].lower() else ""}</small>',
              f'<a class="pill cheia" href="{e(p["enquete"])}" target="_blank" rel="noopener">Votar na enquete</a>'
              + (_link(C, p["teor"], "Ler o texto") if p.get("teor") else "")]
             for p in itens[:limite]]))
        if len(itens) > limite:
            corpo.append(f'<p><small>Mostrando os {limite} com andamento mais recente.</small></p>')
    corpo.append('<p><small>Fonte: Câmara dos Deputados, API de Dados Abertos. A busca é feita por palavras-chave na ementa e pode '
                 'incluir projetos que tocam o tema de forma indireta. O Senado entra assim que a API de dados abertos dele voltar a responder.</small></p>')
    _gravar(C, "/em-votacao/", "Projetos de lei em votação sobre mulheres e crianças",
            "Projetos de lei sobre violência contra a mulher, Lei Maria da Penha, feminicídio e ECA em andamento na Câmara, com situação e link para votar na enquete.",
            "".join(corpo), [("Em votação", "/em-votacao/")], largo=True)
    return ["/em-votacao/"]


def participe(C):
    pa = _ler(C, "participacao.json", {}) or {}
    if not pa.get("iniciativas") and not pa.get("canais"):
        return []
    e = C["esc"]
    ini = pa.get("iniciativas") or []
    corpo = ['<p class="lead">Leis mudam quando as pessoas participam. Aqui estão os canais oficiais para propor e apoiar leis de proteção '
             f'a mulheres e crianças e {len(ini)} iniciativas abertas agora: ideias legislativas, consultas públicas e abaixo-assinados.</p>',
             '<p><b>Cuidado com seus dados:</b> só assine em sites oficiais ou de organizações que você conhece. Nenhuma iniciativa séria pede '
             'senha ou pagamento. Veja também os <a href="/em-votacao/">projetos em votação</a>, com enquete oficial da Câmara.</p>']
    if pa.get("canais"):
        corpo.append('<h2>Como participar</h2><div class="cards-d">' + "".join(
            f'<div><h3>{_link(C, c["url"], c["nome"])}</h3><p>{e(c.get("descricao", ""))}</p>'
            + (f'<p><b>Como funciona:</b> {e(c["como_funciona"])}</p>' if c.get("como_funciona") else "")
            + f'<small>{e(c.get("responsavel", ""))}</small></div>' for c in pa["canais"]) + "</div>")
    for titulo, oficial in (("Iniciativas oficiais abertas", True), ("Abaixo-assinados da sociedade civil", False)):
        its = [i for i in ini if bool(i.get("oficial")) == oficial]
        if not its:
            continue
        its.sort(key=lambda i: -(i.get("apoios") or 0))
        corpo.append(f'<h2>{titulo} <small>({len(its)})</small></h2>'
                     + ('' if oficial else '<p><small>Iniciativas de terceiros, listadas por tratarem de leis de proteção. '
                        'O Observatório não organiza nem endossa as petições.</small></p>')
                     + '<div class="cards-d">' + "".join(
            f'<div><span class="etq">{e(i.get("tipo", ""))}</span><span class="etq">{e(i.get("plataforma", ""))}</span>'
            f'<h3>{_link(C, i["url"], i["titulo"])}</h3><p>{e(i.get("resumo", ""))}</p>'
            f'<p><a class="pill cheia" href="{e(i["url"])}" target="_blank" rel="noopener">{"Apoiar" if i.get("tipo") in ("Ideia legislativa", "Abaixo-assinado") else "Participar"}</a></p>'
            + (f'<p class="valor">{i["apoios"]:,}'.replace(",", ".") + ' apoios</p>' if isinstance(i.get("apoios"), int) else "")
            + (f'<p><b>Meta:</b> {e(i["meta"])}</p>' if i.get("meta") else "")
            + f'<small>{("Até " + _data(i["prazo"])) if i.get("prazo") else "Sem prazo informado"}{(" · " + e(i["autor"])) if i.get("autor") else ""}'
            f' · conferido em {_data(i.get("verificado_em"))}</small></div>' for i in its) + "</div>")
    _gravar(C, "/participe/", "Participe: abaixo-assinados e consultas por leis",
            "Ideias legislativas, consultas públicas, enquetes e abaixo-assinados abertos por leis de proteção a mulheres e crianças, com os canais oficiais para participar.",
            "".join(corpo), [("Participe", "/participe/")], largo=True)
    return ["/participe/"]


# ---------------------------------------------------------------- quem propõe: parlamentares
AVISO_PARL = ('Lista por <b>autoria de projetos de lei</b> sobre mulheres e crianças apresentados na Câmara desde fevereiro de 2023, '
              'com dados oficiais da própria Câmara, pelo mesmo critério para todos os partidos. Quantidade de projetos não mede '
              'qualidade nem resultado, e esta lista não é recomendação de voto.')


def _parl_dados(C):
    import unicodedata
    b = _ler(C, "autoria.json", {}) or {}
    projs, deps = b.get("projetos") or {}, b.get("deputados") or {}
    perfil = {}
    for pid, p in projs.items():
        for a in p["autores"]:
            r = perfil.setdefault(str(a), {"princ": [], "coaut": []})
            (r["princ"] if a in p["principal"] else r["coaut"]).append({**p, "id": pid})
    saida = []
    for did, r in perfil.items():
        d = deps.get(did)
        if not d or not r["princ"]:
            continue
        todos = r["princ"] + r["coaut"]
        slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", d["nome"].lower()).encode("ascii", "ignore").decode()).strip("-")
        saida.append({**d, "id": did, "slug": f"{slug}-{did}",
                      "princ": sorted(r["princ"], key=lambda p: p["apresentacao"], reverse=True),
                      "coaut": sorted(r["coaut"], key=lambda p: p["apresentacao"], reverse=True),
                      "leis": sum(1 for p in todos if p.get("lei")),
                      "criancas": sum(1 for p in r["princ"] if p["tema"] == "criancas")})
    saida.sort(key=lambda d: (-len(d["princ"]), -d["leis"], d["nome"]))
    return saida, b


def _foto_parl(C, d):
    """Foto oficial da Câmara (baixada pelo coletor/parlamentares.py em data/parlamentares-fotos), servida pelo próprio site."""
    arq = C["ROOT"] / "data" / "parlamentares-fotos" / f'{d["id"]}.jpg'
    if not arq.exists():
        return ""
    destino = C["OUT"] / "img" / "parlamentares"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / arq.name).write_bytes(arq.read_bytes())
    return f'/img/parlamentares/{arq.name}'


def _cartao_parl(C, d, foto):
    e = C["esc"]
    n = len(d["princ"])
    lei = (f'<span class="parl-lei">{d["leis"]} virou lei</span>' if d["leis"] == 1 else
           f'<span class="parl-lei">{d["leis"]} viraram lei</span>' if d["leis"] else "")
    return (f'<a class="parl" href="/parlamentares/{d["slug"]}/">'
            + (f'<img src="{foto}" alt="Foto oficial de {e(d["nome"])}" loading="lazy" width="96" height="128">' if foto else '<span class="parl-sem"></span>')
            + f'<span class="parl-in"><b>{e(d["nome"])}</b><small>{e(d["partido"])}-{e(d["uf"])}{"" if d["situacao"] == "Exercício" else " · fora do exercício"}</small>'
            f'<span class="parl-n"><em>{n}</em> projeto{"s" if n > 1 else ""} como autor{"a" if d["sexo"] == "F" else ""}</span>{lei}</span></a>')


def parlamentares(C):
    lista, b = _parl_dados(C)
    if not lista:
        return []
    e = C["esc"]
    fotos = {d["id"]: _foto_parl(C, d) for d in lista}
    mulheres = sum(1 for d in lista if d["sexo"] == "F")
    leis = [p for p in (b.get("projetos") or {}).values() if p.get("lei")]
    corpo = [f'<p class="lead">{len(lista)} deputadas e deputados federais apresentaram, como autores principais, projetos de lei sobre a proteção '
             f'de mulheres e crianças nesta legislatura ({mulheres} são mulheres). Ao todo, {len(b.get("projetos") or {})} projetos do tema; '
             f'{len(leis)} já viraram lei. Clique em cada nome para ver os projetos, a situação de cada um e o histórico.</p>',
             f'<p><small>{AVISO_PARL} Fotos: Câmara dos Deputados. Atualizado em {_data(b.get("gerado_em"))}.</small></p>',
             '<nav class="az" aria-label="Filtros"><a href="#com-leis">Com projetos que viraram lei</a><a href="#todos">Todos</a></nav>']
    com_lei = [d for d in lista if d["leis"]]
    if com_lei:
        corpo.append(f'<h2 id="com-leis">Com projetos que viraram lei ({len(com_lei)})</h2><div class="parls">'
                     + "".join(_cartao_parl(C, d, fotos[d["id"]]) for d in com_lei) + "</div>")
    corpo.append(f'<h2 id="todos">Todos, por número de projetos ({len(lista)})</h2><div class="parls">'
                 + "".join(_cartao_parl(C, d, fotos[d["id"]]) for d in lista) + "</div>")
    corpo.append('<p>Veja também os <a href="/em-votacao/">projetos em votação</a>, com enquete oficial, e as <a href="/leis/">leis em vigor</a>. '
                 'Os senadores entram assim que a API de dados abertos do Senado voltar a responder.</p>')
    _gravar(C, "/parlamentares/", "Quem propõe leis para mulheres e crianças na Câmara",
            "Deputadas e deputados federais que apresentaram projetos de lei sobre violência contra a mulher, Lei Maria da Penha e infância, com foto, projetos e histórico.",
            "".join(corpo), [("Quem propõe", "/parlamentares/")], largo=True)
    urls = ["/parlamentares/"]

    def linha(p):
        selo = '<span class="sit vig">Virou lei</span> ' if p.get("lei") else f'<span class="sit">{e(p["situacao"] or "Em tramitação")}</span> '
        url = f'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p["id"]}'
        votar = ("" if p.get("lei") or re.search(r"arquiv", p["situacao"], re.I)
                 else f' <a class="pill cheia" href="https://www.camara.leg.br/enquetes/{p["id"]}" target="_blank" rel="noopener">Votar na enquete</a>')
        return (f'<li>{selo}<b>{_link(C, url, p["sigla"])}</b> <small>{_data(p["apresentacao"])}</small>'
                f'<p>{e(p["ementa"][:300])}{"…" if len(p["ementa"]) > 300 else ""}</p>{votar}</li>')

    for d in lista:
        foto = fotos[d["id"]]
        anos = {}
        for p in d["princ"]:
            anos.setdefault(p["apresentacao"][:4], []).append(p)
        info = [x for x in (("Nome civil", d["nome_civil"].title()), ("Partido e estado", f'{d["partido"]}-{d["uf"]}'),
                            ("Situação", d["situacao"]), ("Naturalidade", d["naturalidade"]), ("Escolaridade", d["escolaridade"]),
                            ("Profissões", ", ".join(d["profissoes"])), ("E-mail do gabinete", d["email"])) if x[1]]
        corpo = ['<div class="parl-top">' + (f'<img src="{foto}" alt="Foto oficial de {e(d["nome"])}" width="150" height="200">' if foto else "")
                 + '<dl>' + "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in info) + "</dl></div>",
                 f'<div class="cards-d stats-d"><div><span class="num">{len(d["princ"])}</span><h3>projetos como autor principal</h3><p>{d["criancas"]} sobre crianças e adolescentes</p></div>'
                 f'<div><span class="num">{len(d["coaut"])}</span><h3>como coautor</h3><p>projetos de outros parlamentares que também assinou</p></div>'
                 f'<div><span class="num">{d["leis"]}</span><h3>viraram lei</h3><p>entre os projetos que assinou</p></div></div>',
                 f'<p>{_link(C, "https://www.camara.leg.br/deputados/" + d["id"], "Perfil completo na Câmara")}</p>',
                 '<h2>Histórico no tema: projetos como autor principal</h2>']
        for ano in sorted(anos, reverse=True):
            corpo.append(f'<h3>{ano} <small>({len(anos[ano])})</small></h3><ul class="lista-noticias">' + "".join(linha(p) for p in anos[ano]) + "</ul>")
        if d["coaut"]:
            corpo.append(f'<h2>Como coautor ({len(d["coaut"])})</h2><ul class="lista-noticias">' + "".join(linha(p) for p in d["coaut"][:40]) + "</ul>")
        corpo.append(f'<p><small>{AVISO_PARL} Foto: Câmara dos Deputados.</small></p><p><a href="/parlamentares/">Ver todos os parlamentares</a></p>')
        artigo = "da deputada" if d["sexo"] == "F" else "do deputado"
        titulo = f'{d["nome"]} ({d["partido"]}-{d["uf"]}): projetos para mulheres'
        _gravar(C, f'/parlamentares/{d["slug"]}/', titulo[:66],
                (f'Projetos de lei {artigo} {d["nome"]} ({d["partido"]}-{d["uf"]}) sobre a proteção de mulheres e crianças: '
                 f'{len(d["princ"])} como autor principal, situação de cada um e histórico.')[:168],
                "".join(corpo), [("Quem propõe", "/parlamentares/"), (d["nome"], f'/parlamentares/{d["slug"]}/')], largo=True)
        urls.append(f'/parlamentares/{d["slug"]}/')
    return urls


def parlamentares_capa(C):
    """Faixa da capa com os rostos de quem mais propõe leis do tema."""
    lista, b = _parl_dados(C)
    if not lista:
        return ""
    pasta = C["ROOT"] / "data" / "parlamentares-fotos"
    cartoes = "".join(_cartao_parl(C, d, f'/img/parlamentares/{d["id"]}.jpg' if (pasta / f'{d["id"]}.jpg').exists() else "")
                      for d in lista[:8])
    return ('<section class="sec gray" id="parlamentares"><div class="wrap"><div class="sh"><div><span class="eye">Dados oficiais da Câmara</span>'
            '<h2>Quem propõe leis para mulheres e crianças</h2>'
            f'<p>{len(lista)} deputadas e deputados apresentaram projetos do tema nesta legislatura. Veja os projetos, a situação e o histórico de cada um.</p></div>'
            '<a class="lnk" href="/parlamentares/">Ver todos <svg class="ic"><use href="#i-arrow"/></svg></a></div>'
            f'<div class="parls">{cartoes}</div><p class="note">{AVISO_PARL}</p></div></section>')


# ---------------------------------------------------------------- projetos sociais
def projetos(C):
    ps = _ler(C, "projetos.json", []) or []
    if not ps:
        return []
    e = C["esc"]
    cats = {}
    for p in ps:
        cats.setdefault(p["categoria"], []).append(p)
    ufs = sorted({p.get("uf") for p in ps if p.get("uf") and p.get("uf") != "Nacional"})
    corpo = [f'<p class="lead">{len(ps)} projetos sociais e organizações que protegem, acolhem e abrem oportunidades para mulheres e '
             f'protegem crianças e adolescentes, com atuação nacional e em {len(ufs)} estados. O que cada um oferece a quem precisa e '
             'como apoiar. Todos conferidos nos sites oficiais.</p>', URGENTE,
             '<nav class="az" aria-label="Categorias">' + "".join(f'<a href="#p-{i}">{e(c)}</a>' for i, c in enumerate(cats)) + "</nav>"]
    for i, (c, itens) in enumerate(cats.items()):
        itens.sort(key=lambda p: (p.get("uf") != "Nacional", p.get("uf") or "", p["nome"].lower()))
        corpo.append(f'<h2 id="p-{i}">{e(c)} <small>({len(itens)})</small></h2><div class="cards-d">' + "".join(
            f'<div><h3>{_link(C, p["url"], p["nome"])}</h3><p>{e(p.get("descricao", ""))}</p>'
            + (f'<p><b>Como ajuda:</b> {e(p["como_ajuda"])}</p>' if p.get("como_ajuda") else "")
            + (f'<p><b>Como apoiar:</b> {e(p["como_apoiar"])}</p>' if p.get("como_apoiar") else "")
            + f'<small>{e(p.get("responsavel", ""))} · {e(p.get("cidade") + " (" + p["uf"] + ")" if p.get("cidade") else p.get("uf", ""))}'
            + (f' · {_link(C, p["instagram"], "Instagram")}' if p.get("instagram") else "") + "</small></div>"
            for p in itens) + "</div>")
    corpo.append('<p><small>Lista editorial, sem patrocínio. Conhece um projeto que deveria estar aqui? Escreva para a redação.</small></p>')
    _gravar(C, "/projetos/", "Projetos sociais para mulheres e crianças no Brasil",
            "Projetos sociais e organizações que acolhem, protegem e abrem oportunidades para mulheres e crianças em todo o Brasil: o que oferecem e como apoiar.",
            "".join(corpo), [("Projetos sociais", "/projetos/")], largo=True)
    return ["/projetos/"]


# ---------------------------------------------------------------- guias práticos
def guias(C):
    gs = _ler(C, "guias.json")
    if not gs:
        return []
    e = C["esc"]
    urls = []
    for g in gs:
        corpo = [f'<p class="lead">{e(g["intro"])}</p>',
                 '<div class="share"><button type="button" data-ouvir="▶ Ouvir o guia" hidden>▶ Ouvir o guia</button></div>', URGENTE]
        for sec in g.get("secoes", []):
            corpo.append(f'<h2>{e(sec["titulo"])}</h2>' + "".join(f"<p>{e(x)}</p>" for x in sec.get("paragrafos", []))
                         + ("<ul>" + "".join(f"<li>{e(x)}</li>" for x in sec["lista"]) + "</ul>" if sec.get("lista") else ""))
        if g.get("sinais"):
            corpo.append("<h2>Sinais de alerta</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in g["sinais"]) + "</ul>")
        if g.get("o_que_fazer"):
            corpo.append("<h2>O que fazer, passo a passo</h2><ol>" + "".join(f"<li>{e(x)}</li>" for x in g["o_que_fazer"]) + "</ol>")
        if g.get("onde_buscar"):
            corpo.append("<h2>Onde buscar ajuda</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in g["onde_buscar"]) + "</ul>")
        outros = " · ".join(f'<a href="/guias/{o["slug"]}/">{e(o["publico"])}</a>' for o in gs if o["slug"] != g["slug"])
        corpo.append(f'<p>Outros guias: {outros}. Veja também o <a href="/glossario/">glossário</a> e as '
                     '<a href="/leis/">leis de proteção</a>.</p>')
        titulo = g["titulo"] if 30 <= len(g["titulo"]) <= 66 else f'Guia prático: {g["publico"]}'[:66]
        _gravar(C, f'/guias/{g["slug"]}/', titulo, g["descricao"][:168], "".join(corpo),
                [("Guias práticos", "/guias/"), (g["publico"], f'/guias/{g["slug"]}/')],
                ld_extra=[{"@type": "Article", "headline": titulo, "description": g["descricao"], "inLanguage": "pt-BR",
                           "author": {"@id": C["D"] + "/#org"}, "publisher": {"@id": C["D"] + "/#org"}}])
        urls.append(f'/guias/{g["slug"]}/')
    _gravar(C, "/guias/", "Guias práticos: proteção de mulheres e crianças",
            "Guias práticos para quem sofre violência, para quem quer ajudar, para famílias, escolas, empresas, profissionais de saúde e gestores públicos.",
            '<p class="lead">O que fazer diante da violência contra mulheres e crianças: sinais de alerta, passo a passo, direitos e onde buscar ajuda, '
            'em guias escritos para cada público.</p><ul class="lista-noticias">' + "".join(
                f'<li><a href="/guias/{g["slug"]}/">{e(g["titulo"])}</a><p>{e(g["descricao"])}</p></li>' for g in gs) + "</ul>",
            [("Guias práticos", "/guias/")])
    return ["/guias/"] + urls


# ---------------------------------------------------------------- quem protege (capa)
# serviço da rede (nome em data/ajuda.json) -> foto (src/img), ícone (símbolo do portal) e cor da editoria
SERVICOS = [
    (r"^Casa da Mulher Brasileira", "cmb-fachada-df", "I", "--i"),
    (r"^Delegacia Especializada", "deam-viatura-df", "N", "--n"),
    (r"^Patrulha Maria da Penha", "delegacia-viatura", "N", "--n"),
    (r"^Juizado", "cmb-sala-audiencias", "L", "--l"),
    (r"^Defensoria", "forum-fachada-letreiro", "L", "--l"),
    (r"^Minist[eé]rio P[uú]blico", "mpmg-sede", "L", "--l"),
    (r"^Centro de Refer[eê]ncia Especializado", "crm-centro-referencia-mesa", "I", "--i"),
    (r"^Conselho Tutelar", "conselho-tutelar-sede", "A", "--a"),
    (r"^Atendimento a v[ií]timas de viol[eê]ncia sexual", "hospital-da-mulher-sbc", "H", "--h"),
]
ESFERA_ICONE = {"Federal": ("P", "--p"), "Estadual": ("L", "--l"), "Internacional": ("S", "--s"), "Sociedade civil": ("G", "--g")}


def _credito(C, foto):
    c = (C.get("CR") or {}).get(foto)
    return f'<span class="credit">Foto: {_link(C, c[2], c[0])} / {C["esc"](c[1])}</span>' if c else ""


def instituicoes_hero(C):
    """Destaque da capa "A rede de proteção no Brasil": os serviços onde a rede atende (data/ajuda.json),
    com foto e ícone, e as instituições que coordenam e fiscalizam (data/instituicoes.json), com a última notícia."""
    e = C["esc"]
    aj = _ler(C, "ajuda.json", []) or []
    ins = _ler(C, "instituicoes.json", []) or []
    rede = _noticias_rede(C)
    if not aj and not ins:
        return ""
    servicos = []
    for padrao, foto, ic, cor in SERVICOS:
        a = next((x for x in aj if re.search(padrao, x["nome"], re.I)), None)
        if not a or not (C["ROOT"] / "src" / "img" / f"{foto}.jpg").exists():
            continue
        nome = re.sub(r"\s*\((Deam|Creas)\)$", "", a["nome"])
        servicos.append(
            f'<article class="svc" style="--c:var({cor})"><div class="svc-ph"><img src="/img/{foto}.webp" alt="" loading="lazy">{_credito(C, foto)}'
            f'<span class="svc-ic" aria-hidden="true"><svg><use href="#i-ed-{ic}"/></svg></span></div>'
            f'<div class="svc-in"><h3>{e(nome)}</h3><p>{e(a.get("descricao", ""))}</p>'
            + (f'<p class="svc-ct"><b>Como chegar:</b> {e(a["contato"])}</p>' if a.get("contato") else "")
            + f'<a class="svc-go" href="{e(a["url"])}" target="_blank" rel="noopener">Saiba mais ↗</a></div></article>')
    orgaos = []
    for i in ins:
        rx = re.compile(i["padrao"], re.I) if i.get("padrao") else None
        ult = next((n for n in rede if rx and rx.search(n["titulo"] + " " + n["fonte"])), None)
        ic, cor = ESFERA_ICONE.get(i.get("esfera"), ("P", "--p"))
        orgaos.append(
            f'<article class="org" style="--c:var({cor})"><header><span class="org-ic" aria-hidden="true"><svg><use href="#i-ed-{ic}"/></svg></span>'
            f'<div><h3>{e(i["nome"])}</h3><small>{e(i.get("esfera", ""))} · {e(i.get("tipo", ""))}</small></div></header>'
            f'<p>{e(i.get("descricao", ""))}</p>'
            + (f'<p class="org-canal"><b>Como acionar:</b> {e(i["canal"])}</p>' if i.get("canal") else "")
            + f'<a class="svc-go" href="{e(i["url"])}" target="_blank" rel="noopener">Site oficial ↗</a>'
            + (f'<a class="org-ult" href="{e(ult["link"])}" target="_blank" rel="noopener"><small>Última notícia · {_data(ult["data"])}</small>{e(ult["titulo"])}</a>' if ult else "")
            + "</article>")
    return ('<section class="sec rede-sec" id="rede"><div class="wrap">'
            '<div class="sh"><div><span class="eye">Para não enfrentar sozinha</span><h2>A rede de proteção no Brasil</h2>'
            '<p>Onde mulheres, crianças e adolescentes são atendidos depois de pedir ajuda, e quem coordena, julga e fiscaliza. '
            'Em perigo agora, ligue <b>190</b>. Orientação 24 horas: <b>Ligue 180</b>. Crianças e adolescentes: <b>Disque 100</b>.</p></div>'
            '<a class="lnk" href="/ajuda/">Todos os serviços e contatos <svg class="ic"><use href="#i-arrow"/></svg></a></div>'
            + (f'<h3 class="rede-sub">Onde a rede atende</h3><div class="svcs">{"".join(servicos)}</div>' if servicos else "")
            + (f'<h3 class="rede-sub">Quem coordena, julga e fiscaliza</h3><div class="orgs">{"".join(orgaos)}</div>'
               '<p class="rede-mais"><a href="/instituicoes/">Ver todas as instituições</a> · <a href="/projetos/">Projetos sociais que acolhem</a></p>' if orgaos else "")
            + '</div></section>')


# ---------------------------------------------------------------- verticais (infância, segurança, amparo, saúde)
VERTICAIS = [
    {"slug": "infancia", "nome": "Infância", "foto": "parquinho-praca", "ed": "A",
     "titulo": "Proteção da infância no Brasil: ECA, abuso e direitos",
     "desc": "Crianças e adolescentes no Brasil: violência sexual, maus-tratos, violência online, trabalho infantil, ECA, Conselhos Tutelares, programas e leis.",
     "intro": "Violência sexual, maus-tratos, aliciamento na internet, trabalho infantil e o papel de escolas, famílias e Conselhos Tutelares: como o Brasil protege (e ainda falha em proteger) crianças e adolescentes, o que diz a lei e quem está agindo.",
     "re": r"crian[cç]a|infantil|inf[aâ]ncia|adolescen|menor de idade|menina|menino|beb[eê]|\bECA\b|conselho tutelar|estupro de vulner[aá]vel|pedofil|explora[cç][aã]o sexual|trabalho infantil|escola|estudante|creche",
     "setor": r"educa|crian|inf[aâ]n|adolesc|escola",
     "publico": ("criancas", "ambos")},
    {"slug": "seguranca", "nome": "Segurança", "foto": "deam-viatura-df", "ed": "N",
     "titulo": "Feminicídio e segurança das mulheres no Brasil",
     "desc": "Feminicídios, violência doméstica, medidas protetivas, delegacias da mulher, Patrulha Maria da Penha e monitoramento: notícias, dados e leis no Brasil.",
     "intro": "Feminicídios, agressões, ameaças e perseguição: como polícias, delegacias da mulher, Patrulhas Maria da Penha e a Justiça respondem à violência, o que funciona e o que dizem os dados.",
     "re": r"feminic[ií]d|femic[ií]d|viol[eê]ncia dom[eé]stica|medidas? protetivas?|delegacia|\bDEAM|pol[ií]cia|patrulha maria da penha|tornozeleira|agress|amea[cç]|persegui|stalking|assassin|mort[ao]\b|matou",
     "setor": r"seguran|pol[ií]c|justi",
     "publico": ("mulheres", "ambos")},
    {"slug": "amparo", "nome": "Amparo", "foto": "cmb-fachada-df", "ed": "I",
     "titulo": "Rede de amparo: Casa da Mulher Brasileira, abrigos e apoio",
     "desc": "A rede de amparo a mulheres em situação de violência no Brasil: Casa da Mulher Brasileira, centros de referência, abrigos, Ligue 180, auxílio e programas.",
     "intro": "Quem acolhe depois da denúncia: Casas da Mulher Brasileira, centros de referência, casas-abrigo, atendimento psicológico e jurídico, auxílio-aluguel e programas de autonomia. Onde a rede chega, onde falta e quem está investindo.",
     "re": r"casa da mulher brasileira|abrigo|acolhiment|centro de refer[eê]ncia|\bCRAM\b|\bCREAS\b|\bCRAS\b|ligue 180|disque 100|rede de (prote[cç][aã]o|atendimento|enfrentamento)|amparo|aux[ií]lio|atendimento",
     "setor": r"assist|sociedade civil|amparo|acolh",
     "publico": ("mulheres", "ambos")},
    {"slug": "saude", "nome": "Saúde", "foto": "hospital-da-mulher-sbc", "ed": "H",
     "titulo": "Saúde da mulher no Brasil: violência, parto e direitos",
     "desc": "Saúde da mulher e da criança no Brasil: atendimento a vítimas de violência sexual, violência obstétrica, saúde materna, aborto legal, SUS e leis.",
     "intro": "O atendimento a vítimas de violência no SUS, a violência obstétrica, a mortalidade materna, o aborto nos casos previstos em lei e a saúde mental: o que garante a lei, o que acontece nos serviços e o que muda.",
     "re": r"sa[uú]de|\bSUS\b|hospital|m[eé]dic|maternidade|gestante|gravidez|gr[aá]vida|parto|obst[eé]tric|aborto|pr[eé]-natal|mortalidade materna|menstrua",
     "setor": r"sa[uú]de",
     "publico": ("mulheres", "criancas", "ambos")},
]


def verticais(C):
    e = C["esc"]
    intel = _ler(C, "inteligencia.json", {}) or {}
    reg = _ler(C, "leis.json", {}) or {}
    rede = _noticias_rede(C)
    urls = []
    for v in VERTICAIS:
        rx, rs = (re.compile(v[k], re.I) for k in ("re", "setor"))
        nots = [n for n in rede if n.get("editoria") == v["ed"] or rx.search(n["titulo"])]
        br = [n for n in nots if n.get("brasil")]
        dest = [n for n in C["N"] if n.get("e") == v["ed"] or rx.search(n["h"] + " " + n["t"])][:8]
        prog = [p for p in intel.get("programas", []) if rx.search((p.get("nome") or "") + " " + (p.get("descricao") or ""))]
        ini = [c for c in intel.get("iniciativas", []) if rs.search(c.get("setor") or "") or rx.search(c.get("descricao") or "")]
        nor = [n for n in reg.get("normas", []) if n.get("publico") in v["publico"] and rx.search(n["nome"] + " " + n["resumo"])]
        corpo = [f'<p class="lead">{e(v["intro"])}</p>', URGENTE,
                 f'<div class="cards-d stats-d"><div><span class="num">{len(nots)}</span><h3>notícias no repositório</h3><p>{len(br)} sobre o Brasil</p></div>'
                 f'<div><span class="num">{len(prog)}</span><h3>programas e recursos</h3><p>anunciados por órgãos públicos</p></div>'
                 f'<div><span class="num">{len(ini)}</span><h3>iniciativas</h3><p>com resultado divulgado</p></div></div>']
        if dest:
            corpo.append('<h2>Destaques com análise</h2><ul class="lista-noticias">' + "".join(
                f'<li><a href="/noticias/{C["mapa"][n["id"]]}/">{e(n["h"])}</a><p>{e(n["t"][:200])}</p></li>' for n in dest) + "</ul>")
        if prog:
            corpo.append('<h2>Programas e recursos</h2><div class="cards-d">' + "".join(
                f'<div><div class="cab-lg">{logo(C, p.get("orgao"))}<h3>{e(p.get("nome") or p.get("orgao", ""))}</h3></div>'
                + (f'<p class="valor">{e(p["valor"])}</p>' if p.get("valor") else "")
                + (f'<p>{e(p["descricao"])}</p>' if p.get("descricao") else "")
                + f'<small>{_link(C, p["link"], p["fonte"])} · {_data(p["data"])}</small></div>' for p in prog[:12]) + "</div>")
        if ini:
            corpo.append('<h2>Iniciativas</h2><div class="cards-d">' + "".join(
                f'<div><div class="cab-lg">{logo(C, c.get("responsavel"))}<h3>{e(c.get("responsavel", ""))}</h3></div><p>{e(c.get("descricao", ""))}</p>'
                + (f'<p><b>Resultado:</b> {e(c["resultado"])}</p>' if c.get("resultado") else "")
                + f'<small>{_link(C, c["link"], c["fonte"])} · {_data(c["data"])}</small></div>' for c in ini[:12]) + "</div>")
        if nor:
            corpo.append('<h2>O que diz a lei</h2><div class="cards-d">' + "".join(
                f'<div><span class="sit">{e(n["situacao"])}</span><h3>{e(n["nome"])}</h3><p>{e(n["resumo"])}</p>'
                f'<small>{_link(C, n["url"], "texto oficial")}</small></div>' for n in nor) + "</div>"
                + '<p>Veja todas as <a href="/leis/">leis de proteção</a>.</p>')
        corpo.append('<h2>Últimas notícias da rede</h2><ul class="lista-noticias">' + "".join(
            f'<li>{_link(C, n["link"], n["titulo"])}<p>{e(n["fonte"])} · {_data(n["data"])}</p></li>' for n in (br or nots)[:30]) + "</ul>"
            + '<p>Busque mais no <a href="/#radar">repositório de notícias</a>.</p>')
        _gravar(C, f'/{v["slug"]}/', v["titulo"], v["desc"], "".join(corpo), [(v["nome"], f'/{v["slug"]}/')], largo=True)
        urls.append(f'/{v["slug"]}/')
    return urls


def verticais_capa(C):
    """Bloco da capa com as verticais: foto, contagem e as últimas manchetes de cada uma."""
    e = C["esc"]
    rede = _noticias_rede(C)
    blocos = []
    for v in VERTICAIS:
        rx = re.compile(v["re"], re.I)
        nots = [n for n in rede if (n.get("editoria") == v["ed"] or rx.search(n["titulo"])) and n.get("brasil")][:4]
        itens = "".join(f'<li><a href="{e(n["link"])}" target="_blank" rel="noopener">{e(n["titulo"])}</a><small>{e(n["fonte"])} · {_data(n["data"])}</small></li>' for n in nots)
        blocos.append(f'<article class="vert"><img src="/img/{v["foto"]}.webp" alt="" loading="lazy"><div class="vin">'
                      f'<span class="eye">Em foco</span><h3><a href="/{v["slug"]}/">{e(v["nome"])}</a></h3><p>{e(v["intro"][:150].rsplit(" ", 1)[0])}…</p>'
                      f'<ul>{itens}</ul><a class="btn" href="/{v["slug"]}/">Ver tudo sobre {e(v["nome"].lower())} →</a></div></article>')
    return ('<section class="sec" id="verticais"><div class="wrap"><div class="sh"><div><span class="eye">Em foco</span>'
            '<h2>Infância, segurança, amparo e saúde</h2><p>Quatro frentes da proteção de mulheres e crianças no Brasil, com notícias, programas, iniciativas e leis.</p></div></div>'
            f'<div class="verts">{"".join(blocos)}</div></div></section>')


# ---------------------------------------------------------------- números da capa
NUMEROS = [(r"^V[ií]timas de feminic[ií]dio", "#Segurança", "--n"), (r"^Crian[cç]as e adolescentes .*estupro", "#Infância", "--a"),
           (r"descumprimento de medida protetiva", "#Leis", "--l"), (r"^Atendimentos da Central Ligue 180", "#Amparo", "--i")]


def numeros_capa(C):
    """Os quatro números da faixa escura da capa, tirados de data/indicadores.json (com fonte)."""
    e = C["esc"]
    ind = _ler(C, "indicadores.json", []) or []
    saida = []
    for padrao, tag, cor in NUMEROS:
        i = next((x for x in ind if re.search(padrao, x["rotulo"], re.I)), None)
        if i:
            saida.append(f'<div class="stat" style="--c:var({cor})"><span class="tag">{tag}</span><b>{e(i["valor"])}</b>'
                         f'<p>{e(i["rotulo"])} ({e(i["fonte"])}).</p></div>')
    return "".join(saida)


# ---------------------------------------------------------------- painel da capa
def painel(C):
    """HTML do "Painel da proteção" na capa: canais de ajuda, leis, programas e agenda (gerado a cada rodada)."""
    e = C["esc"]
    intel = _ler(C, "inteligencia.json", {}) or {}
    reg = _ler(C, "leis.json", {}) or {}
    tram = _ler(C, "tramitacoes.json", {}) or {}
    evs = _ler(C, "eventos.json", []) or []
    aj = _ler(C, "ajuda.json", []) or []
    hoje = date.today().isoformat()
    colunas = []

    emerg = [a for a in aj if a.get("categoria", "").startswith("Emerg")][:4]
    if emerg:
        itens = "".join(f'<li><a href="{e(a["url"])}" target="_blank" rel="noopener"><b>{e(a.get("contato") or a["nome"])}</b></a>'
                        f'<small>{e(a["nome"])}{(" · " + e(a["funciona"])) if a.get("funciona") else ""}</small></li>' for a in emerg)
        colunas.append(("Precisa de ajuda?", "/ajuda/", "Em perigo agora, ligue 190", f'<ul class="pl">{itens}</ul>', "Todos os canais e serviços"))

    if reg.get("normas"):
        com_tram = [(n, (tram.get(n["id"]) or [None])[0]) for n in reg["normas"] if tram.get(n["id"])]
        marcos = sorted(reg.get("marcos", []), key=lambda m: m["data"], reverse=True)[:3]
        corpo = ""
        if com_tram:
            n, ult = com_tram[0]
            corpo += (f'<p class="pst"><span class="sit tra">{e(n["situacao"])}</span> <b>{e(n["nome"])}</b></p>'
                      f'<p class="pmeta">Último andamento na Câmara, {_data(ult["data"])}: {e(ult["situacao"])}.</p>')
        corpo += '<ul class="pl">' + "".join(f'<li><a href="{e(m["url"])}" target="_blank" rel="noopener">{e(m["titulo"])}</a><small>{_data(m["data"])}</small></li>' for m in marcos) + "</ul>"
        leg = (_ler(C, "legislativo.json", {}) or {}).get("projetos") or []
        prontos = [p for p in leg if p["etapa"].startswith("Pronto")]
        if prontos:
            corpo += (f'<p class="pmeta"><a href="/em-votacao/"><b>{len(prontos)} projetos prontos para votação</b></a> na Câmara. '
                      f'Dê sua opinião: {_link(C, prontos[0]["enquete"], "enquete do " + prontos[0]["sigla"])}.</p>')
        colunas.append(("Leis", "/leis/", f"{len(reg['normas'])} leis em vigor e {len(leg)} projetos em andamento", corpo, "Leis, projetos e como participar"))

    prog = intel.get("programas", [])
    if prog:
        corte = (date.today() - timedelta(days=30)).isoformat()
        n30 = sum(1 for p in prog if p["data"] >= corte)
        itens = "".join(
            f'<li class="plg">{logo(C, p.get("orgao"), 32)}<div><a href="{e(p["link"])}" target="_blank" rel="noopener"><b>{e(p.get("nome") or p.get("orgao", ""))}</b>'
            f'{(" <span class=pv>" + e(p["valor"]) + "</span>") if p.get("valor") else ""}</a>'
            f'<small>{e(p.get("orgao") or "")}{" · " if p.get("orgao") else ""}{_data(p["data"])}</small></div></li>'
            for p in prog[:5])
        colunas.append(("Programas", "/programas/", f"{n30} anúncios nos últimos 30 dias", f'<ul class="pl">{itens}</ul>', "Todos os programas e recursos"))

    vagas = _vagas(C, 30)
    if vagas:
        itens = "".join(f'<li><a href="{e(n["link"])}" target="_blank" rel="noopener"><b>{e(n["titulo"])}</b></a>'
                        f'<small>{e(n["fonte"])} · {_data(n["data"])}</small></li>' for n in vagas[:4])
        colunas.append(("Vagas e oportunidades", "/oportunidades/", f"{len(vagas)} abertas nos últimos 30 dias", f'<ul class="pl">{itens}</ul>', "Todas as vagas, cursos e programas"))

    prox = sorted((v for v in evs if (v.get("fim") or v["inicio"]) >= hoje), key=lambda v: v["inicio"])[:4]
    if prox and len(colunas) < 4:
        itens = "".join(f'<li><a href="{e(v["url"])}" target="_blank" rel="noopener"><b>{e(v["nome"])}</b></a>'
                        f'<small>{_data(v["inicio"])} · {e(v["cidade"])}</small></li>' for v in prox)
        colunas.append(("Agenda", "/eventos/", "Próximas datas e campanhas", f'<ul class="pl">{itens}</ul>', "Agenda completa"))

    if not colunas:
        return ""
    cards = "".join(
        f'<div class="pcard"><div class="ph2"><a href="{u}"><h3>{t}</h3></a><span>{e(sub)}</span></div>{corpo}'
        f'<a class="pmais" href="{u}">{mais} →</a></div>' for t, u, sub, corpo, mais in colunas)
    return ('<section class="sec tech" id="mercado"><canvas class="techbg" aria-hidden="true"></canvas><div class="wrap">'
            '<div class="sh"><div><span class="eye">Atualizado de hora em hora</span><h2>Painel da proteção no Brasil</h2>'
            '<p>Canais de ajuda, leis, programas públicos e agenda: o que se movimenta na defesa de mulheres e crianças no país.</p></div></div>'
            f'<div class="painel">{cards}</div></div></section>')


def gerar(C):
    urls = []
    for f in (verticais, ajuda, oportunidades, projetos, em_votacao, participe, parlamentares, leis, programas, iniciativas, decisoes, instituicoes, guias, indicadores, eventos, glossario,
              briefing, relatorio, busca, ingles):
        try:
            u = f(C)
        except Exception as ex:  # uma seção com dado ruim não derruba o site
            print(f"   seção {f.__name__} falhou: {ex!r}")
            if os.environ.get("IAB_ESTRITO"):
                raise
            u = []
        urls += u
    for u, nome in SECOES:  # o menu e o rodapé apontam para todas: seção ainda sem dados vira página "em preparação"
        if u not in urls:
            (C["OUT"] / u.strip("/")).mkdir(parents=True, exist_ok=True)
            (C["OUT"] / u.strip("/") / "index.html").write_text(C["pagina_simples"](
                u, f"{nome}: seção em preparação no Observatório", f"A seção {nome} do Observatório Brasil Mulher está sendo preparada e entra no ar em breve, com dados atualizados sobre a proteção de mulheres e crianças.",
                '<p class="lead">Esta seção está sendo preparada e entra no ar em breve. Enquanto isso, veja as '
                '<a href="/noticias/">notícias</a> e o <a href="/#radar">repositório</a>.</p>' + _nav(u),
                C["css"], C["topo"], C["footer"], [("Início", "/"), (nome, u)], robots="noindex, follow"), encoding="utf-8")
    _preencher_nav(C, urls)
    print(f"   seções de dados: {len(urls)} páginas")
    return urls
