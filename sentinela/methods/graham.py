"""Graham 1.0.0: comportamento da V1, extraído na Fase 1, sem mudança de número.

Valor justo = raiz de 22,5 × LPA ajustado × VPA, com piso no P/L, limite de P/L e
limite de P/VP pelo perfil. Não usa taxa de desconto.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import BRL, Ratio
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

FATOR_GRAHAM = 22.5
MOTIVO_PL_NAO_CONFIAVEL = "P/L não confiável"
MOTIVO_NAO_POSITIVO = "P/L ou P/VP não positivo"
MOTIVO_PL_ACIMA = "P/L acima do limite"
MOTIVO_PVP_ACIMA = "P/VP acima do limite"
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class GrahamParams:
    pl_limite: float
    pl_piso: float
    pvp_limite_renda: float
    pvp_limite_crescimento: float


class Graham(ValuationMethod):
    nome = "Graham"
    version = "1.0.0"
    regime = Regime.SEM_TAXA
    requires = ("preco", "pl", "pvp", "vpa", "perfil")
    assumptions = (
        "valor justo = raiz de 22,5 × LPA ajustado × VPA",
        "o P/L usado no LPA ajustado tem piso (empresas cíclicas)",
        "P/L não confiável (negativo ou atípico) tira o método",
        "limite de P/VP maior para o perfil crescimento",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    params_type = GrahamParams

    def _calcular(
        self, inputs: MethodInputs, params: GrahamParams
    ) -> MethodResult | Abstention:
        if not inputs.pl_confiavel:
            return Abstention(self.nome, self.version, MOTIVO_PL_NAO_CONFIAVEL)
        pl, pvp = inputs.pl.valor, inputs.pvp.valor
        if not (pl > 0 and pvp > 0):
            return Abstention(self.nome, self.version, MOTIVO_NAO_POSITIVO)
        if pl > params.pl_limite:
            return Abstention(self.nome, self.version, MOTIVO_PL_ACIMA)
        limite_pvp = (
            params.pvp_limite_crescimento
            if inputs.perfil is Perfil.CRESCIMENTO
            else params.pvp_limite_renda
        )
        if pvp > limite_pvp:
            return Abstention(self.nome, self.version, MOTIVO_PVP_ACIMA)
        pl_graham = max(pl, params.pl_piso)
        lpa_ajustado = inputs.preco.valor / pl_graham
        valor = (FATOR_GRAHAM * lpa_ajustado * inputs.vpa.valor) ** 0.5
        if not math.isfinite(valor):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(valor),
            intermediarios=(
                Intermediario("lpa_ajustado", BRL(lpa_ajustado)),
                Intermediario("pl_aplicado", Ratio(pl_graham)),
            ),
        )
