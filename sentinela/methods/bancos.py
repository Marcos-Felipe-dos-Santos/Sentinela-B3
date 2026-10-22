"""Lente bancária da ficha 1.1: múltiplo justificado em regime real, sem I/O."""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date

from sentinela.domain.enums import (
    AssetType,
    DocumentoContabil,
    ModeloDemonstracao,
    Regime,
)
from sentinela.domain.units import BRL, RateNominal, RateReal, Ratio
from sentinela.methods.base import (
    Abstention,
    Intermediario,
    MethodInputs,
    MethodResult,
    ValuationMethod,
)


@dataclass(frozen=True)
class BancosParams:
    """Sem parâmetro próprio: taxa e teto são insumos explícitos."""


class Bancos(ValuationMethod):
    nome = "Bancos"
    version = "1.0.0"
    regime = Regime.REAL
    requires = (
        "classe_ativo",
        "modelo",
        "documento_contabil",
        "base_acionaria_compativel",
        "lucro_anual_controladores",
        "pl_inicial_controladores",
        "vpa",
        "proventos_controladores",
        "custo_capital_real",
        "inflacao",
        "teto_pib_real",
    )
    assumptions = (
        "P/VP justificado = (ROE real − g real) / (k real − g real)",
        "ROE nominal sobre PL inicial dos controladores, persistência como hipótese",
        "VPA CVM final por ação ou unit, com base compatível comprovada na fronteira",
        "payout DVA bruto dos controladores, anual; Fisher antes do teto real PIB",
        "teto altera payout projetado, sem alterar o observado",
    )
    applies_to = frozenset({AssetType.STOCK, AssetType.UNIT})
    modelos = frozenset({ModeloDemonstracao.BANCO})
    params_type = BancosParams

    def _calcular(
        self, inputs: MethodInputs, params: BancosParams
    ) -> MethodResult | Abstention:
        def abster(motivo: str) -> Abstention:
            return Abstention(self.nome, self.version, motivo)

        if inputs.classe_ativo not in self.applies_to:
            return abster(
                f"classe {inputs.classe_ativo.value} fora do escopo do método"
            )
        if inputs.modelo not in self.modelos:
            return abster(f"modelo {inputs.modelo.value} fora do escopo do método")
        if inputs.documento_contabil is not DocumentoContabil.DFP:
            return abster("exige DFP anual, não ITR")
        if not inputs.base_acionaria_compativel:
            return abster("base de ações incompatível ou sem evidência vigente")
        f = inputs.proventos_controladores
        inicio, fim = f.inicio, f.fim
        if (
            inicio.day != 1
            or fim.day != calendar.monthrange(fim.year, fim.month)[1]
            or (fim.year - inicio.year) * 12 + fim.month - inicio.month != 11
        ):
            return abster("janela da DVA incompatível: exige DFP anual completa")
        if fim >= inputs.as_of:
            return abster("DFP anual futura ou ainda não disponível")
        limite_mes = fim.year * 12 + fim.month - 1 + 15
        limite = date(
            limite_mes // 12,
            limite_mes % 12 + 1,
            min(fim.day, calendar.monthrange(limite_mes // 12, limite_mes % 12 + 1)[1]),
        )
        if inputs.as_of > limite:
            return abster("DFP anual além do prazo de 15 meses")
        lucro = inputs.lucro_anual_controladores.valor
        pl_inicial = inputs.pl_inicial_controladores.valor
        if lucro <= 0:
            return abster("lucro anual não positivo: prejuízo ou zero")
        if pl_inicial <= 0:
            return abster("PL inicial dos controladores não positivo")
        vpa = inputs.vpa.valor
        if vpa <= 0:
            return abster("VPA CVM não positivo")
        payout = f.payout.valor
        if not 0 < payout <= 1:
            return abster("payout fora de (0,1]")
        if f.dividendo_anual.valor <= 0:
            return abster("distribuição anual não positiva")
        roe_n = lucro / pl_inicial
        if not math.isfinite(roe_n):
            return abster("resultado não finito antes do teto")
        if roe_n <= 0:
            return abster("ROE nominal não positivo")
        inflacao = inputs.inflacao.valor
        fator = 1 + inflacao
        k, teto = inputs.custo_capital_real.valor, inputs.teto_pib_real.valor
        if k <= -1 or teto <= -1:
            return abster("taxa real sem fator positivo")
        g_n_bruto = roe_n * (1 - payout)
        roe_r = (1 + roe_n) / fator - 1
        g_r_bruto = (1 + g_n_bruto) / fator - 1
        if not all(math.isfinite(v) for v in (roe_n, roe_r, g_n_bruto, g_r_bruto)):
            return abster("resultado não finito antes do teto")
        if g_r_bruto <= -1:
            return abster("crescimento real sem fator positivo")
        g = min(g_r_bruto, teto)
        if g >= roe_r:
            return abster("g >= ROE real")
        if k <= g:
            return abster("k real não maior que g real")
        teto_atuou = g < g_r_bruto
        g_n = (1 + g) * fator - 1 if teto_atuou else g_n_bruto
        p_projetado = 1 - g_n / roe_n if teto_atuou else payout
        if not math.isfinite(p_projetado) or not 0 < p_projetado <= 1:
            return abster("payout projetado incompatível fora de (0,1]")
        multiplo = (roe_r - g) / (k - g)
        valor = multiplo * vpa
        d1_n = (roe_n - g_n) * vpa
        d1_r = d1_n / fator
        k_n = (1 + k) * fator - 1
        if not all(math.isfinite(v) for v in (g_n, multiplo, valor, d1_n, d1_r, k_n)):
            return abster("resultado não finito")
        if valor <= 0 or d1_r <= 0:
            return abster("resultado não positivo")
        intermediarios = (
            Intermediario("roe_nominal", Ratio(roe_n)),
            Intermediario("roe_real", RateReal(roe_r)),
            Intermediario("g_nominal_bruto", RateNominal(g_n_bruto)),
            Intermediario("g_real_bruto", RateReal(g_r_bruto)),
            Intermediario("g_real", RateReal(g)),
            Intermediario("g_nominal_efetivo", RateNominal(g_n)),
            Intermediario("k_real", RateReal(k)),
            Intermediario("k_nominal", RateNominal(k_n)),
            Intermediario("payout_observado", Ratio(payout)),
            Intermediario("payout_projetado", Ratio(p_projetado)),
            Intermediario("pvp_justificado", Ratio(multiplo)),
            Intermediario("vpa", BRL(vpa)),
            Intermediario("d1_nominal", BRL(d1_n)),
            Intermediario("d1_real", BRL(d1_r)),
        )
        alertas = ["evento posterior ao último documento entregue não é detectado"]
        if teto_atuou:
            alertas.append(
                "teto PIB altera retenção e payout projetados; observado preservado"
            )
        if inputs.preco is not None and inputs.preco.valor > 0:
            mercado = inputs.preco.valor / vpa
            if math.isfinite(mercado):
                intermediarios += (Intermediario("pvp_mercado", Ratio(mercado)),)
            else:
                alertas.append("P/VP de mercado não informado: resultado não finito")
        else:
            alertas.append(
                "P/VP de mercado não informado: preço ausente ou não positivo"
            )
        return MethodResult(
            self.nome, self.version, BRL(valor), intermediarios, tuple(alertas)
        )
