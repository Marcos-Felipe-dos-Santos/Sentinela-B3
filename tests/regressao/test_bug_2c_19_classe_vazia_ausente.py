"""F2C-39: classe vazia normalizada é ausência, com motivo específico."""

import pytest

from tests.test_valuation_escopo import DADOS
from valuation_engine import ValuationEngine


@pytest.mark.parametrize("classe", ["", "   "])
def test_classe_vazia_informa_ausencia(classe: str) -> None:
    r = ValuationEngine().processar(
        {**DADOS, "classe_ativo": classe, "modelo_bpp": "empresa"}
    )
    assert r["riscos"] == ["classe do ativo não informada"]
    assert not {"fair_value", "upside", "score_final"} & set(r)
