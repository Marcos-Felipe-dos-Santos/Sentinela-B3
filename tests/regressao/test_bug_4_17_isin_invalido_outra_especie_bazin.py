"""BUG-4-17: ISIN ilegível com aparência de outra espécie ainda descarta o evento no Bazin.

O F4-A11c fez o descarte por emissor exigir ISIN legível, mas a linha seguinte de
`proventos_b3._evento_de_acoes_na_janela` ainda tirava a espécie dos caracteres 7 a 11 de um
ISIN ilegível e descartava o evento por espécie: com o alvo ON, `BRALHEACNPA0` (dígito
inválido, trecho de PNA) liberava o DY (bloqueador 3 da auditoria R2 do bloco 0,
`docs/loop/auditorias/bloco0-codex.md`). ISIN inválido nunca descarta por espécie.

Arranjo e ISINs sintéticos do BUG-4-04.
"""

import pytest
from regressao.test_bug_4_04_corte_e_emissor_da_janela_b3 import (
    ISIN,
    _entradas,
    _evento,
)

from sentinela.data import proventos_b3 as pb

MOTIVO = f"{pb.MOTIVO_EVENTO_ACOES}: DESDOBRAMENTO 15/10/2026"


@pytest.mark.parametrize("isin", ["BRALHEACNPA0", "BRALHEACNPR0", "BRTESTACNPA0"])
def test_isin_ilegivel_de_outra_especie_abstem_com_o_motivo_do_evento(
    isin: str,
) -> None:
    assert not pb.isin_legivel(isin)

    resultado = _entradas(evento=_evento(isin, "01/10/2026"))

    assert isinstance(resultado, pb.Abstencao)
    assert resultado.motivo == MOTIVO


def test_sem_isins_do_emissor_o_ilegivel_de_outra_especie_tambem_abstem() -> None:
    evento = _evento("BRALHEACNPA0", "01/10/2026")

    resultado = pb._evento_de_acoes_na_janela(
        [evento],
        ["ON"],
        pb.ler_data("16/10/2025"),
        pb.ler_data("19/10/2026"),
        pb.ler_data("20/10/2026"),
        [],
    )

    assert resultado == "DESDOBRAMENTO 15/10/2026"


def test_isin_legivel_de_outra_especie_continua_descartado_pela_especie() -> None:
    """Controle: sem conjunto do emissor, o ISIN legível de PNA prova que o evento não é da ON."""
    assert pb.isin_legivel("BRTESTACNPA2")

    resultado = pb._evento_de_acoes_na_janela(
        [_evento("BRTESTACNPA2", "01/10/2026")],
        ["ON"],
        pb.ler_data("16/10/2025"),
        pb.ler_data("19/10/2026"),
        pb.ler_data("20/10/2026"),
        [],
    )

    assert resultado is None


def test_isin_do_emissor_da_mesma_especie_continua_abstendo() -> None:
    resultado = _entradas(evento=_evento(ISIN, "01/10/2026"))

    assert isinstance(resultado, pb.Abstencao)
    assert resultado.motivo == MOTIVO
