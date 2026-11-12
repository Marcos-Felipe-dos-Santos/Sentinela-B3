"""BUG-3-26: valor contraditório da CVM na mesma chave sai da leitura sem aviso.

Os ZIPs da CVM trazem, às vezes, a mesma conta do mesmo documento e período duas vezes, com
valores diferentes: no `dfp_cia_aberta_2025.zip`, a conta 2.02 do BPP consolidado de
20.961.867/0001-10 (`ÚLTIMO`, 31/12/2025) aparece com 2.928.832 e com 3.088.832. A carga
(`carga_cvm`, F3-3b) grava a primeira e põe o caso só no resumo do arquivo
(`cargas_arquivo.resumo_json`, com no máximo 100 casos); `leitura.demonstrativo` devolve o
primeiro valor sem motivo. No backfill do F3-7b (12/11/2026): 1.360 conflitos (568 na
DFP, 775 no ITR e 17 no FCA). Correto (DD-57): como no Informe de
FII (`leitura._versoes_do_informe`), o documento com conflito fica fora da leitura, com o motivo.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import pytest
from test_carga_cvm import CIA, DFP, _copia

from sentinela.data.pit import carga_cvm, leitura
from sentinela.data.store import migracoes

DRE = "dfp_cia_aberta_DRE_con_2019.csv"


def _com_receita_contraditoria(texto):
    linhas = texto.splitlines(keepends=True)
    receita = next(
        linha for linha in linhas if ";ÚLTIMO;" in linha and ";3.01;" in linha
    )
    return "".join(linhas) + receita.replace("6767982.0000000000", "6767983.0000000000")


@pytest.mark.xfail(strict=True, reason="BUG-3-26: corrigido no F3-3b-fix")
def test_bug_3_26_documento_com_conflito_fica_fora_com_motivo(tmp_path):
    arquivo = _copia(DFP, tmp_path / "dfp.zip", {DRE: _com_receita_contraditoria})
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        resumo = carga_cvm.carregar(
            conn, arquivo, tipo="DFP", fonte="cvm:dfp.zip",
            coleta="2026-11-12T19:00:00+00:00",
        )  # fmt: skip
        assert resumo.total_conflitos == 1
        lido = leitura.demonstrativo(
            conn, "DFP", "DRE_con", datetime(2026, 11, 12, 15, tzinfo=UTC)
        )
        assert lido.dados.empty
        assert list(lido.motivos) == [(CIA, "2019-12-31")]
