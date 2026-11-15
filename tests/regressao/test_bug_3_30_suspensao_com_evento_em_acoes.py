"""Ficha§5/decisão42: preço mantido não cria riqueza na troca de base acionária."""

from datetime import date

import pytest

from backtesting.backtest_pit import retorno_total


@pytest.mark.parametrize("fator", [2.0, 0.5])
@pytest.mark.parametrize("caixa", [0.0, 1.0])
def test_evento_durante_suspensao_nao_cria_retorno_de_preco(fator, caixa):
    d, com, ex, t = (
        date(2020, 1, 31),
        date(2020, 6, 30),
        date(2020, 7, 1),
        date(2021, 1, 29),
    )
    # Uma ação de10 vira fator ações de10/fator. Sem variação econômica,
    # só o provento por ação nova emT acrescenta fator×caixa ao patrimônio10.
    saida = retorno_total(
        {d: 10, com: 10},
        [{"data_ex": t, "valor": caixa}],
        [{"data_com": com, "data_ex": ex, "fator": fator}],
        inicio=d,
        fim=t,
        pregoes=[d, com, ex, t],
        suspensao_confirmada=True,
    )
    assert saida["retorno"] == pytest.approx(fator * caixa / 10)
    assert saida["suspensao"] is True
    assert saida["abstencao"] is None
