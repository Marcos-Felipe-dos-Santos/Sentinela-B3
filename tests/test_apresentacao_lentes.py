"""Aritmética da ficha apresentação1.0, sem sinais ou inferência econômica."""

import math

import pytest

from sentinela.domain.apresentacao import distancia


@pytest.mark.parametrize(
    "preco,esperado", [(70, 42.85714285714286), (80, 25), (160, -37.5), (100, 0)]
)
def test_exemplo_independente(preco, esperado):
    assert distancia(100, preco) == pytest.approx(esperado)


@pytest.mark.parametrize("valor", [None, True, False, 0, -1, math.inf, math.nan, "100"])
def test_valor_invalido_nao_vira_distancia_zero(valor):
    assert distancia(valor, 100) is None


@pytest.mark.parametrize("preco", [None, True, False, 0, -1, math.inf, math.nan, "100"])
def test_preco_invalido_nao_vira_distancia_zero(preco):
    assert distancia(100, preco) is None


def test_comparacao_nao_representavel_tem_ausencia():
    assert distancia(1e308, 1e-308) is None


def test_bloco_conserva_valor_regime_janela_e_hipotese_sem_classificacao():
    from types import SimpleNamespace

    from sentinela.domain.apresentacao import bloco
    from sentinela.domain.enums import Regime
    from sentinela.domain.units import BRL
    from sentinela.methods.base import MethodResult

    metodo = SimpleNamespace(
        version="2.0", regime=Regime.NOMINAL, assumptions=("exemplo",)
    )
    r = bloco(
        metodo,
        MethodResult(metodo="Teste", versao="2.0", valor=BRL(100)),
        80,
        {"fim": "2025-12-31"},
    )
    assert r == {
        "versao": "2.0",
        "valor": 100,
        "abstencao": None,
        "regime": "NOMINAL",
        "janela": {"fim": "2025-12-31"},
        "premissas": ["exemplo"],
        "unidade": "BRL",
        "distancia_ao_preco_pct": 25,
    }


def test_bloco_abstido_conserva_causa_e_metadados_sem_distancia():
    from types import SimpleNamespace

    from sentinela.domain.apresentacao import bloco
    from sentinela.domain.enums import Regime
    from sentinela.methods.base import Abstention

    metodo = SimpleNamespace(
        version="2.0", regime=Regime.REAL, assumptions=("hipótese",)
    )
    r = bloco(
        metodo, Abstention("Teste", "2.0", "fonte recusada"), 100, {"cobertura": 4}
    )
    assert r["valor"] is None and r["distancia_ao_preco_pct"] is None
    assert r["abstencao"] == "fonte recusada"
    assert r["regime"] == "REAL" and r["janela"] == {"cobertura": 4}
    assert r["premissas"] == ["hipótese"] and r["versao"] == "2.0"


def test_razao_patrimonial_nao_e_convertida_em_preco():
    from types import SimpleNamespace

    from sentinela.domain.apresentacao import bloco
    from sentinela.domain.enums import Regime
    from sentinela.domain.units import Ratio
    from sentinela.methods.base import MethodResult

    metodo = SimpleNamespace(version="1.0", regime=Regime.SEM_TAXA, assumptions=())
    r = bloco(
        metodo, MethodResult(metodo="P/VP", versao="1.0", valor=Ratio(0.8)), 100, {}
    )
    assert r["valor"] is None and r["distancia_ao_preco_pct"] is None
    assert r["abstencao"] == "lente sem valor monetário"


@pytest.mark.parametrize("valor", [0, -1])
def test_valor_monetario_nao_positivo_nao_vira_estimativa(valor):
    from types import SimpleNamespace

    from sentinela.domain.apresentacao import bloco
    from sentinela.domain.enums import Regime
    from sentinela.domain.units import BRL
    from sentinela.methods.base import MethodResult

    metodo = SimpleNamespace(version="1", regime=Regime.NOMINAL, assumptions=())
    r = bloco(
        metodo, MethodResult(metodo="Teste", versao="1", valor=BRL(valor)), 100, {}
    )
    assert r["valor"] is None and r["distancia_ao_preco_pct"] is None
    assert r["abstencao"] == "valor da lente não positivo ou não finito"


def test_entrada_e_instante_iguais_nao_dependem_de_execucao_anterior():
    from copy import deepcopy

    from apoio_gordon import AS_OF_GORDON
    from test_financeiro_pre_refactor import _acao

    from valuation_engine import ValuationEngine

    dados = _acao()
    motor = ValuationEngine()
    antes = motor.processar(deepcopy(dados), as_of=AS_OF_GORDON)
    motor.processar(_acao(roe=-0.1, pl=-10), as_of=AS_OF_GORDON)
    depois = motor.processar(deepcopy(dados), as_of=AS_OF_GORDON)
    assert antes == depois
