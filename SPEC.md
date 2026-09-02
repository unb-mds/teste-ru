# Especificação — Cardápio do RU da UnB

Site estático que mostra o cardápio dos Restaurantes Universitários da UnB, para quem quer saber o que vai ser servido sem ir até lá.

Os termos em **negrito** estão definidos em [CONTEXT.md](./CONTEXT.md). As decisões estruturais estão em [docs/adr/](./docs/adr/). Este documento não repete nenhum dos dois: descreve o que construir.

---

## 1. Escopo

**Está no escopo**

- Consulta ao **Cardápio** dos cinco campi com **RU**: Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa.
- A **Semana** corrente, nas três **Refeições** (café da manhã, almoço e jantar), na medida em que cada campus as serve — a cobertura varia (§ 3).
- A **Composição** completa de cada refeição, preservando **Categorias**, **Trilhas dietéticas** e **Opções alternativas**.
- Alergênicos por **Item**, com estado explícito quando não puderem ser identificados.
- Ingestão automática a partir da **Fonte oficial**.

**Não está no escopo**

- Restaurante Executivo: tem página própria na UnB e não aparece na **Fonte oficial** definida no `req.md`.
- Semanas anteriores ou futuras: a fonte só publica a semana corrente, e só ela é navegável. As versões antigas do arquivo de dados continuam existindo no histórico de commits, sem rota na interface.
- Preços, horários de funcionamento, filas, autenticação, avaliação de pratos, notificações.
- Qualquer backend: o RNF01 (GitHub Pages) proíbe.

## 2. Personas e uso dominante

| Persona | Uso |
|---|---|
| Estudante da UnB | Consulta recorrente, mesmo campus todo dia, no celular, pouco antes da refeição. É quem dita o desenho. |
| Servidor / funcionário | Igual ao estudante em padrão de uso. |
| Pessoa de fora | Primeira visita, campus desconhecido, provavelmente chegou por um link compartilhado. |

O uso dominante é **"o que tem pra almoçar hoje no meu RU?"**, respondido no menor número de toques possível. Daí decorrem: abrir no dia de hoje, lembrar o campus e ter o estado na URL.

## 3. Fonte de dados

A **Fonte oficial** é `https://ru.unb.br/cardapio-refeitorio/`. O que ela realmente oferece:

- Cinco links para PDF, um por campus, referentes à semana corrente. Não há cardápio em HTML.
- Cada PDF tem uma página por **Refeição**, com uma tabela de **Categorias** (linhas) por dia da semana (colunas).
- **A cobertura varia por campus, e até por refeição dentro de um campus.** Darcy Ribeiro e Planaltina servem os sete dias nas três refeições; Gama serve de segunda a sexta; em Ceilândia o café da manhã cobre seis dias e o jantar cinco; a Fazenda Água Limpa tem PDF de duas páginas e **não serve jantar**. O parser e a interface tratam isso como normal, não como erro.
- O texto é extraível; **não** é imagem escaneada.
- Os alergênicos são imagens de 52×52 posicionadas junto aos pratos, sem contrapartida textual. O mesmo alergênico reaparece com o mesmo object ID.
- A URL de cada PDF contém o mês de upload (`/2026/09/`, `/2026/08/`) e o intervalo da semana. **O parser nunca constrói essas URLs**: ele lê os `href` da página, porque o padrão varia entre campi na mesma semana.
- Os PDFs **não** retornam cabeçalho CORS — ver [ADR-0001](./docs/adr/0001-ingestao-por-github-action-com-json-versionado.md).

Categorias observadas (a lista é dado da fonte, não um enum fixo no código):

- **Café da manhã** — Bebidas, Panificação, Opção extra, Gordura, Complemento padrão, Complemento ovolactovegetariano, Complemento vegetariano estrito, Fruta.
- **Almoço** — Salada 1, Salada 2, Molho para salada, Prato principal padrão, Prato principal ovolactovegetariano, Prato principal vegetariano estrito, Guarnição, Acompanhamentos, Sobremesa, Bebida.
- **Jantar** — as do almoço, mais Sopa.

Cada página traz ainda uma observação de rodapé ("Mesa de apoio: …", "Cardápio sujeito a alteração"), que é preservada por refeição.

## 4. Pipeline de ingestão

Workflow do GitHub Actions, agendado **diariamente de manhã cedo** (não semanalmente: a fonte troca PDF no meio da semana) e disparável manualmente.

1. **Descobrir** — baixar a página da fonte e extrair, por campus, a URL do PDF e o rótulo da semana.
2. **Baixar** — os cinco PDFs.
3. **Extrair** — com biblioteca Python que forneça bounding box de texto e de imagem (PyMuPDF ou pdfplumber):
   - reconstituir a grade da tabela a partir das coordenadas do texto, mapeando cada célula para (dia, categoria);
   - separar os **Itens** dentro da célula (§ 4.1);
   - associar cada ícone de alergênico ao **Item** correto (§ 4.2);
   - células mescladas **horizontalmente** (a bebida do café da manhã vale a semana toda) valem para todos os dias que abrangem; células de categoria mescladas **verticalmente** fazem a linha seguinte pertencer à categoria de cima.
4. **Validar** — o resultado só é aceito se: os 5 campi estiverem presentes; cada um cobrir de 5 a 7 dias; cada campus servir ao menos café da manhã e almoço em algum dia; nenhuma refeição desconhecida aparecer; as categorias esperadas daquela refeição existirem; e nenhum dia ficar sem item algum.
5. **Gravar** — se validou, sobrescrever `data/cardapio.json` e commitar. Se não validou, **não escrever nada**, falhar o job e abrir uma issue com o diagnóstico. O site permanece com o último dado bom, que a interface já sinaliza como desatualizado (§ 6.3).
6. **Republicar** — só quando o arquivo mudou, a coleta chama o workflow de publicação dentro do mesmo run. Não pode ser um workflow separado reagindo ao push: commits feitos com o `GITHUB_TOKEN` não disparam workflows, e o site ficaria congelado na primeira versão.

Categoria desconhecida não invalida a coleta: é preservada no dado com seu nome original e exibida sem **Trilha dietética**. O que invalida é ausência do que deveria existir, não presença do que não se esperava.

### 4.1 Separação de Itens

A geometria não distingue item de continuação: dentro de uma célula, "Arroz branco e" / "integral" / "Feijão preto" têm exatamente o mesmo espaçamento entre linhas. A separação é textual, por marcadores observados no cardápio oficial:

| Marcador | Efeito |
|---|---|
| `OPÇÃO:` / `Opção:` | inicia uma **Opção alternativa** |
| ` ou ` | lista alternativas equivalentes ("Pão francês ou Pão careca ou Pão integral") |
| ` / ` | lista **Itens** independentes |
| quebra de linha, **em molhos** | cada linha é um molho ("Mostarda e mel" / "Limão") |
| `Feijão`, **em acompanhamentos** | arroz e feijão vêm colados e são itens distintos |

O primeiro item de um grupo é o padrão; os seguintes recebem `alternativa: true`.

### 4.2 Associação dos alergênicos

Os ícones ao lado dos pratos e os da legenda são imagens **diferentes** (52 px contra 87 px, object IDs distintos), então não há como casá-los por identidade. Cada imagem é reduzida a uma assinatura de 12×12 em tons de cinza e o ícone do prato recebe o rótulo da legenda mais parecida — aceito apenas se a distância for pequena **e** a segunda melhor estiver claramente atrás.

Dentro da célula, cada **Item** é localizado palavra a palavra (não linha a linha: em "Leite integral ou Bebida de soja" os dois itens dividem uma única linha de texto, e só a posição horizontal do ícone diz a qual deles ele pertence). O ícone vai para o item cujo retângulo estiver mais perto. Ícone ilegível, ou equidistante de dois itens, deixa a célula inteira **indeterminada**.

Na coleta de referência isso deixou 22 de 1050 itens indeterminados (2%), concentrados em células genuinamente ambíguas como "Mix de doces / OPÇÃO: Fruta".

## 5. Formato dos dados

Arquivo único, `data/cardapio.json`, sobrescrito a cada coleta bem-sucedida, contendo os cinco campi da semana corrente.

```jsonc
{
  "gerado_em": "2026-09-02T09:03:11Z",     // fim da coleta, UTC
  "fonte": "https://ru.unb.br/cardapio-refeitorio/",
  "semana": {
    "inicio": "2026-08-31",                 // segunda
    "fim":    "2026-09-06",                 // domingo
    "rotulo": "Semana 02"
  },
  "campi": [
    {
      "id": "darcy-ribeiro",                // darcy-ribeiro | ceilandia | gama
                                            // planaltina | fazenda-agua-limpa
      "nome": "Darcy Ribeiro",
      "pdf": "http://ru.unb.br/wp-content/uploads/2026/09/Darcy-...pdf",
      "dias": [
        {
          "data": "2026-09-02",
          "refeicoes": [
            {
              "tipo": "almoco",             // cafe-da-manha | almoco | jantar
              "observacao": "Mesa de apoio: água, farinha, molho de pimenta...",
              "categorias": [
                {
                  "nome": "Prato principal",
                  "trilha": "padrao",       // padrao | ovolactovegetariano
                                            // vegetariano-estrito | null
                  "itens": [
                    {
                      "nome": "Lasanha à bolonhesa",
                      "alternativa": false, // true = vem de "OPÇÃO:" ou "ou"
                      "alergenicos": ["leite", "trigo", "ovo"],
                      "alergenicos_status": "identificados"
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Regras do formato**

- `alergenicos_status` é `identificados` ou `indeterminado`. Com `indeterminado`, `alergenicos` é sempre `[]` e a interface **nunca** apresenta o item como livre de alergênicos. Lista vazia com status `identificados` significa, aí sim, que nenhum ícone marca aquele item.
- Vocabulário fechado de alergênicos, vindo da legenda oficial: `cogumelo`, `leite`, `mel`, `pimenta`, `soja`, `trigo`, `amendoim`, `oleaginosa`, `ovo`, `suino`.
- `trilha` é `null` para categorias que servem a todas as trilhas (saladas, acompanhamentos, sobremesa, bebida). O cardápio oficial não declara a quem elas pertencem, e a interface não inventa essa informação.
- `categorias` preserva a ordem do PDF. A interface exibe nessa ordem, sem reordenar.
- Datas em ISO 8601. Timestamps em UTC; a interface converte para o fuso local na exibição.
- `dias` cobre apenas os dias que aquele campus serve, e `refeicoes` apenas as refeições daquele dia — listas curtas são normais, não falha de coleta.
- O arquivo é gravado indentado, para que o `git diff` de cada coleta seja legível. São ~430 KB, servidos comprimidos em ~14 KB.

## 6. Interface

Página única, mobile-first, sem framework e sem passo de build: os arquivos são publicados como estão.

### 6.1 Roteamento

Estado na URL, depois do `#`: `#/<campus>/<AAAA-MM-DD>/<refeicao>`.

- A URL tem precedência sobre o campus salvo, e **não** sobrescreve a preferência de quem recebeu o link.
- Trocar de dia, refeição ou campus empurra uma entrada no histórico: o botão voltar volta um passo, não sai do site.
- Rota ausente ou inválida cai no padrão: campus salvo (ou seleção inicial), data de hoje, refeição sugerida pelo horário.

### 6.2 Telas

**Seleção de campus** — só na primeira visita, ou ao acionar "trocar". Os cinco campi, com o nome pelo qual são conhecidos. A escolha é persistida no navegador.

**Cardápio** — a tela principal:

- cabeçalho com o campus atual sempre visível e ação de trocar (RF06);
- seletor dos dias que aquele campus serve, abrindo no dia de hoje (RF03);
- abas das três **Refeições**, abrindo na sugerida pelo horário e desabilitando as que aquele campus não serve naquele dia (RF04);
- **Composição** agrupada por **Categoria**, na ordem do PDF, com as três **Trilhas dietéticas** do prato principal visivelmente distintas (RF05);
- **Opções alternativas** apresentadas como escolha entre itens, não como itens adicionais;
- alergênicos por item, e aviso de indeterminado quando for o caso;
- observação de rodapé da refeição e link para o PDF oficial da semana daquele campus.

### 6.3 Estados

| Situação | Comportamento |
|---|---|
| Semana do dado contém hoje | Exibição normal. |
| Semana do dado **não** contém a data selecionada | Aviso explícito de que a UnB ainda não publicou a semana, com a semana coberta, o horário da coleta e o link da fonte. O cardápio antigo só aparece se a pessoa pedir. |
| Item com `alergenicos_status: indeterminado` | Aviso no item e link para o PDF oficial. Nunca "sem alergênicos". |
| `data/cardapio.json` indisponível | Estado vazio com link para a fonte oficial. |
| Campus sem dado no arquivo | Estado vazio daquele campus, com os demais ainda navegáveis. |
| Refeição não servida naquele dia | Aba desabilitada, com a razão no `title`. A seleção cai na primeira refeição existente do dia. |
| Dia sem nenhuma refeição | Mensagem dizendo que nada é servido ali naquele campus. |

## 7. Critérios de aceitação

| RF | Critério verificável |
|---|---|
| RF01 | Na primeira visita, os cinco campi são oferecidos e nenhum cardápio é exibido antes da escolha. A escolha sobrevive a recarregar e a fechar o navegador. |
| RF02 | Escolhido um campus, a composição da refeição do dia corrente é exibida sem nenhuma outra interação. |
| RF03 | Os dias que o campus serve na semana corrente são navegáveis; a tela abre no dia de hoje; a data selecionada aparece na URL e sobrevive a recarregar. |
| RF04 | Café da manhã, almoço e jantar são exibidos separadamente, um por vez; a troca não altera o dia nem o campus selecionados; refeição não servida aparece desabilitada em vez de vazia. |
| RF05 | Cada refeição exibe suas categorias na ordem do PDF, com todos os itens; as três trilhas do prato principal são distinguíveis; opções alternativas aparecem como alternativas. |
| RF06 | A troca de campus está acessível de qualquer ponto da tela de cardápio, preserva o dia e a refeição selecionados, e atualiza a preferência salva. |
| RNF01 | O site é servido inteiramente por GitHub Pages, sem nenhuma requisição a servidor próprio; a publicação envia os arquivos como estão, sem passo de build. |

Além dos RFs: nenhuma tela apresenta ausência de alergênicos onde a extração falhou, e nenhuma tela apresenta cardápio de outra semana sem dizer que é de outra semana.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| A UnB muda o layout do PDF | Validação bloqueia a gravação, o job falha e abre issue; o site mantém o último dado bom, sinalizado (§ 4, § 6.3). |
| Ícone de alergênico associado ao prato errado | Heurística conservadora: na dúvida, `indeterminado`. O prato indeterminado é uma falha visível; o prato errado, não ([ADR-0002](./docs/adr/0002-alergenicos-extraidos-com-estado-indeterminado.md)). |
| A UnB muda a estrutura da página HTML | O passo de descoberta falha antes do download e cai no mesmo tratamento de erro. |
| A fonte atrasa a publicação da semana | Tratado como estado de produto, não como erro (§ 6.3). |
| Cardápio alterado depois de publicado | A fonte já avisa "cardápio sujeito a alteração"; a interface sempre expõe o horário da coleta e o link do PDF oficial. |

## 9. Verificação

`npm test` executa a interface num DOM headless contra o `data/cardapio.json` real, com relógio fixo, cobrindo cada critério da § 7 e os estados da § 6.3 — incluindo o campus que não serve a semana toda, o link compartilhado que não sobrescreve a preferência de quem o recebeu, a semana desatualizada e o item com alergênico indeterminado.

Para rodar tudo localmente:

```sh
python3 -m venv .venv && .venv/bin/pip install -r parser/requirements.txt
.venv/bin/python parser/coletar.py      # gera data/cardapio.json a partir da fonte
npm install && npm test                 # verifica a interface
python3 -m http.server 8000             # abre em http://localhost:8000
```
