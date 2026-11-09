"""BUG-2B-07: `acoes_cvm.divulgados_coerentes` aceita LPA divulgado NaN ou zero.

Com prejuízo, uma linha NaN ou zero vira `LpaDivulgado(nan)` ou `LpaDivulgado(0.0)`, em vez
da abstenção por valor inválido. O provedor (`lpa_basico_por_classe`) já descarta NaN e zero;
o risco é de outro chamador. Origem: F2B-21, pergunta 8 (2ª passada do Gemini).
"""

import math

import pytest

from sentinela.data import acoes_cvm


@pytest.mark.parametrize("valor", [math.nan, 0.0])
def test_divulgado_invalido_se_abstem(valor):
    resultado = acoes_cvm.divulgados_coerentes({"ON": [valor]}, -10.0, -10.0)
    assert isinstance(resultado["ON"], acoes_cvm.Abstencao)
