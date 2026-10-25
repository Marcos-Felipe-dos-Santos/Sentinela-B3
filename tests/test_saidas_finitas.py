"""Nenhuma saída dos motores com NaN ou infinito (F2A-24; registrado no F1-7 e no F1-16).

Preço não finito: os dois motores devolvem `None`, como com preço zero. FII com Selic zero ou
não finita: desde o F2B-2 a Selic é só contexto e score, e a saída fica finita.
"""

import json
import math
from unittest.mock import patch

import pytest
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON

from fii_engine import FIIEngine
from tests.golden_motores import GOLDEN
from valuation_engine import ValuationEngine

ACAO = {"ticker": "TST3", "roe": 0.15, "pl": 10.0, "pvp": 1.5, "dy": 0.08}
FII = {"ticker": "XPML11", "dy": 0.10, "pvp": 1.0}


def _nao_finitos(valor):
    if isinstance(valor, float):
        return [] if math.isfinite(valor) else [valor]
    if isinstance(valor, dict):
        return [x for v in valor.values() for x in _nao_finitos(v)]
    if isinstance(valor, (list, tuple)):
        return [x for v in valor for x in _nao_finitos(v)]
    return []


def _fii(selic=0.145, **extra):
    with patch("fii_engine.get_selic_atual", return_value=selic):
        # F2B-2: o FII calcula com o Informe e a B3 sintéticos.
        return FIIEngine().analisar(
            enriquecer_fii({**FII, "preco_atual": 100.0, **extra}), as_of=AS_OF_GORDON
        )


@pytest.mark.parametrize("preco", [math.nan, math.inf, -math.inf])
def test_acao_com_preco_nao_finito_devolve_none(preco):
    assert ValuationEngine().processar({**ACAO, "preco_atual": preco}) is None
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        assert FIIEngine().analisar({**FII, "preco_atual": preco}) is None


@pytest.mark.parametrize("preco", [-10.0, -0.01])
def test_preco_negativo_nao_e_analisado(preco):
    # F2B-20 (BUG-2A-22): preço ≤ 0 devolve `None`, como o zero (F2A-24).
    assert ValuationEngine().processar({**ACAO, "preco_atual": preco}) is None
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        assert FIIEngine().analisar({**FII, "preco_atual": preco}) is None


@pytest.mark.parametrize("selic", [0.0, math.nan, math.inf])
def test_fii_com_selic_zero_nao_devolve_nan(selic):
    # F2B-2: a Selic só entra no score e no contexto; inválida, fica sem a comparação e a
    # saída traz `selic_liquida` nula, sem NaN. A lente de rendimento não depende dela.
    resultado = _fii(selic=selic)
    assert _nao_finitos(resultado) == []
    assert resultado["metodos_usados"].startswith("Rendimento do FII: R$")
    assert resultado["fair_value"] == _fii()["fair_value"]
    if not math.isfinite(selic):
        assert resultado["selic_liquida"] is None


@pytest.mark.parametrize("pvp", [math.nan, math.inf, -math.inf])
def test_fii_com_pvp_nao_finito_sai_sem_pvp(pvp):
    # F2A-42: P/VP não finito é tratado como ausente; a lente não pontua.
    resultado = _fii(pvp=pvp)
    assert _nao_finitos(resultado) == []
    assert resultado["pvp"] is None
    assert resultado["score_final"] == _fii(pvp=None)["score_final"]


def test_golden_sem_nan_nem_infinito():
    with GOLDEN.open(encoding="utf-8") as f:
        casos = [json.loads(linha) for linha in f]
    assert casos
    ruins = [(c["motor"], c["id"]) for c in casos if _nao_finitos(c["saida"])]
    assert ruins == []
