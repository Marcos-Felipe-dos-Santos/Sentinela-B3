"""Tipos de unidade do domínio: dinheiro, razões, taxas e quantidade de ações.

Imutáveis, rejeitam NaN e infinito na construção, e só somam com o mesmo tipo
(taxa real e nominal nunca se misturam). Conversões são explícitas. Fisher exato e a conversão
dos fluxos seguem a ficha taxa-real 1.0, com inflação explícita da mesma janela.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Escala(Enum):
    """Escala em que a quantidade de ações foi informada no documento."""

    UNIDADE = 1
    MIL = 1000

    @property
    def fator(self) -> int:
        return self.value


def _finito(valor: float) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError(f"valor deve ser um número, não {type(valor).__name__}")
    if not math.isfinite(valor):
        raise ValueError(f"valor deve ser finito, recebido {valor!r}")
    return float(valor)


@dataclass(frozen=True, slots=True)
class _Escalar:
    valor: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "valor", _finito(self.valor))

    def __add__(self, outro: object) -> _Escalar:
        if type(outro) is not type(self):
            return NotImplemented
        return type(self)(self.valor + outro.valor)

    def __sub__(self, outro: object) -> _Escalar:
        if type(outro) is not type(self):
            return NotImplemented
        return type(self)(self.valor - outro.valor)


@dataclass(frozen=True, slots=True)
class BRL(_Escalar):
    """Valor monetário em reais."""


@dataclass(frozen=True, slots=True)
class Ratio(_Escalar):
    """Razão decimal (0,125 = 12,5%)."""

    def para_percent(self) -> Percent:
        return Percent(self.valor * 100)


@dataclass(frozen=True, slots=True)
class Percent(_Escalar):
    """Percentual (12,5 = 12,5%)."""

    def para_ratio(self) -> Ratio:
        return Ratio(self.valor / 100)


@dataclass(frozen=True, slots=True)
class RateNominal(_Escalar):
    """Taxa nominal anual, em decimal."""

    def para_real(self, inflacao: Inflacao) -> RateReal:
        """Fisher exato: (1 + nominal)/(1 + inflação) − 1."""
        valor = _fator_positivo(self.valor) / _fator_inflacao(inflacao) - 1
        _fator_positivo(valor)
        return RateReal(valor)


@dataclass(frozen=True, slots=True)
class RateReal(_Escalar):
    """Taxa real anual (descontada a inflação), em decimal."""

    def para_nominal(self, inflacao: Inflacao) -> RateNominal:
        """Fisher exato: (1 + real)(1 + inflação) − 1."""
        valor = _fator_positivo(self.valor) * _fator_inflacao(inflacao) - 1
        _fator_positivo(valor)
        return RateNominal(valor)


@dataclass(frozen=True, slots=True)
class Inflacao(_Escalar):
    """Variação de preços da janela anual convertida; razão, admitindo deflação."""

    def __post_init__(self) -> None:
        _Escalar.__post_init__(self)
        _fator_positivo(self.valor)


def _fator_positivo(valor: float) -> float:
    valor = _finito(valor)
    if valor <= -1:
        raise ValueError("taxa exige fator positivo (valor > −1)")
    return 1 + valor


def _fator_inflacao(inflacao: Inflacao) -> float:
    if not isinstance(inflacao, Inflacao):
        raise TypeError("inflacao deve ser Inflacao")
    return 1 + inflacao.valor


def _fator_fluxo(fluxo: BRL, inflacao: Inflacao, t: float) -> float:
    if not isinstance(fluxo, BRL):
        raise TypeError("fluxo deve ser BRL")
    fator = _fator_inflacao(inflacao)
    t = _finito(t)
    try:
        potencia = _finito(fator**t)
    except OverflowError as erro:
        raise ValueError("fator do fluxo não finito") from erro
    if potencia == 0:
        raise ValueError("fator do fluxo perdeu precisão para zero")
    return potencia


def fluxo_nominal(fluxo: BRL, inflacao: Inflacao, t: float) -> BRL:
    """CF nominal,t = CF real,t × (1 + π)^t, em BRL de t.

    O fluxo real está em BRL da moeda-base em t=0; t mede anos relativos a essa
    base, e π é a inflação anual constante do cenário na janela convertida.
    A função converte representação, sem julgar elegibilidade do fluxo.
    """
    fator = _fator_fluxo(fluxo, inflacao, t)
    return BRL(fluxo.valor * fator)


def fluxo_real(fluxo: BRL, inflacao: Inflacao, t: float) -> BRL:
    """Inversa: traz BRL nominais de t para a moeda-base em t=0."""
    fator = _fator_fluxo(fluxo, inflacao, t)
    return BRL(fluxo.valor / fator)


@dataclass(frozen=True, slots=True)
class QuantidadeAcoes:
    """Quantidade de ações com a escala do documento sempre informada (armadilha 10)."""

    valor: float
    escala: Escala

    def __post_init__(self) -> None:
        if not isinstance(self.escala, Escala):
            raise TypeError(f"escala deve ser Escala, não {type(self.escala).__name__}")
        object.__setattr__(self, "valor", _finito(self.valor))

    def em_unidades(self) -> QuantidadeAcoes:
        return QuantidadeAcoes(self.valor * self.escala.fator, Escala.UNIDADE)

    def __add__(self, outro: object) -> QuantidadeAcoes:
        if not isinstance(outro, QuantidadeAcoes):
            return NotImplemented
        self._exigir_mesma_escala(outro)
        return QuantidadeAcoes(self.valor + outro.valor, self.escala)

    def __sub__(self, outro: object) -> QuantidadeAcoes:
        if not isinstance(outro, QuantidadeAcoes):
            return NotImplemented
        self._exigir_mesma_escala(outro)
        return QuantidadeAcoes(self.valor - outro.valor, self.escala)

    def _exigir_mesma_escala(self, outro: QuantidadeAcoes) -> None:
        if outro.escala is not self.escala:
            raise TypeError(
                f"escala diferente: {self.escala.name} e {outro.escala.name}"
            )
