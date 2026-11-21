"""BUG-3-56 (Gemini C5): abstenções do backtest por data e motivo, sem a pseudo-lente "analise".

A ficha (docs/metodologia/backtest.md, §3.3) pede o relatório das abstenções por motivo em
cada D. `BacktestPIT._grupos` tirava as abstenções antes de `quintis_por_modo`, e o grupo de
cada data saía com `abstencoes` vazio; e a análise que falhava antes das lentes virava uma
lente "analise", que entrava no resumo como se fosse uma lente real.

Mesmo cenário do F3-8b (`test_backtest_pit_executar.py`): 27 ativos com Graham e Bazin, o
27º sem valor finito no Graham, Bazin abstido em todos e dois ativos sem registro de lente
(um com o erro do serviço, outro sem lentes), nas datas D1 e D2.
"""

import sqlite3
from contextlib import closing
from types import SimpleNamespace

from test_backtest_pit_executar import (
    D1,
    D2,
    MOTIVO_BAZIN,
    SEM_REGISTRO,
    SEM_REGISTRO_COM_ERRO,
    cenario,  # noqa: F401 (fixture)
)

from sentinela.data.store import migracoes, resultados
from sentinela.data.store.resultados import buscar as buscar_do_banco
from sentinela.services.analyze_asset import AnalysisService

SEM_VALOR = "lente sem valor finito e positivo"


def _gravado_pelo_servico(ticker, as_of, motivo):
    """O registro que `AnalysisService._gravar_resultados` grava para a análise sem lente."""
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        resultado = SimpleNamespace(
            ticker=ticker,
            raw={},
            error=motivo,
            execucao_id=f"exec-{ticker}-{as_of.date()}",
        )
        AnalysisService._gravar_resultados(conn, resultado, as_of)
        return buscar_do_banco(conn, ticker, as_of=as_of)


def test_grupo_de_cada_data_conta_as_abstencoes_por_motivo(cenario):  # noqa: F811
    saida = cenario.executar()
    grupos = {(g["lente"], g["D"]): g for g in saida["grupos"]}
    assert grupos[("Graham", D1.isoformat())]["abstencoes"] == {SEM_VALOR: 1}
    bazin = grupos[("Bazin", D1.isoformat())]
    assert bazin["abstencoes"] == {MOTIVO_BAZIN: 27}
    assert bazin["elegiveis"] == 0 and bazin["quintis"] == {}


def test_analise_sem_lentes_fica_fora_das_lentes_com_data_e_motivo(cenario):  # noqa: F811
    saida = cenario.executar()
    assert "analise" not in {o["lente"] for o in saida["observacoes"]}
    assert "analise" not in {r["lente"] for r in saida["resumo"]["lentes"]}
    assert sorted(
        (s["D"], s["ticker"], s["motivo"]) for s in saida["sem_lentes"]
    ) == sorted(
        (d.isoformat(), t, m)
        for d in (D1, D2)
        for t, m in (
            (SEM_REGISTRO_COM_ERRO, "histórico sem cadastro"),
            (SEM_REGISTRO, "análise sem lentes"),
        )
    )
    por_data = saida["resumo"]["abstencoes_antes_das_lentes"]
    assert por_data == {
        d.isoformat(): {"histórico sem cadastro": 1, "análise sem lentes": 1}
        for d in (D1, D2)
    }


def test_contagem_por_data_soma_o_mesmo_motivo(cenario, monkeypatch):  # noqa: F811
    """Dois ativos sem lente pelo mesmo motivo na mesma data contam 2."""
    from sentinela.data.store import resultados

    buscar = resultados.buscar
    monkeypatch.setattr(
        resultados,
        "buscar",
        lambda conn, ticker, **k: (
            [] if ticker == "TKAA3" else buscar(conn, ticker, **k)
        ),
    )
    por_data = cenario.executar()["resumo"]["abstencoes_antes_das_lentes"]
    assert por_data[D1.isoformat()] == {
        "histórico sem cadastro": 1,
        "análise sem lentes": 2,
    }


def test_registro_analise_gravado_pelo_servico_vai_para_sem_lentes(
    cenario,  # noqa: F811
    monkeypatch,
):
    """Sem atalho no `buscar`: o serviço grava `metodo="analise"` com o motivo."""
    buscar = resultados.buscar
    monkeypatch.setattr(
        resultados,
        "buscar",
        lambda conn, ticker, *, as_of=None: (
            _gravado_pelo_servico(ticker, as_of, "motivo gravado pelo serviço")
            if ticker == SEM_REGISTRO_COM_ERRO
            else buscar(conn, ticker, as_of=as_of)
        ),
    )
    saida = cenario.executar()
    assert "analise" not in {o["lente"] for o in saida["observacoes"]}
    assert "analise" not in {g["lente"] for g in saida["grupos"]}
    motivos = {(s["ticker"], s["D"]): s["motivo"] for s in saida["sem_lentes"]}
    # o motivo é o do registro, não o erro devolvido nesta execução
    assert motivos[(SEM_REGISTRO_COM_ERRO, D1.isoformat())] == (
        "motivo gravado pelo serviço"
    )
