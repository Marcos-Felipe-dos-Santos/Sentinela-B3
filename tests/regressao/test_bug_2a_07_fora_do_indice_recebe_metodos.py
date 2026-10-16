"""BUG-2A-07: ativo fora do índice oficial recebe os métodos de ação.

Sem registro no índice, `market_engine._aplicar_referencia` não grava `classe_ativo`, e a
guarda do F2A-29 em `valuation_engine.ValuationEngine.processar` só atua com a chave. A
BPAC11 (final 11, fora do índice e das listas conhecidas) é UNKNOWN para o classificador, mas
recebe Graham, Bazin, Lynch e Gordon. Origem: auditoria externa da Fase 2A (Gemini 1ª e 2ª
passadas e Codex, 15/10/2026).
"""

from unittest.mock import patch

import pytest

from tests.test_market_engine_referencia import (
    FakeReferencia,
    _indice,
    _motor,
    _registro,
)
from valuation_engine import ROTULO_FORA_DO_ESCOPO, ValuationEngine


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-07 · ativo fora do índice recebe os métodos de ação: a guarda do F2A-29 "
        "não dispara · corrige: F2A-43"
    ),
)
def test_final_11_fora_do_indice_fica_fora_do_escopo(monkeypatch):
    engine = _motor(monkeypatch, FakeReferencia(_indice(_registro())))
    dados = engine.buscar_dados_ticker("BPAC11")
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
        resultado = ValuationEngine().processar(dados)
    assert resultado["recomendacao"] == ROTULO_FORA_DO_ESCOPO
