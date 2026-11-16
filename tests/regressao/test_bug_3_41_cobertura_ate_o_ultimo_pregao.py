"""BUG-3-41: a cobertura do COTAHIST anual exige 31/12, dia sem pregão.

`proventos_b3.calendario_anual` (F3-P14b) só aceita o arquivo anual de um ano que não é o do
fim do trecho se a data de geração for 31/12 ou depois. Os arquivos anuais do banco real são
gerados no último pregão do ano (30/12/2024, 30/12/2025), então o calendário abstém em todo
trecho que atravessa a virada do ano: o calendário anual de proventos da qualidade de um ano
inteiro e o calendário da data ex do motor histórico (BUG-3-40, F3-8h-cal) com início da
janela entre 31/12 e 07/01. Decisão 44 do Marcos (16/11/2026): a cobertura vai até o último
pregão do mês, pelo próprio COTAHIST armazenado, não até o último dia do calendário.
"""

import sqlite3
from contextlib import closing
from datetime import date

import pytest
from test_calendario_proventos import COLETA, _anual

from sentinela.data import proventos_b3
from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes

ULTIMO_PREGAO_2024 = date(2024, 12, 30)  # 31/12/2024 sem pregão na B3
REFERENCIA = date(2026, 1, 2)
INICIO = proventos_b3.inicio_da_janela(REFERENCIA)  # 02/01/2025
DATA_COM = date(2024, 12, 27)  # sexta-feira; a data ex é 30/12/2024, antes da janela


@pytest.fixture
def conn(tmp_path):
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        for arquivo in (
            _anual(tmp_path, 2024, ULTIMO_PREGAO_2024, ate=ULTIMO_PREGAO_2024),
            _anual(tmp_path, 2025, date(2025, 1, 10), ate=date(2025, 1, 10)),
        ):
            b3_cotahist.carregar(
                conexao, arquivo, fonte=f"b3:{arquivo.name}", coleta=COLETA
            )
        yield conexao


def test_ano_inteiro_coberto_pelo_arquivo_gerado_no_ultimo_pregao(conn):
    lido = proventos_b3.calendario_do_banco(conn, date(2024, 1, 1), date(2024, 12, 31))
    assert not isinstance(lido, proventos_b3.Abstencao), lido
    assert lido["pregoes"][-1] == ULTIMO_PREGAO_2024.isoformat()


def test_data_ex_no_inicio_de_janeiro_decidida_pelo_calendario(conn):
    registro = {"lastDatePriorEx": DATA_COM.strftime("%d/%m/%Y")}
    pregoes = b3_proventos.pregoes_da_data_ex(conn, [registro], REFERENCIA)
    assert pregoes is not None
    calendario = frozenset(date.fromisoformat(p) for p in pregoes)
    assert proventos_b3._na_janela(DATA_COM, INICIO, REFERENCIA, calendario) is False
