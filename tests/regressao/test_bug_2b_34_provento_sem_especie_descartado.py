"""BUG-2B-34: registro da relação B3 sem espécie é descartado em silêncio.

Achado da 2ª auditoria FASE do Codex (20/10/2026): `serie_12_meses` ignora todo registro cujo
`typeStock` não está nos componentes, inclusive o campo ausente. ON válido de 0,40 com um
evento de 0,60 sem espécie dava D = 0,40 (subcontagem); sem o ON corrente, D = 0 (falso
zero). Espécie ausente ou ilegível não comprova a série: abstém, com D positivo ou zero.
"""

from datetime import date

import pytest

from sentinela.data import proventos_b3 as pb


def _r(data_com, valor, especie):
    registro = {
        "corporateAction": "DIVIDENDO",
        "valueCash": valor,
        "lastDatePriorEx": data_com,
        "dateApproval": "01/01/2025",
        "quotedPerShares": "1",
    }
    if especie is not ...:
        registro["typeStock"] = especie
    return registro


ANTIGO = _r("10/06/2020", "9,0", "ON")


@pytest.mark.parametrize(
    "registros",
    [
        [_r("10/12/2025", "0,40", "ON"), _r("10/06/2026", "0,60", ...), ANTIGO],
        [_r("10/06/2026", "0,60", ...), ANTIGO],
        [_r("10/06/2026", "0,60", "  "), ANTIGO],
        [_r("10/06/2026", "0,60", None), ANTIGO],
    ],
)
def test_especie_ausente_ou_ilegivel_abstem(registros):
    s = pb.serie_12_meses(
        registros,
        total=len(registros),
        referencia=date(2026, 9, 30),
        dia_as_of=date(2026, 10, 19),
        especie="ON",
    )
    assert s == pb.Abstencao("insumo inválido: espécie do provento")
