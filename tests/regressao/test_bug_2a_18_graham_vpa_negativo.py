"""BUG-2A-18: o método `Graham` com VPA < 0 calcula raiz de negativo.

`sentinela/methods/graham.py` confere P/L e P/VP positivos, mas não o VPA: com VPA negativo,
`(22,5 × LPA × VPA) ** 0,5` vira número complexo e `math.isfinite` levanta `TypeError`, em vez
de o método se abster. Com P/VP e VPA da mesma fonte a guarda do P/VP já abstém; o caminho
real é a cascata misturar fontes (P/VP de uma, VPA de outra). Origem: auditoria externa da
Fase 2A (Gemini 2ª passada, 15/10/2026).
"""

from datetime import date

import pytest

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil
from sentinela.domain.units import BRL, Ratio
from sentinela.methods.base import Abstention, MethodInputs
from sentinela.methods.graham import Graham, GrahamParams

# F2B-4: escopo de companhia (STOCK, modelo empresa pelo BPP consolidado).
ESCOPO = {"classe_ativo": AssetType.STOCK, "modelo": ModeloDemonstracao.EMPRESA}

PARAMS = GrahamParams()


@pytest.mark.parametrize("vpa", [-50.0, 0.0])
def test_vpa_negativo_se_abstem(vpa: float) -> None:
    inputs = MethodInputs(
        **ESCOPO,
        as_of=date(2026, 10, 2),
        preco=BRL(100.0),
        pl=Ratio(10.0),
        pvp=Ratio(1.5),
        vpa=BRL(vpa),
        lpa=BRL(2.0),
        perfil=Perfil.RENDA,
    )
    resultado = Graham().calcular(inputs, PARAMS)
    assert isinstance(resultado, Abstention)
    assert resultado.motivo == "VPA ≤ 0"
    assert (resultado.metodo, resultado.versao) == ("Graham", "2.1.0")
