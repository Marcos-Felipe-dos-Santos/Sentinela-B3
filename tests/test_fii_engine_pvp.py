import math
from unittest.mock import patch

import pytest
from apoio_apresentacao import verificar_lentes
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

import fii_engine
from fii_engine import FIIEngine
from sentinela.methods.base import MethodResult
from sentinela.methods.fii_nav import (
    FAIXA_DESCONTO,
    FAIXA_PREMIO_ALTO,
    FAIXA_PREMIO_MODERADO,
)


def test_pontos_aposentados_nao_geram_score():
    assert not hasattr(fii_engine, "_PONTOS_PVP")
    r = _analisar(pvp=0.8)
    verificar_lentes(r)
    assert r["pvp"] == 0.8


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

# XPML11 nunca esteve na tabela de vacância manual (removida no F2A-13); DY acima da Selic líquida.
BASE = {"ticker": "XPML11", "preco_atual": 100.0, "dy": 0.12}


def _analisar(**extra):
    with patch("fii_engine.get_selic_atual", return_value=0.10):
        # F2B-2: o FII calcula com o Informe e a B3 sintéticos.
        return FIIEngine().analisar(
            enriquecer_fii({**BASE, **extra}), as_of=AS_OF_GORDON
        )


@pytest.mark.parametrize("pvp", [None, 0, 0.0])
def test_pvp_ausente_vira_abstencao(pvp):
    resultado = _analisar(pvp=pvp)
    assert resultado["pvp"] is None
    # A faixa neutra de antes também não pontuava: o score é o mesmo do P/VP neutro.
    verificar_lentes(resultado)
    verificar_lentes(_analisar(pvp=1.0))


def test_pvp_negativo_nao_recebe_bonus():
    negativo = _analisar(pvp=-0.5)
    assert negativo["pvp"] is None
    verificar_lentes(negativo)
    assert (
        negativo["lentes"]
        == _analisar(pvp=1.0)["lentes"]
        == _analisar(pvp=0.8)["lentes"]
    )
    verificar_lentes(_analisar(pvp=1.0))
    verificar_lentes(negativo)
    verificar_lentes(_analisar(pvp=0.8))
