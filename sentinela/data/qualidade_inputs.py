"""Fronteira pura do quadro de qualidade: B3 anual não é DVA de competência.

O calendário anual exige cobertura declarada, não apenas os pregões nas bordas
coletadas para o Bazin. Sem prova, mantém os indicadores contábeis e explica a
indisponibilidade de cada ano da contagem por data-ex.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta

from sentinela.data import proventos_b3


def _coleta(fonte: Mapping, instante: datetime) -> bool:
    try:
        coleta = datetime.fromisoformat(str(fonte.get("coleta")))
        return coleta.utcoffset() is not None and coleta <= instante
    except (TypeError, ValueError):
        return False


def _provento(dados: Mapping, exercicio: Mapping, instante: datetime) -> dict:
    saida = {
        "valor": None,
        "cobertura_integral": False,
        "inicio": exercicio.get("inicio"),
        "fim": exercicio.get("fim"),
    }
    try:
        if instante.utcoffset() is None:
            raise ValueError("as_of exige fuso horário")
        relacao = dados.get("proventos_b3")
        if not isinstance(relacao, Mapping) or relacao.get("abstencao"):
            raise ValueError("relação B3 anual indisponível")
        prov = relacao.get("proveniencia")
        if (
            not _coleta(relacao, instante)
            or not isinstance(prov, Mapping)
            or not isinstance(prov.get("fonte"), str)
            or not prov["fonte"].strip()
        ):
            raise ValueError("fonte/coleta da relação B3 não demonstrada até o as_of")
        calendario = dados.get("calendario_proventos_b3")
        if (
            not isinstance(calendario, Mapping)
            or not isinstance(calendario.get("fonte"), str)
            or not calendario["fonte"].strip()
            or not _coleta(calendario, instante)
        ):
            raise TypeError("calendário anual B3 sem cobertura demonstrada")
        inicio = date.fromisoformat(exercicio["inicio"])
        fim = date.fromisoformat(exercicio["fim"])
        if date.fromisoformat(calendario["inicio"]) > inicio - timedelta(
            days=7
        ) or date.fromisoformat(calendario["fim"]) < fim + timedelta(days=7):
            raise ValueError(
                "calendário anual sem cobertura das bordas data-com/data-ex"
            )
        pregoes = [date.fromisoformat(p) for p in calendario["pregoes"]]
        if (
            not pregoes
            or min(pregoes) > inicio
            or max(pregoes) < fim
            or not any(inicio <= p <= fim for p in pregoes)
        ):
            raise ValueError("calendário vazio ou sem pregões nas bordas do exercício")
        for campo in ("registros", "eventos_acoes", "dinheiro_complemento"):
            registros = relacao.get(campo) or ()
            if not isinstance(registros, (list, tuple)) or any(
                not isinstance(e, Mapping) for e in registros
            ):
                raise TypeError(f"coleção B3 inválida: {campo}")

        serie = proventos_b3.serie_12_meses(
            relacao.get("registros") or (),
            total=relacao.get("total"),
            referencia=fim,
            dia_as_of=instante.astimezone(proventos_b3.FUSO).date(),
            especie=dados.get("especie"),
            eh_unit=dados.get("classe_ativo") == "UNIT",
            acoes_por_unit=dados.get("acoes_por_unit"),
            eventos_acoes=relacao.get("eventos_acoes") or (),
            dinheiro_complemento=relacao.get("dinheiro_complemento") or (),
            pregoes=pregoes,
        )
        if isinstance(serie, proventos_b3.Abstencao):
            raise TypeError(serie.motivo)
        if date.fromisoformat(serie["inicio_exclusivo"]) + timedelta(days=1) != inicio:
            raise ValueError("janela B3 não corresponde ao exercício contábil completo")
        saida.update(
            valor=serie["d_bruto_12m"],
            cobertura_integral=True,
            fonte=relacao["proveniencia"]["fonte"],
            coleta=relacao["coleta"],
            calendario={k: calendario[k] for k in ("fonte", "inicio", "fim", "coleta")},
        )
    except (KeyError, TypeError, ValueError, OverflowError) as erro:
        saida["motivo"] = str(erro)
    return saida


def entradas(dados: Mapping, instante: datetime) -> list[dict]:
    """Cópia documental com B3 por exercício; nunca reutiliza bloco calculado sem fonte."""
    serie = dados.get("serie_cvm")
    registros = serie.get("exercicios") if isinstance(serie, Mapping) else None
    if not isinstance(registros, (list, tuple)):
        return []
    return [
        dict(e) | {"proventos_b3": _provento(dados, e, instante)}
        for e in registros
        if isinstance(e, Mapping)
    ]
