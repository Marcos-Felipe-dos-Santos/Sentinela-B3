"""BUG-3-25: o Informe de FII de 2016 a 2020 é recusado inteiro na carga.

A CVM republicou os anos de 2021 em diante no leiaute da Resolução 175 (`CNPJ_Fundo_Classe`),
mas os ZIPs de 2016 a 2020 continuam com a coluna `CNPJ_Fundo`. `carga_cvm._carregar_fii` exige
`CNPJ_Fundo_Classe` e recusa cada linha ("CNPJ_Fundo_Classe vazio"): no backfill do F3-7b
(12/11/2026), 0 linhas gravadas e 1.104 a 18.237 recusadas por ano, e o arquivo fica registrado
em `cargas_arquivo`, de modo que a segunda carga devolve `ja_carregado` sem ler o ZIP. Sem esses
anos, nenhum FII entra no universo ponto-no-tempo antes de 2021 (F3-5). Correto: as linhas do
leiaute antigo são gravadas com o mesmo CNPJ do fundo.

A fixture é o recorte oficial do `inf_mensal_fii_2017.zip` (SHA-256 `4d24ef32…`, baixado em
12/11/2026) para o mesmo fundo da fixture de 2023 (00.332.266/0001-31), com os bytes das
linhas preservados.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from sentinela.data.pit import carga_cvm
from sentinela.data.store import migracoes

INFORME_2017 = (
    Path(__file__).parents[1] / "fixtures" / "pit_cvm" / "inf_mensal_fii_2017.zip"
)


@pytest.mark.xfail(strict=True, reason="BUG-3-25: corrigido no F3-3b-fix")
def test_bug_3_25_informe_de_2017_grava_as_linhas_do_fundo():
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        resumo = carga_cvm.carregar(
            conn, INFORME_2017, tipo="FII_INFORME",
            fonte="cvm:inf_mensal_fii_2017.zip", coleta="2026-11-12T19:00:00+00:00",
        )  # fmt: skip
        assert resumo.recusadas == []
        assert resumo.inseridas == {"fii_informe_linhas": 36}
