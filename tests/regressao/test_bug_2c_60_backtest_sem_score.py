"""BUG-2C-60: ausência de score pós-F2C-3 não é abstenção de escopo.

Especificação: decisão do Marcos de 09/11/2026, opção (a) da auditoria
Claude de fechamento. O backtest aguarda reconstrução na Fase 3.
"""

from unittest.mock import patch

import pytest
from test_financeiro_pre_refactor import _acao, _processar

from backtesting.backtest_engine import BacktestEngine
from tests.test_backtest_engine import _fundamentos, _historico


def test_analise_pos_2c_sem_score_nao_e_fora_do_escopo() -> None:
    analise = _processar(_acao())
    assert "score_final" not in analise
    assert analise["lentes"]
    assert not analise.get("abstencao")
    engine = BacktestEngine(tickers=["TEST3.SA"], end_date="2024-08-01")
    engine.dados_historico = {"TEST3.SA": _historico()}
    with patch(
        "backtesting.backtest_engine.ValuationEngine.processar", return_value=analise
    ):
        resultado = engine.simular_analise_mensal(
            "TEST3", "2024-04-15", {"TEST3": _fundamentos()["PETR4"]}
        )
    assert resultado["status"] == "INDISPONIVEL"
    assert resultado["motivo"] == (
        "backtest indisponível desde a 2C: sem score agregado; reconstrução na Fase 3"
    )
    assert "score_final" not in resultado


@pytest.mark.parametrize("riscos", [[], ["motivo de escopo do motor"]])
def test_abstencao_explicita_preserva_motivo_de_escopo(riscos: list[str]) -> None:
    engine = BacktestEngine(tickers=["TEST3.SA"], end_date="2024-08-01")
    engine.dados_historico = {"TEST3.SA": _historico()}
    analise = {"abstencao": "modelo fora do escopo", "riscos": riscos}
    with patch(
        "backtesting.backtest_engine.ValuationEngine.processar", return_value=analise
    ):
        resultado = engine.simular_analise_mensal(
            "TEST3", "2024-04-15", {"TEST3": _fundamentos()["PETR4"]}
        )
    assert resultado["status"] == "FORA_DO_ESCOPO"
    assert resultado["motivo"] == (riscos or [analise["abstencao"]])[0]
