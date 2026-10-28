"""Janelas aprovadas em28/10: cálculo puro, com evidência explícita por documento.

A presença de cinco números não prova comparabilidade nem cobertura de eventos.
Fontes recusadas conservam motivo; a falta de IPCA não apaga o CAGR nominal.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sentinela.data.fatores_acoes_b3 import fatores_da_relacao
from sentinela.data.series_cvm import _meses

FUSO = ZoneInfo("America/Sao_Paulo")


def _mapa(valor: object) -> Mapping:
    if not isinstance(valor, Mapping):
        raise TypeError("registro de fonte ausente ou inválido")
    return valor


def _numero(valor: object) -> float:
    if (
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(valor)
    ):
        raise ValueError("insumo numérico ausente ou não finito")
    return float(valor)


def _fonte(registro: Mapping, instante: datetime, campo: str = "coleta") -> None:
    if not registro.get("fonte"):
        raise ValueError("fonte não demonstrada")
    coleta = datetime.fromisoformat(str(registro.get(campo)))
    if coleta.tzinfo is None or coleta.utcoffset() is None or coleta > instante:
        raise ValueError("coleta sem fuso ou posterior ao as_of")


def _acoes_documentais(registros: list[dict]) -> list[float]:
    quantidades = []
    for e in registros:
        try:
            quantidades.append(_numero(e.get("acoes")))
        except ValueError as erro:
            motivo = (e.get("motivos") or {}).get("acoes") or str(erro)
            raise ValueError(
                f"ações do exercício {e.get('exercicio')}: {motivo}"
            ) from erro
    if any(q <= 0 for q in quantidades):
        raise ValueError("ações do documento não positivas")
    return quantidades


def fatores_da_base(
    registros: list[dict], reconciliacao: object, instante: datetime
) -> dict[str, float]:
    """Ficha2.1: quantidades já escaladas por documento, razão estrita ou fator B3."""
    quantidades = _acoes_documentais(registros)
    incompativeis = [
        i
        for i in range(1, len(quantidades))
        if not 0.9 < quantidades[i] / quantidades[i - 1] < 1.1
    ]
    if not incompativeis:
        return {str(e["exercicio"]): 1.0 for e in registros}
    if not isinstance(reconciliacao, Mapping):
        raise TypeError("base de ações incompatível sem fator oficial B3")
    _fonte(reconciliacao, instante)
    if date.fromisoformat(reconciliacao["inicio"]) > date.fromisoformat(
        registros[0]["inicio"]
    ) or date.fromisoformat(reconciliacao["fim"]) < date.fromisoformat(
        registros[-1]["fim"]
    ):
        raise ValueError("eventos sem cobertura da janela")
    fatores = _mapa(reconciliacao.get("fatores"))
    resultado = {}
    for e in registros:
        fator = _numero(fatores.get(str(e["exercicio"])))
        if fator <= 0:
            raise ValueError("fator oficial de evento não positivo")
        resultado[str(e["exercicio"])] = fator
    return resultado


def entradas(dados: Mapping, instante: datetime) -> dict:
    """Insumos de Graham/Lynch separados, sem reservar valores em múltiplos."""
    cobertura = {"esperados": 5, "disponiveis": 0}
    meta = {"avisos": ["reorganização societária no período não é detectada"]}
    try:
        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError("as_of exige fuso horário")
        dia = instante.astimezone(FUSO).date()
        serie = _mapa(dados.get("serie_cvm"))
        registros = serie.get("exercicios")
        if not isinstance(registros, (list, tuple)):
            raise TypeError("série anual ausente")
        cobertura["disponiveis"] = len(registros)
        registros = sorted(registros, key=lambda e: _mapa(e)["exercicio"])
        if registros:
            meta.update(
                {
                    "inicio": registros[0].get("inicio"),
                    "fim": registros[-1].get("fim"),
                    "exercicios": [e.get("exercicio") for e in registros],
                    "fontes_documentais": [e.get("proveniencia") for e in registros],
                }
            )
        if len(registros) != 5:
            raise ValueError("exige cinco exercícios completos contínuos")
        reconciliacao = dados.get("reconciliacao_serie")
        if reconciliacao is None:
            _acoes_documentais(registros)
            reconciliacao = fatores_da_relacao(dados, registros, instante)
            if "abstencao" in reconciliacao:
                raise ValueError(
                    f"fator oficial B3 indisponível: {reconciliacao['abstencao']}"
                )
        fatores = fatores_da_base(registros, reconciliacao, instante)
        perimetros = set()
        lpas, meses = [], []
        anterior = None
        for e in registros:
            inicio, fim = date.fromisoformat(e["inicio"]), date.fromisoformat(e["fim"])
            if _meses(inicio, fim) != 12 or fim >= dia:
                raise ValueError("exercício incompleto ou posterior ao corte")
            if anterior is not None and inicio != anterior + timedelta(days=1):
                raise ValueError("exercícios não contíguos")
            if e["exercicio"] != fim.year:
                raise ValueError("identidade do exercício incompatível")
            anterior = fim
            prov = _mapa(e.get("proveniencia"))
            _fonte(prov, instante, "data_coleta")
            if date.fromisoformat(prov["data_entrega"]) >= dia:
                raise ValueError("documento não entregue até o corte")
            perimetros.add(e.get("perimetro") or "controladores")
            fator = _numero(fatores.get(str(e["exercicio"])))
            if fator <= 0:
                raise ValueError("fator oficial de evento não positivo")
            lpas.append(_numero(e.get("lpa")) / fator)
            meses.append(fim.strftime("%Y-%m"))
    except (ValueError, TypeError, KeyError, OverflowError) as erro:
        motivo = {**meta, "abstencao": str(erro)}
        return {
            "graham": {**motivo, "regime": "nominal na moeda final"},
            "lynch": {**motivo, "regime": "nominal"},
            "cobertura": cobertura,
        }

    meta = {
        "inicio": registros[0]["inicio"],
        "fim": registros[-1]["fim"],
        "perimetro": "; ".join(sorted(perimetros)),
        "exercicios": [e["exercicio"] for e in registros],
        "fontes_documentais": [e["proveniencia"] for e in registros],
        "fonte_eventos": (reconciliacao or {}).get(
            "fonte", "Composição do Capital de cada documento"
        ),
        "avisos": ["reorganização societária no período não é detectada"],
    }
    try:
        if lpas[0] <= 0 or lpas[-1] <= 0:
            raise ValueError("CAGR exige extremos positivos")
        crescimento = (lpas[-1] / lpas[0]) ** 0.25 - 1
        if not math.isfinite(crescimento):
            raise ValueError("CAGR não finito")
        lynch = {
            "lpa": lpas[-1],
            "crescimento_lpa": crescimento,
            "regime": "nominal",
            **meta,
        }
    except (ValueError, OverflowError, ZeroDivisionError) as erro:
        lynch = {**meta, "regime": "nominal", "abstencao": str(erro)}
    try:
        ipca = _mapa(dados.get("ipca_serie"))
        if ipca.get("abstencao"):
            raise ValueError(ipca["abstencao"])
        _fonte(ipca, instante)
        indices = _mapa(ipca.get("indices"))
        publicacoes = _mapa(ipca.get("publicacoes"))
        valores = []
        for mes in meses:
            indice = _numero(indices.get(mes))
            if indice <= 0 or date.fromisoformat(publicacoes[mes]) >= dia:
                raise ValueError("IPCA de fim de exercício inválido ou futuro")
            valores.append(indice)
        media = (
            math.fsum(
                lpa * valores[-1] / indice
                for lpa, indice in zip(lpas, valores, strict=True)
            )
            / 5
        )
        vpa = _numero(registros[-1].get("vpa"))
        if media <= 0 or vpa <= 0 or not math.isfinite(media):
            raise ValueError("LPA médio ou VPA não positivo ou inválido")
        graham = {
            "lpa": media,
            "vpa": vpa,
            "regime": "nominal na moeda final",
            "fonte_ipca": ipca["fonte"],
            **meta,
        }
    except (ValueError, TypeError, KeyError, OverflowError) as erro:
        graham = {**meta, "regime": "nominal na moeda final", "abstencao": str(erro)}
    return {"graham": graham, "lynch": lynch, "cobertura": cobertura}
