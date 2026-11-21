"""BUG-3-34: ativo do universo sem fechamento de entrada derruba o backtest inteiro.

Ficha PIT §3 e §5: sem o fechamento de D, o retorno daquele ativo se abstém com
motivo; os demais ativos e datas seguem. A execução não pode parar com exceção.
"""

import sqlite3
from contextlib import closing
from datetime import date
from types import SimpleNamespace

from backtesting.backtest_pit import BacktestPIT
from sentinela.data.providers import b3_indices
from sentinela.data.referencia import universo
from sentinela.data.store import migracoes, resultados

D, T = date(2022, 3, 31), date(2023, 3, 31)


def test_ativo_sem_fechamento_de_entrada_abstem_sem_derrubar_a_execucao(monkeypatch):
    from sentinela.services import analyze_asset

    class _Servico:
        def __init__(self, *args, **kwargs):
            pass

        def analisar(self, ticker, as_of, use_ai=False):
            return SimpleNamespace(raw={}, execucao_id="e", error="sem histórico")

    monkeypatch.setattr(analyze_asset, "AnalysisService", _Servico)
    # BUG-3-56: a análise sem lente não vira mais a pseudo-lente "analise"; uma lente real
    # abstida mantém o caminho do retorno sem o fechamento de entrada
    lente = SimpleNamespace(
        metodo="Graham",
        versao="2.1.0",
        resultado=None,
        motivo_abstencao="sem histórico",
        execucao_id="e",
    )
    monkeypatch.setattr(resultados, "buscar", lambda *a, **k: [lente])
    monkeypatch.setattr(
        universo,
        "universo_backtest",
        lambda *a, **k: {"elegiveis": [{"ticker": "SEMP3", "cnpj": None}]},
    )
    monkeypatch.setattr(b3_indices, "benchmarks_ate", lambda *a, **k: [])
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        # 28/04/2023 fecha o mês de T (ficha §8, BUG-3-35)
        for dia in (D, T, date(2023, 4, 28)):
            conn.execute(
                "INSERT INTO precos VALUES (?, 'OUTR3', '010', '02', '', 'ON', 'BR', "
                "1000, 1000, 1000, 1000, 1000, 1, 1, 1, 1, 'f', 'c', 'h')",
                (dia.isoformat(),),
            )
        saida = BacktestPIT(
            conn, None, hoje=date(2026, 11, 13), cache_dir="pit"
        ).executar([D], horizontes=(12,))
    assert saida["sem_lentes"] == []
    (obs,) = saida["observacoes"]
    assert obs["ticker"] == "SEMP3" and obs["abstencao"] == "sem histórico"
    assert obs["retorno_total"] is None
    assert obs["abstencao_retorno"] == "fechamento de entrada indisponível"
    assert obs["deslistada"] is False and obs["motivo_deslistagem"] is None
