"""Regra de liquidez decidida em 18/10/2026; não deriva de limiar da implementação."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from fii_engine import FIIEngine
from valuation_engine import ValuationEngine


def _bloco(presenca=0.8, volume=500000, *, incompleta=False, meses=()):
    return {
        "janelas": {
            "63": {
                "presenca": presenca,
                "volume_mediano": volume,
                "pregoes": 63,
                "incompleta": incompleta,
            }
        },
        "meses_ausentes": list(meses),
        "data_final": "2026-10-20",
        "fonte": "COTAHIST sintético",
    }


def _dados(fii=False, **extra):
    return (
        dict(
            ticker="TSTU11" if fii else "TSTC3",
            classe_ativo="FII" if fii else "STOCK",
            preco_atual=100.0,
            roe=0.15,
            pl=10.0,
            pvp=1.5,
            dy=0.08,
        )
        | extra
    )


def _analisar(fii=False, **extra):
    with (
        patch("valuation_engine.get_selic_atual", return_value=0.145),
        patch("fii_engine.get_selic_atual", return_value=0.145),
    ):
        dados = _dados(fii, **extra)
        return (
            FIIEngine().analisar(dados) if fii else ValuationEngine().processar(dados)
        )


@pytest.mark.parametrize("fii", [False, True])
def test_abaixo_do_limiar_se_abstem(fii):
    resultado = _analisar(fii, liquidez=_bloco(0.79, 1e6))
    assert not {"fair_value", "upside", "score_final"} & set(resultado)
    assert "liquidez abaixo do mínimo" in resultado["riscos"][0]


@pytest.mark.parametrize("fii", [False, True])
def test_sem_chave_nada_muda(fii):
    assert _analisar(fii, liquidez=_bloco(1, 1000000)) == _analisar(fii)


@pytest.mark.parametrize("fii", [False, True])
def test_falha_de_coleta_segue_com_aviso(fii):
    r = _analisar(fii, liquidez={"abstencao": "falha de coleta: fonte indisponível"})
    assert "fair_value" in r
    assert any("liquidez não medida:" in s for s in r.get("riscos", []))


@pytest.mark.parametrize("fii", [False, True])
def test_sem_negocio_na_janela_se_abstem(fii):
    assert "fair_value" not in _analisar(fii, liquidez=_bloco(0, 0))


def test_recem_listado_com_presenca_baixa_se_abstem():
    assert "fair_value" not in _analisar(
        liquidez=_bloco(0.2, 1e6), data_estreia="2026-10-01"
    )


def test_limiar_por_classe():
    assert "fair_value" not in _analisar(liquidez=_bloco(0.8, 100000))
    assert "fair_value" in _analisar(True, liquidez=_bloco(0.8, 100000))
    assert "fair_value" in _analisar(liquidez=_bloco(0.8, 500000))


def test_abstencao_sem_numero():
    r = _analisar(liquidez=_bloco(0.8, 499999))
    assert not {"fair_value", "upside", "score_final"} & set(r)
    assert r["metodos_usados"] == ""
    assert r["confianca"] == 0


@pytest.mark.parametrize(
    "alteracao,esperado",
    [
        ({}, None),
        ({"presenca": 0.7999}, "abstencao"),
        ({"volume_mediano": 499999.99}, "abstencao"),
        ({"presenca": 0, "volume_mediano": 0}, "abstencao"),
        ({"incompleta": True}, "aviso"),
        ({"pregoes": 62}, "aviso"),
        ({"presenca": None}, "aviso"),
        ({"presenca": True}, "aviso"),
        ({"presenca": float("nan")}, "aviso"),
        ({"presenca": float("inf")}, "aviso"),
        ({"presenca": -0.1}, "aviso"),
        ({"presenca": 1.1}, "aviso"),
        ({"volume_mediano": -1}, "aviso"),
        ({"volume_mediano": "texto"}, "aviso"),
    ],
)
def test_funcao_pura_e_dominios(alteracao, esperado):
    from sentinela.data import liquidez

    bloco = _bloco()
    bloco["janelas"]["63"].update(alteracao)
    r = liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500000)
    if esperado is None:
        assert r is None
    else:
        assert esperado in r


def test_meses_ausentes_e_janela_incompleta_sao_verificados_juntos():
    from sentinela.data import liquidez

    bloco = _bloco(0, 0, meses=("2026-09",))
    original = deepcopy(bloco)
    r = liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500000)
    assert "aviso" in r
    assert bloco == original


@pytest.mark.parametrize(
    "bloco",
    [
        None,
        {},
        {"janelas": None},
        {"janelas": {"63": None}},
        {"abstencao": "falha de coleta"},
        {"incompleta": True},
    ],
)
def test_bloco_sem_dados_ou_coleta_incompleta_da_aviso(bloco):
    from sentinela.data import liquidez

    r = liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500000)
    assert r["aviso"].startswith("liquidez não medida:")


def test_ticker_ausente_com_cobertura_completa_abstem():
    from sentinela.data import liquidez

    r = liquidez.avaliar(
        {"abstencao": liquidez.MOTIVO_TICKER_AUSENTE, "incompleta": False},
        janela=63,
        presenca_min=0.8,
        volume_min=500000,
    )
    assert "presença de 0.0%" in r["abstencao"]
    assert "63 pregões" in r["abstencao"]


def test_guarda_de_classe_tem_prioridade_sobre_liquidez():
    r = _analisar(classe_ativo="ETF", liquidez=_bloco(0, 0))
    assert r["riscos"] == ["Classe ETF fora do escopo dos métodos de ação"]


def test_aviso_chega_a_saida_distressed():
    with patch("valuation_engine.DISTRESSED_TICKERS", {"TSTC3"}):
        r = _analisar(liquidez={"abstencao": "falha de coleta"})
    assert r["perfil"] == "DISTRESSED"
    assert any("liquidez não medida:" in s for s in r["riscos"])


def test_texto_da_abstencao_expoe_as_duas_medidas_e_o_limiar():
    from sentinela.data import liquidez

    r = liquidez.avaliar(
        _bloco(0.79, 499999.0), janela=63, presenca_min=0.8, volume_min=500000
    )
    assert r == {
        "abstencao": (
            "liquidez abaixo do mínimo para análise: presença de 79.0% e volume mediano "
            "de R$ 499999.0 nos últimos 63 pregões (mínimo: 80% e R$ 500000)"
        )
    }


def test_incompletude_do_bloco_domina_as_metricas_parciais():
    from sentinela.data import liquidez

    bloco = _bloco(0, 0)
    bloco["incompleta"] = True
    assert liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500000) == {
        "aviso": "liquidez não medida: janela incompleta"
    }


@pytest.mark.parametrize(
    "bloco,motivo",
    [
        (None, "bloco sem dados"),
        ({"janelas": {}}, "janela de 63 pregões ausente"),
        (_bloco(None, 1000000), "presença ou volume inválido"),
        (_bloco(-0.1, 1000000), "presença ou volume fora do domínio"),
    ],
)
def test_aviso_expoe_o_motivo_sem_inventar_medida(bloco, motivo):
    from sentinela.data import liquidez

    assert liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500000) == {
        "aviso": "liquidez não medida: " + motivo
    }
