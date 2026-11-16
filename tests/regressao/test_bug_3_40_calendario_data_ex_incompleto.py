"""BUG-3-40: calendário da data ex do motor histórico sem prova de cobertura do COTAHIST.

`b3_proventos.pregoes_da_data_ex` (F3-8h) devolvia os pregões guardados em `precos` nos meses
do limite e do início da janela, sem conferir que a carga do COTAHIST cobre esses meses. Com
o mês guardado incompleto, o pregão real seguinte à data com falta, o primeiro guardado cai
depois do início da janela e o provento de data ex anterior à janela é contado nela
(`proventos_b3._na_janela`). A cascata abstém quando o COTAHIST não é lido; o calendário do
banco (F3-P14b, `proventos_b3.calendario_do_banco`) exige a carga anual cuja geração alcança
o intervalo. Achado da revisão do F3-8h (16/11/2026).
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import date, timedelta

import pytest
from test_calendario_proventos import _cabecalho
from test_cotahist import _linha

from sentinela.data import proventos_b3
from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes

REFERENCIA = date(2026, 10, 30)
INICIO = proventos_b3.inicio_da_janela(REFERENCIA)  # 30/10/2025, quinta-feira
DATA_COM = date(2025, 10, 27)  # segunda-feira; a data ex real é 28/10, fora da janela
GUARDADOS = [date(2025, 10, 1), DATA_COM, date(2025, 10, 31)]  # faltam 28, 29 e 30/10


def _carregar(conn, pasta, nome, dias, geracao=None):
    linhas = [_linha(DATA=d.strftime("%Y%m%d"), CODNEG="TSTA3") for d in dias]
    if geracao is not None:
        linhas.insert(0, _cabecalho(2025, geracao))
    caminho = pasta / nome
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("COTAHIST.TXT", "\n".join(linhas).encode("latin-1"))
    b3_cotahist.carregar(conn, caminho, fonte="b3", coleta="2026-11-12T00:00:00+00:00")


CENARIOS = {
    # carga avulsa, sem o arquivo anual que prove o ano
    "sem-arquivo-anual": [("COTAHIST_LOTE.ZIP", GUARDADOS, None)],
    # o arquivo anual de 2025 gerado antes do início da janela, e um lote avulso depois
    "anual-gerado-antes": [
        ("COTAHIST_A2025.ZIP", GUARDADOS[:2], DATA_COM),
        ("COTAHIST_LOTE.ZIP", GUARDADOS[2:], None),
    ],
}


@pytest.mark.parametrize("cenario", CENARIOS, ids=list(CENARIOS))
def test_mes_incompleto_nao_decide_a_data_ex(cenario, tmp_path):
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        for nome, dias, geracao in CENARIOS[cenario]:
            _carregar(conn, tmp_path, nome, dias, geracao)
        registro = {"lastDatePriorEx": DATA_COM.strftime("%d/%m/%Y")}
        pregoes = b3_proventos.pregoes_da_data_ex(conn, [registro], REFERENCIA)
    assert DATA_COM > INICIO - proventos_b3.FOLGA_SEM_PREGAO
    assert pregoes is None
    assert proventos_b3._na_janela(DATA_COM, INICIO, REFERENCIA, None) is None


def test_controle_o_mes_guardado_incompleto_conta_o_provento():
    """Sem a guarda, o calendário guardado põe a data ex depois do início da janela."""
    calendario = frozenset(GUARDADOS) | {INICIO + timedelta(days=1)}
    assert proventos_b3._na_janela(DATA_COM, INICIO, REFERENCIA, calendario) is True
