"""Coleta o cardapio da semana e grava data/cardapio.json.

Nada e gravado se a validacao falhar: o site continua com o ultimo dado bom,
que a interface ja sinaliza como desatualizado.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import fonte
from extrator import PdfInesperado, extrair
from validacao import resumo, validar

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "data" / "cardapio.json"


def _agora():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def coletar(pdfs_locais=None):
    campi_fonte = fonte.descobrir()
    cliente = fonte.sessao()
    campi = []
    for campus in campi_fonte:
        if pdfs_locais and campus["id"] in pdfs_locais:
            conteudo = Path(pdfs_locais[campus["id"]]).read_bytes()
        else:
            conteudo = fonte.baixar(campus["pdf"], cliente)
        dias = extrair(conteudo)
        campi.append(
            {
                "id": campus["id"],
                "nome": campus["nome"],
                "pdf": campus["pdf"],
                "dias": dias,
            }
        )

    datas = sorted(d["data"] for c in campi for d in c["dias"])
    rotulo = next((c["rotulo_semana"] for c in campi_fonte if c["rotulo_semana"]), None)
    return {
        "gerado_em": _agora(),
        "fonte": fonte.FONTE,
        "semana": {
            "inicio": datas[0] if datas else None,
            "fim": datas[-1] if datas else None,
            "rotulo": rotulo,
        },
        "campi": campi,
    }


def main():
    args = argparse.ArgumentParser(description="Coleta o cardapio do RU da UnB")
    args.add_argument("--saida", default=str(DESTINO))
    args.add_argument(
        "--pdf",
        action="append",
        default=[],
        metavar="campus=arquivo.pdf",
        help="usa um PDF local em vez de baixar (para desenvolvimento)",
    )
    opcoes = args.parse_args()
    locais = dict(p.split("=", 1) for p in opcoes.pdf)

    try:
        cardapio = coletar(locais)
    except (fonte.FonteIndisponivel, PdfInesperado) as erro:
        print(f"coleta abortada: {erro}", file=sys.stderr)
        return 1

    problemas = validar(cardapio, [c[0] for c in fonte.CAMPI])
    numeros = resumo(cardapio)
    print(
        f"campi={numeros['campi']} itens={numeros['itens']} "
        f"indeterminados={numeros['itens_indeterminados']}"
    )
    if problemas:
        print("validacao falhou; nada foi gravado:", file=sys.stderr)
        for problema in problemas:
            print(f"  - {problema}", file=sys.stderr)
        return 1

    destino = Path(opcoes.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(cardapio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"gravado em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
