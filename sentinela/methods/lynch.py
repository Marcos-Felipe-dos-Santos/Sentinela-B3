"""Lynch2.0: CAGR nominal de cinco observações/quatro intervalos, m1 e gmax25%."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal, Ratio
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

MOTIVO_PERFIL_RENDA = "perfil renda"
MOTIVO_LPA_NAO_POSITIVO = "LPA não positivo"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class LynchParams:
    """Teto aprovado; não há multiplicador, teto de P/L ou truncamento de payout."""


class Lynch(ValuationMethod):
    nome = "Lynch"
    version = "2.1.0"
    regime = Regime.NOMINAL
    requires = ("lpa", "crescimento_lpa", "perfil")
    assumptions = (
        "reorganização societária no período não é detectada",
        "CAGR nominal de cinco observações em quatro intervalos anuais",
        "P/L de referência = crescimento em pontos percentuais, m=1; teto g25%",
        "payout somente contexto, mesma fonte do perfil; extremos positivos",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    modelos = frozenset({ModeloDemonstracao.EMPRESA})
    params_type = LynchParams

    def _calcular(
        self, inputs: MethodInputs, params: LynchParams
    ) -> MethodResult | Abstention:
        if inputs.perfil is not Perfil.CRESCIMENTO:
            return Abstention(self.nome, self.version, MOTIVO_PERFIL_RENDA)
        lpa = inputs.lpa.valor
        if lpa <= 0:
            return Abstention(self.nome, self.version, MOTIVO_LPA_NAO_POSITIVO)
        crescimento = inputs.crescimento_lpa.valor
        if crescimento <= 0:
            return Abstention(self.nome, self.version, "CAGR não positivo")
        g = min(crescimento, 0.25)
        pl_justo = g * 100
        valor = lpa * pl_justo
        if not math.isfinite(valor):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(valor),
            intermediarios=(
                Intermediario("g", RateNominal(g)),
                Intermediario("pl_justo", Ratio(pl_justo)),
            ),
        )
