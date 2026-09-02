"""Converte um PDF semanal de um campus na estrutura descrita na SPEC.

A grade da tabela vem do detector de tabelas do PyMuPDF, que ja resolve as
celulas mescladas horizontalmente (a bebida do cafe da manha, por exemplo,
vale a semana inteira): a celula mesclada aparece com bbox estendida e as
vizinhas como None.
"""

import re
import unicodedata
from datetime import date

import pymupdf

from alergenicos import classificador, icones_dos_pratos, ler_legenda

REFEICOES = [
    ("cafe-da-manha", "Café da manhã", ("cafe da manha",)),
    ("almoco", "Almoço", ("almoco",)),
    ("jantar", "Jantar", ("jantar",)),
]

TRILHAS = [
    ("OVOLACTOVEGETARIANO", "ovolactovegetariano"),
    ("VEGETARIANO ESTRITO", "vegetariano-estrito"),
    ("VEGETARIANO", "vegetariano-estrito"),
    ("PADRÃO", "padrao"),
]

DIAS_MIN = 3   # campi menores servem de segunda a sexta
DIAS_MAX = 7
MARGEM_MINIMA = 4.0  # icone equidistante de dois itens fica indeterminado
MARCA_OPCAO = re.compile(r"\bOP[ÇC][ÃA]O\s*:\s*", re.IGNORECASE)
DATA_CELULA = re.compile(r"(\d{1,2})[º°]?\s*/\s*(\d{1,2})\s*/\s*(\d{4})")
OBSERVACAO = re.compile(r"(Mesa de apoio:.*?)(?:\n|$)", re.IGNORECASE | re.DOTALL)


class PdfInesperado(Exception):
    """O PDF nao tem a forma que o parser conhece."""


def _sem_acento(txt):
    nfkd = unicodedata.normalize("NFKD", txt.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _limpar(txt):
    return " ".join((txt or "").split())


def normalizar_categoria(bruto):
    """'PRATO PRINCIPAL\\nOVOLACTOVEGETARIANO' -> ('Prato principal', trilha)."""
    texto = _limpar(bruto)
    if not texto:
        return None, None
    trilha = None
    for marcador, valor in TRILHAS:
        if marcador in texto.upper():
            trilha = valor
            texto = re.sub(marcador, "", texto, flags=re.IGNORECASE)
            break
    nome = _limpar(texto)
    if not nome:
        return None, trilha
    return nome[0].upper() + nome[1:].lower(), trilha


def segmentar(texto, categoria):
    """Quebra o conteudo de uma celula em Itens.

    A geometria nao separa item de continuacao de forma confiavel: dentro de
    uma mesma celula, "Arroz branco e" / "integral" / "Feijao preto" tem
    exatamente o mesmo espacamento. A separacao e feita por marcadores
    textuais, cada um observado no cardapio oficial:

      - "OPÇÃO:"  inicia uma Opcao alternativa;
      - " ou "    lista alternativas equivalentes;
      - " / "     lista itens independentes;
      - em molhos, cada linha e um molho ("Mostarda e mel" / "Limão");
      - em acompanhamentos, arroz e feijao vem colados e sao itens distintos.
    """
    bruto = (texto or "").strip()
    if not bruto:
        return []
    chave = _sem_acento(categoria or "")
    if "molho" in chave:
        bruto = re.sub(r"\s*\n\s*", " / ", bruto)
    texto = _limpar(bruto.replace("\n", " "))
    if "acompanhamento" in chave:
        texto = re.sub(r"\s+(?=Feijão)", " / ", texto)
    texto = re.sub(r"(?:\s*/\s*){2,}", " / ", texto)

    itens = []
    for indice_grupo, grupo in enumerate(MARCA_OPCAO.split(texto)):
        for parte in re.split(r"\s+/\s+", grupo):
            parte = parte.strip(" /")
            if not parte:
                continue
            alternativas = [p.strip() for p in re.split(r"\s+ou\s+", parte) if p.strip()]
            for indice, alternativa in enumerate(alternativas):
                itens.append(
                    {
                        "nome": alternativa[0].upper() + alternativa[1:],
                        "alternativa": indice_grupo > 0 or indice > 0,
                        "alergenicos": [],
                        "alergenicos_status": "identificados",
                    }
                )
    return itens


def _identificar_refeicao(pagina, indice):
    texto = _sem_acento(pagina.get_text())
    encontradas = [
        (tipo, nome) for tipo, nome, chaves in REFEICOES if any(c in texto for c in chaves)
    ]
    if len(encontradas) == 1:
        return encontradas[0]
    if indice < len(REFEICOES):
        tipo, nome, _ = REFEICOES[indice]
        return tipo, nome
    raise PdfInesperado(f"nao foi possivel identificar a refeicao da pagina {indice}")


def _datas(tabela):
    """Datas dos dias cobertos por esta pagina.

    O numero de dias varia por campus e ate por refeicao: Darcy e Planaltina
    servem os sete dias, Gama vai de segunda a sexta, e em Ceilandia o cafe
    cobre seis dias enquanto o jantar cobre cinco.
    """
    melhor = []
    for texto in tabela.extract():
        achadas = [DATA_CELULA.search(c or "") for c in texto]
        achadas = [a for a in achadas if a]
        if len(achadas) > len(melhor):
            melhor = achadas
    if not DIAS_MIN <= len(melhor) <= DIAS_MAX:
        raise PdfInesperado(
            f"esperava de {DIAS_MIN} a {DIAS_MAX} dias no cabecalho, "
            f"encontrei {len(melhor)}"
        )
    return [date(int(a.group(3)), int(a.group(2)), int(a.group(1))) for a in melhor]


def _celulas_da_linha(linha, quantidade_de_dias):
    """[(indice_do_primeiro_dia, quantidade_de_dias, bbox)] tratando merges."""
    dias = linha.cells[-quantidade_de_dias:]
    blocos = []
    for indice, celula in enumerate(dias):
        if celula is not None:
            blocos.append([indice, 1, celula])
        elif blocos:
            blocos[-1][1] += 1
    return blocos


def _dentro(bbox_icone, bbox_celula):
    cx = (bbox_icone[0] + bbox_icone[2]) / 2
    cy = (bbox_icone[1] + bbox_icone[3]) / 2
    return (
        bbox_celula[0] <= cx <= bbox_celula[2]
        and bbox_celula[1] <= cy <= bbox_celula[3]
    )


def _caixas_dos_itens(itens, palavras):
    """Retangulo que o texto de cada item ocupa dentro da celula.

    Precisa ser palavra a palavra, e nao linha a linha: em "Leite integral ou
    Bebida de soja" os dois itens dividem uma unica linha de texto, e so a
    posicao horizontal do icone diz a qual deles ele pertence.

    A segmentacao preserva a ordem do texto original, entao os itens sao
    localizados em sequencia, pulando as palavras de ligacao.
    """
    ligacoes = {"ou", "opcao", "opcao:", "/", ""}
    caixas = [None] * len(itens)
    inicio = 0
    for indice, item in enumerate(itens):
        alvos = _sem_acento(item["nome"]).split()
        if not alvos:
            continue
        posicao, caixa, casadas = inicio, None, 0
        while posicao < len(palavras) and casadas < len(alvos):
            token = _sem_acento(palavras[posicao][4]).strip(" /:")
            if token == alvos[casadas]:
                caixa_palavra = palavras[posicao][:4]
                caixa = (
                    (
                        min(caixa[0], caixa_palavra[0]),
                        min(caixa[1], caixa_palavra[1]),
                        max(caixa[2], caixa_palavra[2]),
                        max(caixa[3], caixa_palavra[3]),
                    )
                    if caixa
                    else tuple(caixa_palavra)
                )
                casadas += 1
            elif casadas == 0 or token in ligacoes:
                pass  # ainda nao comecou, ou e palavra de ligacao no meio
            else:
                caixa, casadas = None, 0  # falso comeco: recomeca a busca
            posicao += 1
        if casadas == len(alvos):
            caixas[indice] = caixa
            inicio = posicao
    return caixas


def _distancia_ao_item(icone, caixa):
    """Distancia do centro do icone ate o retangulo do texto do item."""
    centro_x = (icone[0] + icone[2]) / 2
    centro_y = (icone[1] + icone[3]) / 2
    dx = max(caixa[0] - centro_x, 0.0, centro_x - caixa[2])
    dy = max(caixa[1] - centro_y, 0.0, centro_y - caixa[3])
    return (dx * dx + dy * dy) ** 0.5


def _indeterminar(itens):
    for item in itens:
        item["alergenicos"] = []
        item["alergenicos_status"] = "indeterminado"


def _aplicar_alergenicos(itens, icones, classificar, palavras):
    """Distribui os icones da celula entre os itens.

    Regra do ADR-0002: so atribui quando nao ha duvida de a qual item o icone
    pertence. Icone ilegivel, ou equidistante de dois itens, deixa a celula
    inteira indeterminada -- nunca vira ausencia de alergenico.
    """
    if not icones:
        return
    if any(classificar(xref) is None for _, xref in icones):
        _indeterminar(itens)
        return
    if len(itens) == 1:
        itens[0]["alergenicos"] = sorted(
            {classificar(xref) for _, xref in icones}
        )
        return

    caixas = _caixas_dos_itens(itens, palavras)
    conhecidas = [(i, c) for i, c in enumerate(caixas) if c]
    if not conhecidas:
        _indeterminar(itens)
        return

    atribuidos = {}
    for bbox, xref in icones:
        notas = sorted(
            (_distancia_ao_item(bbox, caixa), indice) for indice, caixa in conhecidas
        )
        if len(notas) > 1 and notas[1][0] - notas[0][0] < MARGEM_MINIMA:
            _indeterminar(itens)
            return
        atribuidos.setdefault(notas[0][1], set()).add(classificar(xref))

    for indice, nomes in atribuidos.items():
        itens[indice]["alergenicos"] = sorted(nomes)


def extrair(conteudo_pdf):
    """PDF de um campus -> (dias, rotulo da semana implicito nas datas)."""
    doc = pymupdf.open(stream=conteudo_pdf, filetype="pdf")
    if doc.page_count == 0:
        raise PdfInesperado("PDF sem paginas")

    por_data = {}
    for indice in range(doc.page_count):
        pagina = doc[indice]
        tabelas = pagina.find_tables().tables
        if not tabelas:
            raise PdfInesperado(f"pagina {indice + 1} nao tem tabela reconhecivel")
        tabela = max(tabelas, key=lambda t: t.row_count * t.col_count)
        tipo, nome_refeicao = _identificar_refeicao(pagina, indice)
        datas = _datas(tabela)
        offset = tabela.col_count - len(datas)
        conteudo = tabela.extract()

        palavras = sorted(pagina.get_text("words"), key=lambda w: (round(w[1]), w[0]))

        legenda = ler_legenda(doc, pagina)
        classificar = classificador(doc, legenda)
        icones = icones_dos_pratos(pagina)

        observacao = None
        achado = OBSERVACAO.search(pagina.get_text())
        if achado:
            observacao = _limpar(achado.group(1))

        categorias_por_dia = {d: [] for d in datas}
        ultima_por_dia = {}
        for indice_linha, linha in enumerate(tabela.rows):
            bruto = conteudo[indice_linha][offset - 1] if offset >= 1 else ""
            if "COMPOSI" in (bruto or "").upper():
                continue
            nome_categoria, trilha = normalizar_categoria(bruto)
            # Linha sem rotulo pertence a categoria de cima: a celula de
            # categoria esta mesclada verticalmente (BEBIDAS abrange tanto
            # "Leite ou bebida de soja" quanto "Cafe ou cha").
            continuacao = nome_categoria is None

            for primeiro, quantidade, bbox in _celulas_da_linha(linha, len(datas)):
                anterior = ultima_por_dia.get(primeiro)
                if continuacao and anterior is None:
                    continue
                rotulo = anterior["nome"] if continuacao else nome_categoria
                itens = segmentar(conteudo[indice_linha][offset + primeiro], rotulo)
                if not itens:
                    continue
                _aplicar_alergenicos(
                    itens,
                    [i for i in icones if _dentro(i[0], bbox)],
                    classificar,
                    [w for w in palavras if _dentro(w[:4], bbox)],
                )
                for deslocamento in range(quantidade):
                    dia = primeiro + deslocamento
                    if dia >= len(datas):
                        continue
                    copias = [dict(i) for i in itens]
                    if continuacao:
                        alvo = ultima_por_dia.get(dia)
                        if alvo is None:
                            continue
                        alvo["itens"].extend(copias)
                    else:
                        categoria = {
                            "nome": nome_categoria,
                            "trilha": trilha,
                            "itens": copias,
                        }
                        categorias_por_dia[datas[dia]].append(categoria)
                        ultima_por_dia[dia] = categoria

        for data, categorias in categorias_por_dia.items():
            if not categorias:
                continue
            registro = por_data.setdefault(data, [])
            registro.append(
                {
                    "tipo": tipo,
                    "nome": nome_refeicao,
                    "observacao": observacao,
                    "categorias": categorias,
                }
            )

    ordem = {tipo: i for i, (tipo, _, _) in enumerate(REFEICOES)}
    dias = [
        {
            "data": data.isoformat(),
            "refeicoes": sorted(refeicoes, key=lambda r: ordem.get(r["tipo"], 9)),
        }
        for data, refeicoes in sorted(por_data.items())
    ]
    doc.close()
    return dias
