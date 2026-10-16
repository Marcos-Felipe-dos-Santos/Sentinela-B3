"""BUG-2A-04: minoritários do balanço lidos só no modelo do setor.

`cvm_provider.lucro_controladores_com_reserva` lê as três contas da DRE em todos os modelos
da tabela, mas a 2.03.09 (participação dos não controladores) só no modelo do setor. Banco
sem setor no índice (modelo empresa) com a participação na 2.08.09 recebe a reserva do lucro
total. Origem: auditoria externa da Fase 2A (Gemini 1ª passada e Codex, 15/10/2026).
"""

import pandas as pd
import pytest

from cvm_provider import lucro_controladores_com_reserva
from sentinela.data.controladores import MOTIVO_LUCRO_NAO_SEPARADO


def _df(*linhas):
    return pd.DataFrame(
        [
            {"CD_CONTA": codigo, "DS_CONTA": descricao, "VL_CONTA": valor}
            for codigo, descricao, valor in linhas
        ]
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-04 · minoritários do balanço lidos só no modelo do setor · corrige: F2A-41"
    ),
)
def test_minoritarios_do_balanco_de_outro_modelo_impedem_a_reserva():
    # Layout do Itaú (DFP 2025): DRE em 3.09, participação dos não controladores em 2.08.09.
    dre = _df(
        ("3.09", "Lucro/Prejuízo Consolidado do Período", 100.0),
        ("3.09.01", "Atribuído a Sócios da Empresa Controladora", 0.0),
        ("3.09.02", "Atribuído a Sócios Não Controladores", 0.0),
    )
    bpp = _df(("2.08.09", "Participação dos Acionistas Não Controladores", 50.0))
    resultado = lucro_controladores_com_reserva(dre, bpp, "empresa")
    assert resultado.valor is None
    assert resultado.motivo == MOTIVO_LUCRO_NAO_SEPARADO
