"""BUG-2B-12: a tabela de correções aceita ticker fora do formato.

`referencia.correcoes.validar_correcoes` confere a evidência, mas não o ticker: uma linha com
`"INVALIDO"` entra no índice. Origem: F2B-21, pergunta 8 (2ª passada do Gemini).
"""

import pytest

from sentinela.data.referencia.correcoes import (
    Correcao,
    CorrecaoInvalida,
    validar_correcoes,
)


def test_ticker_fora_do_formato_e_rejeitado():
    correcao = Correcao(
        "INVALIDO", "11.111.111/0001-11", "X", "sintético", "oficial.csv", "codigo",
        "2026-10-18",
    )  # fmt: skip
    with pytest.raises(CorrecaoInvalida):
        validar_correcoes([correcao])
