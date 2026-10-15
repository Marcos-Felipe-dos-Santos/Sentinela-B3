"""Nenhuma saída dos motores com NaN ou infinito (F2A-24; registrado no F1-7 e no F1-16).

Preço não finito: os dois motores devolvem `None`, como com preço zero. FII sem método
calculado (Selic zero ou não finita, vacância não finita): o resultado do DY inválido, com o
motivo da abstenção do método em `metodos_usados`.
"""

import json
import math
from unittest.mock import patch

import pytest

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
        return FIIEngine().analisar({**FII, "preco_atual": 100.0, **extra})


@pytest.mark.parametrize("preco", [math.nan, math.inf, -math.inf])
def test_acao_com_preco_nao_finito_devolve_none(preco):
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
        assert ValuationEngine().processar({**ACAO, "preco_atual": preco}) is None
    with patch("fii_engine.get_selic_atual", return_value=0.145):
        assert FIIEngine().analisar({**FII, "preco_atual": preco}) is None


@pytest.mark.parametrize("selic", [0.0, math.nan, math.inf])
def test_fii_com_selic_zero_nao_devolve_nan(selic):
    resultado = _fii(selic=selic)
    assert _nao_finitos(resultado) == []
    assert resultado["metodos_usados"].startswith("Dados insuficientes (")
    assert resultado["recomendacao"] == "NEUTRO"


def test_golden_sem_nan_nem_infinito():
    with GOLDEN.open(encoding="utf-8") as f:
        casos = [json.loads(linha) for linha in f]
    assert casos
    ruins = [(c["motor"], c["id"]) for c in casos if _nao_finitos(c["saida"])]
    assert ruins == []
