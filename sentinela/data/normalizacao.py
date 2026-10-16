"""Normalização de percentuais na fronteira de cada provedor (F2A-4 e F2A-30; E-4, E-5, E-15).

Um só lugar converte o DY e o ROE de cada provedor para razão (0,0674 = 6,74%), pela
representação declarada dele, via `Percent` e `Ratio` (`sentinela.domain.units`). A conversão
não valida: o invariante do DY fica nos motores (`config._normalizar_dy`), e o ROE tem a guarda
`guardar_roe`, aplicada pela cascata a toda fonte, inclusive ao ROE derivado da CVM.

Representação por provedor (F2A-16, `docs/decisoes/fontes-fase2a.md`, seção 8):
- **yfinance:** `dividendYield` em percentual (PETR4: 6,74; os proventos de 12 meses ÷ preço
  dão 0,0674). Um percentual abaixo de 1 (BBAS3: 0,57) também é percentual.
- **brapi:** não determinada (documentação renderizada por JavaScript, chamada sem token sem
  fundamentos). Vale a regra da V1, como inferência: acima de 1 é percentual, senão razão. No
  ROE, que pode ser negativo, a regra olha o módulo (−21,5 é −21,5%, como 21,5 é 21,5%).
- **ROE do yfinance:** `returnOnEquity` em razão (ITUB4 0,215 contra 0,213 de lucro ÷ PL da
  DFP 2025; BBDC4 0,138 contra 0,134). A escala bate, mas o número diverge mais de 5 pontos
  do lucro ÷ PL da CVM em 4 de 10 tickers (KLBN11, SUZB3, WEGE3, RENT3). O da brapi segue a
  regra da V1, como no DY. O da CVM é derivado no próprio código (lucro ÷ PL dos
  controladores), em razão.

Funções puras: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from sentinela.domain.units import Percent, Ratio


class Representacao(Enum):
    PERCENTUAL = "percentual (evidência do F2A-16)"
    RAZAO = "razão (evidência do F2A-16 ou derivada no código)"
    INFERIDA_V1 = "inferida pela regra da V1: acima de 1 é percentual, senão razão"


REPRESENTACAO_DY: dict[str, Representacao] = {
    "yfinance": Representacao.PERCENTUAL,
    "brapi": Representacao.INFERIDA_V1,
}
REPRESENTACAO_ROE: dict[str, Representacao] = {
    "yfinance": Representacao.RAZAO,
    "brapi": Representacao.INFERIDA_V1,
    "cvm": Representacao.RAZAO,
}
ROE_MAX = 2.0  # o limite da V1 (`brapi_provider`), agora para todas as fontes
MOTIVO_ROE_NAO_FINITO = "ROE não finito: descartado"
MOTIVO_ROE_ACIMA = "ROE acima de 2 (200%) depois da conversão: descartado"


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


def converter(
    bruto: object, representacao: Representacao, por_modulo: bool = False
) -> float | None:
    """O número em razão pela representação; sem número finito, `None`.

    `por_modulo`: na regra da V1, compara o módulo com 1 (ROE, que pode ser negativo).
    """
    numero = _numero(bruto)
    if numero is None:
        return None
    referencia = abs(numero) if por_modulo else numero
    if representacao is Representacao.PERCENTUAL or (
        representacao is Representacao.INFERIDA_V1 and referencia > 1
    ):
        return Percent(numero).para_ratio().valor
    return Ratio(numero).valor


def _proveniencia(representacao: Representacao, provedor: str) -> dict:
    return {
        "fonte": provedor,
        "representacao": representacao.value,
        "inferida": representacao is Representacao.INFERIDA_V1,
    }


def proveniencia_dy(provedor: str) -> dict:
    """Registro da conversão do DY do provedor, para `dados['proveniencia']['dy']` (D16)."""
    return _proveniencia(REPRESENTACAO_DY[provedor], provedor)


def proveniencia_roe(provedor: str) -> dict:
    """Registro da conversão do ROE do provedor, para `dados['proveniencia']['roe']` (D16)."""
    return _proveniencia(REPRESENTACAO_ROE[provedor], provedor)


def roe_na_fronteira(bruto: object, provedor: str) -> Normalizado:
    """ROE do provedor em razão, sem validar. Provedor sem representação declarada é erro."""
    representacao = REPRESENTACAO_ROE[provedor]
    return Normalizado(converter(bruto, representacao, por_modulo=True), representacao)


def guardar_roe(valor: float | None) -> tuple[float | None, str | None]:
    """(ROE, None) se finito e até `ROE_MAX`; (None, motivo) se não. ROE negativo é válido.

    `None` na entrada é ausência, sem motivo.
    """
    if valor is None:
        return None, None
    if not math.isfinite(valor):
        return None, MOTIVO_ROE_NAO_FINITO
    if valor > ROE_MAX:
        return None, MOTIVO_ROE_ACIMA
    return valor, None


def dy_na_fronteira(bruto: object, provedor: str) -> Normalizado:
    """DY do provedor em razão. Provedor sem representação declarada é erro."""
    representacao = REPRESENTACAO_DY[provedor]
    return Normalizado(converter(bruto, representacao), representacao)
