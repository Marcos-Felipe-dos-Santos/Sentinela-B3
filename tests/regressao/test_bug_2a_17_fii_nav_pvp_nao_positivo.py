"""BUG-2A-17: o método `FiiNav` classifica P/VP ≤ 0 como desconto.

`sentinela/methods/fii_nav.py` cai na faixa de desconto para P/VP zero ou negativo; a
abstenção do F2A-11 ficou só no `fii_engine`. Chamado direto, o método devolve número em vez
de se abster (contrato de método: sem insumo válido, abstém-se). Origem: auditoria externa
da Fase 2A (Gemini 2ª passada, 15/10/2026).
"""

from datetime import date

import pytest

from sentinela.domain.units import Ratio
from sentinela.methods.base import Abstention, MethodInputs
from sentinela.methods.fii_nav import FiiNav, FiiNavParams

PARAMS = FiiNavParams(premio_alto=1.15, premio_moderado=1.05, desconto=0.85)


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2A-17 · FiiNav classifica P/VP ≤ 0 como desconto · corrige: F2B-41",
)
@pytest.mark.parametrize("pvp", [0.0, -1.0])
def test_pvp_nao_positivo_se_abstem(pvp):
    resultado = FiiNav().calcular(
        MethodInputs(as_of=date(2026, 10, 2), pvp=Ratio(pvp)), PARAMS
    )
    assert isinstance(resultado, Abstention)
