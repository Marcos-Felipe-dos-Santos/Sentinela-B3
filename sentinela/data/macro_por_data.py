"""Macro por data a partir das séries completas do SGS (F3-1b).

Funções puras sobre o JSON oficial do SGS: o valor vigente numa data, sem olhar observação
posterior ao `as_of`. Sem rede, banco nem relógio: a coleta fica em `providers/macro.py`.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

SELIC_META = 432
CDI = 12
IPCA = 433
# Primeira observação de cada série diária; as diárias só aceitam janelas de até 10 anos.
INICIO_SERIE = {SELIC_META: date(1999, 3, 5), CDI: date(1986, 3, 6)}
JANELA_MAX_ANOS = 10
DIAS_UTEIS_ANO = 252
MESES_IPCA = 12
_DATA_SGS = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


@dataclass(frozen=True)
class Observacao:
    data: date
    valor: float  # percentual, como publicado no SGS


def _mais_anos(dia: date, anos: int) -> date:
    try:
        return dia.replace(year=dia.year + anos)
    except ValueError:  # 29/02 em ano não bissexto
        return date(dia.year + anos, 3, 1)


def janelas(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Janelas contíguas de menos de 10 anos que cobrem `inicio` a `fim`."""
    resultado = []
    atual = inicio
    while atual <= fim:
        final = min(_mais_anos(atual, JANELA_MAX_ANOS) - timedelta(days=1), fim)
        resultado.append((atual, final))
        atual = final + timedelta(days=1)
    return resultado


def data_sgs(texto: str) -> date:
    """Data do SGS, `dd/mm/aaaa`; outra forma é recusada."""
    casamento = _DATA_SGS.fullmatch(texto)
    if casamento is None:
        raise ValueError(f"SGS: data fora do formato dd/mm/aaaa: {texto!r}")
    dia, mes, ano = (int(parte) for parte in casamento.groups())
    return date(ano, mes, dia)


def ler_sgs(conteudo: str) -> tuple[Observacao, ...]:
    """Observações do JSON oficial (`[{"data": "dd/mm/aaaa", "valor": "1.23"}]`)."""
    dados = json.loads(conteudo)
    if not isinstance(dados, list):
        # Formato errado é falha da fonte (ValueError), não erro do código (TypeError).
        raise ValueError("SGS: formato inesperado, sem lista de observações")  # noqa: TRY004
    observacoes = []
    for item in dados:
        if not isinstance(item, dict) or "data" not in item or "valor" not in item:
            raise ValueError("SGS: observação sem data ou valor")
        try:
            dia = data_sgs(item["data"])
            valor = float(item["valor"])
        except (TypeError, ValueError) as erro:
            raise ValueError(f"SGS: observação inválida: {item!r}") from erro
        if not math.isfinite(valor):
            raise ValueError(f"SGS: valor não finito em {item['data']}")
        observacoes.append(Observacao(dia, valor))
    return juntar([observacoes])


def juntar(partes: Iterable[Iterable[Observacao]]) -> tuple[Observacao, ...]:
    """Une janelas em ordem de data; a mesma data com valores diferentes é recusada."""
    por_data: dict[date, Observacao] = {}
    for parte in partes:
        for observacao in parte:
            anterior = por_data.setdefault(observacao.data, observacao)
            if anterior.valor != observacao.valor:
                raise ValueError(
                    f"SGS: valores diferentes para a mesma data {observacao.data.isoformat()}"
                )
    return tuple(por_data[dia] for dia in sorted(por_data))


def _sem_observacao(serie: int, as_of: date) -> dict:
    return {"abstencao": f"série SGS {serie} sem observação até {as_of.isoformat()}"}


def vigente(observacoes: Iterable[Observacao], as_of: date) -> Observacao | None:
    """Última observação com data até `as_of`; datas futuras da série ficam de fora."""
    anteriores = [o for o in observacoes if o.data <= as_of]
    return max(anteriores, key=lambda o: o.data) if anteriores else None


def selic(observacoes: Iterable[Observacao], as_of: date) -> dict:
    """Meta Selic (SGS 432) vigente em `as_of`, em razão ao ano."""
    observacao = vigente(observacoes, as_of)
    if observacao is None:
        return _sem_observacao(SELIC_META, as_of)
    return {"valor": observacao.valor / 100, "data": observacao.data}


def cdi(observacoes: Iterable[Observacao], as_of: date) -> dict:
    """CDI diário (SGS 12) vigente em `as_of`, anualizado em 252 dias úteis."""
    observacao = vigente(observacoes, as_of)
    if observacao is None:
        return _sem_observacao(CDI, as_of)
    return {
        "valor": (1 + observacao.valor / 100) ** DIAS_UTEIS_ANO - 1,
        "data": observacao.data,
    }


def _indice_mes(dia: date) -> int:
    return dia.year * 12 + dia.month - 1


def ipca_disponivel(referencia: date, as_of: date, coleta: date) -> bool:
    """Mês de referência M conta a partir do primeiro dia de M+2 (decisão provisória, F3-1b).

    O SGS não traz a data de divulgação; na coleta, tudo o que está na série já saiu.
    """
    if referencia > as_of:
        return False
    return as_of >= coleta or _indice_mes(as_of) >= _indice_mes(referencia) + 2


def ipca_12m(observacoes: Iterable[Observacao], as_of: date, coleta: date) -> dict:
    """IPCA acumulado dos 12 últimos meses disponíveis em `as_of` (SGS 433), em razão."""
    disponiveis = sorted(
        (o for o in observacoes if ipca_disponivel(o.data, as_of, coleta)),
        key=lambda o: o.data,
    )[-MESES_IPCA:]
    if len(disponiveis) < MESES_IPCA or (
        _indice_mes(disponiveis[-1].data) - _indice_mes(disponiveis[0].data)
        != MESES_IPCA - 1
    ):
        return {
            "abstencao": (
                f"série SGS {IPCA} sem 12 meses consecutivos disponíveis até "
                f"{as_of.isoformat()}"
            )
        }
    acumulado = 1.0
    for observacao in disponiveis:
        acumulado *= 1 + observacao.valor / 100
    return {"valor": acumulado - 1, "data": disponiveis[-1].data}
