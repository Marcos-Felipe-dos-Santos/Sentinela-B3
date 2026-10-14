import math
from unittest.mock import patch

import pytest

import fii_engine
from fii_engine import FIIEngine
from sentinela.methods.base import MethodResult
from sentinela.methods.fii_nav import (
    FAIXA_DESCONTO,
    FAIXA_PREMIO_ALTO,
    FAIXA_PREMIO_MODERADO,
)


def test_pontos_por_faixa_sao_os_da_v1():
    assert fii_engine._PONTOS_PVP == {
        FAIXA_PREMIO_ALTO: -15,
        FAIXA_PREMIO_MODERADO: -7,
        FAIXA_DESCONTO: 10,
    }


@pytest.mark.parametrize(
    ("pvp", "alertas"),
    [
        (1.16, (FAIXA_PREMIO_ALTO,)),
        (1.15, (FAIXA_PREMIO_MODERADO,)),
        (1.05, ()),
        (0.85, ()),
        (0.84, (FAIXA_DESCONTO,)),
    ],
)
def test_faixa_usa_os_limites_do_macro_context(pvp, alertas):
    r = FIIEngine()._faixa_pvp(pvp)
    assert isinstance(r, MethodResult)
    assert r.alertas == alertas


@pytest.mark.parametrize("ruim", [math.nan, math.inf, -math.inf])
def test_pvp_nao_finito_nao_calcula_a_lente(ruim):
    assert FIIEngine()._faixa_pvp(ruim) is None


# ── F2A-11: sem P/VP positivo, a lente se abstém ─────────────────────────────
# Antes, P/VP ausente ou zero virava 1,0 (faixa neutra), e o negativo passava pelo `or 1.0` e
# caía na faixa de desconto, com bônus. Agora a lente não é calculada, não pontua e a saída
# traz `pvp` nulo.

# XPML11 não está em `VACANCIA_CONHECIDA`; DY acima da Selic líquida.
BASE = {"ticker": "XPML11", "preco_atual": 100.0, "dy": 0.12}


def _analisar(**extra):
    with patch("fii_engine.get_selic_atual", return_value=0.10):
        return FIIEngine(cvm_provider=None).analisar({**BASE, **extra})


@pytest.mark.parametrize("pvp", [None, 0, 0.0])
def test_pvp_ausente_vira_abstencao(pvp):
    resultado = _analisar(pvp=pvp)
    assert resultado["pvp"] is None
    # A faixa neutra de antes também não pontuava: o score é o mesmo do P/VP neutro.
    assert resultado["score_final"] == _analisar(pvp=1.0)["score_final"]


def test_pvp_negativo_nao_recebe_bonus():
    negativo = _analisar(pvp=-0.5)
    assert negativo["pvp"] is None
    assert negativo["score_final"] == _analisar(pvp=1.0)["score_final"]
    assert (
        negativo["score_final"] < _analisar(pvp=0.8)["score_final"]
    )  # o bônus de desconto
