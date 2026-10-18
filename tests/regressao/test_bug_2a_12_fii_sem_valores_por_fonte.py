"""BUG-2A-12: o FII da CVM não registra `valores_por_fonte['CVM']`.

`market_engine.MarketEngine._buscar_cvm_fii` faz o merge do VPA e do P/VP do Informe Mensal
sem `_guardar_por_fonte`; a checagem cruzada do P/VP em `data_quality` fica sem o valor da
CVM e vira identidade. Origem: auditoria externa da Fase 2A (Gemini e Codex, 15/10/2026).
"""

import pytest

from tests.test_market_engine_fii_cvm import INFORME, _cascata, _InformeFalso


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-12 · FII da CVM sem valores_por_fonte['CVM']: checagem cruzada do P/VP "
        "vira identidade · corrige: F2B-16"
    ),
)
def test_informe_mensal_fica_registrado_por_fonte(monkeypatch):
    dados = _cascata(monkeypatch, _InformeFalso(INFORME))
    cvm = dados.get("valores_por_fonte", {}).get("CVM", {})
    assert cvm.get("pvp") == pytest.approx(0.9)
    assert cvm.get("vpa") == pytest.approx(100.0)
