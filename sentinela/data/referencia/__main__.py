"""Atualiza o índice e, com `--cobertura`, mostra a cobertura sobre os arquivos reais.

Uso: python -m sentinela.data.referencia [--pasta data] [--cobertura]
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sentinela.data.referencia import fontes
from sentinela.data.referencia.cobertura import cobertura
from sentinela.data.referencia.indice import salvar_indice
from sentinela.data.referencia.montagem import montar_indice


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pasta", default="data", help="pasta de dados (padrão: data)")
    ap.add_argument(
        "--cobertura", action="store_true", help="mostra a cobertura do índice"
    )
    args = ap.parse_args(argv)
    pasta = Path(args.pasta)
    agora = datetime.now(UTC)
    f = fontes.carregar_fontes(agora, pasta)
    indice = montar_indice(f.fcas, f.cadastro, f.informe, f.cotacoes, f.meta, f.data)
    salvar_indice(indice, pasta / "referencia")
    print(f"índice: {len(indice.registros)} registros, {len(indice.excecoes)} exceções")
    if args.cobertura:
        print(
            json.dumps(
                cobertura(indice, f.fcas, f.informe), ensure_ascii=False, indent=1
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
