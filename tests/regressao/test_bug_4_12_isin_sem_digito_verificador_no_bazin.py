"""BUG-4-12: ISIN alheio com dígito verificador inválido descarta o evento em ações no Bazin.

`proventos_b3._evento_de_acoes_na_janela` descartava como de outro emissor qualquer ISIN de 12
caracteres fora do conjunto do emissor, sem conferir o dígito verificador, enquanto o
`fatores_acoes_b3` o confere (DD-95). Um ISIN corrompido não prova outro emissor: é ilegível e,
pela DD-93, o evento conserva a abstenção (observação da revisão cruzada da DD-93; decisão 2
do Marcos de 25/11/2026).

Arranjo e ISINs sintéticos do BUG-4-04.
"""

import pytest
from regressao.test_bug_4_04_corte_e_emissor_da_janela_b3 import (
    ISIN,
    _entradas,
    _evento,
)

from sentinela.data import proventos_b3 as pb


@pytest.mark.parametrize("isin", ["BRALHEACNOR0", "BRALHEACNOR1", "brALHEACNOR9"])
def test_isin_alheio_com_digito_invalido_e_ilegivel_e_abstem(isin: str) -> None:
    assert not pb.isin_legivel(isin)

    resultado = _entradas(evento=_evento(isin, "01/10/2026"))

    assert isinstance(resultado, pb.Abstencao)
    assert resultado.motivo == f"{pb.MOTIVO_EVENTO_ACOES}: DESDOBRAMENTO 15/10/2026"


def test_isin_alheio_legivel_continua_descartado() -> None:
    assert pb.isin_legivel("BRALHEACNOR9")

    resultado = _entradas(evento=_evento("BRALHEACNOR9", "01/10/2026"))

    assert not isinstance(resultado, pb.Abstencao), resultado
    assert resultado["dy"] == pytest.approx(0.15)


def test_isin_do_emissor_continua_abstendo_mesmo_sem_digito_valido() -> None:
    assert not pb.isin_legivel(ISIN)

    resultado = _entradas(evento=_evento(ISIN, "01/10/2026"))

    assert isinstance(resultado, pb.Abstencao)
