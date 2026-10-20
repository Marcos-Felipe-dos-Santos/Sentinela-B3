"""Bazin 2.0.0: critério de rendimento mínimo de 6% fixos (F2B-31; ficha Bazin 1.0).

Preço-limite do critério = D_bruto_12m ÷ 0,06 = DY × preço ÷ 0,06; os 6% são constante da
versão (`TAXA_CRITERIO`), não parâmetro: mudar a taxa é versão nova. É critério de rendimento
mínimo nominal, não avaliação por desconto: a Selic não entra (F-5). O DY é o bruto de 12
meses pela relação de proventos da B3, montado pelo motor (`sentinela.data.proventos_b3`).
Gate de DY de 5% e alerta acima de 15% ficam; o DY acima de 25% chega não confiável.
Prejuízo (LPA negativo) com DY positivo é elegível, com aviso.

2.0.0 (F2B-31): sai a taxa máx(Selic, piso) e o `requires` da Selic; entra o critério fixo.
1.0.1 (F2A-21): "DY não confiável" é testado antes do DY mínimo.
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

TAXA_CRITERIO = 0.06
ALERTA_DY_ARMADILHA = "DY muito alto (possível armadilha)"
AVISO_PREJUIZO = "prejuízo no exercício; rendimento passado não demonstra sustentabilidade"
MOTIVO_PERFIL_CRESCIMENTO = "perfil crescimento"
MOTIVO_DY_NAO_CONFIAVEL = "DY não confiável"
MOTIVO_DY_ABAIXO_DO_MINIMO = "DY abaixo do mínimo"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class BazinParams:
    dy_min: float
    dy_armadilha: float


class Bazin(ValuationMethod):
    nome = "Bazin"
    version = "2.0.0"
    regime = Regime.NOMINAL
    requires = ("preco", "dy", "perfil")
    assumptions = (
        "preço-limite do critério = DY bruto de 12 meses × preço ÷ 6%",
        "critério de rendimento mínimo nominal, não avaliação por desconto",
        "DY bruto de dividendos e JCP por data ex, pela relação de proventos da B3",
        "só para o perfil renda, com DY confiável e DY mínimo",
        "DY acima do limite de armadilha mantém o método e gera alerta",
        "prejuízo com DY positivo mantém o método e gera aviso",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    params_type = BazinParams

    def _calcular(
        self, inputs: MethodInputs, params: BazinParams
    ) -> MethodResult | Abstention:
        if inputs.perfil is Perfil.CRESCIMENTO:
            return Abstention(self.nome, self.version, MOTIVO_PERFIL_CRESCIMENTO)
        if not inputs.dy_confiavel:
            return Abstention(self.nome, self.version, MOTIVO_DY_NAO_CONFIAVEL)
        dy = inputs.dy.valor
        if not dy >= params.dy_min:
            return Abstention(self.nome, self.version, MOTIVO_DY_ABAIXO_DO_MINIMO)
        alertas = (ALERTA_DY_ARMADILHA,) if dy > params.dy_armadilha else ()
        if inputs.lpa is not None and inputs.lpa.valor < 0:
            alertas += (AVISO_PREJUIZO,)
        valor = (dy * inputs.preco.valor) / TAXA_CRITERIO
        if not math.isfinite(valor):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(valor),
            intermediarios=(
                Intermediario("taxa_aplicada", RateNominal(TAXA_CRITERIO)),
                Intermediario("relacao_ao_criterio", Ratio(dy / TAXA_CRITERIO - 1)),
            ),
            alertas=alertas,
        )
