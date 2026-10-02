"""Contrato dos métodos de valuation.

`MethodInputs` é congelado e carrega `as_of`. Todo método declara `nome`, `version`,
`regime`, `requires`, `assumptions`, `applies_to` e `params_type`, e devolve
`MethodResult` ou `Abstention`: sem insumo exigido, abstém-se, nunca devolve um
número conservador. Os parâmetros entram como argumento explícito (dataclass
congelada, sem valor padrão); os métodos não importam `config`.
"""

from __future__ import annotations

import dataclasses
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sentinela.domain.enums import AssetType, Perfil, Regime
from sentinela.domain.units import (
    BRL,
    Percent,
    QuantidadeAcoes,
    RateNominal,
    RateReal,
    Ratio,
)

TIPO_TAXA: dict[Regime, type | None] = {
    Regime.REAL: RateReal,
    Regime.NOMINAL: RateNominal,
    Regime.SEM_TAXA: None,
}

_UNIDADES = (BRL, Ratio, Percent, RateNominal, RateReal, QuantidadeAcoes)
_TIPOS_CAMPOS: dict[str, type] = {
    "preco": BRL,
    "lpa": BRL,
    "vpa": BRL,
    "pl": Ratio,
    "pvp": Ratio,
    "dy": Ratio,
    "roe": Ratio,
    "selic": RateNominal,
    "vacancia": Ratio,
    "perfil": Perfil,
}
_FLAGS = ("pl_confiavel", "dy_confiavel", "erro_scraper")
_VERSAO = re.compile(r"\d+\.\d+\.\d+")


@dataclass(frozen=True, slots=True)
class MethodInputs:
    as_of: date
    preco: BRL | None = None
    lpa: BRL | None = None
    vpa: BRL | None = None
    pl: Ratio | None = None
    pvp: Ratio | None = None
    dy: Ratio | None = None
    roe: Ratio | None = None
    selic: RateNominal | None = None
    vacancia: Ratio | None = None
    perfil: Perfil | None = None
    pl_confiavel: bool = True
    dy_confiavel: bool = True
    erro_scraper: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.as_of, date) or isinstance(self.as_of, datetime):
            raise TypeError(f"as_of deve ser date, não {type(self.as_of).__name__}")
        for campo, tipo in _TIPOS_CAMPOS.items():
            valor = getattr(self, campo)
            if valor is not None and not isinstance(valor, tipo):
                raise TypeError(
                    f"{campo} deve ser {tipo.__name__}, não {type(valor).__name__}"
                )
        for campo in _FLAGS:
            if not isinstance(getattr(self, campo), bool):
                raise TypeError(f"{campo} deve ser bool")


@dataclass(frozen=True, slots=True)
class Intermediario:
    """Valor intermediário nomeado de um cálculo."""

    nome: str
    valor: Any

    def __post_init__(self) -> None:
        if not isinstance(self.nome, str) or not self.nome:
            raise ValueError("nome do intermediário não pode ser vazio")
        numero = isinstance(self.valor, (int, float)) and not isinstance(
            self.valor, bool
        )
        if not (numero or isinstance(self.valor, _UNIDADES)):
            raise TypeError(
                f"valor do intermediário deve ser número ou unidade, não {type(self.valor).__name__}"
            )


@dataclass(frozen=True, slots=True)
class MethodResult:
    metodo: str
    versao: str
    valor: Any
    intermediarios: tuple[Intermediario, ...] = ()
    alertas: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.valor, _UNIDADES):
            raise TypeError(f"valor deve ter unidade, não {type(self.valor).__name__}")
        object.__setattr__(self, "intermediarios", tuple(self.intermediarios))
        object.__setattr__(self, "alertas", tuple(self.alertas))
        if not all(isinstance(i, Intermediario) for i in self.intermediarios):
            raise TypeError("intermediarios devem ser Intermediario")

    def obter(self, nome: str) -> Any:
        for item in self.intermediarios:
            if item.nome == nome:
                return item.valor
        raise KeyError(nome)


@dataclass(frozen=True, slots=True)
class Abstention:
    metodo: str
    versao: str
    motivo: str

    def __post_init__(self) -> None:
        if not isinstance(self.motivo, str) or not self.motivo.strip():
            raise ValueError("motivo da abstenção não pode ser vazio")


def _validar_params_type(tipo: Any) -> None:
    if not (isinstance(tipo, type) and dataclasses.is_dataclass(tipo)):
        raise TypeError("params_type deve ser uma dataclass")
    if not tipo.__dataclass_params__.frozen:
        raise TypeError("params_type deve ser uma dataclass congelada")
    com_padrao = [
        f.name
        for f in dataclasses.fields(tipo)
        if f.default is not dataclasses.MISSING
        or f.default_factory is not dataclasses.MISSING
    ]
    if com_padrao:
        raise TypeError(
            f"params_type: campos devem ficar sem valor padrão ({com_padrao})"
        )


class ValuationMethod(ABC):
    nome: str
    version: str
    regime: Regime
    requires: tuple[str, ...]
    assumptions: tuple[str, ...]
    applies_to: frozenset[AssetType]
    params_type: type

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "calcular" in cls.__dict__:
            raise TypeError("calcular não pode ser sobrescrito: implemente _calcular")
        for campo in (
            "nome",
            "version",
            "regime",
            "requires",
            "assumptions",
            "applies_to",
            "params_type",
        ):
            if getattr(cls, campo, None) is None:
                raise TypeError(f"{campo} é obrigatório na declaração do método")
        if not isinstance(cls.nome, str) or not cls.nome:
            raise TypeError("nome deve ser texto não vazio")
        if not isinstance(cls.version, str) or not _VERSAO.fullmatch(cls.version):
            raise TypeError(
                f"version deve ser MAJOR.MINOR.PATCH, recebido {cls.version!r}"
            )
        if not isinstance(cls.regime, Regime):
            raise TypeError("regime deve ser Regime")
        if not isinstance(cls.assumptions, tuple):
            raise TypeError("assumptions deve ser tupla")
        if not isinstance(cls.requires, tuple) or any(
            r not in _TIPOS_CAMPOS for r in cls.requires
        ):
            raise TypeError(
                f"requires deve ser tupla de insumos de MethodInputs: {cls.requires!r}"
            )
        if "selic" in cls.requires and cls.regime is not Regime.NOMINAL:
            raise TypeError("selic é taxa nominal: só método NOMINAL pode exigi-la")
        if (
            not isinstance(cls.applies_to, frozenset)
            or not cls.applies_to
            or not all(isinstance(a, AssetType) for a in cls.applies_to)
        ):
            raise TypeError("applies_to deve ser frozenset não vazio de AssetType")
        _validar_params_type(cls.params_type)

    def calcular(self, inputs: MethodInputs, params: Any) -> MethodResult | Abstention:
        if not isinstance(inputs, MethodInputs):
            raise TypeError("inputs deve ser MethodInputs")
        if not isinstance(params, self.params_type):
            raise TypeError(f"parâmetros devem ser {self.params_type.__name__}")
        faltantes = [r for r in self.requires if getattr(inputs, r) is None]
        if faltantes:
            return Abstention(
                self.nome, self.version, f"insumo ausente: {', '.join(faltantes)}"
            )
        resultado = self._calcular(inputs, params)
        if not isinstance(resultado, (MethodResult, Abstention)):
            raise TypeError("_calcular deve devolver MethodResult ou Abstention")
        return resultado

    @abstractmethod
    def _calcular(
        self, inputs: MethodInputs, params: Any
    ) -> MethodResult | Abstention: ...
