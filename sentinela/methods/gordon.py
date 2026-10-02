"""Gordon 1.0.0: comportamento da V1, extraído na Fase 1, sem mudança de número.

Valor justo = dividendo do próximo ano ÷ (k − g), com k = Selic + prêmio de risco e
g = ROE × retenção limitado a um teto. Tudo em regime nominal: a troca por taxa real
(k e g no mesmo regime) é o F2B-1 (armadilha 1). Exige DY confiável, DY e ROE acima
dos mínimos e k > g.
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

PAYOUT_SEM_LPA = 0.5
MOTIVO_DY_NAO_CONFIAVEL = "DY não confiável"
MOTIVO_DY_ABAIXO_DO_MINIMO = "DY abaixo do mínimo"
MOTIVO_ROE_ABAIXO_DO_MINIMO = "ROE abaixo do mínimo"
MOTIVO_K_NAO_MAIOR_QUE_G = "k não maior que g"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class GordonParams:
    dy_min: float
    roe_min: float
    g_max: float
    premio_risco: float
    payout_max: float


class Gordon(ValuationMethod):
    nome = "Gordon"
    version = "1.0.0"
    regime = Regime.NOMINAL
    requires = ("preco", "lpa", "roe", "dy", "selic")
    assumptions = (
        "valor justo = dividendo do próximo ano ÷ (k − g)",
        "k = Selic + prêmio de risco; g = ROE × (1 − payout), limitado a um teto; tudo nominal",
        "com LPA não positivo o payout é 50% (fallback da V1, sem abstenção)",
        "exige DY confiável, DY e ROE acima dos mínimos e k maior que g",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    params_type = GordonParams

    def _calcular(
        self, inputs: MethodInputs, params: GordonParams
    ) -> MethodResult | Abstention:
        if not inputs.dy_confiavel:
            return Abstention(self.nome, self.version, MOTIVO_DY_NAO_CONFIAVEL)
        dy = inputs.dy.valor
        if not dy > params.dy_min:
            return Abstention(self.nome, self.version, MOTIVO_DY_ABAIXO_DO_MINIMO)
        roe = inputs.roe.valor
        if not roe > params.roe_min:
            return Abstention(self.nome, self.version, MOTIVO_ROE_ABAIXO_DO_MINIMO)
        p = inputs.preco.valor
        lpa = inputs.lpa.valor
        payout_ratio_g = (
            min((dy * p) / lpa, params.payout_max) if lpa > 0 else PAYOUT_SEM_LPA
        )
        retencao_g = 1 - payout_ratio_g
        g = roe * retencao_g
        g = min(g, params.g_max)
        k = inputs.selic.valor + params.premio_risco
        if not k > g:
            return Abstention(self.nome, self.version, MOTIVO_K_NAO_MAIOR_QUE_G)
        div_prox = (dy * p) * (1 + g)
        valor = div_prox / (k - g)
        if not math.isfinite(valor):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(valor),
            intermediarios=(
                Intermediario("payout", Ratio(payout_ratio_g)),
                Intermediario("g", RateNominal(g)),
                Intermediario("k", RateNominal(k)),
                Intermediario("dividendo_proximo", BRL(div_prox)),
            ),
        )
