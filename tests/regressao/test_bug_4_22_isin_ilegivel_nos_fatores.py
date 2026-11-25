"""BUG-4-22: nos fatores de Graham e Lynch, ISIN ilegível fora do emissor descarta o evento.

`fatores_acoes_b3._fator_do_par` tirava a espécie de um ISIN sem conferir o dígito verificador:
um evento em ações na janela de reconciliação com ISIN ilegível fora do conjunto do emissor era
descartado (pela espécie, ou pelo descarte legado do C3-03b), e o fator saía só com os eventos
próprios. É o mesmo defeito do BUG-4-17 no Bazin (decisão do Marcos de 25/11/2026, F4-C11).

Arranjo e ISINs sintéticos de `tests/test_fatores_acoes_b3.py`.
"""

import pytest
from test_fatores_acoes_b3 import AS_OF, dados, documentos, evento

from sentinela.data import proventos_b3 as pb
from sentinela.data.fatores_acoes_b3 import fatores_da_relacao

MOTIVO = "espécie do evento em ações não demonstrada"


@pytest.mark.parametrize("alheio", ["BRALHEACNPA0", "BRALHEACNOR0"])
def test_isin_ilegivel_fora_do_emissor_na_janela_abstem(alheio: str) -> None:
    assert not pb.isin_legivel(alheio)

    resultado = fatores_da_relacao(
        dados([evento(), evento(isin=alheio)]), documentos(), AS_OF
    )

    assert resultado.get("abstencao") == MOTIVO


def test_isin_legivel_fora_do_emissor_continua_descartado() -> None:
    """Controle: com o dígito válido, o evento de outro emissor sai antes da janela."""
    assert pb.isin_legivel("BRALHEACNOR9")
    so_o_proprio = fatores_da_relacao(dados([evento()]), documentos(), AS_OF)

    resultado = fatores_da_relacao(
        dados([evento(), evento(isin="BRALHEACNOR9")]), documentos(), AS_OF
    )

    assert resultado == so_o_proprio
