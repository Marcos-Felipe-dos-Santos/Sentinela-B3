"""Normalização de percentuais na fronteira de cada provedor (F2A-4; E-4, E-5, armadilha 4).

Um só lugar converte o DY de cada provedor para razão (0,0674 = 6,74%), pela representação
declarada dele, via `Percent` e `Ratio` (`sentinela.domain.units`). Não valida: o invariante
dos motores (0 ≤ DY ≤ 25%) fica em `config._normalizar_dy`.

Representação por provedor (F2A-16, `docs/decisoes/fontes-fase2a.md`, seção 8):
- **yfinance:** `dividendYield` em percentual (PETR4: 6,74; os proventos de 12 meses ÷ preço
  dão 0,0674). Um percentual abaixo de 1 (BBAS3: 0,57) também é percentual.
- **brapi:** não determinada (documentação renderizada por JavaScript, chamada sem token sem
  fundamentos). Vale a regra da V1, como inferência: acima de 1 é percentual, senão razão.

Funções puras: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from sentinela.domain.units import Percent, Ratio


class Representacao(Enum):
    PERCENTUAL = "percentual (evidência do F2A-16)"
    INFERIDA_V1 = "inferida pela regra da V1: acima de 1 é percentual, senão razão"


REPRESENTACAO_DY: dict[str, Representacao] = {
    "yfinance": Representacao.PERCENTUAL,
    "brapi": Representacao.INFERIDA_V1,
}


@dataclass(frozen=True)
class Normalizado:
    """Valor em razão (`None` sem número finito) e a representação usada na conversão."""

    valor: float | None
    representacao: Representacao


def _numero(bruto: object) -> float | None:
    if isinstance(bruto, bool):
        return None
    try:
        numero = float(bruto)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def converter(bruto: object, representacao: Representacao) -> float | None:
    """O número em razão pela representação; sem número finito, `None`."""
    numero = _numero(bruto)
    if numero is None:
        return None
    if representacao is Representacao.PERCENTUAL or (
        representacao is Representacao.INFERIDA_V1 and numero > 1
    ):
        return Percent(numero).para_ratio().valor
    return Ratio(numero).valor


def proveniencia_dy(provedor: str) -> dict:
    """Registro da conversão do DY do provedor, para `dados['proveniencia']['dy']` (D16)."""
    representacao = REPRESENTACAO_DY[provedor]
    return {
        "fonte": provedor,
        "representacao": representacao.value,
        "inferida": representacao is Representacao.INFERIDA_V1,
    }


def dy_na_fronteira(bruto: object, provedor: str) -> Normalizado:
    """DY do provedor em razão. Provedor sem representação declarada é erro."""
    representacao = REPRESENTACAO_DY[provedor]
    return Normalizado(converter(bruto, representacao), representacao)
