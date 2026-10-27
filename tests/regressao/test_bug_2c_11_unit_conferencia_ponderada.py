"""Ficha por ação §1/7.3: comparar grandezas na mesma base da unit."""

import pytest

from data_quality import DataQualityReport
from market_engine import _lpa_divulgado_comparado
from sentinela.data.acoes_cvm import LpaDivulgado


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2C-11 · conferência da unit ignora pesos · corrige: F2C-50 (2C-b)",
)
def test_unit_sem_divergencia_na_soma_ponderada() -> None:
    # Unit: 1 ON de LPA1 + 2 PN de LPA2 =5. Recalculado também5 por unit.
    comparado = _lpa_divulgado_comparado(
        {"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)}, None, None
    )
    dados = {
        "classe_ativo": "UNIT",
        "acoes_por_unit": {"ON": 1, "PN": 2},
        "acoes_cvm": {
            "acoes_por_papel": 3,
            "lpa_recalculado": 5.0,
            "lpa_divulgado_comparado": comparado,
        },
    }
    assert DataQualityReport(dados)._alertas_fontes_independentes(5.0) == []
