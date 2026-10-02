"""Rendimento do FII 1.0.0: comportamento da V1, extraído na Fase 1, sem mudança de número.

Preço justo = preço × DY efetivo ÷ (Selic × fator de IR). O DY efetivo é o DY ajustado
pela vacância, quando há vacância. DY efetivo e Selic líquida voltam como intermediários
para o score, que fica no motor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

MOTIVO_SELIC_LIQUIDA_ZERO = "Selic líquida zero"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class FiiYieldParams:
    fator_ir: float


class FiiYield(ValuationMethod):
    nome = "Bazin FII"
    version = "1.0.0"
    regime = Regime.NOMINAL
    requires = ("preco", "dy", "selic")
    assumptions = (
        "preço justo = preço × DY efetivo ÷ (Selic × fator de IR)",
        "DY efetivo = DY × (1 − vacância), quando há vacância; sem vacância, o próprio DY",
        "o fator de IR (15% de imposto na renda fixa de longo prazo) reduz a Selic",
    )
    applies_to = frozenset({AssetType.FII})
    params_type = FiiYieldParams

    def _calcular(
        self, inputs: MethodInputs, params: FiiYieldParams
    ) -> MethodResult | Abstention:
        dy = inputs.dy.valor
        if inputs.vacancia is not None:
            dy_efetivo = dy * (1 - inputs.vacancia.valor)
        else:
            dy_efetivo = dy
        selic_liquida = inputs.selic.valor * params.fator_ir
        if selic_liquida == 0:
            return Abstention(self.nome, self.version, MOTIVO_SELIC_LIQUIDA_ZERO)
        preco_justo = (inputs.preco.valor * dy_efetivo) / selic_liquida
        if not math.isfinite(preco_justo):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(preco_justo),
            intermediarios=(
                Intermediario("dy_efetivo", Ratio(dy_efetivo)),
                Intermediario("selic_liquida", RateNominal(selic_liquida)),
            ),
        )
