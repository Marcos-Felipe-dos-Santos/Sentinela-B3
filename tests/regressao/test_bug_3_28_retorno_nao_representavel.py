"""D17: insumo/ajuste não representável abstém; não escapa divisão por zero/overflow."""

from datetime import date

import pytest

from backtesting.backtest_pit import retorno_total

D, COM, EX, T = (
    date(2020, 1, 31),
    date(2020, 6, 30),
    date(2020, 7, 1),
    date(2021, 1, 29),
)


@pytest.mark.parametrize(
    "precos,eventos",
    [
        ({D: 1e-308, T: 1e-308}, [{"data_com": COM, "data_ex": EX, "fator": 1e308}]),
        ({D: 10**400, T: 1}, []),
    ],
)
def test_retorno_abstem_sem_excecao_quando_escala_nao_e_representavel(precos, eventos):
    saida = retorno_total(precos, eventos=eventos, inicio=D, fim=T)
    assert saida["retorno"] is None
    assert saida["abstencao"]
