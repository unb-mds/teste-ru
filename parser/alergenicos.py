"""Leitura dos alergenicos, que a Fonte oficial publica apenas como icones.

Os icones ao lado dos pratos e os da legenda do rodape sao imagens diferentes
(resolucoes diferentes, xrefs diferentes), entao o vinculo entre eles e feito
por semelhanca visual: cada imagem vira uma assinatura em escala de cinza e o
icone do prato recebe o rotulo da legenda mais parecida.

Regra do ADR-0002: na duvida, indeterminado. Nunca inferir ausencia.
"""

import unicodedata

import pymupdf

# Vocabulario fechado, vindo da legenda oficial. A chave e a primeira palavra
# do rotulo impresso ("Leite e derivados" -> leite, "Trigo/Gluten" -> trigo).
VOCABULARIO = {
    "cogumelo": "cogumelo",
    "leite": "leite",
    "mel": "mel",
    "pimenta": "pimenta",
    "soja": "soja",
    "trigo": "trigo",
    "gluten": "trigo",
    "amendoim": "amendoim",
    "oleaginosa": "oleaginosa",
    "ovo": "ovo",
    "suino": "suino",
}

LADO = 12           # assinatura 12x12
DIST_MAXIMA = 22    # casamentos corretos ficam abaixo de 15; os errados, acima de 29
MARGEM_MINIMA = 6   # melhor e segunda melhor precisam estar bem separadas


def _sem_acento(txt):
    nfkd = unicodedata.normalize("NFKD", txt.lower())
    limpo = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(limpo.replace("/", " ").replace("-", " ").split())


def _assinatura(doc, xref):
    """Reduz a imagem a LADO x LADO tons de cinza, por amostragem."""
    pix = pymupdf.Pixmap(doc, xref)
    if pix.alpha:
        pix = pymupdf.Pixmap(pix, 0)
    if pix.colorspace is None:
        return None
    if pix.colorspace.n != 1:
        pix = pymupdf.Pixmap(pymupdf.csGRAY, pix)
    largura, altura, dados = pix.width, pix.height, pix.samples
    return [
        dados[int(j * altura / LADO) * pix.stride + int(i * largura / LADO)]
        for j in range(LADO)
        for i in range(LADO)
    ]


def _distancia(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def ler_legenda(doc, pagina):
    """Mapeia xref -> nome do alergenico, a partir da legenda do rodape."""
    rodape = pagina.rect.height * 0.85
    icones = [
        img
        for img in pagina.get_image_info(xrefs=True)
        if img["bbox"][1] > rodape and 22 < (img["bbox"][2] - img["bbox"][0]) < 45
    ]
    # Palavras do rodape que nomeiam um alergenico, com seu centro horizontal.
    candidatas = []
    for palavra in pagina.get_text("words"):
        chave = _sem_acento(palavra[4]).split(" ")[0]
        if chave in VOCABULARIO:
            candidatas.append(((palavra[0] + palavra[2]) / 2, palavra[1], chave))

    legenda = {}
    for img in icones:
        x0, _, x1, y1 = img["bbox"]
        centro = (x0 + x1) / 2
        abaixo = [c for c in candidatas if y1 - 8 < c[1] < y1 + 32]
        if not abaixo:
            continue
        mais_perto = min(abaixo, key=lambda c: abs(c[0] - centro))
        if abs(mais_perto[0] - centro) < 60:
            legenda[img["xref"]] = VOCABULARIO[mais_perto[2]]
    return legenda


def icones_dos_pratos(pagina):
    """Icones pequenos espalhados pela tabela: [(bbox, xref)]."""
    rodape = pagina.rect.height * 0.85
    return [
        (img["bbox"], img["xref"])
        for img in pagina.get_image_info(xrefs=True)
        if img["bbox"][1] < rodape and (img["bbox"][2] - img["bbox"][0]) < 22
    ]


def classificador(doc, legenda):
    """Devolve uma funcao xref -> nome do alergenico (ou None se incerto)."""
    assinaturas = {}
    for xref, nome in legenda.items():
        assinatura = _assinatura(doc, xref)
        if assinatura:
            assinaturas[xref] = (nome, assinatura)
    cache = {}

    def classificar(xref):
        if xref in cache:
            return cache[xref]
        resultado = None
        alvo = _assinatura(doc, xref)
        if alvo and assinaturas:
            notas = sorted(
                (_distancia(alvo, ass), nome) for nome, ass in assinaturas.values()
            )
            melhor, nome = notas[0]
            margem = notas[1][0] - melhor if len(notas) > 1 else 99
            if melhor <= DIST_MAXIMA and margem >= MARGEM_MINIMA:
                resultado = nome
        cache[xref] = resultado
        return resultado

    return classificar
