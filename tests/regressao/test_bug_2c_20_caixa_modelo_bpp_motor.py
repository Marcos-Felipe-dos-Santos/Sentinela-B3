"""F2C-39: comparação de modelo após normalizar caixa/espaços."""

import pytest

from tests.test_valuation_escopo import DADOS
from valuation_engine import ValuationEngine


@pytest.mark.parametrize("modelo", ["EMPRESA", " empresa "])
def test_modelo_empresa_normalizado_segue(modelo: str) -> None:
    r = ValuationEngine().processar(
        {**DADOS, "classe_ativo": "STOCK", "modelo_bpp": modelo}
    )
    assert r["metodos_usados"].startswith("Graham")
