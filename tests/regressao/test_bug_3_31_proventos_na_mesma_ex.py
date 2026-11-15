"""Decisão42: quem entra no fechamento ex não recebe outro provento com a mesma ex."""

from datetime import date

import pytest

from backtesting.backtest_pit import retorno_total


@pytest.mark.parametrize("valores", [(1, 2), (2, 1)])
@pytest.mark.parametrize("fator", [1, 2])
def test_dois_proventos_na_mesma_ex_nao_remuneram_fracao_recem_comprada(valores, fator):
    d, ex, com, evento, t = (
        date(2020, 1, 31),
        date(2020, 4, 30),
        date(2020, 6, 30),
        date(2020, 7, 1),
        date(2021, 1, 29),
    )
    # Uma ação tem direito a3 e compra0,3 ao fechamento10. Nenhum dos3
    # remunera a fração comprada naquele fechamento. Split posterior conserva13.
    saida = retorno_total(
        {d: 10, ex: 10, com: 10, evento: 10 / fator, t: 10 / fator},
        [{"data_ex": ex, "valor": v} for v in valores],
        [{"data_com": com, "data_ex": evento, "fator": fator}],
        inicio=d,
        fim=t,
    )
    assert saida["retorno"] == pytest.approx(0.30)
    assert saida["abstencao"] is None
