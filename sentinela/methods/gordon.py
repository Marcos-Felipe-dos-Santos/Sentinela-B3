"""Gordon 1.1.0: comportamento da V1, extraído na Fase 1, menos o fallback do LPA.

Valor justo = dividendo do próximo ano ÷ (k − g), com k = Selic + prêmio de risco e
g = ROE × retenção limitado a um teto. Tudo em regime nominal: a troca por taxa real
(k e g no mesmo regime) é o F2B-1 (armadilha 1). Exige DY confiável, DY e ROE acima
dos mínimos, LPA positivo e k > g.

1.1.0 (F2A-25): com LPA não positivo, abstém-se. A 1.0.0 usava payout de 50% (fallback da
V1), número degradado contra o contrato de método.
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

MOTIVO_DY_NAO_CONFIAVEL = "DY não confiável"
MOTIVO_DY_ABAIXO_DO_MINIMO = "DY abaixo do mínimo"
MOTIVO_ROE_ABAIXO_DO_MINIMO = "ROE abaixo do mínimo"
MOTIVO_LPA_NAO_POSITIVO = "LPA não positivo"
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
    version = "1.1.0"
    regime = Regime.NOMINAL
    requires = ("preco", "lpa", "roe", "dy", "selic")
    assumptions = (
        "valor justo = dividendo do próximo ano ÷ (k − g)",
        "k = Selic + prêmio de risco; g = ROE × (1 − payout), limitado a um teto; tudo nominal",
        "exige DY confiável, DY e ROE acima dos mínimos, LPA positivo e k maior que g",
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
        lpa = inputs.lpa.valor
        if not lpa > 0:
            return Abstention(self.nome, self.version, MOTIVO_LPA_NAO_POSITIVO)
        p = inputs.preco.valor
        payout_ratio_g = min((dy * p) / lpa, params.payout_max)
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
