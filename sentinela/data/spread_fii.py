"""Spread dos FIIs de tijolo sobre a NTN-B: calibração de 60 meses (F2B-2; ficha FII 1.1, §6).

Plano final da 2B, seção 3: em cada mês, a mediana entre os fundos válidos de (rendimento de
12 meses ÷ fechamento do último pregão do mês) − média da taxa de aplicação da NTN-B da última
data-base elegível até esse pregão. O spread é a mediana das 60 medianas mensais contíguas
encerradas no último mês com Informe elegível, cada mês com o mesmo peso. Mês sem fundo
válido é lacuna, e com lacuna o spread fica indisponível: a janela não é reduzida.

Quem decide os fundos válidos de cada mês (tipo, liquidez, eventos, Informe) é o script de
calibração (`scripts/calibrar_spread_fii.py`). Função pura: sem rede, sem relógio, sem
`config`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from statistics import median, quantiles

MESES = 60
MOTIVO_LACUNA = "spread indisponível: mês sem fundo válido na janela de 60 meses"


@dataclass(frozen=True)
class Abstencao:
    motivo: str


@dataclass(frozen=True)
class Calibracao:
    spread: float
    mes_inicial: str
    mes_final: str
    fundos_por_mes: tuple[int, int, float]  # mínimo, máximo e mediana
    p25: float
    p75: float
    medianas: tuple[tuple[str, float, int], ...]  # (mês, mediana, fundos)


def mediana_do_mes(diferencas: Iterable[float]) -> float | None:
    """Mediana das diferenças finitas dos fundos do mês; `None` sem nenhuma."""
    validas = [d for d in diferencas if isinstance(d, float) and math.isfinite(d)]
    return median(validas) if validas else None


def _anterior(mes: str) -> str:
    ano, m = int(mes[:4]), int(mes[5:7])
    return f"{ano - 1:04d}-12" if m == 1 else f"{ano:04d}-{m - 1:02d}"


def janela(mes_final: str, meses: int = MESES) -> list[str]:
    """Os `meses` meses (AAAA-MM) contíguos que terminam em `mes_final`, em ordem."""
    saida = [mes_final]
    while len(saida) < meses:
        saida.append(_anterior(saida[-1]))
    return saida[::-1]


def calibrar(
    por_mes: Mapping[str, Iterable[float]], mes_final: str
) -> Calibracao | Abstencao:
    """Spread dos 60 meses que terminam em `mes_final`, com contagens e quartis."""
    linhas = []
    for mes in janela(mes_final):
        valores = [
            d for d in por_mes.get(mes, ()) if isinstance(d, float) and math.isfinite(d)
        ]
        mediana = mediana_do_mes(valores)
        if mediana is None:
            return Abstencao(f"{MOTIVO_LACUNA}: {mes}")
        linhas.append((mes, mediana, len(valores)))
    medianas = [m for _, m, _ in linhas]
    contagens = [n for _, _, n in linhas]
    p25, _, p75 = quantiles(medianas, n=4, method="inclusive")
    return Calibracao(
        spread=median(medianas),
        mes_inicial=linhas[0][0],
        mes_final=linhas[-1][0],
        fundos_por_mes=(min(contagens), max(contagens), median(contagens)),
        p25=p25,
        p75=p75,
        medianas=tuple(linhas),
    )
