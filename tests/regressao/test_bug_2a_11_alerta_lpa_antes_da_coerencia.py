"""BUG-2A-11: o alerta do F2A-5 compara com o LPA divulgado antes do filtro de coerência.

`market_engine._lpa_divulgado_comparado` lê `lpa_divulgado_por_especie` bruto; o divulgado
que `acoes_cvm.divulgados_coerentes` rejeitou (sinal oposto ao lucro) ainda vira a
referência da conferência em `dados['acoes_cvm']['lpa_divulgado_comparado']`. Origem:
auditoria externa da Fase 2A (Gemini e Codex, 15/10/2026).
"""

import pytest

from tests.test_market_engine_acoes_cvm import _ind, _motor
from tests.test_market_engine_referencia import FakeReferencia, _indice, _registro


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-11 · alerta do F2A-5 compara com o LPA divulgado rejeitado pela coerência "
        "· corrige: proposta da 2B"
    ),
)
def test_divulgado_de_sinal_oposto_nao_e_a_referencia_da_conferencia(monkeypatch):
    # Lucro dos controladores positivo (2.000); a PN divulgada negativa é incoerente.
    ind = _ind(
        lpa_basico_por_classe={"ON": [2.1], "PN": [-2.0]},
        lpa_divulgado_por_especie={"ON": 2.1, "PN": -2.0},
    )
    referencia = FakeReferencia(_indice(_registro("TSTA4", especie="PN")))
    dados = _motor(monkeypatch, ind, referencia=referencia).buscar_dados_ticker("TSTA4")
    comparado = dados["acoes_cvm"].get("lpa_divulgado_comparado") or {}
    assert comparado.get("valor") != -2.0
