"""BUG-3-36: sem ISIN do ticker antes de D, eventos em ações do emissor somem em silêncio.

Ficha PIT §5 e armadilha 11: preço e provento na mesma base acionária. Um
desdobramento 2:1 no horizonte, ignorado, faz o retorno de 10 → 5,5 sair −45% em vez
de +10%. Sem como associar o evento ao ticker, o retorno se abstém com motivo.
"""

from datetime import date

from backtesting.backtest_pit import BacktestPIT
from sentinela.data.providers import b3_proventos

D, EX, T = date(2022, 3, 31), date(2022, 9, 30), date(2023, 3, 31)


class _Consulta:
    def __init__(self, linhas):
        self.linhas = linhas

    def fetchall(self):
        return self.linhas

    def fetchone(self):
        return self.linhas[0] if self.linhas else None


class _Banco:
    def execute(self, sql, parametros):
        if "SELECT data, fechamento_centavos" in sql:
            return _Consulta([(D.isoformat(), 1000, 1), (T.isoformat(), 550, 1)])
        if "SELECT isin FROM precos" in sql:
            return _Consulta([])
        raise AssertionError(sql)


def test_evento_do_emissor_sem_isin_do_ticker_abstem(monkeypatch):
    monkeypatch.setattr(
        b3_proventos,
        "proventos_ate",
        lambda *a, **k: {"proventos": [], "sem_prova": []},
    )
    monkeypatch.setattr(
        b3_proventos,
        "eventos_ate",
        lambda *a, **k: {
            "eventos": [
                {
                    "isin": "BRABEVACNOR1",
                    "data_com": "2022-09-29",
                    "data_ex": EX.isoformat(),
                    "fator": 2,
                }
            ],
            "sem_prova": [],
        },
    )
    executor = BacktestPIT(_Banco(), None, hoje=date(2026, 11, 13), cache_dir="c")
    retorno, *_ = executor._retornos(
        "ABEV3", None, D, T, [D, EX, T], {"IBOV": [], "CDI": []}, b3_proventos
    )
    assert retorno["retorno"] is None
    assert retorno["abstencao"] == (
        "ISIN do ticker não demonstrado para associar eventos em ações"
    )
