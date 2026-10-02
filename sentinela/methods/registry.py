"""Registro dos métodos de valuation: catálogo e changelog.

Fixa a 1.0.0 de cada método ao comportamento da V1. O `applies_to` é declarado, mas
não aplicado: descreve o roteamento da V1 (ações para STOCK e UNIT, FII para FII; o
classificador atual nunca devolve ETF nem BDR). Aplicar e estreitar é o F2B-4.
"""

from __future__ import annotations

from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Regime
from sentinela.methods.base import ValuationMethod
from sentinela.methods.bazin import Bazin
from sentinela.methods.fii_nav import FiiNav
from sentinela.methods.fii_yield import FiiYield
from sentinela.methods.gordon import Gordon
from sentinela.methods.graham import Graham
from sentinela.methods.lynch import Lynch

METODOS: tuple[ValuationMethod, ...] = (
    Graham(),
    Bazin(),
    Lynch(),
    Gordon(),
    FiiYield(),
    FiiNav(),
)

DESCRICAO_1_0_0 = "comportamento da V1, extraído na Fase 1, sem mudança de número"


@dataclass(frozen=True, slots=True)
class Mudanca:
    version: str
    descricao: str


@dataclass(frozen=True, slots=True)
class Entrada:
    nome: str
    version: str
    regime: Regime
    requires: tuple[str, ...]
    assumptions: tuple[str, ...]
    applies_to: frozenset[AssetType]


CHANGELOG: dict[str, tuple[Mudanca, ...]] = {
    m.nome: (Mudanca("1.0.0", DESCRICAO_1_0_0),) for m in METODOS
}


def validar(
    metodos: tuple[ValuationMethod, ...], changelog: dict[str, tuple[Mudanca, ...]]
) -> None:
    nomes = [m.nome for m in metodos]
    if len(nomes) != len(set(nomes)):
        raise ValueError("nome de método repetido no registro")
    for m in metodos:
        historico = changelog.get(m.nome)
        if not historico or historico[-1].version != m.version:
            raise ValueError(f"changelog de {m.nome} não termina na versão {m.version}")
    if set(changelog) != set(nomes):
        raise ValueError("changelog com método que não está no registro")


validar(METODOS, CHANGELOG)


def entradas() -> tuple[Entrada, ...]:
    return tuple(
        Entrada(m.nome, m.version, m.regime, m.requires, m.assumptions, m.applies_to)
        for m in METODOS
    )


def obter(nome: str) -> ValuationMethod:
    for m in METODOS:
        if m.nome == nome:
            return m
    raise KeyError(nome)
