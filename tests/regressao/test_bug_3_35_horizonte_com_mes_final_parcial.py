"""BUG-3-35: horizonte cujo mês final ainda está incompleto é tratado como completo.

Ficha PIT §8: a observação só entra no horizonte h se D mais h meses couber no último
pregão guardado. Pendência de 12/11 (F3-7a → F3-8b): o mês só fecha com pregão
observado no mês seguinte. Com o COTAHIST até 13/11/2026, novembro de 2026 está
aberto; T = 13/11 encurtaria o horizonte de D = 28/11/2025.
"""

from datetime import date

from backtesting.backtest_pit import BacktestPIT


def test_mes_final_sem_pregao_no_mes_seguinte_nao_fecha_o_horizonte():
    datas = [
        date(2025, 11, 28),
        date(2026, 10, 30),
        date(2026, 11, 12),
        date(2026, 11, 13),
    ]
    assert BacktestPIT._fim_horizonte(date(2025, 11, 28), 12, datas) == (
        None,
        "horizonte sem mês final fechado",
    )
    # o mês anterior está fechado: há pregão observado depois dele
    assert BacktestPIT._fim_horizonte(date(2025, 10, 31), 12, datas) == (
        date(2026, 10, 30),
        None,
    )
