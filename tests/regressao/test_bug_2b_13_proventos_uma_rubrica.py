"""BUG-2B-13: a rubrica informada não some quando a outra não ocorre na DVA.

Decisão do Marcos de 19/10/2026, F2B-46; soma dos proventos declarados,
distinguindo linha ausente de DVA indisponível ou leitura inválida.
"""

import pytest

from sentinela.data.series_cvm import proventos


@pytest.mark.parametrize("parcelas", [(10.0, None), (None, 10.0)])
def test_parcela_declarada_nao_some(parcelas):
    assert proventos(*parcelas) == 10.0
