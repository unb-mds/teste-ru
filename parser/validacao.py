"""Invariantes que o resultado precisa satisfazer para ser gravado.

Ausencia do que deveria existir invalida a coleta. Presenca do que nao se
esperava, nao: uma categoria nova e preservada e exibida sem trilha.
"""

import unicodedata

# Nem todo campus serve a semana inteira nem as tres refeicoes: Gama vai de
# segunda a sexta e a Fazenda Agua Limpa nao serve jantar. O que se exige e
# que cada campus tenha uma semana plausivel e nenhum dia oco.
DIAS_MINIMOS = 5
DIAS_MAXIMOS = 7
REFEICOES_CONHECIDAS = {"cafe-da-manha", "almoco", "jantar"}
REFEICOES_INDISPENSAVEIS = {"cafe-da-manha", "almoco"}

CATEGORIAS_MINIMAS = {
    "cafe-da-manha": ["panificacao", "complemento", "fruta"],
    "almoco": ["salada 1", "prato principal", "acompanhamentos", "sobremesa"],
    "jantar": ["salada 1", "prato principal", "acompanhamentos", "sobremesa"],
}


def _chave(txt):
    nfkd = unicodedata.normalize("NFKD", (txt or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip()


def validar(cardapio, campi_esperados):
    """Devolve a lista de problemas encontrados. Vazia = pode gravar."""
    problemas = []
    campi = cardapio.get("campi", [])
    ids = {c["id"] for c in campi}

    for esperado in campi_esperados:
        if esperado not in ids:
            problemas.append(f"campus ausente: {esperado}")

    for campus in campi:
        rotulo = campus["id"]
        dias = campus.get("dias", [])
        if not DIAS_MINIMOS <= len(dias) <= DIAS_MAXIMOS:
            problemas.append(
                f"{rotulo}: {len(dias)} dias, esperados entre "
                f"{DIAS_MINIMOS} e {DIAS_MAXIMOS}"
            )

        tipos_do_campus = {
            r["tipo"] for d in dias for r in d.get("refeicoes", [])
        }
        desconhecidas = tipos_do_campus - REFEICOES_CONHECIDAS
        if desconhecidas:
            problemas.append(
                f"{rotulo}: refeicao desconhecida: {', '.join(sorted(desconhecidas))}"
            )
        faltando = REFEICOES_INDISPENSAVEIS - tipos_do_campus
        if faltando:
            problemas.append(
                f"{rotulo}: nenhum dia tem {', '.join(sorted(faltando))}"
            )

        for dia in dias:
            data = dia["data"]
            refeicoes = dia.get("refeicoes", [])
            if not refeicoes:
                problemas.append(f"{rotulo} {data}: dia sem nenhuma refeicao")
                continue

            vazio = True
            for refeicao in refeicoes:
                categorias = refeicao.get("categorias", [])
                nomes = {_chave(c["nome"]) for c in categorias}
                for minima in CATEGORIAS_MINIMAS.get(refeicao["tipo"], []):
                    if not any(minima in n for n in nomes):
                        problemas.append(
                            f"{rotulo} {data} {refeicao['tipo']}: "
                            f"categoria ausente: {minima}"
                        )
                if any(c.get("itens") for c in categorias):
                    vazio = False
            if vazio:
                problemas.append(f"{rotulo} {data}: dia sem nenhum item")

    return problemas


def resumo(cardapio):
    """Numeros de uma coleta, para o log do workflow."""
    itens = indeterminados = 0
    for campus in cardapio.get("campi", []):
        for dia in campus.get("dias", []):
            for refeicao in dia.get("refeicoes", []):
                for categoria in refeicao.get("categorias", []):
                    for item in categoria.get("itens", []):
                        itens += 1
                        if item["alergenicos_status"] == "indeterminado":
                            indeterminados += 1
    return {
        "campi": len(cardapio.get("campi", [])),
        "itens": itens,
        "itens_indeterminados": indeterminados,
    }
