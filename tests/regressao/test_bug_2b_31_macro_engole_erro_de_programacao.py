"""BUG-2B-31: o provedor macro trata erro de programação como falha da fonte.

Auditoria do F2B-48/F2B-30, ressalva 2: o `except` de `MacroProvider.registro` captura
`KeyError` e `TypeError`, e um erro do código vira abstenção como se a fonte tivesse falhado.
"""

import logging
from datetime import date

import pytest

from sentinela.data import taxas
from tests.test_macro_fontes import AS_OF, _registro_preparado


def _erro(tipo):
    def levantar(*a, **kw):
        raise tipo("campo")

    return levantar


@pytest.mark.parametrize("tipo", [KeyError, TypeError])
def test_erro_do_codigo_na_cesta_vai_para_o_log_com_motivo_proprio(
    tipo, tmp_path, monkeypatch, caplog
):
    provider = _registro_preparado(tmp_path, monkeypatch)
    monkeypatch.setattr(taxas, "calcular", _erro(tipo))
    with caplog.at_level(logging.ERROR):
        registro = provider.registro(AS_OF)
    assert registro == {
        "abstencao": f"erro inesperado no provedor macro: {tipo.__name__}"
    }
    assert any(r.levelno == logging.ERROR for r in caplog.records)


@pytest.mark.parametrize("tipo", [KeyError, TypeError])
def test_erro_do_codigo_na_inflacao_e_no_pib_tem_motivo_proprio(
    tipo, tmp_path, monkeypatch
):
    provider = _registro_preparado(tmp_path, monkeypatch)
    monkeypatch.setattr(provider, "inflacao", _erro(tipo))
    monkeypatch.setattr(provider, "pib", _erro(tipo))
    registro = provider.registro(AS_OF, (date(2025, 1, 1), date(2025, 12, 31)))
    motivo = {"abstencao": f"erro inesperado no provedor macro: {tipo.__name__}"}
    assert registro["inflacao"] == motivo
    assert registro["pib"] == motivo
