"""Golden dos motores V1 (F1-16): a saída atual de `ValuationEngine` e `FIIEngine`.

Comparação exata (`==` nos floats, NaN == NaN), incluindo a ordem de `riscos` e o
texto de `metodos_usados`. Geração única: ver `tests/golden_motores.py`.
"""

import os

import pytest
from golden_motores import executar, gravar_golden, iguais, ler_golden, montar_casos


def _divergentes(motor):
    return [
        c["id"]
        for c in ler_golden()
        if c["motor"] == motor and not iguais(executar(c), c["saida"])
    ]


def test_acoes_iguais_ao_golden():
    assert _divergentes("acoes") == []


def test_fii_iguais_ao_golden():
    assert _divergentes("fii") == []


def test_golden_tem_os_casos_da_grade():
    golden = [(c["motor"], c["id"]) for c in ler_golden()]
    assert len(golden) == len(set(golden))
    assert golden == [(c["motor"], c["id"]) for c in montar_casos()]


def test_comparador_distingue_nan_tipo_e_ordem():
    nan = float("nan")
    assert iguais({"a": [nan, 1.0]}, {"a": [nan, 1.0]})
    assert not iguais({"a": 1}, {"a": 1.0})
    assert not iguais({"riscos": ["x", "y"]}, {"riscos": ["y", "x"]})
    assert not iguais({"a": 1.0}, {"a": 1.0000000000000002})
    assert not iguais({"a": 1.0}, {"b": 1.0})
    assert not iguais(None, {})


@pytest.mark.skipif(
    not os.environ.get("GERAR_GOLDEN"), reason="gerador do golden: rodar uma vez"
)
def test_gerar_golden():
    gravar_golden(montar_casos())
