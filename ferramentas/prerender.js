// Pré-renderiza src/portal.html: executa o script da página num navegador simulado (jsdom)
// e grava o HTML já montado, para buscadores, robôs de IA e prévias de link verem o conteúdo
// sem depender de JavaScript. Também exporta os dados da página (notícias, editorias...) para o gerador.
//
// Uso: node ferramentas/prerender.js <portal.html> <noticias.json> <saida.json> <dominio>
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs");

const [, , srcPath, newsPath, outPath, dominio] = process.argv;
const html = fs.readFileSync(srcPath, "utf8");
const news = JSON.parse(fs.readFileSync(newsPath, "utf8"));
const PAGINAS = { "": "/", norte: "/norte/", nordeste: "/nordeste/", "centro-oeste": "/centro-oeste/", sudeste: "/sudeste/", sul: "/sul/" };

function render(caminho) {
  return new Promise((resolve, reject) => {
    const erros = [];
    const vc = new VirtualConsole();
    vc.on("jsdomError", (e) => erros.push(e.message));
    const dom = new JSDOM(html, {
      url: dominio + caminho, runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc,
      beforeParse(w) {
        w.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve(news) });
        w.IntersectionObserver = class { observe() {} unobserve() {} };
        w.MutationObserver = class { observe() {} };
        w.matchMedia = () => ({ matches: true }); // como "movimento reduzido": slider parado no 1º destaque
        w.HTMLCanvasElement.prototype.getContext = () => null;
        w.Element.prototype.scrollIntoView = () => {};
        w.scrollTo = () => {};
      },
    });
    setTimeout(() => {
      if (erros.length) return reject(new Error(caminho + ": " + erros.join(" | ")));
      const w = dom.window, d = w.document;
      const dados = JSON.parse(JSON.stringify(w.IAB || {}));
      // estado de tela que não deve ir para o HTML estático
      d.documentElement.classList.remove("js");
      d.querySelectorAll(".rv,.seen").forEach((e) => e.classList.remove("rv", "seen"));
      d.querySelectorAll("#destaques.paused").forEach((e) => e.classList.remove("paused"));
      resolve({ body: d.body.innerHTML, dados });
    }, 900);
  });
}

(async () => {
  const saida = { paginas: {}, dados: null };
  for (const [slug, caminho] of Object.entries(PAGINAS)) {
    const r = await render(caminho);
    saida.paginas[slug] = r.body;
    if (!saida.dados) saida.dados = r.dados;
  }
  fs.writeFileSync(outPath, JSON.stringify(saida));
  console.log("pré-renderizado:", Object.keys(saida.paginas).map((s) => s || "home").join(", "));
})().catch((e) => { console.error(e.message); process.exit(1); });
