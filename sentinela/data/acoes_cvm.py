"""Valores por ação a partir da Composição do Capital da CVM (F2A-3, E-1, armadilhas 3 e 10).

Funções puras: sem rede, sem banco, sem relógio.

- **Ações:** ON + PN − tesouraria, da Composição do Capital do **mesmo documento** do lucro e
  do PL (mesmo CNPJ, `DT_REFER` e `VERSAO`). São as ações do fim do período; o LPA divulgado
  usa a média ponderada do exercício.
- **Escala** (armadilha 10): o CSV não a traz. Vale a (unidade ou mil) que deixa
  (lucro ÷ ações) ÷ LPA básico divulgado mais perto de 1. Fora de `FAIXA_DA_ESCALA`, a escala
  fica indeterminada (o F2A-16 mediu 250 de 255 empresas dentro dessa faixa; as duas hipóteses
  só se confundem perto de 31,6, a raiz de 1.000).
- **Lucro e PL:** os atribuídos aos controladores (CPC 41).
- **Unit:** LPA e VPA multiplicados pelas ações por unit do índice oficial.

Sem insumo, abstém-se com o motivo; nunca devolve número conservador.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sentinela.domain.units import Escala, QuantidadeAcoes

FAIXA_DA_ESCALA = (0.1, 10.0)

MOTIVO_SEM_COMPOSICAO = "sem Composição do Capital no documento do lucro"
MOTIVO_DOCUMENTO_DIFERENTE = (
    "Composição do Capital de documento diferente do lucro (outra data ou versão)"
)
MOTIVO_ESCALA = "escala das ações indeterminada"
MOTIVO_TOTAL = "total de ações da Composição do Capital ≤ 0"
MOTIVO_UNIT = "unit sem composição oficial (ações por unit)"
MOTIVO_ROE_PL = "PL dos controladores ≤ 0"
MOTIVO_ROE_SEM_PL = "PL dos controladores não identificado no documento"
MOTIVO_ROE_SEM_LUCRO = "lucro dos controladores não identificado no documento"
NOTA_FIM_DO_PERIODO = (
    "ações do fim do período (Composição do Capital); o LPA divulgado usa a média "
    "ponderada do exercício"
)


@dataclass(frozen=True)
class Composicao:
    """Linha da Composição do Capital, na escala do documento (desconhecida)."""

    on: float
    pn: float
    tesouraria_on: float
    tesouraria_pn: float
    tesouraria_total: float
    dt_refer: str
    versao: str

    @property
    def total(self) -> float:
        return self.on + self.pn - self.tesouraria_total


@dataclass(frozen=True)
class PorAcao:
    acoes: QuantidadeAcoes
    escala: Escala
    razao_lpa: float | None
    lpa: float | None
    vpa: float | None
    pl: float | None
    pvp: float | None

    def detalhe(self, documento: dict) -> dict:
        return {
            "documento": documento,
            "escala": self.escala.name,
            "acoes": self.acoes.valor,
            "razao_lpa_calculado_sobre_divulgado": self.razao_lpa,
            "nota": NOTA_FIM_DO_PERIODO,
        }


@dataclass(frozen=True)
class Abstencao:
    motivo: str


def inferir_escala(
    lucro: float | None, acoes: float, lpa_divulgado: float | None
) -> tuple[Escala, float] | None:
    """(escala, razão calculado ÷ divulgado) ou `None` se indeterminada.

    Lucro e LPA precisam de valor e do mesmo sinal (prejuízo com LPA negativo também serve).
    """
    if not lucro or not lpa_divulgado or acoes <= 0:
        return None
    if (lucro > 0) != (lpa_divulgado > 0):
        return None
    melhor = min(
        Escala,
        key=lambda e: abs(math.log(lucro / (acoes * e.fator) / lpa_divulgado)),
    )
    razao = lucro / (acoes * melhor.fator) / lpa_divulgado
    if not FAIXA_DA_ESCALA[0] <= razao <= FAIXA_DA_ESCALA[1]:
        return None
    return melhor, razao


def _dividir(numerador: float | None, denominador: float | None) -> float | None:
    if numerador is None or not denominador:
        return None
    return numerador / denominador


def derivar_por_acao(
    *,
    lucro_controladores: float | None,
    pl_controladores: float | None,
    composicao: Composicao | None,
    motivo_composicao: str | None,
    lpa_divulgado: float | None,
    preco: float | None,
    eh_unit: bool,
    acoes_por_unit: dict | None,
) -> PorAcao | Abstencao:
    """LPA, VPA, P/L e P/VP da CVM; abstém-se só quando a própria CVM falha."""
    if composicao is None:
        return Abstencao(motivo_composicao or MOTIVO_SEM_COMPOSICAO)
    if eh_unit and not acoes_por_unit:
        return Abstencao(MOTIVO_UNIT)
    if composicao.total <= 0:
        return Abstencao(MOTIVO_TOTAL)
    inferida = inferir_escala(lucro_controladores, composicao.total, lpa_divulgado)
    if inferida is None:
        return Abstencao(MOTIVO_ESCALA)
    escala, razao = inferida
    acoes = QuantidadeAcoes(composicao.total, escala).em_unidades()
    fator = sum(acoes_por_unit.values()) if eh_unit else 1
    lpa = _dividir(lucro_controladores, acoes.valor)
    vpa = _dividir(pl_controladores, acoes.valor)
    lpa = lpa * fator if lpa is not None else None
    vpa = vpa * fator if vpa is not None else None
    preco_valido = preco if preco and preco > 0 else None
    return PorAcao(
        acoes=acoes,
        escala=escala,
        razao_lpa=razao,
        lpa=lpa,
        vpa=vpa,
        pl=_dividir(preco_valido, lpa),
        pvp=_dividir(preco_valido, vpa),
    )


def divergencia_acoes(
    composicao: Composicao,
    escala: Escala,
    *,
    especie: str | None,
    eh_unit: bool,
    acoes_por_unit: dict | None,
    shares_outstanding: float | None,
) -> dict | None:
    """Ações da espécie do ticker na CVM × `sharesOutstanding` do yfinance (alerta, não abstenção).

    Ação ON: ON − tesouraria ON; ação PN: PN − tesouraria PN; unit: total ÷ ações por unit.
    `None` se falta a espécie ou o número do yfinance.
    """
    if not shares_outstanding or shares_outstanding <= 0:
        return None
    if eh_unit:
        if not acoes_por_unit:
            return None
        bruto, rotulo = composicao.total / sum(acoes_por_unit.values()), "UNIT"
    elif especie == "ON":
        bruto, rotulo = composicao.on - composicao.tesouraria_on, "ON"
    elif especie == "PN":
        bruto, rotulo = composicao.pn - composicao.tesouraria_pn, "PN"
    else:
        return None
    cvm = QuantidadeAcoes(bruto, escala).em_unidades().valor
    if cvm <= 0:
        return None
    return {
        "especie": rotulo,
        "acoes_cvm": cvm,
        "acoes_yfinance": float(shares_outstanding),
        "diferenca": shares_outstanding / cvm - 1,
    }


def roe_dos_controladores(
    lucro_controladores: float | None, pl_controladores: float | None
) -> tuple[float | None, str | None]:
    """(ROE, motivo da abstenção). Com PL ≤ 0, lucro negativo daria ROE positivo: abstém-se."""
    if lucro_controladores is None:
        return None, MOTIVO_ROE_SEM_LUCRO
    if pl_controladores is None:
        return None, MOTIVO_ROE_SEM_PL
    if pl_controladores <= 0:
        return None, MOTIVO_ROE_PL
    return lucro_controladores / pl_controladores, None
