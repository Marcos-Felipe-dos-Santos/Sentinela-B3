"""BUG-2A-05: PL total inválido devolve `None` sem motivo.

`controladores.pl_dos_controladores` devolve `Resultado(None)` para qualquer leitura do PL
total que não seja `Leitura`, e o valor inválido (NaN, linhas divergentes) some sob o motivo
genérico do ROE. Origem: auditoria externa da Fase 2A (Gemini 2ª passada, 15/10/2026).
"""

import pytest

from sentinela.data.contas_cvm import (
    MOTIVO_LINHA_AUSENTE,
    MOTIVO_LINHAS_DIVERGENTES,
    MOTIVO_VALOR_INVALIDO,
    Abstencao,
)
from sentinela.data.controladores import MOTIVO_PL_INVALIDO, pl_dos_controladores

AUSENTE = Abstencao(MOTIVO_LINHA_AUSENTE)


@pytest.mark.parametrize("motivo", [MOTIVO_VALOR_INVALIDO, MOTIVO_LINHAS_DIVERGENTES])
def test_pl_total_invalido_traz_o_motivo(motivo):
    resultado = pl_dos_controladores(Abstencao(motivo), AUSENTE, AUSENTE)
    assert resultado.valor is None
    assert resultado.motivo == MOTIVO_PL_INVALIDO
