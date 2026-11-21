"""Série de preços ajustada só por eventos societários, separada do preço bruto (F3-4c).

Armadilha 11: o múltiplo numa data usa o preço bruto daquela data e as ações do mesmo
documento; o retorno usa a série ajustada. Aqui só a aritmética dos fatores oficiais da B3
(F3-4b, `eventos_societarios`): a quantidade é multiplicada pelo fator F na data ex, então o
preço anterior é dividido por F. O preço de cada data é o bruto dividido pelo produto dos
fatores dos eventos com data ex depois dela e até o fim da série. Proventos (reinvestimento,
data, bruto ou líquido) ficam fora: são decisão de método da ficha do backtest (F3-F1, F3-8b).

Evento do papel no intervalo sem fator, sem data ex demonstrada ou sem prova (`sem_prova`)
abstém as datas anteriores a ele, com o motivo: o retorno que o atravessa não é calculável.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from itertools import pairwise

from sentinela.data.providers import b3_cotahist, b3_proventos

MOTIVO_SEM_FATOR = "evento em ações sem fator oficial no intervalo"
MOTIVO_SEM_DATA_EX = "evento em ações sem data ex demonstrada no intervalo"
MOTIVO_SEM_PROVA = "evento em ações sem prova de aprovação, data ou fator no intervalo"
MOTIVO_OUTRA_ESPECIE = "evento em espécie distinta sem reconciliação demonstrada"
MOTIVO_COTACAO_REPETIDA = "código com mais de uma cotação no mesmo pregão"
MOTIVO_SEM_ISIN = "código sem ISIN único nos preços do período"


def evento_emite_mesmo_papel(evento: Mapping, isin: str) -> bool:
    """Só o fator que emite o próprio ISIN ajusta preço ou retorno do papel."""
    return evento.get("ativo_emitido") == isin


def _data(texto: object) -> date | None:
    try:
        return date.fromisoformat(str(texto))
    except ValueError:
        return None


def ajustar(
    precos: Sequence[tuple[date, float]],
    eventos: Iterable[Mapping],
    bloqueados: Iterable[Mapping] = (),
) -> list[dict]:
    """Série ajustada pelos eventos, com o bruto ao lado; data sem ajuste possível, com motivo.

    `precos`: (data, fechamento bruto) com datas estritamente crescentes (senão, `ValueError`).
    `eventos`: os do `eventos_ate`, já do papel. Contam os eventos com data com a partir do
    primeiro preço e antes do último; os de antes não mudam a série, e os de depois ainda não
    ocorreram nela. `bloqueados`: eventos que abstêm o intervalo até a data com deles, com o
    `motivo` de cada um (sem prova, por padrão); evento sem data com abstém a série inteira.
    """
    if any(a >= b for (a, _), (b, _) in pairwise(precos)):
        raise ValueError("datas da série fora de ordem ou repetidas")
    if not precos:
        return []
    inicio, fim = precos[0][0], precos[-1][0]
    aplicaveis: list[tuple[date, float]] = []
    bloqueios: list[tuple[date, str]] = []
    for evento in bloqueados:
        data_com = _data(evento.get("data_com"))
        if data_com is None or inicio <= data_com < fim:
            bloqueios.append(
                (data_com or fim, evento.get("motivo") or MOTIVO_SEM_PROVA)
            )
    for evento in eventos:
        data_com = _data(evento.get("data_com"))
        if data_com is None:
            bloqueios.append((fim, MOTIVO_SEM_PROVA))
            continue
        if data_com < inicio or data_com >= fim:
            continue
        data_ex = _data(evento.get("data_ex"))
        fator = evento.get("fator")
        if data_ex is None:
            bloqueios.append((data_com, MOTIVO_SEM_DATA_EX))
        elif (
            isinstance(fator, bool)
            or not isinstance(fator, (int, float))
            or not math.isfinite(fator)
            or fator <= 0
        ):
            bloqueios.append((data_com, MOTIVO_SEM_FATOR))
        elif data_ex <= fim:
            aplicaveis.append((data_ex, float(fator)))
    serie = []
    for dia, bruto in precos:
        bloqueio = [m for limite, m in sorted(bloqueios) if dia <= limite]
        if bloqueio:
            serie.append(
                {
                    "data": dia.isoformat(),
                    "bruto": bruto,
                    "ajustado": None,
                    "motivo": bloqueio[0],
                }
            )
            continue
        acumulado = 1.0
        for data_ex, fator in aplicaveis:
            if dia < data_ex:
                acumulado *= fator
        serie.append(
            {
                "data": dia.isoformat(),
                "bruto": bruto,
                "ajustado": bruto / acumulado,
                "fator": acumulado,
            }
        )
    return serie


def serie_do_banco(conn, codigo: str, emissor: str, dia: date, pregoes: int) -> dict:
    """Série ajustada do código até o dia local de D, pelo banco único (F3-4a e F3-4b).

    Preços: os brutos do código nos `pregoes` pregões anteriores a D (`cotacoes_ate`).
    Eventos: os do emissor conhecidos em D (`eventos_ate`), só os do ISIN do código. Evento
    que emite outra espécie, ou sem o ativo emitido, não tem conversão presumida e abstém o
    intervalo, como em `fatores_acoes_b3`. Código sem ISIN único (inclusive com linha sem
    ISIN) ou com mais de uma cotação no mesmo pregão abstém.
    """
    if isinstance(dia, datetime) or not isinstance(dia, date):
        raise TypeError(
            "serie_do_banco recebe o dia local de D (date), não um instante"
        )
    cotacoes = [
        c
        for c in b3_cotahist.cotacoes_ate(conn, dia, pregoes)
        if c.codigo_negociacao == codigo
    ]
    isins = {c.isin for c in cotacoes}
    if len(isins) != 1 or "" in isins:
        return {"serie": [], "motivo": MOTIVO_SEM_ISIN}
    if len({c.data for c in cotacoes}) != len(cotacoes):
        return {"serie": [], "motivo": MOTIVO_COTACAO_REPETIDA}
    (isin,) = isins
    lidos = b3_proventos.eventos_ate(conn, emissor, dia)
    do_papel = [e for e in lidos["eventos"] if e.get("isin") == isin]
    mesma_especie = [e for e in do_papel if evento_emite_mesmo_papel(e, isin)]
    outra_especie = [
        e | {"motivo": MOTIVO_OUTRA_ESPECIE}
        for e in do_papel
        if not evento_emite_mesmo_papel(e, isin)
    ]
    sem_prova = [e for e in lidos["sem_prova"] if e.get("isin") == isin]
    precos = [(c.data, c.fechamento) for c in cotacoes]
    return {
        "serie": ajustar(precos, mesma_especie, [*outra_especie, *sem_prova]),
        "isin": isin,
    }
