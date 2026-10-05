"""Mensagens de erro exatas do contrato de método (F1-17): são o que o relatório e o
desenvolvedor leem quando um método ou um insumo viola o contrato."""

import dataclasses
from datetime import date

import pytest

from sentinela.domain.enums import AssetType, Regime
from sentinela.domain.units import BRL
from sentinela.methods import registry
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)


@dataclasses.dataclass(frozen=True)
class _Params:
    fator: float


def _msg(excecao, chamada):
    with pytest.raises(excecao) as e:
        chamada()
    return str(e.value)


def _metodo(**sobrescreve):
    attrs = {
        "nome": "X",
        "version": "1.0.0",
        "regime": Regime.SEM_TAXA,
        "requires": ("preco",),
        "assumptions": (),
        "applies_to": frozenset({AssetType.STOCK}),
        "params_type": _Params,
        "_calcular": lambda self, inputs, params: Abstention("X", "1.0.0", "n/a"),
    }
    attrs.update(sobrescreve)
    return lambda: type("X", (ValuationMethod,), attrs)


def test_mensagens_dos_inputs():
    assert (
        _msg(TypeError, lambda: MethodInputs(as_of="2026-10-02"))
        == "as_of deve ser date, não str"
    )
    assert (
        _msg(TypeError, lambda: MethodInputs(as_of=None))
        == "as_of deve ser date, não NoneType"
    )


def test_mensagens_do_intermediario():
    assert (
        _msg(ValueError, lambda: Intermediario("", 1.0))
        == "nome do intermediário não pode ser vazio"
    )
    assert _msg(TypeError, lambda: Intermediario("a", "x")) == (
        "valor do intermediário deve ser número ou unidade, não str"
    )


def test_mensagens_do_resultado():
    assert (
        _msg(TypeError, lambda: MethodResult("M", "1.0.0", "x"))
        == "valor deve ter unidade, não str"
    )
    assert _msg(TypeError, lambda: MethodResult("M", "1.0.0", BRL(1.0), ("a",))) == (
        "intermediarios devem ser Intermediario"
    )


def test_mensagem_da_abstencao():
    assert (
        _msg(ValueError, lambda: Abstention("M", "1.0.0", ""))
        == "motivo da abstenção não pode ser vazio"
    )


def test_mensagens_do_params_type():
    assert (
        _msg(TypeError, _metodo(params_type=dict))
        == "params_type deve ser uma dataclass"
    )
    assert (
        _msg(
            TypeError,
            _metodo(params_type=dataclasses.make_dataclass("P", [("a", float)])),
        )
        == "params_type deve ser uma dataclass congelada"
    )


def test_mensagens_da_declaracao_do_metodo():
    assert _msg(TypeError, _metodo(calcular=lambda self, i, p: None)) == (
        "calcular não pode ser sobrescrito: implemente _calcular"
    )
    assert _msg(TypeError, _metodo(nome="")) == "nome deve ser texto não vazio"
    assert _msg(TypeError, _metodo(regime="NOMINAL")) == "regime deve ser Regime"
    assert _msg(TypeError, _metodo(assumptions=["a"])) == "assumptions deve ser tupla"
    assert _msg(TypeError, _metodo(regime=Regime.REAL, requires=("selic",))) == (
        "selic é taxa nominal: só método NOMINAL pode exigi-la"
    )
    assert _msg(TypeError, _metodo(applies_to=frozenset())) == (
        "applies_to deve ser frozenset não vazio de AssetType"
    )


def test_mensagens_do_calcular():
    i = MethodInputs(as_of=date(2026, 10, 2), preco=BRL(1.0))
    metodo = _metodo()()
    assert _msg(TypeError, lambda: metodo().calcular({"preco": 1}, _Params(1.0))) == (
        "inputs deve ser MethodInputs"
    )
    ruim = _metodo(_calcular=lambda self, inputs, params: 42)()
    assert _msg(TypeError, lambda: ruim().calcular(i, _Params(1.0))) == (
        "_calcular deve devolver MethodResult ou Abstention"
    )


def test_mensagens_do_registro():
    g = registry.obter("Graham")
    ok = {"Graham": (registry.Mudanca("1.0.0", "x"),)}
    assert (
        _msg(ValueError, lambda: registry.validar((g, g), ok))
        == "nome de método repetido no registro"
    )
    assert (
        _msg(
            ValueError,
            lambda: registry.validar(
                (g,), {**ok, "Outro": (registry.Mudanca("1.0.0", "x"),)}
            ),
        )
        == "changelog com método que não está no registro"
    )
