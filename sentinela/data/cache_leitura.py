"""Caches limitados de snapshots: sem relógio e sem alterar a observação de origem.

CSV: caminho, mtime em nanossegundos, tamanho, membro do ZIP e política de NA.
HTTP: o chamador fornece a identidade completa da coleta; este módulo não escolhe TTL.
"""

from __future__ import annotations

import io
import threading
import zipfile
from collections import OrderedDict
from collections.abc import Hashable
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, eq=False)
class IdentidadeLeitor:
    """Identidade real, sem chamar igualdade/hash do leitor; conserva sua referência."""

    leitor: object

    def __hash__(self) -> int:
        return id(self.leitor)

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, IdentidadeLeitor) and self.leitor is outro.leitor


class CacheCopia[T]:
    """LRU em memória com cópias isoladas e chaves hashable definidas pelo consumidor."""

    def __init__(self, limite: int = 32) -> None:
        self._limite = limite
        self._dados: OrderedDict[Hashable, T] = OrderedDict()
        self._trava = threading.Lock()

    def buscar(self, chave: Hashable) -> T | None:
        with self._trava:
            if chave not in self._dados:
                return None
            self._dados.move_to_end(chave)
            return deepcopy(self._dados[chave])

    def guardar(self, chave: Hashable, valor: T) -> None:
        copia = deepcopy(valor)
        with self._trava:
            self._dados[chave] = copia
            self._dados.move_to_end(chave)
            while len(self._dados) > self._limite:
                self._dados.popitem(last=False)


_TRAVA_CSV = threading.Lock()


@lru_cache(maxsize=8)
def _csv_do_snapshot(
    assinatura: tuple[str, int, int], membro: str, literal: bool
) -> pd.DataFrame:
    import pandas as pd

    with zipfile.ZipFile(assinatura[0]) as arquivo, arquivo.open(membro) as csv:
        return pd.read_csv(
            io.TextIOWrapper(csv, encoding="latin-1"),
            sep=";",
            dtype=str,
            low_memory=False,
            keep_default_na=not literal,
        )


def ler_csv_zip(caminho: Path, membro: str, *, literal: bool = False) -> pd.DataFrame:
    """Mesmo arquivo e modo de leitura compartilham CSV; consumidores recebem cópia."""
    caminho = Path(caminho)
    stat = caminho.stat()
    assinatura = (str(caminho.resolve()), stat.st_mtime_ns, stat.st_size)
    with _TRAVA_CSV:
        return _csv_do_snapshot(assinatura, membro, literal).copy(deep=True)
