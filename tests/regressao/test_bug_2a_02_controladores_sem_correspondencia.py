"""BUG-2A-02: reserva dos controladores liberada quando a conta tem outra descrição.

`sentinela/data/controladores.py` (`_AUSENTE`) trata `MOTIVO_SEM_CORRESPONDENCIA` como linha
ausente e autoriza o total no lugar do dos controladores. A D20 manda: par sem
correspondência vira abstenção com motivo. Origem: auditoria externa da Fase 2A (Gemini e
Codex, 15/10/2026).
"""

import pytest

from sentinela.data.contas_cvm import (
    MOTIVO_LINHA_AUSENTE,
    MOTIVO_SEM_CORRESPONDENCIA,
    Abstencao,
    Leitura,
)
from sentinela.data.controladores import lucro_dos_controladores, pl_dos_controladores

BUG = pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-02 · par sem correspondência libera a reserva dos controladores, contra a "
        "D20 · corrige: F2A-41"
    ),
)

AUSENTE = Abstencao(MOTIVO_LINHA_AUSENTE)
OUTRA_CONTA = Abstencao(MOTIVO_SEM_CORRESPONDENCIA)


def _l(valor):
    return Leitura(valor, "x", "x")


@BUG
def test_lucro_com_linha_de_outra_conta_se_abstem():
    resultado = lucro_dos_controladores(OUTRA_CONTA, OUTRA_CONTA, _l(70.0), AUSENTE)
    assert resultado.valor is None
    assert resultado.reserva is None
    assert resultado.motivo


@BUG
def test_pl_com_minoritarios_de_outra_conta_se_abstem():
    resultado = pl_dos_controladores(_l(100.0), OUTRA_CONTA, AUSENTE)
    assert resultado.valor is None
    assert resultado.reserva is None
    assert resultado.motivo
