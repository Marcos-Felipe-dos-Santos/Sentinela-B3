"""Bazin 1.0.0: comportamento da V1, extraído na Fase 1, sem mudança de número.

Valor justo = (DY × preço) ÷ taxa mínima, com taxa mínima = máx(Selic, piso). Só no
perfil renda, com DY confiável e a partir de um DY mínimo. O DY acima do limite de
armadilha não tira o método: vira alerta do resultado.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import BRL, RateNominal
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

ALERTA_DY_ARMADILHA = "DY muito alto (possível armadilha)"
MOTIVO_PERFIL_CRESCIMENTO = "perfil crescimento"
MOTIVO_DY_NAO_CONFIAVEL = "DY não confiável"
MOTIVO_DY_ABAIXO_DO_MINIMO = "DY abaixo do mínimo"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class BazinParams:
    dy_min: float
    dy_armadilha: float
    taxa_min: float


class Bazin(ValuationMethod):
    nome = "Bazin"
    version = "1.0.0"
    regime = Regime.NOMINAL
    requires = ("preco", "dy", "selic", "perfil")
    assumptions = (
        "valor justo = DY × preço ÷ taxa mínima",
        "taxa mínima = máximo entre a Selic e um piso",
        "só para o perfil renda, com DY confiável e DY mínimo",
        "DY acima do limite de armadilha mantém o método e gera alerta",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    params_type = BazinParams

    def _calcular(
        self, inputs: MethodInputs, params: BazinParams
    ) -> MethodResult | Abstention:
        if inputs.perfil is Perfil.CRESCIMENTO:
            return Abstention(self.nome, self.version, MOTIVO_PERFIL_CRESCIMENTO)
        dy = inputs.dy.valor
        if not dy >= params.dy_min:
            return Abstention(self.nome, self.version, MOTIVO_DY_ABAIXO_DO_MINIMO)
        if not inputs.dy_confiavel:
            return Abstention(self.nome, self.version, MOTIVO_DY_NAO_CONFIAVEL)
        alertas = (ALERTA_DY_ARMADILHA,) if dy > params.dy_armadilha else ()
        taxa_minima = max(inputs.selic.valor, params.taxa_min)
        valor = (dy * inputs.preco.valor) / taxa_minima
        if not math.isfinite(valor):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(valor),
            intermediarios=(Intermediario("taxa_aplicada", RateNominal(taxa_minima)),),
            alertas=alertas,
        )
