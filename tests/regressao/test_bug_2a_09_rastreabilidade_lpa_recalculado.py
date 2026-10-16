"""BUG-2A-09: o relatório de rastreabilidade descreve o LPA da CVM como lucro ÷ ações.

Desde o F2A-36 (D19) o LPA dos métodos é o LPA básico divulgado da espécie, e o recalculado
é conferência ou reserva marcada (`dados['lpa_cvm']`). `rastreabilidade.LIMITES` e
`_proveniencia_derivada` ainda dizem "lucro dos controladores ÷ ações". Origem: auditoria
externa da Fase 2A (Gemini 2ª passada, 15/10/2026).
"""

import pytest

from tests.test_rastreabilidade import _acao, _html

ACOES_CVM = {
    "documento": {"dt_refer": "2025-12-31", "versao": "1"},
    "escala": "MIL",
    "acoes": 1_000_000.0,
    "nota": "ações do fim do período",
}
LPA_DIVULGADO = {"origem": "divulgado", "classe": "ON", "notas": []}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-09 · rastreabilidade diz que o LPA da CVM é lucro ÷ ações, e não o "
        "divulgado · corrige: F2A-44"
    ),
)
def test_lpa_divulgado_nao_e_descrito_como_lucro_sobre_acoes():
    html = _html(_acao(acoes_cvm=ACOES_CVM, lpa_cvm=LPA_DIVULGADO))
    assert "lucro dos controladores ÷" not in html
    assert "LPA e VPA são o lucro" not in html
