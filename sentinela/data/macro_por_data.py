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
from itertools import pairwise

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
        if isinstance(item["valor"], bool):
            # BUG-3-08: `float(True)` é 1.0; marcador lógico não demonstra taxa. Falha da
            # fonte (ValueError), como as outras observações inválidas.
            raise ValueError(f"SGS: observação inválida: {item!r}")  # noqa: TRY004
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


def _nao_representavel(serie: int, data: date) -> dict:
    """BUG-3-07: entrada finita com resultado não finito ou fator não positivo."""
    return {
        "abstencao": (
            f"série SGS {serie}: resultado não representável com a observação de "
            f"{data.isoformat()}"
        )
    }


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
    fator = 1 + observacao.valor / 100
    try:
        valor = fator**DIAS_UTEIS_ANO - 1
    except OverflowError:
        return _nao_representavel(CDI, observacao.data)
    if fator <= 0 or not math.isfinite(valor):
        return _nao_representavel(CDI, observacao.data)
    return {"valor": valor, "data": observacao.data}


def _indice_mes(dia: date) -> int:
    return dia.year * 12 + dia.month - 1


MOTIVO_CALENDARIO_IPCA = "calendário de divulgação do IPCA ausente ou fora de ordem"


def calendario_crescente(publicacoes: dict[str, date]) -> bool:
    """Datas de divulgação crescentes com o mês de referência (o IPCA sai em ordem)."""
    datas = [publicacoes[mes] for mes in sorted(publicacoes)]
    return bool(datas) and all(a < b for a, b in pairwise(datas))


def ipca_publicado(
    referencia: date,
    as_of: date,
    coleta: date,
    publicacoes: dict[str, date] | None,
) -> bool:
    """O mês de referência M estava divulgado em `as_of`? (decisão 31, F3-1c-a; DD-39)

    Na data da coleta ou depois, tudo o que está na série já saiu. Antes dela, só o
    calendário do IBGE prova: M divulgado antes de `as_of`, ou um mês posterior a M
    divulgado antes de `as_of` (o IPCA sai em ordem). Sem prova, não conta.
    """
    if referencia > as_of:
        return False
    if as_of >= coleta:
        return True
    chave = f"{referencia:%Y%m}"
    calendario = publicacoes or {}
    if chave in calendario:
        return calendario[chave] < as_of
    return any(mes > chave and dia < as_of for mes, dia in calendario.items())


def ipca_12m(
    observacoes: Iterable[Observacao],
    as_of: date,
    coleta: date,
    publicacoes: dict[str, date] | None = None,
) -> dict:
    """IPCA acumulado dos 12 últimos meses divulgados até `as_of` (SGS 433), em razão.

    Antes da data da coleta, a divulgação de cada mês vem do calendário do IBGE
    (`publicacoes`, mês `AAAAMM` → dia); sem calendário em ordem, abstém.
    """
    if as_of < coleta and not calendario_crescente(publicacoes or {}):
        return {"abstencao": MOTIVO_CALENDARIO_IPCA}
    disponiveis = sorted(
        (o for o in observacoes if ipca_publicado(o.data, as_of, coleta, publicacoes)),
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
        fator = 1 + observacao.valor / 100
        if fator <= 0:
            return _nao_representavel(IPCA, observacao.data)
        acumulado *= fator
    if not math.isfinite(acumulado):
        return _nao_representavel(IPCA, disponiveis[-1].data)
    return {"valor": acumulado - 1, "data": disponiveis[-1].data}
