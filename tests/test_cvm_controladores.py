"""Reservas do lucro e do PL dos controladores (F2A-37, ADR-0003 D20; ficha por ação, 7.2).

DRE e BPP sintéticos pelo layout da DFP (CVM): 3.11 (lucro consolidado), 3.11.01 e 3.11.02
(atribuídos à controladora e aos não controladores), 2.03 e 2.03.09 (PL e participação dos
não controladores).
"""

import pytest

from sentinela.data.controladores import (
    MOTIVO_LUCRO_COM_MINORITARIOS,
    MOTIVO_LUCRO_INVALIDO,
    MOTIVO_LUCRO_NAO_SEPARADO,
    MOTIVO_PL_COM_MINORITARIOS,
    MOTIVO_PL_INVALIDO,
    RESERVA_LUCRO_NAO_SEPARADO,
    RESERVA_LUCRO_SEM_LINHA,
    RESERVA_PL,
)
from tests.test_market_engine_acoes_cvm import _calcular, _motor, _registro
from tests.test_market_engine_referencia import FakeReferencia, _indice

CONSOLIDADO = ("3.11", "Lucro/Prejuízo Consolidado do Período")
CONTROLADORA = ("3.11.01", "Atribuído a Sócios da Empresa Controladora")
MINORITARIOS = ("3.11.02", "Atribuído a Sócios Não Controladores")
PL = ("2.03", "Patrimônio Líquido Consolidado")
PL_MINORITARIOS = ("2.03.09", "Participação dos Acionistas Não Controladores")


def _linhas(*pares):
    return [(codigo, descricao, valor) for (codigo, descricao), valor in pares]


def test_lucro_total_nao_substitui_controladores_com_minoritarios(
    tmp_path, monkeypatch
):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=_linhas((CONSOLIDADO, 1_000.0), (MINORITARIOS, 300.0)),
        bpp=_linhas((PL, 5_000.0), (PL_MINORITARIOS, 1_000.0)),
    )
    assert ind["lucro_controladores"] is None
    assert ind["roe"] is None
    assert ind["roe_motivo"] == MOTIVO_LUCRO_COM_MINORITARIOS
    assert ind["reservas_controladores"] == {}


def test_pl_total_nao_substitui_com_lucro_de_minoritarios(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=_linhas(
            (CONSOLIDADO, 1_000.0), (CONTROLADORA, 800.0), (MINORITARIOS, 200.0)
        ),
        bpp=_linhas((PL, 5_000.0)),
    )
    assert ind["lucro_controladores"] == pytest.approx(800.0)
    assert ind["pl_controladores"] is None
    assert ind["roe"] is None
    assert ind["roe_motivo"] == MOTIVO_PL_COM_MINORITARIOS


@pytest.mark.parametrize(
    ("dre", "bpp", "campo", "motivo"),
    [
        # Linha dos controladores ausente e a dos não controladores com NaN.
        (_linhas((CONSOLIDADO, 1_000.0), (MINORITARIOS, float("nan"))),
         _linhas((PL, 5_000.0), (PL_MINORITARIOS, 0.0)),
         "lucro_controladores", MOTIVO_LUCRO_INVALIDO),
        # Controladora zerada e não controladores com NaN.
        (_linhas((CONSOLIDADO, 1_000.0), (CONTROLADORA, 0.0), (MINORITARIOS, float("nan"))),
         _linhas((PL, 5_000.0)),
         "lucro_controladores", MOTIVO_LUCRO_INVALIDO),
        # PL dos não controladores com valor não numérico.
        (_linhas((CONSOLIDADO, 1_000.0), (CONTROLADORA, 1_000.0)),
         _linhas((PL, 5_000.0), (PL_MINORITARIOS, "abc")),
         "pl_controladores", MOTIVO_PL_INVALIDO),
        # Lucro dos não controladores infinito, sem participação no balanço.
        (_linhas((CONSOLIDADO, 1_000.0), (CONTROLADORA, 1_000.0), (MINORITARIOS, float("inf"))),
         _linhas((PL, 5_000.0)),
         "pl_controladores", MOTIVO_PL_INVALIDO),
    ],
)  # fmt: skip
def test_valor_invalido_nao_autoriza_reserva(
    tmp_path, monkeypatch, dre, bpp, campo, motivo
):
    ind = _calcular(tmp_path, monkeypatch, dre=dre, bpp=bpp)
    assert ind[campo] is None
    assert ind["roe_motivo"] == motivo
    if campo == "pl_controladores":
        assert ind["lucro_controladores"] == pytest.approx(1_000.0)  # sem reserva, vale
    assert campo not in ind["reservas_controladores"]


def test_sem_minoritarios_usa_total_e_registra_reserva(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=_linhas((CONSOLIDADO, 700.0)),
        bpp=_linhas((PL, 7_000.0)),
    )
    assert ind["lucro_controladores"] == pytest.approx(700.0)
    assert ind["pl_controladores"] == pytest.approx(7_000.0)
    assert ind["reservas_controladores"] == {
        "lucro_controladores": RESERVA_LUCRO_SEM_LINHA,
        "pl_controladores": RESERVA_PL,
    }
    documento = {"dt_refer": "2025-12-31", "versao": "1"}
    dados = _motor(
        monkeypatch,
        {2025: {**ind, "proveniencia": documento}},
        referencia=FakeReferencia(_indice(_registro("TSTA3"))),
    ).buscar_dados_ticker("TSTA3")
    assert dados["proveniencia"]["roe"]["reservas"] == [
        RESERVA_LUCRO_SEM_LINHA,
        RESERVA_PL,
    ]
    assert dados["proveniencia"]["ativo_total"] == documento


def test_controladora_zerada_com_minoritarios_no_balanco_abstem(tmp_path, monkeypatch):
    # KLBN11 na DFP 2025: 3.11.01 e 3.11.02 zeradas, R$ 6,5 bi de não controladores na 2.03.09.
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=_linhas((CONSOLIDADO, 1_000.0), (CONTROLADORA, 0.0), (MINORITARIOS, 0.0)),
        bpp=_linhas((PL, 5_000.0), (PL_MINORITARIOS, 1_000.0)),
    )
    assert ind["lucro_controladores"] is None
    assert ind["roe_motivo"] == MOTIVO_LUCRO_NAO_SEPARADO
    assert ind["pl_controladores"] == pytest.approx(4_000.0)  # o PL segue separado


def test_controladora_zerada_sem_minoritarios_usa_total(tmp_path, monkeypatch):
    ind = _calcular(
        tmp_path,
        monkeypatch,
        dre=_linhas((CONSOLIDADO, 1_000.0), (CONTROLADORA, 0.0), (MINORITARIOS, 0.0)),
        bpp=_linhas((PL, 5_000.0), (PL_MINORITARIOS, 0.0)),
    )
    assert ind["lucro_controladores"] == pytest.approx(1_000.0)
    assert (
        ind["reservas_controladores"]["lucro_controladores"]
        == RESERVA_LUCRO_NAO_SEPARADO
    )
    assert ind["roe"] == pytest.approx(0.2)
