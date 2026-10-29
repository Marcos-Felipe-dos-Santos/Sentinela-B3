"""BUG-2A-07: ativo fora do índice oficial recebe os métodos de ação.

Sem registro no índice, `market_engine._aplicar_referencia` não grava `classe_ativo`, e a
guarda do F2A-29 em `valuation_engine.ValuationEngine.processar` só atua com a chave. A
BPAC11 (final 11, fora do índice e das listas conhecidas) é UNKNOWN para o classificador, mas
recebe Graham, Bazin, Lynch e Gordon. Origem: auditoria externa da Fase 2A (Gemini 1ª e 2ª
passadas e Codex, 15/10/2026).
"""

from apoio_apresentacao import verificar_lentes

from tests.test_market_engine_referencia import (
    FakeReferencia,
    _indice,
    _motor,
    _registro,
)
from valuation_engine import ValuationEngine


def test_final_11_fora_do_indice_fica_fora_do_escopo(monkeypatch):
    engine = _motor(monkeypatch, FakeReferencia(_indice(_registro())))
    dados = engine.buscar_dados_ticker("BPAC11")
    resultado = ValuationEngine().processar(dados)
    verificar_lentes(resultado)
    assert resultado["abstencao"] == "Classe UNKNOWN fora do escopo dos métodos de ação"
    assert resultado["metodos_usados"] == ""
    assert not {"fair_value", "upside"} & resultado.keys()
    assert all(
        lente["valor"] is None and lente["abstencao"]
        for lente in resultado["lentes"].values()
    )
