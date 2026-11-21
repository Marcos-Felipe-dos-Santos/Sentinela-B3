"""BUG-3-43: retorno não converte emissão de outra espécie em desdobramento.

Reproduz CYRE3 e RENT3 da auditoria C-1 com fixtures, sem abrir o banco real.
"""

from datetime import date

import pytest

from backtesting.backtest_pit import BacktestPIT
from sentinela.data.pit.serie_ajustada import MOTIVO_OUTRA_ESPECIE
from sentinela.data.providers import b3_proventos


class _Consulta:
    def __init__(self, linhas):
        self.linhas = linhas

    def fetchall(self):
        return self.linhas

    def fetchone(self):
        return self.linhas[0] if self.linhas else None


class _Banco:
    def __init__(self, linhas, isin):
        self.linhas = linhas
        self.isin = isin

    def execute(self, sql, _parametros):
        if "SELECT data, fechamento_centavos" in sql:
            return _Consulta(self.linhas)
        if "SELECT isin FROM precos" in sql:
            return _Consulta([(self.isin,)])
        raise AssertionError(f"consulta inesperada: {sql}")


@pytest.mark.parametrize(
    "ticker,isin,emitido,data_com,data_ex,fator,entrada,saida",
    [
        (
            "CYRE3", "BRCYREACNOR7", "BRCYREACNPR4", "2025-12-30",
            "2026-01-02", 1.1895833333299999, 26.14, 23.02,
        ),
        (
            "RENT3", "BRRENTACNOR4", "BRRENTACNPR1", "2025-12-29",
            "2025-12-30", 1.0384609533429, 40.52, 41.54,
        ),
    ],
)
def test_retorno_abstem_evento_que_emite_outra_especie(
    monkeypatch, ticker, isin, emitido, data_com, data_ex, fator, entrada, saida
):
    inicio, fim = date(2025, 6, 30), date(2026, 6, 30)
    linhas = [
        (inicio.isoformat(), round(entrada * 100), 1),
        (fim.isoformat(), round(saida * 100), 1),
    ]
    evento = {
        "isin": isin,
        "ativo_emitido": emitido,
        "data_com": data_com,
        "data_ex": data_ex,
        "fator": fator,
    }
    monkeypatch.setattr(
        b3_proventos,
        "proventos_ate",
        lambda *_a, **_k: {"proventos": [], "sem_prova": []},
    )
    monkeypatch.setattr(
        b3_proventos,
        "eventos_ate",
        lambda *_a, **_k: {"eventos": [evento], "sem_prova": []},
    )
    executor = BacktestPIT(
        _Banco(linhas, isin), None, hoje=date(2026, 11, 17), cache_dir="cache"
    )
    monkeypatch.setattr(
        executor,
        "_estado_terminal",
        lambda *_a: {
            "deslistagem": None,
            "suspensao_confirmada": False,
            "motivo_deslistagem": None,
        },
    )

    retorno, *_ = executor._retornos(
        ticker, "cnpj sintético", inicio, fim, [inicio, fim],
        {"IBOV": [], "CDI": []}, b3_proventos,
    )

    assert retorno["retorno"] is None
    assert retorno["abstencao"] == MOTIVO_OUTRA_ESPECIE
