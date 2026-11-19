"""BUG-3-58 (Codex A-2): o relógio abaixo do serviço não muda a análise de uma data passada.

`AnalysisService` decide pela própria data de hoje (`hoje`, injetada) que D é passado e
usa o motor histórico; abaixo dele, `MarketEngine.buscar_dados_ticker` marcava
`disponibilidade_por_publicacao` (decisão 40) comparando D com o relógio do sistema
(`market_engine._hoje_sp()`), e `_buscar_cvm` repetia a comparação. Com o `hoje` do serviço
fixo, um relógio no dia de D (replay, máquina com outra data) trocava a regra de
disponibilidade e o resultado da mesma análise.

Arranjo do F3-3d (`test_servico_historico.py`): banco em memória com a DFP oficial de 2019,
FCA e COTAHIST sintéticos, fontes correntes como espiões; só o relógio varia.
"""

from datetime import UTC, date, datetime

import pandas as pd
import pytest
from test_servico_historico import (  # noqa: F401 (fixtures)
    HOJE,
    _servico,
    banco,
    espioes,
    resultados_conn,
)

import market_engine
from sentinela.services.historico import MotorHistorico

D = datetime(2020, 3, 2, 15, tzinfo=UTC)
DISTRESSED = "Empresa em situação especial/distressed"


def _analise(banco, tmp_path, resultados_conn, monkeypatch, relogio):  # noqa: F811
    monkeypatch.setattr(market_engine, "_hoje_sp", lambda agora=None: relogio)
    servico, *_ = _servico(banco, tmp_path / relogio.isoformat(), resultados_conn)
    dados = servico.analisar("AMER3", D, use_ai=False).raw
    return {
        "por_publicacao": dados.get("disponibilidade_por_publicacao"),
        "cvm_disponivel": dados.get("cvm_disponivel"),
        "lentes": {
            nome: lente.get("abstencao") for nome, lente in dados["lentes"].items()
        },
        "janelas": {
            nome: bloco.get("abstencao")
            for nome, bloco in dados["janelas_fundamentais"].items()
            if isinstance(bloco, dict)
        },
    }


def test_referencia_com_o_relogio_no_hoje_do_servico(
    banco,  # noqa: F811
    espioes,  # noqa: F811
    tmp_path,
    resultados_conn,  # noqa: F811
    monkeypatch,
):
    """Controle: relógio igual ao `hoje` do serviço, regra da decisão 40."""
    referencia = _analise(banco, tmp_path, resultados_conn, monkeypatch, HOJE)
    assert referencia["por_publicacao"] is True
    assert set(referencia["lentes"].values()) == {DISTRESSED}


@pytest.mark.parametrize("relogio", [date(2020, 3, 2), date(2020, 2, 1)])
def test_relogio_do_sistema_nao_muda_a_analise_da_data_passada(
    banco,  # noqa: F811
    espioes,  # noqa: F811
    tmp_path,
    resultados_conn,  # noqa: F811
    monkeypatch,
    relogio,
):
    referencia = _analise(banco, tmp_path, resultados_conn, monkeypatch, HOJE)
    assert (
        _analise(banco, tmp_path, resultados_conn, monkeypatch, relogio) == referencia
    )


def test_analise_corrente_segue_o_relogio(monkeypatch):
    """D = hoje na cascata corrente: sem a marca da decisão 40, como antes."""
    monkeypatch.setattr(
        market_engine, "_hoje_sp", lambda agora=None: date(2026, 11, 12)
    )
    motor = market_engine.MarketEngine()
    assert motor._data_passada(datetime(2026, 11, 12, 15, tzinfo=UTC)) is False
    assert motor._data_passada(datetime(2026, 11, 11, 15, tzinfo=UTC)) is True
    assert motor._data_passada(None) is False


def test_motor_historico_responde_pela_data_do_servico(tmp_path, monkeypatch):
    monkeypatch.setattr(market_engine, "_hoje_sp", lambda agora=None: date(2020, 3, 2))
    motor = MotorHistorico(None, D, tmp_path, pd.DataFrame())
    assert motor._data_passada(D) is True
    assert motor._data_passada(None) is False
