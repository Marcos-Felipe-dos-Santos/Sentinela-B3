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

import pytest
from test_servico_historico import (  # noqa: F401 (fixtures)
    _servico,
    banco,
    espioes,
    resultados_conn,
)

import market_engine

D = datetime(2020, 3, 2, 15, tzinfo=UTC)


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


@pytest.mark.xfail(
    strict=True, reason="BUG-3-58 / F3-AUD-CA2: relógio abaixo do serviço"
)
@pytest.mark.parametrize("relogio", [date(2020, 3, 2), date(2020, 2, 1)])
def test_relogio_do_sistema_nao_muda_a_analise_da_data_passada(
    banco,  # noqa: F811
    espioes,  # noqa: F811
    tmp_path,
    resultados_conn,  # noqa: F811
    monkeypatch,
    relogio,
):
    referencia = _analise(
        banco, tmp_path, resultados_conn, monkeypatch, date(2026, 11, 12)
    )
    assert referencia["por_publicacao"] is True
    assert (
        _analise(banco, tmp_path, resultados_conn, monkeypatch, relogio) == referencia
    )
