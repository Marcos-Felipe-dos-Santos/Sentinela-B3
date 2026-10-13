"""Lucro e PL dos controladores, com as reservas da D20 (F2A-37, ADR-0003; ficha por ação, 7.2).

Funções puras sobre as leituras da tabela de contas (`contas_cvm.ler_conta`): sem rede, sem
banco, sem relógio.

- **Ausente:** linha não encontrada, ou o código presente com outra descrição (não é a conta).
- **Inválida:** valor não numérico, NaN, infinito, ou o mesmo par com valores diferentes. Valor
  inválido nunca autoriza reserva: o campo se abstém.
- **Reserva:** o total (lucro consolidado ou PL consolidado) no lugar do dos controladores, só
  sem evidência de minoritários. Cada reserva usada volta com o texto que vai para a
  proveniência do campo.
"""

from __future__ import annotations

from dataclasses import dataclass

from sentinela.data.contas_cvm import (
    MOTIVO_LINHA_AUSENTE,
    MOTIVO_SEM_CORRESPONDENCIA,
    Abstencao,
    Leitura,
)

MOTIVO_LUCRO_COM_MINORITARIOS = (
    "lucro dos controladores ausente, com lucro de não controladores no documento"
)
MOTIVO_LUCRO_NAO_SEPARADO = "lucro dos controladores não separado no documento, com não controladores no balanço"
MOTIVO_LUCRO_INVALIDO = "lucro dos controladores com valor inválido no documento"
MOTIVO_LUCRO_SEM_TOTAL = "lucro dos controladores ausente, sem lucro consolidado válido"
MOTIVO_PL_COM_MINORITARIOS = (
    "PL dos controladores não separado, com lucro de não controladores no documento"
)
MOTIVO_PL_INVALIDO = "PL dos controladores com valor inválido no documento"
RESERVA_LUCRO_SEM_LINHA = (
    "lucro total: documento sem a linha dos controladores e sem minoritários"
)
RESERVA_LUCRO_NAO_SEPARADO = (
    "lucro total: linhas dos controladores e dos não controladores zeradas, sem minoritários "
    "no balanço"
)
RESERVA_PL = "PL total: participação e lucro de não controladores ausentes ou zerados"

_AUSENTE = (MOTIVO_LINHA_AUSENTE, MOTIVO_SEM_CORRESPONDENCIA)


@dataclass(frozen=True)
class Resultado:
    valor: float | None
    reserva: str | None = None
    motivo: str | None = None


def _ausente(leitura: Leitura | Abstencao) -> bool:
    return isinstance(leitura, Abstencao) and leitura.motivo in _AUSENTE


def _invalida(leitura: Leitura | Abstencao) -> bool:
    return isinstance(leitura, Abstencao) and leitura.motivo not in _AUSENTE


def _ausente_ou_zerada(leitura: Leitura | Abstencao) -> bool:
    return _ausente(leitura) or (isinstance(leitura, Leitura) and leitura.valor == 0)


def lucro_dos_controladores(
    controladores: Leitura | Abstencao,
    nao_controladores: Leitura | Abstencao,
    consolidado: Leitura | Abstencao,
    pl_nao_controladores: Leitura | Abstencao,
) -> Resultado:
    """Lucro atribuído à controladora, ou o consolidado quando a D20 e a decisão 7.2 permitem."""
    if _invalida(controladores):
        return Resultado(None, motivo=MOTIVO_LUCRO_INVALIDO)
    if isinstance(controladores, Leitura) and controladores.valor != 0:
        return Resultado(controladores.valor)
    if _invalida(nao_controladores):
        return Resultado(None, motivo=MOTIVO_LUCRO_INVALIDO)
    if not _ausente_ou_zerada(nao_controladores):
        if _ausente(controladores):
            return Resultado(None, motivo=MOTIVO_LUCRO_COM_MINORITARIOS)
        return Resultado(controladores.valor)
    if not isinstance(consolidado, Leitura):
        if _ausente(controladores):
            return Resultado(None, motivo=MOTIVO_LUCRO_SEM_TOTAL)
        return Resultado(controladores.valor)
    if _ausente(controladores):
        return Resultado(consolidado.valor, reserva=RESERVA_LUCRO_SEM_LINHA)
    if consolidado.valor == 0:
        return Resultado(0.0)
    if not _ausente_ou_zerada(pl_nao_controladores):
        return Resultado(None, motivo=MOTIVO_LUCRO_NAO_SEPARADO)
    return Resultado(consolidado.valor, reserva=RESERVA_LUCRO_NAO_SEPARADO)


def pl_dos_controladores(
    pl_total: Leitura | Abstencao,
    pl_nao_controladores: Leitura | Abstencao,
    lucro_nao_controladores: Leitura | Abstencao,
) -> Resultado:
    """PL total menos não controladores; o PL total só sem nenhuma evidência de minoritários.

    Sem o par do PL total no modelo (a 2.03 do banco é "Provisões"), `None` sem motivo: o PL
    dos bancos é do F2A-9.
    """
    if not isinstance(pl_total, Leitura):
        return Resultado(None)
    if _invalida(pl_nao_controladores):
        return Resultado(None, motivo=MOTIVO_PL_INVALIDO)
    if isinstance(pl_nao_controladores, Leitura) and pl_nao_controladores.valor != 0:
        return Resultado(pl_total.valor - pl_nao_controladores.valor)
    if _invalida(lucro_nao_controladores):
        return Resultado(None, motivo=MOTIVO_PL_INVALIDO)
    if not _ausente_ou_zerada(lucro_nao_controladores):
        return Resultado(None, motivo=MOTIVO_PL_COM_MINORITARIOS)
    return Resultado(pl_total.valor, reserva=RESERVA_PL)
