# Observatório Brasil Mulher · entrega

| Pasta | Para quê |
|---|---|
| `1-site-para-publicar/` | **O que sobe no servidor.** Todo o conteúdo vai para a raiz de www.observatoriobrasilmulher.com.br. Veja o LEIA-ME dentro dela. |
| `2-para-enviar/` | Um arquivo HTML único, com imagens embutidas, para mandar por WhatsApp ou e-mail. **Não hospede este arquivo**: ele é pesado e não tem as páginas internas. |
| `3-gerador/` | A fonte da verdade: `main.py` (bloco CFG no topo), `src/portal.html`, coletor e dados. Para regerar: `npm install` em `ferramentas/` e depois `uv run main.py`. |
| `4-imagens/` | Fotos em WebP e a imagem de compartilhamento, para propostas e apresentações. |

Regra de ouro: mudou algo, mude no gerador e gere de novo. Não edite o HTML da pasta 1 à mão.
