"""BUG-4-19: quantidade integral do NumPy vira BLOB e o preço médio pode virar infinito.

Ressalvas da auditoria R2 do bloco 0 sobre o F4-A11 (`docs/loop/auditorias/bloco0-codex.md`):
`np.int64(10)` passa por `numbers.Integral` e o SQLite o grava como BLOB, e uma redução
posterior encontra bytes onde espera um inteiro; duas compras finitas a `1e308` gravam `inf`
como preço médio, porque `qtd × preço` estoura na média ponderada.

Banco SQLite temporário; tickers e valores sintéticos, sem dado da carteira real.
"""

import math
import sqlite3
from contextlib import closing

import numpy as np
import pytest

from database import DatabaseManager


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(db_path=str(tmp_path / "carteira.db"))


def _tipo(db, ticker: str) -> str:
    with closing(sqlite3.connect(db.db_path)) as conn:
        return conn.execute(
            "SELECT typeof(quantidade) FROM carteira_real WHERE ticker = ?", (ticker,)
        ).fetchone()[0]


@pytest.mark.parametrize("tipo", [np.int64, np.int32, np.uint16])
def test_quantidade_integral_do_numpy_e_gravada_como_inteiro(db, tipo):
    assert db.adicionar_posicao("TSTA3", tipo(10), 10.0) is True
    assert _tipo(db, "TSTA3") == "integer"

    assert db.adicionar_posicao("TSTA3", -4, 12.0) is True
    assert db.listar_carteira()[0]["quantidade"] == 6


def test_preco_medio_nao_finito_e_rejeitado_sem_alterar_a_posicao(db):
    db.adicionar_posicao("TSTA3", 2, 1e308)

    with pytest.raises(ValueError, match="preço médio"):
        db.adicionar_posicao("TSTA3", 2, 1e308)

    posicao = db.listar_carteira()[0]
    assert posicao["quantidade"] == 2
    assert posicao["preco_medio"] == 1e308
    assert math.isfinite(posicao["preco_medio"])


def test_preco_do_numpy_continua_aceito_como_real(db):
    assert db.adicionar_posicao("TSTA3", 3, np.float64(12.5)) is True
    assert db.listar_carteira()[0]["preco_medio"] == pytest.approx(12.5)
