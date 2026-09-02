"""Descoberta dos PDFs na Fonte oficial.

O parser nunca constroi as URLs dos PDFs: o mes de upload varia entre campi na
mesma semana (/2026/09/ para um, /2026/08/ para outro). Elas sao sempre lidas
dos hrefs da pagina.
"""

import re

import requests
from bs4 import BeautifulSoup

FONTE = "https://ru.unb.br/cardapio-refeitorio/"

# id -> (nome de exibicao, marcador procurado no href do PDF)
CAMPI = [
    ("darcy-ribeiro", "Darcy Ribeiro", "darcy"),
    ("ceilandia", "Ceilândia", "ceilandia"),
    ("gama", "Gama", "gama"),
    ("planaltina", "Planaltina", "planaltina"),
    ("fazenda-agua-limpa", "Fazenda Água Limpa", "fazenda"),
]

TIMEOUT = 60


class FonteIndisponivel(Exception):
    """A Fonte oficial nao pode ser lida ou nao tem os PDFs esperados."""


def sessao():
    s = requests.Session()
    s.headers["User-Agent"] = "cardapio-ru-unb/1.0 (+https://github.com)"
    return s


def descobrir(cliente=None):
    """Devolve [{id, nome, pdf, rotulo_semana}] para os cinco campi."""
    cliente = cliente or sessao()
    try:
        resp = cliente.get(FONTE, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as erro:
        raise FonteIndisponivel(f"nao foi possivel ler {FONTE}: {erro}") from erro

    sopa = BeautifulSoup(resp.text, "html.parser")
    pdfs = [
        a["href"].strip()
        for a in sopa.find_all("a", href=True)
        if a["href"].lower().strip().endswith(".pdf")
    ]

    achados = []
    faltando = []
    for campus_id, nome, marcador in CAMPI:
        url = next((u for u in pdfs if marcador in u.lower().rsplit("/", 1)[-1]), None)
        if url is None:
            faltando.append(nome)
            continue
        achados.append(
            {
                "id": campus_id,
                "nome": nome,
                "pdf": url,
                "rotulo_semana": _rotulo_semana(url),
            }
        )

    if faltando:
        raise FonteIndisponivel(
            "PDF nao encontrado na pagina para: " + ", ".join(faltando)
        )
    return achados


def _rotulo_semana(url):
    """'...-Semana-02-31-8-a-6-9.pdf' -> 'Semana 02'."""
    achado = re.search(r"semana[-_ ]?(\d{1,2})", url, re.IGNORECASE)
    return f"Semana {achado.group(1)}" if achado else None


def baixar(url, cliente=None):
    cliente = cliente or sessao()
    try:
        resp = cliente.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as erro:
        raise FonteIndisponivel(f"falha ao baixar {url}: {erro}") from erro
    if not resp.content.startswith(b"%PDF"):
        raise FonteIndisponivel(f"{url} nao devolveu um PDF")
    return resp.content
