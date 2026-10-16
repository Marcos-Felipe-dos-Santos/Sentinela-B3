"""Funções puras de `sentinela.data.controladores` (F2A-37): reservas da D20 e da ficha 7.2."""

import pytest

from sentinela.data.contas_cvm import (
    MOTIVO_LINHA_AUSENTE,
    MOTIVO_LINHAS_DIVERGENTES,
    MOTIVO_SEM_CORRESPONDENCIA,
    MOTIVO_VALOR_INVALIDO,
    Abstencao,
    Leitura,
)
from sentinela.data.controladores import (
    MOTIVO_LUCRO_INVALIDO,
    MOTIVO_LUCRO_NAO_SEPARADO,
    MOTIVO_LUCRO_SEM_CORRESPONDENCIA,
    MOTIVO_LUCRO_SEM_TOTAL,
    MOTIVO_PL_INVALIDO,
    MOTIVO_PL_SEM_CORRESPONDENCIA,
    RESERVA_LUCRO_SEM_LINHA,
    RESERVA_PL,
    Resultado,
    lucro_dos_controladores,
    pl_dos_controladores,
)

AUSENTE = Abstencao(MOTIVO_LINHA_AUSENTE)
OUTRA_CONTA = Abstencao(MOTIVO_SEM_CORRESPONDENCIA)
INVALIDA = Abstencao(MOTIVO_VALOR_INVALIDO)
DIVERGENTE = Abstencao(MOTIVO_LINHAS_DIVERGENTES)


def _l(valor):
    return Leitura(valor, "x", "x")


@pytest.mark.parametrize("invalida", [INVALIDA, DIVERGENTE])
def test_controladora_invalida_abstem_mesmo_com_total(invalida):
    assert lucro_dos_controladores(invalida, AUSENTE, _l(100.0), AUSENTE) == Resultado(
        None, motivo=MOTIVO_LUCRO_INVALIDO
    )


def test_controladora_zerada_com_minoritarios_e_zero_informado():
    assert lucro_dos_controladores(_l(0.0), _l(100.0), _l(100.0), AUSENTE) == Resultado(
        0.0
    )


def test_sem_consolidado_valido():
    assert lucro_dos_controladores(AUSENTE, AUSENTE, INVALIDA, AUSENTE) == Resultado(
        None, motivo=MOTIVO_LUCRO_SEM_TOTAL
    )
    assert lucro_dos_controladores(_l(0.0), AUSENTE, AUSENTE, AUSENTE) == Resultado(0.0)


def test_consolidado_zerado_nao_e_reserva():
    assert lucro_dos_controladores(_l(0.0), _l(0.0), _l(0.0), _l(5.0)) == Resultado(0.0)


def test_linha_de_outra_conta_se_abstem():
    # F2A-41 (D20): par sem correspondência é abstenção, não linha ausente.
    assert lucro_dos_controladores(
        OUTRA_CONTA, OUTRA_CONTA, _l(70.0), AUSENTE
    ) == Resultado(None, motivo=MOTIVO_LUCRO_SEM_CORRESPONDENCIA)
    assert lucro_dos_controladores(AUSENTE, AUSENTE, _l(70.0), AUSENTE) == Resultado(
        70.0, reserva=RESERVA_LUCRO_SEM_LINHA
    )


@pytest.mark.parametrize("pl_minoritarios", [INVALIDA, DIVERGENTE, OUTRA_CONTA])
def test_linha_ausente_com_minoritarios_ilegiveis_no_balanco_se_abstem(pl_minoritarios):
    # F2A-41: sem a 2.03.09 legível, não há como afirmar que não há minoritários.
    assert lucro_dos_controladores(
        AUSENTE, AUSENTE, _l(70.0), pl_minoritarios
    ) == Resultado(None, motivo=MOTIVO_LUCRO_NAO_SEPARADO)


def test_pl_subtrai_minoritarios_e_reserva_so_sem_evidencia():
    assert pl_dos_controladores(_l(100.0), _l(1.0), _l(5.0)) == Resultado(99.0)
    assert pl_dos_controladores(_l(100.0), _l(0.0), _l(0.0)) == Resultado(
        100.0, reserva=RESERVA_PL
    )
    assert pl_dos_controladores(_l(100.0), OUTRA_CONTA, AUSENTE) == Resultado(
        None, motivo=MOTIVO_PL_SEM_CORRESPONDENCIA
    )
    assert pl_dos_controladores(_l(100.0), AUSENTE, OUTRA_CONTA) == Resultado(
        None, motivo=MOTIVO_PL_SEM_CORRESPONDENCIA
    )
    assert pl_dos_controladores(AUSENTE, _l(1.0), AUSENTE) == Resultado(None)
    assert pl_dos_controladores(_l(100.0), DIVERGENTE, AUSENTE) == Resultado(
        None, motivo=MOTIVO_PL_INVALIDO
    )
