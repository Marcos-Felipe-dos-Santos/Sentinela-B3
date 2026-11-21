"""Uma cotação final ausente não demonstra, sozinha, suspensão."""

from datetime import date

from backtesting.backtest_pit import retorno_total


def test_cotacao_terminal_ausente_sem_status_abstem():
    inicio, fim = date(2020, 1, 31), date(2021, 1, 29)
    saida = retorno_total({inicio: 10}, inicio=inicio, fim=fim, pregoes=[inicio, fim])
    assert saida["retorno"] is None
    assert saida["abstencao"] == "estado terminal sem prova de suspensão ou deslistagem"
