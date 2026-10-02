"""Lente de P/VP do FII 1.0.0: comportamento da V1, extraído na Fase 1.

Na V1 o patrimônio não forma valor justo: o P/VP só pesa no score. Esta lente devolve o
P/VP e a faixa (prêmio alto, prêmio moderado, desconto ou neutra, esta sem alerta); a
conversão da faixa em pontos de score fica no motor. Não usa taxa de desconto.
"""

from __future__ import annotations

from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Regime
from sentinela.methods.base import MethodInputs, MethodResult, ValuationMethod

FAIXA_PREMIO_ALTO = "prêmio alto sobre o patrimônio"
FAIXA_PREMIO_MODERADO = "prêmio moderado sobre o patrimônio"
FAIXA_DESCONTO = "desconto sobre o patrimônio"


@dataclass(frozen=True)
class FiiNavParams:
    premio_alto: float
    premio_moderado: float
    desconto: float


class FiiNav(ValuationMethod):
    nome = "P/VP do FII"
    version = "1.0.0"
    regime = Regime.SEM_TAXA
    requires = ("pvp",)
    assumptions = (
        "o patrimônio não forma valor justo na V1: o P/VP só pesa no score",
        "faixas pelo P/VP: prêmio alto, prêmio moderado, desconto ou neutra (limites estritos)",
    )
    applies_to = frozenset({AssetType.FII})
    params_type = FiiNavParams

    def _calcular(self, inputs: MethodInputs, params: FiiNavParams) -> MethodResult:
        pvp = inputs.pvp.valor
        if pvp > params.premio_alto:
            alertas: tuple[str, ...] = (FAIXA_PREMIO_ALTO,)
        elif pvp > params.premio_moderado:
            alertas = (FAIXA_PREMIO_MODERADO,)
        elif pvp < params.desconto:
            alertas = (FAIXA_DESCONTO,)
        else:
            alertas = ()
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=inputs.pvp,
            alertas=alertas,
        )
