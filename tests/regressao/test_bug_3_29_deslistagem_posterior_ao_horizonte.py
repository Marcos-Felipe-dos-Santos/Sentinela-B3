"""Ficha §5/decisão42: fato depois de T não altera o retorno nem a suspensão até T."""

from datetime import date

import pytest

from backtesting.backtest_pit import retorno_total


def test_deslistagem_depois_do_horizonte_nao_muda_preco_mantido():
    d, ex, t = date(2020, 1, 31), date(2020, 4, 30), date(2021, 1, 29)
    kwargs = {
        "inicio": d,
        "fim": t,
        "pregoes": [d, ex, t],
        "suspensao_confirmada": True,
    }
    precos = {d: 10, ex: 12}
    sem = retorno_total(precos, **kwargs)
    com = retorno_total(precos, deslistagem=date(2022, 1, 31), **kwargs)
    assert sem["retorno"] == pytest.approx(0.2)
    assert com == sem
    assert com["suspensao"] is True
