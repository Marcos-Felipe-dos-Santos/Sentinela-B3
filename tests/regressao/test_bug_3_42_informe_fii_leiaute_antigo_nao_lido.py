"""BUG-3-42: o provedor do Informe não acha o fundo no leiaute anterior à Resolução 175.

O BUG-3-25 (F3-3b-fix) passou a gravar no banco as linhas do Informe de 2016 a 2020, que vêm
com a coluna `CNPJ_Fundo`. A remontagem em D devolve esses ZIPs com o cabeçalho original, mas
`CVMFIIProvider._linhas_do_fundo` só procura `CNPJ_Fundo_Classe`: o ano sai "sem linhas do
fundo", e o rendimento e o DY do FII abstêm em toda data antes de 2021. Sonda do F3-8j
(16/11/2026): ALMI11 em 28/06/2019, com 36 linhas por ano no banco de 2017 a 2025, lido como
"Informe Mensal incompleto: 2018 sem linhas do fundo; 2017 sem linhas do fundo".

A fixture é o recorte oficial do `inf_mensal_fii_2017.zip` (a do BUG-3-25), carregada pelo
produtor real e lida pelo motor histórico, como na amostra.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from sentinela.data.pit import carga_cvm
from sentinela.data.store import migracoes
from sentinela.services import historico

INFORME_2017 = (
    Path(__file__).parents[1] / "fixtures" / "pit_cvm" / "inf_mensal_fii_2017.zip"
)
CNPJ = "00.332.266/0001-31"
AS_OF = datetime(2018, 2, 20, 15, tzinfo=UTC)  # o Informe de 2017 entregue até jan/2018


def test_bug_3_42_motor_le_o_fundo_no_informe_de_2017(tmp_path):
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        carga_cvm.carregar(
            conn, INFORME_2017, tipo="FII_INFORME",
            fonte="cvm:inf_mensal_fii_2017.zip", coleta="2026-11-12T19:00:00+00:00",
        )  # fmt: skip
        motor = historico.MotorHistorico(conn, AS_OF, tmp_path / "pit", pd.DataFrame())
        informe = motor.cvm_fii.obter_rendimentos_fii(CNPJ, as_of=AS_OF)
    meses = {r["Data_Referencia"][:7] for r in informe["registros"]}
    assert {f"2017-{m:02d}" for m in range(1, 13)} <= meses
    assert all(r.get("Data_Entrega") for r in informe["registros"])
