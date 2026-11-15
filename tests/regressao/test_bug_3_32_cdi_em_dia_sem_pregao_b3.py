"""Fator DI aprovado: inclui taxa de dia bancário sem pregão B3, em [L,T).

Fontes D18 em backtest_pit/macro_2022.zip: SGS12 tem29 e30/12/2022 a0,050788%;
COTAHIST2022 termina29/12. Em02/01/2023 a taxa já fica fora do intervalo.
"""

from datetime import date
from fractions import Fraction

import pytest

from backtesting.backtest_pit import retorno_total


def test_cdi_30_de_dezembro_conta_sem_pregao_b3():
    d, ultimo, bancario, t = (
        date(2022, 1, 31),
        date(2022, 12, 29),
        date(2022, 12, 30),
        date(2023, 1, 2),
    )
    saida = retorno_total(
        {d: 10, ultimo: 10},
        inicio=d,
        fim=t,
        deslistagem=ultimo,
        cdi={ultimo: 0.050788, bancario: 0.050788, t: 99},
        pregoes=[d, ultimo, t],
    )
    esperado = (1 + Fraction("0.050788") / 100) ** 2 - 1
    assert saida["retorno"] == pytest.approx(float(esperado))
    assert saida["abstencao"] is None
