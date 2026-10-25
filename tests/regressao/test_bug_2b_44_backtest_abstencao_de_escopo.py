"""BUG-2B-44: o backtest grava "OK" para a abstenção de escopo do motor e quebra no score.

Desde o F2B-4, snapshot sem classe oficial ou sem modelo do BPP consolidado sai do motor sem
`score_final`; o backtest marcava "OK" e `validar_recomendacao` lia `analise["score_final"]`
(KeyError). Origem: revisão do F2B-4, 25/10/2026.
"""

from unittest.mock import patch

from backtesting.backtest_engine import BacktestEngine
from tests.test_backtest_engine import _fundamentos, _historico


def test_abstencao_de_escopo_nao_e_ok():
    engine = BacktestEngine(tickers=["PETR4.SA"], end_date="2024-08-01")
    engine.dados_historico = {"PETR4.SA": _historico()}
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
        resultado = engine.simular_analise_mensal("PETR4", "2024-04-15", _fundamentos())
    assert resultado["status"] == "FORA_DO_ESCOPO"
    assert resultado["motivo"] == "classe do ativo não informada"
    assert "score_final" not in resultado
