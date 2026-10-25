"""Gordon2.0.0, ficha1.1: fluxo DVA dos controladores e desconto real.

ROE nominal sobre PL inicial; crescimento por Fisher antes do teto PIB real.
O fluxo anual está na moeda-base do fim do exercício. Sem fonte, abstém.
"""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date

from sentinela.domain.enums import AssetType, ModeloDemonstracao, Regime
from sentinela.domain.units import BRL, RateNominal, RateReal, Ratio
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)

AVISO_EVENTOS = "evento posterior ao último documento entregue não é detectado"

MOTIVO_K_NAO_MAIOR_QUE_G = "k não maior que g"
MOTIVO_NAO_FINITO = "resultado não finito"
MOTIVO_LPA_NAO_POSITIVO = "LPA não positivo"


@dataclass(frozen=True)
class GordonParams:
    """Sem parâmetro discricionário: insumos e guardas da ficha versionada."""


class Gordon(ValuationMethod):
    nome = "Gordon"
    version = "2.1.0"
    regime = Regime.REAL
    requires = (
        "preco",
        "lpa",
        "roe",
        "custo_capital_real",
        "inflacao",
        "teto_pib_real",
        "proventos_controladores",
    )
    assumptions = (
        "valor justo = D0 dos controladores × (1 + g real) ÷ (k real − g real)",
        "k real = NTN-B integral + prêmio das ações; risco Brasil já no título",
        "ROE nominal sobre PL inicial e payout DVA; Fisher antes do teto PIB real",
        "LPA positivo, DFP anual, proventos brutos e perímetro dos controladores comprovados",
        "DVA anual como aproximação do fluxo recorrente: hipótese, não prova de estabilidade futura",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    modelos = frozenset({ModeloDemonstracao.EMPRESA})
    params_type = GordonParams

    def _calcular(
        self, inputs: MethodInputs, params: GordonParams
    ) -> MethodResult | Abstention:
        def abster(motivo: str) -> Abstention:
            return Abstention(self.nome, self.version, motivo)

        proventos = inputs.proventos_controladores
        inicio, fim = proventos.inicio, proventos.fim
        if (
            inicio.day != 1
            or fim.day != calendar.monthrange(fim.year, fim.month)[1]
            or (fim.year - inicio.year) * 12 + fim.month - inicio.month != 11
        ):
            return abster("janela da DVA incompatível: exige exercício anual completo")
        if fim >= inputs.as_of:
            return abster("DVA anual futura ou ainda não disponível")
        limite_mes = fim.year * 12 + fim.month - 1 + 15
        limite = date(
            limite_mes // 12,
            limite_mes % 12 + 1,
            min(fim.day, calendar.monthrange(limite_mes // 12, limite_mes % 12 + 1)[1]),
        )
        if inputs.as_of > limite:
            return abster("DFP anual além do prazo de 15 meses")
        if inputs.preco.valor <= 0:
            return abster("preço não positivo")
        if inputs.lpa.valor <= 0:
            return abster(MOTIVO_LPA_NAO_POSITIVO)
        roe = inputs.roe.valor
        if roe <= 0:
            return abster("ROE não positivo")
        d0, payout = proventos.dividendo_anual.valor, proventos.payout.valor
        if d0 <= 0:
            return abster("distribuição não positiva")
        if not 0 < payout <= 1:
            return abster("payout fora de (0,1]")
        k, teto = inputs.custo_capital_real.valor, inputs.teto_pib_real.valor
        if k <= -1 or teto <= -1:
            return abster("taxa real sem fator positivo")
        g_nominal = roe * (1 - payout)
        g_bruto = (1 + g_nominal) / (1 + inputs.inflacao.valor) - 1
        if not math.isfinite(g_nominal) or not math.isfinite(g_bruto):
            return abster(MOTIVO_NAO_FINITO)
        if g_bruto <= -1:
            return abster("crescimento real sem fator positivo")
        g = min(g_bruto, teto)
        if not k > g:
            return abster(MOTIVO_K_NAO_MAIOR_QUE_G)
        d1 = d0 * (1 + g)
        valor = d1 / (k - g)
        if not math.isfinite(d1) or not math.isfinite(valor):
            return abster(MOTIVO_NAO_FINITO)
        if valor <= 0:
            return abster("resultado não positivo")
        return MethodResult(
            self.nome,
            self.version,
            BRL(valor),
            (
                Intermediario("d0", BRL(d0)),
                Intermediario("payout", Ratio(payout)),
                Intermediario("roe_nominal", Ratio(roe)),
                Intermediario("g_nominal_bruto", RateNominal(g_nominal)),
                Intermediario("g_real_bruto", RateReal(g_bruto)),
                Intermediario("g", RateReal(g)),
                Intermediario("teto_pib_real", RateReal(teto)),
                Intermediario("k", RateReal(k)),
                Intermediario("dividendo_proximo", BRL(d1)),
            ),
            alertas=(AVISO_EVENTOS,),
        )
