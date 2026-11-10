"""Conferência do LPA divulgado da unit pela soma ponderada dos componentes (F3-P03)."""

import pytest

from data_quality import DataQualityReport
from market_engine import _lpa_divulgado_comparado
from sentinela.data.acoes_cvm import LpaDivulgado


def _alertas_lpa(comparado, recalculado, papel):
    dados = {
        "classe_ativo": "UNIT",
        "acoes_cvm": {
            "acoes_por_papel": papel,
            "lpa_recalculado": recalculado,
            "lpa_divulgado_comparado": comparado,
        },
    }
    return [
        a
        for a in DataQualityReport(dados)._alertas_fontes_independentes(None)
        if "LPA" in a
    ]


def test_unit_soma_ponderada_na_base_por_acao():
    comparado = _lpa_divulgado_comparado(
        {"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)},
        None,
        None,
        {"ON": 1, "PN": 2},
    )
    assert comparado == {"especie": "unit (1 ON + 2 PN)", "valor": pytest.approx(5 / 3)}
    assert _alertas_lpa(comparado, 5.0, 3) == []


def test_unit_divergente_na_soma_ponderada_alerta():
    comparado = _lpa_divulgado_comparado(
        {"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)},
        None,
        None,
        {"ON": 1, "PN": 2},
    )
    assert _alertas_lpa(comparado, 10.0, 3)


def test_unit_pela_classe_preferencial_da_especie():
    comparado = _lpa_divulgado_comparado(
        {"ON": LpaDivulgado(1.0), "PNA": LpaDivulgado(3.0)},
        None,
        None,
        {"ON": 1, "PN": 4},
    )
    assert comparado["valor"] == pytest.approx((1.0 + 4 * 3.0) / 5)


@pytest.mark.parametrize(
    ("divulgados", "composicao"),
    [
        ({"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)}, None),
        ({"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)}, {}),
        ({"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)}, {"ON": 1, "PN": 0}),
        ({"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)}, {"ON": 1, "PN": 1.5}),
        ({"ON": LpaDivulgado(1.0)}, {"ON": 1, "PN": 2}),
        ({"ON": LpaDivulgado(1.0), "PN": "descartado"}, {"ON": 1, "PN": 2}),
        (
            {
                "ON": LpaDivulgado(1.0),
                "PNA": LpaDivulgado(2.0),
                "PNB": LpaDivulgado(3.0),
            },
            {"ON": 1, "PN": 2},
        ),
    ],
)
def test_unit_com_composicao_incompleta_nao_escolhe_a_primeira_classe(
    divulgados, composicao
):
    assert _lpa_divulgado_comparado(divulgados, None, None, composicao) is None


def test_acao_sem_classe_continua_pela_escala():
    divulgados = {"PN": LpaDivulgado(2.0), "ON": LpaDivulgado(1.0)}
    assert _lpa_divulgado_comparado(divulgados, None, None, escala=True) == {
        "especie": "ON",
        "valor": 1.0,
    }
    assert _lpa_divulgado_comparado({"PN": "x"}, None, None, escala=True) is None


def test_classe_do_ticker_tem_precedencia_sobre_a_unit():
    divulgados = {"ON": LpaDivulgado(1.0), "PN": LpaDivulgado(2.0)}
    assert _lpa_divulgado_comparado(divulgados, "PN", None, {"ON": 1, "PN": 2}) == {
        "especie": "PN",
        "valor": 2.0,
    }


def test_cascata_da_unit_confere_pela_soma_ponderada(monkeypatch):
    from test_data_quality_fontes import (
        FakeReferencia,
        _alertas,
        _ind,
        _indice,
        _motor,
        _registro,
    )

    unit = _registro(
        "TSTA11", classe="UNIT", especie=None, acoes_por_unit={"ON": 1, "PN": 2}
    )
    engine = _motor(
        monkeypatch,
        _ind(lpa_divulgado_por_especie={"ON": 1.4, "PN": 2.3}),
        referencia=FakeReferencia(_indice(unit)),
    )
    dados = engine.buscar_dados_ticker("TSTA11")
    assert dados["acoes_cvm"]["lpa_divulgado_comparado"] == {
        "especie": "unit (1 ON + 2 PN)",
        "valor": pytest.approx((1.4 + 2 * 2.3) / 3),
    }
    assert not [a for a in _alertas(dados) if "LPA" in a]
