"""Ressalva Gemini atribuída ao F2B-1: agregado divergente não escolhe primeira linha."""

import pandas as pd

from cvm_provider import lpa_basico_agregado
from sentinela.data.acoes_cvm import Abstencao


def test_lpa_agregado_com_linhas_conflitantes_abstem():
    linhas = pd.DataFrame(
        [
            {"CD_CONTA": "3.99.01", "VL_CONTA": "1"},
            {"CD_CONTA": "3.99.01", "VL_CONTA": "2"},
        ]
    )
    assert isinstance(lpa_basico_agregado(linhas)["3.99.01"], Abstencao)
