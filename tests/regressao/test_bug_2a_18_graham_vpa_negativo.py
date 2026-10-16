"""BUG-2A-18: o método `Graham` com VPA < 0 calcula raiz de negativo.

`sentinela/methods/graham.py` confere P/L e P/VP positivos, mas não o VPA: com VPA negativo,
`(22,5 × LPA × VPA) ** 0,5` vira número complexo e `math.isfinite` levanta `TypeError`, em vez
de o método se abster. Com P/VP e VPA da mesma fonte a guarda do P/VP já abstém; o caminho
real é a cascata misturar fontes (P/VP de uma, VPA de outra). Origem: auditoria externa da
Fase 2A (Gemini 2ª passada, 15/10/2026).
"""

from datetime import date

import pytest

from sentinela.domain.enums import Perfil
from sentinela.domain.units import BRL, Ratio
from sentinela.methods.base import Abstention, MethodInputs
from sentinela.methods.graham import Graham, GrahamParams

PARAMS = GrahamParams(
    pl_limite=25.0, pl_piso=7.0, pvp_limite_renda=2.5, pvp_limite_crescimento=3.0
)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-2A-18 · Graham com VPA < 0 calcula raiz de negativo em vez de se abster · "
        "corrige: proposta da 2B"
    ),
)
def test_vpa_negativo_se_abstem():
    inputs = MethodInputs(
        as_of=date(2026, 10, 2),
        preco=BRL(100.0),
        pl=Ratio(10.0),
        pvp=Ratio(1.5),
        vpa=BRL(-50.0),
        perfil=Perfil.RENDA,
    )
    assert isinstance(Graham().calcular(inputs, PARAMS), Abstention)
