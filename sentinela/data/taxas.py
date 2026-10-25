"""Cesta real da ficha 1.1, pura: calendário e disponibilidade vêm do chamador."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from sentinela.data.providers.tesouro import CestaTesouro


PREMIO_ACOES_REAL = 0.05
ANO_MIN_NTNB = 2035


@dataclass(frozen=True)
class Abstencao:
    motivo: str


@dataclass(frozen=True)
class Calendario:
    inicio: date
    fim: date
    feriados: frozenset[date]
    proveniencia: dict

    def dias_uteis(self, inicio: date, fim: date) -> int:
        if not self.proveniencia or not self.inicio <= inicio <= fim <= self.fim:
            raise ValueError("calendário sem cobertura comprovada")
        return sum(
            dia.weekday() < 5 and dia not in self.feriados
            for dia in (
                inicio + timedelta(days=n) for n in range(1, (fim - inicio).days + 1)
            )
        )


def calcular(
    cesta: CestaTesouro,
    *,
    as_of: datetime,
    calendario: Calendario | None,
    proveniencia: dict,
) -> dict | Abstencao:
    """Média igual por título + prêmio das ações, sem spread soberano adicional."""
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        return Abstencao("as_of exige fuso horário")
    dia = as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()
    if cesta.motivo:
        return Abstencao(cesta.motivo)
    if cesta.data_base is None or cesta.data_base >= dia:
        return Abstencao("referência ainda não disponível: exige fim do dia local")
    if calendario is None:
        return Abstencao("calendário ausente")
    try:
        idade = calendario.dias_uteis(cesta.data_base, dia)
    except ValueError as erro:
        return Abstencao(str(erro))
    if idade > 5:
        return Abstencao("NTN-B além de 5 dias úteis")
    if not proveniencia:
        return Abstencao("proveniência ausente")
    valores = [t.taxa_aplicacao.valor for t in cesta.titulos]
    if not valores or any(not math.isfinite(v) or v <= -1 for v in valores):
        return Abstencao("cesta inválida: taxa fora do domínio")
    try:
        media = math.fsum(valores) / len(valores)
    except OverflowError:
        return Abstencao("resultado não finito: soma das taxas")
    custo = media + PREMIO_ACOES_REAL
    if not math.isfinite(custo):
        return Abstencao("resultado não finito: custo de capital")
    return {
        "ntnb": media,
        "custo_capital_real": custo,
        "premio": PREMIO_ACOES_REAL,
        "composicao": "NTN-B integral + 5 pp das ações; risco Brasil já no título",
        "vertice": "NTN-B e NTN-B Principal, vencimentos a partir de 2035, pesos iguais",
        "data_base": cesta.data_base.isoformat(),
        "quantidade": len(valores),
        "dias_uteis": idade,
        "as_of": as_of.isoformat(),
        "fonte": proveniencia.get("fonte"),
        "proveniencia": dict(proveniencia)
        | cesta.proveniencia
        | {"calendario": calendario.proveniencia},
    }
