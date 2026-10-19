"""BUG-2B-08: `series_cvm._meses` ignora o dia.

De 31/01/2026 a 01/03/2026 a função conta 3 meses, e o intervalo passa por trimestre. Os
documentos da CVM começam no dia 1, então hoje não há efeito; um documento com início ou fim
fora do mês cheio seria aceito. Origem: F2B-21, pergunta 8 (2ª passada do Gemini).
"""

from datetime import date

import pytest

from sentinela.data import series_cvm


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-08 · _meses ignora o dia do intervalo · corrige: a decidir no marcador",
)
def test_intervalo_de_um_mes_e_um_dia_nao_e_trimestre():
    assert series_cvm._meses(date(2026, 1, 31), date(2026, 3, 1)) != 3
