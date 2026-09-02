# Cardápio do RU da UnB

Site estático que mostra o cardápio dos Restaurantes Universitários da Universidade de Brasília, para quem quer saber o que vai ser servido sem ir até lá.

A UnB publica o cardápio apenas como **PDFs semanais**, um por campus, e esses PDFs não retornam cabeçalho CORS — o navegador não consegue baixá-los. Como o site roda em GitHub Pages, sem backend, a ingestão acontece fora do navegador: um workflow agendado baixa os PDFs, extrai o conteúdo e commita `data/cardapio.json` no próprio repositório. A página só faz `fetch` desse arquivo.

## Documentos

| Arquivo | O que é |
|---|---|
| [SPEC.md](./SPEC.md) | O que construir: escopo, pipeline, schema, telas, critérios de aceitação |
| [CONTEXT.md](./CONTEXT.md) | Glossário do domínio |
| [docs/adr/](./docs/adr/) | Decisões estruturais e por quê |
| [req.md](./req.md) | Requisitos originais |

## Estrutura

```
index.html  assets/        interface (sem framework, sem build)
data/cardapio.json         snapshot da semana corrente
parser/                    coleta: descoberta, extração, validação
testes/ui.mjs              verificação da interface em DOM headless
.github/workflows/         coleta diária agendada
```

## Rodando localmente

```sh
python3 -m venv .venv
.venv/bin/pip install -r parser/requirements.txt
.venv/bin/python parser/coletar.py     # gera data/cardapio.json a partir da fonte oficial
python3 -m http.server 8000            # http://localhost:8000
```

O coletor aceita PDFs locais, útil para trabalhar sem rede ou reproduzir uma semana específica:

```sh
.venv/bin/python parser/coletar.py --pdf darcy-ribeiro=/caminho/darcy.pdf
```

## Testes

```sh
npm install && npm test
```

Roda a interface num DOM headless contra o `data/cardapio.json` real, com relógio fixo, cobrindo RF01–RF06 e os estados de erro. É a única dependência de Node do projeto: a publicação não tem passo de build.

## Publicação

GitHub Pages servindo a branch principal a partir da raiz. Não há build — os arquivos vão como estão.

O workflow `coletar.yml` roda todo dia às 06:00 (Brasília). Se a extração falhar na validação, **nada é gravado**: o job falha, abre uma issue e o site continua com o último dado bom, que a interface sinaliza como desatualizado.

## Alergênicos

O cardápio oficial marca alergênicos apenas por ícone. Nós os extraímos por semelhança visual e posição, e quando a associação é ambígua o item aparece como **indeterminado**, com link para o PDF oficial — nunca como "sem alergênicos". Ver [ADR-0002](./docs/adr/0002-alergenicos-extraidos-com-estado-indeterminado.md).
