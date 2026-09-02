# Ingestão do cardápio por GitHub Action com JSON versionado

A fonte oficial (`ru.unb.br/cardapio-refeitorio/`) publica o cardápio apenas como PDFs semanais — um por campus — e esses PDFs não retornam cabeçalho CORS, então o navegador não consegue baixá-los. Como o requisito não funcional obriga a hospedagem em GitHub Pages (estático, sem backend), a ingestão acontece **fora do navegador**: um workflow agendado do GitHub Actions baixa os PDFs, extrai o texto, gera arquivos JSON e os commita no próprio repositório; a página apenas faz `fetch` desses JSON servidos pelo mesmo domínio.

## Considered Options

- **Parse no navegador com pdf.js** — rejeitado: o PDF não tem `Access-Control-Allow-Origin`, e só funcionaria através de um proxy CORS público de terceiros, um ponto único de falha fora do nosso controle.
- **Curadoria manual do JSON** — rejeitado como mecanismo principal: são 5 campi × 3 refeições × 7 dias por semana, trabalho recorrente que faz o site envelhecer sempre que ninguém o executa. Continua disponível como correção pontual, já que o dado é um arquivo versionado.

## Consequences

- O dado do site é sempre um **snapshot**, nunca a fonte ao vivo: o frescor é limitado pela frequência do agendamento.
- O histórico de cardápios se acumula no repositório sem custo adicional, mesmo que a fonte só publique a semana corrente.
- Quando a UnB mudar o layout do PDF, o parser quebra silenciosamente — a detecção dessa falha precisa ser parte do pipeline, não do site.
