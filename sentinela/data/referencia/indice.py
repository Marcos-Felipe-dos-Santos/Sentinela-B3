"""Leitura e gravação do índice em JSON (F2A-1)."""

from __future__ import annotations

import json
from pathlib import Path

from sentinela.data.referencia.registro import Excecao, Indice, Registro

NOME_ARQUIVO = "indice.json"


def salvar_indice(indice: Indice, pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / NOME_ARQUIVO
    conteudo = {
        "gerado_em": indice.gerado_em,
        "fontes": indice.fontes,
        "registros": {t: r.para_dict() for t, r in sorted(indice.registros.items())},
        "excecoes": [e.para_dict() for e in indice.excecoes],
    }
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    temporario.replace(destino)
    return destino


def carregar_indice(pasta: Path) -> Indice | None:
    caminho = pasta / NOME_ARQUIVO
    if not caminho.exists():
        return None
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    return Indice(
        gerado_em=bruto["gerado_em"],
        fontes=bruto["fontes"],
        registros={t: Registro.de_dict(r) for t, r in bruto["registros"].items()},
        excecoes=[Excecao(**e) for e in bruto["excecoes"]],
    )
