"""Graham2.0: LPA médio normalizado aprovado, VPA final, sem piso/guardas legadas."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Regime
from sentinela.domain.units import BRL
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

FATOR_GRAHAM = 22.5
MOTIVO_NAO_FINITO = "resultado não finito"


@dataclass(frozen=True)
class GrahamParams:
    """Sem parâmetros ajustáveis;22,5 faz parte da versão aprovada."""


class Graham(ValuationMethod):
    nome = "Graham"
    version = "2.1.0"
    regime = Regime.SEM_TAXA
    requires = ("lpa", "vpa")
    assumptions = (
        "reorganização societária no período não é detectada",
        "LPA médio de cinco exercícios, corrigido por IPCA de fim de exercício",
        "VPA do último documento; base documental compatível ou fator oficial B3",
        "raiz de 22,5 × LPA médio × VPA, sem reconstrução por múltiplos",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    modelos = frozenset({ModeloDemonstracao.EMPRESA})
    params_type = GrahamParams

    def _calcular(
        self, inputs: MethodInputs, params: GrahamParams
    ) -> MethodResult | Abstention:
        lpa, vpa = inputs.lpa.valor, inputs.vpa.valor
        if vpa <= 0:
            return Abstention(self.nome, self.version, "VPA ≤ 0")
        if lpa <= 0:
            return Abstention(self.nome, self.version, "LPA médio ≤ 0")
        valor = math.sqrt(FATOR_GRAHAM * lpa) * math.sqrt(vpa)
        if not math.isfinite(valor):
            return Abstention(self.nome, self.version, MOTIVO_NAO_FINITO)
        return MethodResult(
            metodo=self.nome,
            versao=self.version,
            valor=BRL(valor),
            intermediarios=(
                Intermediario("lpa_medio_normalizado", inputs.lpa),
                Intermediario("vpa_final", inputs.vpa),
            ),
        )
