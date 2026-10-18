# Observatório Brasil Mulher · observatoriobrasilmulher.com.br

Observatório de notícias, leis, dados e canais de ajuda sobre a defesa de mulheres e crianças no Brasil.
Clone do IA Brasil (mesmo layout, mesma lógica de editorias, verticais, coleta e curadoria) com outro tema.

- `src/portal.html`: capa (fonte única do layout e do script).
- `main.py` + `secoes.py`: geram o site estático em `entrega/1-site-para-publicar/`.
- `coletor/`: coleta (`coletar.py`), curadoria dos destaques (`curar.py`), extração de programas, decisões e iniciativas (`extrair.py`).
- `data/fontes.json`: 384 fontes (governo, Judiciário, MPs, Defensorias, secretarias estaduais, terceiro setor, imprensa de todas as UFs).
- Dados mantidos à mão: `leis.json`, `ajuda.json`, `instituicoes.json`, `indicadores.json`, `eventos.json`, `glossario.json`, `guias.json`, `src/fotos.json`.
- `JURIDICO.md`: uso de conteúdo de terceiros e regras de proteção das vítimas.

```bash
uv run coletor/coletar.py
uv run coletor/curar.py            # primeira carga: --semear
uv run coletor/extrair.py
uv run main.py
```
