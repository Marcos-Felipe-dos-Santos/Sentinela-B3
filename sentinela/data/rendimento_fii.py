"""Rendimento de 12 meses do FII pelo Informe Mensal da CVM (F2B-28; insumo da [FII], F2B-2).

Só mede: nenhum motor lê. O complemento do Informe não tem o valor distribuído por cota; o
rendimento do mês é reconstruído pelo DY do mês × valor patrimonial da cota do fim do mês
anterior, a base que a norma define (Resolução CVM 175, anexo da 184; F2B-21, pergunta 4).
`Percentual_Dividend_Yield_Mes` vem em razão (F2B-21, pergunta 4) e passa pela fronteira de
`sentinela/data/normalizacao.py`, provedor `cvm_fii`.

Doze meses consecutivos terminando no último mês do Informe, cada um com o DY e com o valor
da cota do mês anterior (13 valores de cota); mês com mais de uma versão usa a maior
`Versao`. Faltou algum: abstenção, com o motivo. O DY de 12 meses é a soma dos rendimentos ÷
o preço, que vem de outra fonte.

Função pura: sem rede, sem relógio, sem `config`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sentinela.data import normalizacao

PROVEDOR = "cvm_fii"
MESES = 12
BASE = (
    "valor patrimonial da cota do fim do mês anterior (Resolução CVM 175, anexo da 184)"
)
MOTIVO_SEM_MESES = "Informe sem meses do fundo"
MOTIVO_MESES_INCOMPLETOS = "menos de 12 meses com DY e valor da cota do mês anterior"
MOTIVO_PRECO = "preço ausente ou não positivo"


@dataclass(frozen=True)
class Abstencao:
    motivo: str


def _numero(bruto: object) -> float | None:
    """Número finito do CSV (vírgula ou ponto decimal); `None` sem número.

    Pelo texto: `None` e booleano viram "None", "True" e "False", que não são número.
    """
    try:
        numero = float(str(bruto).replace(",", "."))
    except ValueError:
        return None
    return numero if math.isfinite(numero) else None


def _versao(registro: Mapping) -> float:
    versao = _numero(registro.get("Versao"))
    return versao if versao is not None else float("-inf")


def _mes(registro: Mapping) -> tuple[int, int] | None:
    texto = str(registro.get("Data_Referencia") or "")[:7]
    try:
        ano, mes = texto.split("-")
        chave = (int(ano), int(mes))
    except ValueError:
        return None
    return chave if 1 <= chave[1] <= 12 else None


def _anterior(mes: tuple[int, int]) -> tuple[int, int]:
    ano, m = mes
    return (ano - 1, 12) if m == 1 else (ano, m - 1)


def _por_mes(registros: Iterable[Mapping]) -> dict[tuple[int, int], Mapping]:
    """Um registro por mês: o de maior `Versao` (versão ilegível perde)."""
    escolhidos: dict[tuple[int, int], Mapping] = {}
    for registro in registros:
        mes = _mes(registro)
        if mes is None:
            continue
        atual = escolhidos.get(mes)
        if atual is None or _versao(registro) > _versao(atual):
            escolhidos[mes] = registro
    return escolhidos


def rendimento_12_meses(
    registros: Iterable[Mapping], preco: object
) -> dict | Abstencao:
    """DY de 12 meses sobre o preço, com os meses, a base e a representação usada."""
    meses = _por_mes(registros)
    if not meses:
        return Abstencao(MOTIVO_SEM_MESES)
    preco_valor = _numero(preco)
    if preco_valor is None or preco_valor <= 0:
        return Abstencao(MOTIVO_PRECO)
    final = max(meses)
    mes, rendimentos = final, []
    for _ in range(MESES):  # `mes` sempre existe: o final, ou o `anterior` com cota
        anterior = _anterior(mes)
        dy = normalizacao.dy_na_fronteira(
            _numero(meses[mes].get("Percentual_Dividend_Yield_Mes")), PROVEDOR
        ).valor
        cota = _numero(meses.get(anterior, {}).get("Valor_Patrimonial_Cotas"))
        if dy is None or cota is None or cota <= 0:
            return Abstencao(MOTIVO_MESES_INCOMPLETOS)
        rendimentos.append(dy * cota)
        mes = anterior
    rendimento = sum(rendimentos)
    return {
        "dy": rendimento / preco_valor,
        "rendimento_12m": rendimento,
        "meses": MESES,
        "mes_final": f"{final[0]:04d}-{final[1]:02d}",
        "base": BASE,
        "conversao": normalizacao.proveniencia_dy(PROVEDOR),
    }
