"""BUG-2A-01: LPA, VPA, ROE, P/L ou P/VP ≤ 0 da CVM descartados no merge.

`market_engine._is_field_missing` trata valor ≤ 0 desses campos como ausente; o merge o
ignora, e o valor positivo de outra fonte (ou do cache) fica. Origem: auditoria externa da
Fase 2A (Gemini e Codex, 15/10/2026).
"""

import pytest

from market_engine import list_missing_required_fields, merge_if_valid
from tests.test_market_engine import FakeCVM, _cvm_ind, _engine, _historico

BUG = pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-01 · prejuízo ou PL negativo da CVM descartado no merge; o positivo "
        "anterior fica · corrige: F2B-8"
    ),
)


@BUG
@pytest.mark.parametrize("campo", ["lpa", "vpa", "roe", "pl", "pvp"])
def test_valor_nao_positivo_sobrescreve_o_anterior(campo):
    dados = {campo: 2.0}
    merge_if_valid(dados, {campo: -1.0}, overwrite=True)
    assert dados[campo] == -1.0


@BUG
def test_prejuizo_nao_conta_como_dado_ausente():
    dados = {"ticker": "PETR4", "pl": -5.0, "pvp": 1.2, "roe": -0.05, "dy": 0.04}
    assert list_missing_required_fields(dados) == []


@BUG
def test_roe_negativo_da_cvm_chega_ao_fim_da_cascata(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(20.0),
        info={"currentPrice": 20.0, "quoteType": "EQUITY", "returnOnEquity": 0.10},
        cvm=FakeCVM(_cvm_ind(roe=-0.05)),
    )
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["roe"] == pytest.approx(-0.05)
