"""Perímetro DVA e entradas do Gordon, sem rede, banco ou relógio."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sentinela.data import acoes_cvm
from sentinela.data.contas_cvm import (
    MOTIVO_LINHA_AUSENTE,
    Leitura,
)
from sentinela.data.contas_cvm import (
    Abstencao as ContaAbstida,
)
from sentinela.domain.units import (
    BRL,
    Escala,
    Inflacao,
    ProventosControladores,
    RateReal,
    Ratio,
)


@dataclass(frozen=True)
class Abstencao:
    motivo: str


def _ausente(linha: Leitura | ContaAbstida) -> bool:
    return isinstance(linha, ContaAbstida) and linha.motivo == MOTIVO_LINHA_AUSENTE


def _zero_ou_ausente(linha: Leitura | ContaAbstida) -> bool:
    return _ausente(linha) or (isinstance(linha, Leitura) and linha.valor == 0)


def proventos_da_dva(
    dividendos: Leitura | ContaAbstida,
    jcp: Leitura | ContaAbstida,
    participacao_dva: Leitura | ContaAbstida,
    lucro_minoritarios: Leitura | ContaAbstida,
    pl_minoritarios: Leitura | ContaAbstida,
) -> float | Abstencao:
    """Somente JCP/dividendos, nunca a parcela separada dos não controladores."""
    motivo = "estrutura da DVA não permite atribuir proventos aos controladores"
    if isinstance(participacao_dva, Leitura):
        if (
            isinstance(participacao_dva.valor, bool)
            or not math.isfinite(participacao_dva.valor)
            or participacao_dva.valor < 0
        ):
            return Abstencao(motivo)
        if participacao_dva.valor == 0 and not (
            _zero_ou_ausente(lucro_minoritarios) and _zero_ou_ausente(pl_minoritarios)
        ):
            return Abstencao(motivo)
    elif not (
        _ausente(participacao_dva)
        and _zero_ou_ausente(lucro_minoritarios)
        and _zero_ou_ausente(pl_minoritarios)
    ):
        return Abstencao(motivo)
    valores = []
    for leitura in (dividendos, jcp):
        if isinstance(leitura, Leitura):
            if (
                isinstance(leitura.valor, bool)
                or not math.isfinite(leitura.valor)
                or leitura.valor < 0
            ):
                return Abstencao("provento inválido ou negativo na DVA")
            valores.append(leitura.valor)
        elif not _ausente(leitura):
            return Abstencao("proventos incompletos: " + leitura.motivo)
    if not valores:
        return Abstencao("proventos incompletos: duas rubricas ausentes")
    try:
        total = math.fsum(valores)
    except OverflowError:
        return Abstencao("resultado não finito: proventos DVA")
    return (
        total
        if math.isfinite(total)
        else Abstencao("resultado não finito: proventos DVA")
    )


def entradas(dados: dict[str, Any], as_of: date | datetime) -> dict | Abstencao:
    """Fronteira tipada: nenhum DY agregado substitui a prova documental."""
    instante = as_of if isinstance(as_of, datetime) else None
    if instante is not None:
        if instante.tzinfo is None or instante.utcoffset() is None:
            return Abstencao("as_of exige fuso horário")
        as_of = instante.astimezone(ZoneInfo("America/Sao_Paulo")).date()
    fonte = dados.get("gordon_cvm") or {}
    if not fonte:
        return Abstencao("DFP anual dos controladores ausente")
    if "abstencao" in fonte:
        return Abstencao(fonte["abstencao"])
    try:
        if fonte["modelo"] != "empresa" or dados.get("classe_ativo") not in (
            "STOCK",
            "UNIT",
        ):
            return Abstencao("classe ou modelo fora do escopo do Gordon")
        if (
            dados.get("classes_preferenciais")
            and len(dados["classes_preferenciais"]) > 1
        ):
            return Abstencao("classes com direitos distintos na fase 2B")
        if fonte.get("base_acionaria_compativel") is not True:
            return Abstencao("base de ações incompatível ou sem evidência vigente")
        if fonte.get("hipotese_dva_anual") is not True:
            return Abstencao("hipótese de DVA anual não demonstrada")
        if (
            fonte.get("distribuicao_extraordinaria_identificada") is True
            or fonte.get("mudanca_estrutural_sem_reconciliacao") is True
        ):
            return Abstencao(
                "fluxo não representativo: evento identificado sem reconciliação"
            )
        inicio, fim = (
            date.fromisoformat(fonte["inicio"]),
            date.fromisoformat(fonte["fim"]),
        )
        entrega = date.fromisoformat(fonte["data_entrega"])
        if entrega >= as_of or fim >= as_of:
            return Abstencao("DFP entregue após o corte de disponibilidade")
        base = dados.get("base_acionaria_gordon") or {}
        for nome, prov in (
            ("DFP", fonte.get("proveniencia")),
            ("composição", base.get("proveniencia")),
        ):
            if not isinstance(prov, dict) or any(
                not prov.get(c)
                for c in ("periodo_referencia", "data_entrega", "data_coleta")
            ):
                return Abstencao(f"proveniência temporal da {nome} ausente")
            coleta = datetime.fromisoformat(prov["data_coleta"])
            if coleta.tzinfo is None or coleta.utcoffset() is None:
                return Abstencao(f"coleta da {nome} sem fuso horário")
            if (
                date.fromisoformat(prov["periodo_referencia"]) >= as_of
                or date.fromisoformat(prov["data_entrega"]) >= as_of
                or (instante is not None and coleta > instante)
                or (
                    instante is None
                    and coleta.astimezone(ZoneInfo("America/Sao_Paulo")).date() > as_of
                )
            ):
                return Abstencao(f"evidência da {nome} posterior ao as_of")
        macro = dados.get("taxa_real") or {}
        if macro.get("as_of") is not None:
            corte_macro = datetime.fromisoformat(macro["as_of"])
            if corte_macro.tzinfo is None or corte_macro.utcoffset() is None:
                return Abstencao("contexto da taxa real sem fuso horário")
            if (instante is not None and corte_macro > instante) or (
                instante is None
                and corte_macro.astimezone(ZoneInfo("America/Sao_Paulo")).date() > as_of
            ):
                return Abstencao("contexto da taxa real posterior ao as_of")
        ipca, pib = macro.get("inflacao") or {}, macro.get("pib") or {}
        if (
            ipca.get("inicio") != inicio.isoformat()
            or ipca.get("fim") != fim.isoformat()
        ):
            return Abstencao("inflação incompatível com a janela da DFP")
        lucro, pl = fonte["lucro_controladores"], fonte["pl_inicial_controladores"]
        if (
            isinstance(lucro, bool)
            or isinstance(pl, bool)
            or not math.isfinite(lucro)
            or not math.isfinite(pl)
            or lucro <= 0
            or pl <= 0
        ):
            return Abstencao(
                "lucro ou PL inicial dos controladores não positivo ou inválido"
            )
        total, acoes = fonte["proventos_controladores"], fonte["acoes_base"]
        if (
            not isinstance(acoes, (float, int))
            or isinstance(acoes, bool)
            or not math.isfinite(acoes)
            or acoes <= 0
            or acoes % 1
        ):
            return Abstencao("ações da DFP não positivas ou inválidas")
        if (
            isinstance(total, bool)
            or not isinstance(total, (float, int))
            or not math.isfinite(total)
        ):
            return Abstencao("provento DVA inválido")
        fator = fonte.get("fator_unit", 1)
        if dados["classe_ativo"] == "UNIT" and (
            not fonte.get("direitos_compativeis")
            or isinstance(fator, bool)
            or not isinstance(fator, (float, int))
            or not math.isfinite(fator)
            or fator <= 0
            or fator % 1
        ):
            return Abstencao("unit sem composição e direitos compatíveis")
        return {
            "lpa": BRL(fonte["lpa"]),
            "roe": Ratio(lucro / pl),
            "custo_capital_real": RateReal(macro["custo_capital_real"]),
            "inflacao": Inflacao(ipca["valor"]),
            "teto_pib_real": RateReal(pib["valor"]),
            "proventos_controladores": ProventosControladores(
                BRL(total / acoes * fator), Ratio(total / lucro), inicio, fim
            ),
        }
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as erro:
        return Abstencao(f"insumo ausente ou inválido do Gordon: {erro}")


AVISO_EVENTOS = "evento posterior ao último documento entregue não é detectado"


def compatibilidade_base(
    base: acoes_cvm.Composicao,
    recente: acoes_cvm.Composicao,
    *,
    escala: Escala,
    especie: str | None,
    eh_unit: bool,
    acoes_por_unit: dict | None,
    shares_outstanding: float | None,
) -> dict:
    """Gordon1.1: composição recente/DFP em (0,9;1,1), yfinance só aviso.

    As duas composições usam a quantidade documental, líquida de tesouraria.
    A escala conferida na DFP só converte a conferência externa por ticker.
    """
    avisos = [AVISO_EVENTOS]
    anterior, atual = base.total, recente.total
    if not all(math.isfinite(v) and v > 0 for v in (anterior, atual)):
        return {
            "compativel": False,
            "motivo": "base de ações incompatível",
            "avisos": avisos,
        }
    razao = atual / anterior
    resultado = {
        "compativel": 0.9 < razao < 1.1,
        "razao": razao,
        "avisos": avisos,
        "motivo": None if 0.9 < razao < 1.1 else "base de ações incompatível",
    }
    if (
        isinstance(shares_outstanding, (int, float))
        and not isinstance(shares_outstanding, bool)
        and math.isfinite(shares_outstanding)
        and shares_outstanding > 0
        and (not eh_unit or acoes_cvm._unit_valida(acoes_por_unit))
    ):
        comparacao = acoes_cvm.divergencia_acoes(
            recente,
            escala,
            especie=especie,
            eh_unit=eh_unit,
            acoes_por_unit=acoes_por_unit,
            shares_outstanding=shares_outstanding,
        )
        if comparacao is not None:
            resultado["conferencia_yfinance"] = comparacao
            if (
                abs(shares_outstanding - comparacao["acoes_cvm"])
                > 0.05 * comparacao["acoes_cvm"]
            ):
                avisos.append(
                    "ações do documento mais recente divergem mais de 5% do yfinance"
                )
    return resultado
