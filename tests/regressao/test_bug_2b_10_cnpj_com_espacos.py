"""BUG-2B-10: `proveniencia.entrega_no_indice` não acha o CNPJ com espaços nas pontas.

O índice de entregas com `" 11.111.111/0001-11 "` não casa com o documento
`"11.111.111/0001-11"`, e a data de entrega sai ausente. Origem: F2B-21, pergunta 8
(2ª passada do Gemini).
"""

import pytest

from sentinela.data import proveniencia


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-10 · CNPJ com espaços não acha a entrega no índice · corrige: F2C-19",
)
def test_cnpj_com_espacos_acha_a_entrega():
    linhas = [{"CNPJ_CIA": " 11.111.111/0001-11 ", "DT_RECEB": "2026-03-01"}]
    documento = {"CNPJ_CIA": "11.111.111/0001-11"}
    assert proveniencia.entrega_no_indice(linhas, documento) == "2026-03-01"
