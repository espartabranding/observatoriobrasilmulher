# Uso de conteúdo de terceiros e proteção das vítimas: regras do Observatório Brasil Mulher

Análise de 16/10/2026, revista em 17/10/2026. Não substitui parecer de advogado; leve este documento a um especialista em direito autoral antes do lançamento.

## Base legal (Lei 9.610/1998)

- **Art. 8º, I:** ideias não são protegidas. Fatos noticiados podem ser contados com palavras próprias.
- **Art. 8º, VI:** "nomes e títulos isolados" não são protegidos. O **art. 10** protege o título de uma obra quando é "original e inconfundível".
- **Art. 46, I, "a":** permite reproduzir notícia ou artigo informativo **na imprensa**, citando o autor (se assinado) e a publicação. Há debate sobre se um portal ou agregador conta como "imprensa"; não dependemos disso porque não reproduzimos matérias.
- **Art. 46, III:** permite citar trechos "na medida justificada", com autor e origem.
- O STJ (REsp 964.404/ES) trata as limitações do art. 46 como exemplificativas, a interpretar à luz dos direitos fundamentais. Não há precedente claro do STJ sobre agregadores e links.

## O que o portal faz (e por que é defensável)

| Prática | Situação |
|---|---|
| Resumo próprio do fato + nome do veículo + link para a matéria | Permitido: fato não é protegido e o texto é nosso |
| Título do veículo + link (Radar da rede) | Baixo risco: prática comum de agregadores; título isolado não é protegido em regra |
| Resumo do feed (texto do veículo) | **Não publicado.** Fica só em `data/noticias_completo.json`, para uso interno da redação |
| Fotos das matérias | **Não usadas.** O portal usa só fotos do Wikimedia Commons com licença livre |
| Análise com IA (destaques) | A IA lê o texto da matéria só como insumo e escreve texto próprio (no máximo 6 palavras seguidas iguais à fonte), com crédito ao veículo e aviso de uso de IA. **Não lê** matérias de veículos com paywall nem de sites cujo robots.txt bloqueia robôs de IA (ClaudeBot, GPTBot, Google-Extended etc.); nesses casos usa só título e chamada do feed. Apuração exclusiva de um só veículo: análise curta |
| Leitura de feeds RSS | Respeita o robots.txt de cada site. Sites que bloqueiam robôs são acompanhados manualmente |
| Nomes dos veículos | Citados por nome, sem logotipos |

## Regras para a redação

1. Escreva o resumo com suas palavras. Não copie frases da matéria original. Se citar um trecho, use aspas, seja breve e indique veículo e autor.
2. Sempre cite o veículo e, quando a matéria for assinada, o autor.
3. Link sempre para a matéria original, sem moldura (iframe) e sem esconder que o conteúdo é de terceiros.
4. Não republique matérias de veículos com paywall, nem trechos longos delas.
5. Não use imagens dos veículos. Use fotos próprias, de bancos licenciados ou com licença livre, com crédito e link da licença.
6. Evite fotos de pessoas identificáveis sem autorização. As licenças Creative Commons cobrem o direito autoral da foto, não o direito de imagem de quem aparece nela. **Nunca use imagem de criança identificável** (ECA).
7. Mantenha um canal de correção e remoção, e responda rápido aos pedidos.
8. Antes de monetizar o Radar (anúncios, assinatura), leia os termos de uso dos principais veículos coletados. Muitos proíbem uso comercial do conteúdo sem autorização; isso afeta títulos e feeds, não o seu texto próprio.

## Licenças das fotos

- O crédito de cada foto traz autor, link para a obra e link para a licença, como exigem as licenças CC.
- As fotos foram redimensionadas e comprimidas, e o rodapé indica isso.
- Fotos CC BY-SA: se você criar uma imagem derivada (montagem, filtro forte, recorte que mude a obra), a nova imagem precisa sair sob a mesma licença.

## Cenário legislativo (out/2026)

- **PL 2338/2023 (marco da IA):** aprovado no Senado em dez/2024, parado na Câmara. O texto do Senado prevê transparência sobre conteúdo protegido usado por sistemas de IA, direito do titular de proibir o uso (opt-out) e remuneração. O capítulo de direito autoral é o mais disputado e pode cair. Se for aprovado, revisar o uso de texto de matérias como insumo da IA. O bloqueio por robots.txt já é respeitado.
- **Remuneração do jornalismo por plataformas (PL 2370/2019):** sem lei aprovada. O alvo são big techs, não portais pequenos.
- **Cade (abr/2026):** investiga o Google pelo uso de conteúdo jornalístico em IA sem remuneração. Mostra a sensibilidade do tema.
- **Concorrência desleal (Lei 9.279/1996, art. 195):** além do direito autoral, um veículo pode alegar aproveitamento parasitário se o portal substituir sistematicamente suas reportagens. Por isso: análise como contexto, crédito visível e link para o original.
- **Direito de resposta (Lei 13.188/2015):** o portal publica conteúdo próprio e precisa de canal ativo para pedidos de resposta e correção.

## Pendências antes do lançamento

- [ ] Parecer de advogado sobre o Radar da rede em uso comercial.
- [ ] Revisar os termos de uso de Folha, Estadão, Globo, Valor e demais veículos coletados.
- [ ] Publicar canal de correção e remoção (e-mail da redação). **Hoje os Termos mostram "a preencher".**
- [ ] Política de privacidade e consentimento LGPD na newsletter.

## Proteção das vítimas (regra própria deste portal)

- **Crianças e adolescentes:** nunca identificar vítima, testemunha ou autor de ato infracional, nem por nome, apelido, foto, escola, endereço ou parentesco (ECA, arts. 17, 143 e 247). Vale para os resumos escritos pela IA: o prompt da curadoria proíbe esses dados e a redação revisa.
- **Violência sexual:** processos correm em segredo de justiça (Código Penal, art. 234-B). Não publicar nome nem dado que identifique a vítima, mesmo que o veículo de origem tenha publicado.
- **Linguagem:** sem "crime passional", "por ciúmes" ou qualquer expressão que culpe a vítima ou romantize o agressor; sem detalhes gráficos da violência.
- **Fotos:** só lugares e instituições, nunca pessoas.
- **Segurança de quem lê:** o site não grava a escolha de região no aparelho e só carrega medição de audiência depois do aceite de cookies.
