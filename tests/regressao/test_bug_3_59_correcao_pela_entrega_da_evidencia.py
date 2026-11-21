"""BUG-3-59 (Codex C3-01, checkpoint da Fase 3): a correção vale pela entrega da evidência.

A DD-89 cortava cada linha da tabela de correções pela data que ela registrava. Na MGLU3 a
`data` era a referência da DFP 2025 (2025-12-31), mas a DFP só foi entregue em 12/03/2026
(`DT_RECEB` da versão 1 no índice do ZIP oficial): de 01/01 a 12/03/2026 o índice em D já
trocava PN por ON com um documento que ainda não existia. Decisão 51 do Marcos (20/11/2026):
a linha vale pela entrega ou publicação comprovada da evidência, anterior a D.

FCA sintético no layout oficial com a MGLU3 como PNA, pela carga e pela montagem reais
(o mesmo da regressão BUG-3-55), e a tabela real de correções.
"""

from datetime import date

import pytest
from test_bug_3_55_correcoes_no_indice_historico import CADASTRO, conn  # noqa: F401

from sentinela.data.referencia import universo

ENTREGA_DFP_2025 = date(2026, 3, 12)  # DT_RECEB da MGLU3 em dfp_cia_aberta_2025.csv


@pytest.mark.parametrize(
    ("dia", "especie"),
    [(date(2026, 3, 11), "PN"), (ENTREGA_DFP_2025, "PN"), (date(2026, 3, 13), "ON")],
)
def test_especie_da_mglu3_so_muda_depois_da_entrega_da_dfp(conn, dia, especie):  # noqa: F811
    assert universo.indice_em(conn, dia, CADASTRO).registros["MGLU3"].especie == especie


def test_linha_da_mglu3_registra_a_entrega_da_dfp():
    (mglu,) = [c for c in universo.ler_correcoes() if c.ticker == "MGLU3"]
    assert mglu.data == ENTREGA_DFP_2025.isoformat()
