"""F2C-39: ausência de fuso tem motivo próprio antes da validação documental."""

from datetime import UTC, datetime

from tests.test_valuation_escopo import _PROVENIENCIA, DADOS
from valuation_engine import ValuationEngine


def test_asof_sem_fuso_informa_motivo_proprio() -> None:
    r = ValuationEngine().processar(
        {
            **DADOS,
            "classe_ativo": "STOCK",
            "modelo_bpp": "empresa",
            "modelo_bpp_proveniencia": _PROVENIENCIA,
        },
        as_of=datetime(2026, 3, 1, 18, tzinfo=UTC).replace(tzinfo=None),
    )
    assert r["riscos"] == ["as_of exige fuso horário"]
    assert not {"fair_value", "upside", "score_final"} & set(r)
