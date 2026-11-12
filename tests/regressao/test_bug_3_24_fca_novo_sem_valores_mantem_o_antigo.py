"""BUG-3-24: companhia cujo FCA mais recente não lista valor mobiliário fica pelo FCA anterior.

A montagem do índice (`montagem.fca_mais_recente`) escolhe a referência mais recente entre as
linhas lidas; uma referência nova entregue sem nenhuma linha `valor_mobiliario` não aparece
ali, e os códigos da referência anterior continuam no índice. Na comparação do F3-5 (D =
12/11/2026): ZAMP3, PTNT3, PTNT4 e RDNI3, com o FCA de 2026 entregue sem valores mobiliários
e sem negócio de agosto a outubro de 2026, seguem no índice pelo FCA de 2025. Correto: a
referência mais recente entregue decide; sem linhas, o código não entra pelo FCA antigo.
"""

import sqlite3
from contextlib import closing
from datetime import date

import pytest
from test_universo_pit import CADASTRO_TSTE, TSTE, _fca_sintetico, _valor

from sentinela.data.referencia import universo
from sentinela.data.store import migracoes


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


@pytest.mark.xfail(strict=True, reason="BUG-3-24: corrigido em F3-5-fix")
def test_bug_3_24_fca_novo_sem_valores_nao_volta_ao_antigo(conn, tmp_path):
    antiga = _valor(Data_Referencia="2025-01-01", Valor_Mobiliario="Ações Ordinárias",
                    Codigo_Negociacao="VELH3", Data_Inicio_Negociacao="2020-01-02")  # fmt: skip
    _fca_sintetico(
        conn, tmp_path, [(TSTE, "2025-01-01", "1", "2025-02-01")], [antiga], ano=2025
    )
    _fca_sintetico(conn, tmp_path, [(TSTE, "2026-01-01", "1", "2026-02-01")], [])
    assert universo.indice_em(conn, date(2026, 3, 1), CADASTRO_TSTE).registros == {}
