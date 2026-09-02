# Cardápio do RU da UnB

Consulta pública ao cardápio dos Restaurantes Universitários da Universidade de Brasília, para quem quer saber o que vai ser servido sem ir até o restaurante.

## Language

**Campus**:
Unidade geográfica da UnB que possui um Restaurante Universitário próprio. É por ele que o usuário escolhe qual cardápio quer ver. São cinco: Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa.
_Avoid_: unidade, faculdade, polo

**Restaurante Universitário (RU)**:
O refeitório que serve as refeições de um campus. Existe exatamente um por campus, e é por isso que o usuário seleciona um **Campus** e não um restaurante.
_Avoid_: bandejão, refeitório, RU Central

**Cardápio**:
O conjunto de refeições servidas em um **Campus** ao longo de uma **Semana**. É publicado pela UnB como um documento semanal por campus, e é a unidade em que o dado chega até nós.
_Avoid_: menu, ementa

**Semana**:
O período de segunda a domingo coberto por um **Cardápio**. A **Fonte oficial** mantém publicada apenas a semana em curso; é também a única que o usuário consegue navegar. Nem todo **Campus** serve a semana inteira.
_Avoid_: período, ciclo

**Refeição**:
Um dos três momentos servidos em um dia: café da manhã, almoço e jantar. Toda **Refeição** pertence a um único dia de um único **Campus**, e cada **Campus** serve o seu próprio conjunto delas — a Fazenda Água Limpa, por exemplo, não serve jantar.
_Avoid_: turno, horário

**Fonte oficial**:
A página `ru.unb.br/cardapio-refeitorio/`, mantida pela UnB, de onde todo cardápio se origina. É a única autoridade sobre o que será servido — nós apenas reapresentamos o que ela publica.
_Avoid_: site do RU, origem, upstream

**Categoria**:
O papel que um alimento cumpre dentro de uma **Refeição** — salada, prato principal, guarnição, acompanhamento, sobremesa, bebida. A **Fonte oficial** define quais categorias existem em cada refeição, e nós preservamos essa lista e sua ordem em vez de inventar a nossa.
_Avoid_: seção, grupo, tipo de prato

**Item**:
Um alimento ou prato concreto servido dentro de uma **Categoria** — "Lasanha à bolonhesa", "Arroz branco e integral". Uma **Categoria** pode ter mais de um **Item** no mesmo dia.
_Avoid_: prato, comida, alimento (como termo técnico)

**Trilha dietética**:
A restrição alimentar que uma **Categoria** atende: padrão, ovolactovegetariano ou vegetariano estrito. A **Fonte oficial** publica as três em paralelo para o prato principal, e é o que permite responder "tem opção vegana hoje?".
_Avoid_: dieta, perfil, preferência, tag

**Opção alternativa**:
Um **Item** oferecido no lugar de outro dentro da mesma **Categoria**, marcado no cardápio oficial por "OPÇÃO:" ou por "ou". Não é um item adicional — é uma escolha entre os dois.
_Avoid_: variação, substituto, extra

**Composição**:
O conjunto ordenado de **Categorias** e seus **Itens** que forma uma **Refeição** — é o que a pessoa quer ver quando pergunta "o que tem no almoço de hoje". A **Fonte oficial** usa essa mesma palavra como cabeçalho da tabela.
_Avoid_: conteúdo, detalhe, cardápio do dia

**Alergênico**:
Uma substância que a **Fonte oficial** sinaliza em um **Item** por meio de ícone — leite, soja, trigo, ovo, amendoim, oleaginosa, mel, pimenta, cogumelo, suíno. Um **Item** cujo alergênico não pôde ser lido com confiança é **indeterminado**, que é diferente de não conter nenhum.
_Avoid_: restrição, ingrediente, aviso

## Flagged ambiguities

**"Desjejum" vs "café da manhã"**: o `req.md` usa _desjejum_ (RF04); a **Fonte oficial** usa _café da manhã_. Termo canônico: **café da manhã**, por ser o que o usuário lê no PDF oficial e o que ele usa para falar da refeição. _Desjejum_ fica como alias a evitar na UI e no código.


## Example dialogue

> **Dev**: A pessoa abre o site e escolhe um campus. Aí ela vê o cardápio daquele campus, certo?
>
> **Especialista**: Ela vê o **Cardápio** da **Semana** daquele **Campus**. Mas o que ela quer mesmo é uma **Refeição** — o almoço de hoje. O cardápio inteiro é o que a UnB publica; a refeição é o que ela veio buscar.
>
> **Dev**: Então dia e refeição são coisas separadas.
>
> **Especialista**: São. Um **Cardápio** cobre sete dias, cada dia tem três **Refeições**. E toda **Refeição** existe dentro de um único dia de um único campus — não faz sentido falar do "almoço da semana".
>
> **Dev**: E dentro da refeição, é uma lista de comidas?
>
> **Especialista**: É a **Composição**. Ela é dividida em **Categorias** — salada, prato principal, guarnição, sobremesa — e cada categoria tem seus **Itens**. Isso importa: "Arroz branco e integral" é acompanhamento, "Lasanha à bolonhesa" é prato principal. Numa lista solta, a pessoa não distingue.
>
> **Dev**: Vi que aparecem três pratos principais no mesmo dia. É escolha?
>
> **Especialista**: Cuidado, são duas coisas diferentes. Três pratos principais são três **Trilhas dietéticas** — padrão, ovolactovegetariano e vegetariano estrito. Servem públicos diferentes, e todas estão disponíveis. Agora, quando o cardápio diz "OPÇÃO: Suíno agridoce" embaixo do prato padrão, aí sim é uma **Opção alternativa**: ou um, ou outro, dentro da mesma trilha.
>
> **Dev**: E a salada? É de qual trilha?
>
> **Especialista**: De nenhuma em particular. A **Fonte oficial** não declara isso, então nós também não. Só o prato principal tem trilha declarada.
>
> **Dev**: Então todo **Campus** tem sete dias com três **Refeições**?
>
> **Especialista**: Não, e essa é uma pegadinha. O Darcy e Planaltina servem a semana toda; o Gama vai de segunda a sexta; em Ceilândia o café cobre seis dias e o jantar cinco; e a Fazenda Água Limpa não serve jantar nenhum dia. Um campus com cinco dias não é sinal de erro na coleta — é o serviço daquele RU.
>
> **Dev**: Se eu não conseguir ler o **Alergênico** de um item, deixo a lista vazia?
>
> **Especialista**: Não. Lista vazia quer dizer "olhamos e não tem nenhum". Quando não deu para ler, o item é **indeterminado** — e aí a pessoa com alergia precisa ir ao PDF da **Fonte oficial**. As duas situações nunca podem parecer a mesma na tela.
