"""Registro do índice oficial de ativos (F2A-1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Registro:
    ticker: str
    classe: str
    regra: str
    fonte: dict
    especie: str | None = None
    cnpj: str | None = None
    cd_cvm: int | None = None
    nome: str | None = None
    acoes_por_unit: dict | None = None
    motivo: str | None = None
    setor: str | None = None
    controle_acionario: str | None = None
    segmento: str | None = None

    def para_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def de_dict(dados: dict) -> Registro:
        return Registro(**dados)


@dataclass(frozen=True)
class Excecao:
    codigo: str
    motivo: str
    cnpj: str | None = None
    nome: str | None = None

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class Indice:
    gerado_em: str
    fontes: dict
    registros: dict[str, Registro] = field(default_factory=dict)
    excecoes: list[Excecao] = field(default_factory=list)

    def buscar(self, ticker: str | None) -> Registro | None:
        return self.registros.get(str(ticker or "").strip().upper())
