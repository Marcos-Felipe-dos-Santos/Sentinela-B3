"""Rendimento do FII 2.0.0: NTN-B real mais spread, com crescimento real zero (ficha FII 1.1).

Preço justo = R ÷ (y_real + s), com R = preço × DY de 12 meses do Informe (o rendimento de
12 meses por cota, tratado como fluxo real constante), y_real a média da NTN-B da taxa real
sem o prêmio das ações e s o spread calibrado dos FIIs de tijolo (parâmetro datado). A Selic
líquida e o P/VP ficam no motor, como contexto e score; não formam o preço justo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Regime
from sentinela.domain.units import BRL, RateReal
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

DY_MAXIMO = 0.25
MOTIVO_SPREAD = "spread indisponível"
MOTIVO_TAXA_FORA = "taxa indisponível: NTN-B real fora do domínio"
MOTIVO_TAXA_NAO_POSITIVA = "taxa não positiva"
MOTIVO_RENDIMENTO = "rendimento anual não positivo"
MOTIVO_DY_NAO_CONFIAVEL = "rendimento não confiável"
MOTIVO_PRECO = "preço não positivo"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class FiiYieldParams:
    spread: float | None


class FiiYield(ValuationMethod):
    nome = "Rendimento do FII"
    version = "2.0.0"
    regime = Regime.REAL
    requires = ("preco", "dy", "ntnb_real")
    assumptions = (
        "preço justo = R ÷ (NTN-B real + spread), R = preço × DY de 12 meses do Informe",
        "crescimento real zero: o rendimento de 12 meses é tratado como fluxo real constante",
        "spread bruto sobre benchmark bruto, sem fator tributário",
        "o spread é a mediana de 60 meses dos FIIs de tijolo, constante datada",
    )
    applies_to = frozenset({AssetType.FII})
    params_type = FiiYieldParams

    def _calcular(
        self, inputs: MethodInputs, params: FiiYieldParams
    ) -> MethodResult | Abstention:
        def abster(motivo: str) -> Abstention:
            return Abstention(self.nome, self.version, motivo)

        spread = params.spread
        if (
            spread is None
            or isinstance(spread, bool)
            or not isinstance(spread, (int, float))
            or not math.isfinite(spread)
        ):
            return abster(MOTIVO_SPREAD)
        preco = inputs.preco.valor
        dy = inputs.dy.valor
        ntnb = inputs.ntnb_real.valor
        if not math.isfinite(ntnb) or ntnb <= -1:
            return abster(MOTIVO_TAXA_FORA)
        taxa = ntnb + spread
        if taxa <= 0:
            return abster(MOTIVO_TAXA_NAO_POSITIVA)
        if not math.isfinite(preco) or preco <= 0:
            return abster(MOTIVO_PRECO)
        if not math.isfinite(dy) or dy <= 0:
            return abster(MOTIVO_RENDIMENTO)
        if dy > DY_MAXIMO:
            return abster(MOTIVO_DY_NAO_CONFIAVEL)
        rendimento = preco * dy
        preco_justo = rendimento / taxa
        if not (math.isfinite(rendimento) and math.isfinite(preco_justo)):
            return abster(MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(preco_justo),
            intermediarios=(
                Intermediario("rendimento_12m", BRL(rendimento)),
                Intermediario("ntnb", RateReal(ntnb)),
                Intermediario("spread", RateReal(spread)),
                Intermediario("taxa", RateReal(taxa)),
            ),
        )
