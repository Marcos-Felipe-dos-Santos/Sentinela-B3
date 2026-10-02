"""Lynch 1.0.0: comportamento da V1, extraído na Fase 1, sem mudança de número.

Valor justo = LPA × P/L justo, com P/L justo = multiplicador × g (em pontos
percentuais), g = ROE × retenção e tetos de payout, de g e de P/L justo. Só no
perfil crescimento, com DY confiável e P/L, LPA e ROE positivos. O g é nominal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

MOTIVO_PERFIL_RENDA = "perfil renda"
MOTIVO_DY_NAO_CONFIAVEL = "DY não confiável"
MOTIVO_PL_NAO_POSITIVO = "P/L não positivo"
MOTIVO_LPA_NAO_POSITIVO = "LPA não positivo"
MOTIVO_ROE_NAO_POSITIVO = "ROE não positivo"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class LynchParams:
    payout_max: float
    g_max: float
    pl_multiplicador: float
    pl_max: float


class Lynch(ValuationMethod):
    nome = "Lynch"
    version = "1.0.0"
    regime = Regime.NOMINAL
    requires = ("preco", "lpa", "pl", "roe", "dy", "perfil")
    assumptions = (
        "valor justo = LPA × P/L justo; P/L justo = multiplicador × g em pontos percentuais",
        "g = ROE × (1 − payout), nominal, com tetos de payout, de g e de P/L justo",
        "só para o perfil crescimento, com DY confiável",
        "exige P/L, LPA e ROE positivos",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    params_type = LynchParams

    def _calcular(
        self, inputs: MethodInputs, params: LynchParams
    ) -> MethodResult | Abstention:
        if inputs.perfil is not Perfil.CRESCIMENTO:
            return Abstention(self.nome, self.version, MOTIVO_PERFIL_RENDA)
        if not inputs.dy_confiavel:
            return Abstention(self.nome, self.version, MOTIVO_DY_NAO_CONFIAVEL)
        if not inputs.pl.valor > 0:
            return Abstention(self.nome, self.version, MOTIVO_PL_NAO_POSITIVO)
        lpa = inputs.lpa.valor
        if not lpa > 0:
            return Abstention(self.nome, self.version, MOTIVO_LPA_NAO_POSITIVO)
        roe = inputs.roe.valor
        if not roe > 0:
            return Abstention(self.nome, self.version, MOTIVO_ROE_NAO_POSITIVO)
        payout_ratio = min(
            (inputs.dy.valor * inputs.preco.valor) / lpa, params.payout_max
        )
        retencao = 1 - payout_ratio
        g = roe * retencao
        g = min(g, params.g_max)
        pl_justo = params.pl_multiplicador * (g * 100)
        pl_justo = min(pl_justo, params.pl_max)
        valor = lpa * pl_justo
        if not math.isfinite(valor):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(valor),
            intermediarios=(
                Intermediario("payout", Ratio(payout_ratio)),
                Intermediario("g", RateNominal(g)),
                Intermediario("pl_justo", Ratio(pl_justo)),
            ),
        )
