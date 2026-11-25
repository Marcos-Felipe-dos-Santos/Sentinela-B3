"""F4-C08: provento sem `dateApproval` legível na janela de 12 meses leva à abstenção.

Observação da auditoria do Claude (chat) no checkpoint do bloco 0. A conferência do executor
não reproduziu soma com aprovação ilegível: a `serie_12_meses` já se abstém com o motivo de
disponibilidade. Este teste fixa esse comportamento nas formas de aprovação ilegível
(DD-100). Arranjo e valores sintéticos do BUG-4-04.
"""

import pytest
from regressao.test_bug_4_04_corte_e_emissor_da_janela_b3 import _entradas, _registro

from sentinela.data import proventos_b3 as pb


@pytest.mark.parametrize(
    "aprovacao",
    [
        pytest.param("", id="vazia"),
        pytest.param(None, id="nula"),
        pytest.param("31/02/2026", id="data_impossivel"),
        pytest.param("ilegível", id="texto"),
        pytest.param("2026-10-01", id="formato_iso"),
    ],
)
def test_provento_na_janela_sem_aprovacao_legivel_abstem_com_motivo(aprovacao):
    resultado = _entradas(provento=_registro("16/10/2026", aprovacao, "2,00"))

    assert isinstance(resultado, pb.Abstencao)
    assert resultado.motivo == pb.MOTIVO_DISPONIBILIDADE


def test_provento_sem_a_chave_de_aprovacao_abstem_com_motivo():
    registro = _registro("16/10/2026", "01/10/2026", "2,00")
    del registro["dateApproval"]

    resultado = _entradas(provento=registro)

    assert isinstance(resultado, pb.Abstencao)
    assert resultado.motivo == pb.MOTIVO_DISPONIBILIDADE


def test_provento_fora_da_janela_sem_aprovacao_nao_entra_nem_abstem():
    """Controle: fora da janela, a falta de aprovação não muda o DY dos demais."""
    resultado = _entradas(provento=_registro("15/09/2024", "", "2,00"))

    assert not isinstance(resultado, pb.Abstencao), resultado
    assert resultado["dy"] == pytest.approx(0.15)
