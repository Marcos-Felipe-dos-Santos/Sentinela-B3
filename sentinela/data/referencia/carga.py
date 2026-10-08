"""Índice oficial carregado uma vez por processo, com trava (F2A-19).

O `peers_engine` busca tickers em threads; a trava garante uma só montagem por vez. O
índice é recarregado quando o TTL vence. Se nem a rede nem o índice salvo respondem,
devolve `None` (a cascata volta ao mapa manual) e só tenta de novo depois de uma pausa,
para não repetir o download a cada ticker.
"""

from __future__ import annotations

import logging
import threading
import zipfile
from datetime import datetime
from pathlib import Path

import requests

from sentinela.data.referencia.correcoes import CorrecaoInvalida
from sentinela.data.referencia.fontes import TTL_SEGUNDOS, obter_indice
from sentinela.data.referencia.registro import Indice

logger = logging.getLogger(__name__)

PAUSA_APOS_FALHA_SEGUNDOS = 3600


class ReferenciaOficial:
    def __init__(self, pasta_dados: Path = Path("data")) -> None:
        self.pasta_dados = pasta_dados
        self._trava = threading.Lock()
        self._indice: Indice | None = None
        self._carregado_em: float | None = None
        self._falhou_em: float | None = None

    def indice(self, agora: datetime) -> Indice | None:
        """O índice em memória, recarregado se o TTL venceu; `None` se não há índice."""
        instante = agora.timestamp()
        with self._trava:
            if (
                self._indice is not None
                and instante - self._carregado_em < TTL_SEGUNDOS
            ):
                return self._indice
            if (
                self._falhou_em is not None
                and instante - self._falhou_em < PAUSA_APOS_FALHA_SEGUNDOS
            ):
                return self._indice
            try:
                self._indice = obter_indice(agora, self.pasta_dados)
            except (
                requests.RequestException,
                OSError,
                ValueError,
                KeyError,
                zipfile.BadZipFile,
                CorrecaoInvalida,
            ) as erro:
                logger.warning("Índice oficial indisponível: %s", erro)
                self._falhou_em = instante
                return self._indice
            self._carregado_em = instante
            self._falhou_em = None
            return self._indice
