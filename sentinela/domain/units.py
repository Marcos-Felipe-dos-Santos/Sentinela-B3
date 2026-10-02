"""Tipos de unidade do domínio: dinheiro, razões, taxas e quantidade de ações.

Imutáveis, rejeitam NaN e infinito na construção, e só somam com o mesmo tipo
(taxa real e nominal nunca se misturam). Conversões são explícitas. A conversão
real ↔ nominal não existe aqui de propósito: depende da decisão da inflação (F2B-1).
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


@dataclass(frozen=True, slots=True)
class RateReal(_Escalar):
    """Taxa real anual (descontada a inflação), em decimal."""


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
