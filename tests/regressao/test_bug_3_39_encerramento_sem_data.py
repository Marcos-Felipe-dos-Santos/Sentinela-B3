"""BUG-3-39: exercício sem data de fim vira "erro inesperado" no IPCA das janelas.

Um exercício da série CVM pode chegar com `fim` ausente. `macro._encerramentos` fazia
`date.fromisoformat(None)`, o `TypeError` caía no ramo de erro do código, com traceback no log,
e o IPCA abstinha com "erro inesperado no provedor macro: TypeError", no lugar do motivo do
dado ausente. Sonda do F3-8f-col (16/11/2026): 5 chamadas no motor histórico; o caminho do
SIDRA da cascata usa a mesma função.
"""

import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import pytest

from market_engine import MarketEngine
from sentinela.data.providers import macro
from sentinela.data.store import migracoes

D = datetime(2026, 3, 2, 15, tzinfo=UTC)
MOTIVO = "IPCA exige cinco encerramentos com data"
SEM_DATA = [{"fim": None}, {}, None]
IDS = ["fim-nulo", "sem-chave", "nao-dicionario"]


def _exercicios(sem_data):
    exercicios = [{"fim": f"{ano}-12-31"} for ano in range(2021, 2026)]
    exercicios[2] = sem_data
    return exercicios


@pytest.mark.parametrize("sem_data", SEM_DATA, ids=IDS)
def test_banco_abstem_pelo_dado_ausente(sem_data, caplog):
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        with caplog.at_level(logging.ERROR, logger=macro.__name__):
            resultado = macro.ipca_serie_do_banco(conn, _exercicios(sem_data), D)
    assert resultado == {"abstencao": MOTIVO}
    assert not caplog.records


@pytest.mark.parametrize("sem_data", SEM_DATA, ids=IDS)
def test_sidra_levanta_falha_do_dado(sem_data):
    provedor = macro.MacroProvider()

    def sem_rede(url, instante):
        raise AssertionError("o encerramento é conferido antes de baixar")

    provedor.baixar = sem_rede
    with pytest.raises(ValueError, match=MOTIVO):
        provedor.ipca_serie(_exercicios(sem_data), D)


@pytest.mark.parametrize("sem_data", SEM_DATA, ids=IDS)
def test_cascata_abstem_sem_log_de_erro(sem_data, caplog):
    """O caminho do SIDRA na cascata: a falha do dado vira o motivo, sem traceback."""
    dados = {"serie_cvm": {"exercicios": _exercicios(sem_data)}}
    with caplog.at_level(logging.ERROR):
        MarketEngine.__new__(MarketEngine)._contexto_janelas(dados, D)
    assert dados["ipca_serie"] == {"abstencao": MOTIVO}
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
