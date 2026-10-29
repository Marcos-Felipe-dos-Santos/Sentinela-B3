"""Quadro descritivo da ficha qualidade 1.0; sem valor escalar ou pontuação.

Contratos separados das lentes de valuation: entradas documentais por exercício,
data explícita e resultado serializável. Ausência e ruptura não viram desempenho.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from itertools import pairwise
from numbers import Real
from statistics import mean, pstdev
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
INDICADORES = ("roe", "lucros", "margem_consolidada", "alavancagem", "proventos")


def _texto(valor: object) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _proveniencia(valor: object) -> dict | None:
    """Proveniência pública serializável; um valor recusado não reaparece aqui."""
    if not isinstance(valor, Mapping):
        return None
    campos = (
        "fonte",
        "data_coleta",
        "data_entrega",
        "periodo_referencia",
        "documento",
        "versao",
        "hash_sha256",
        "motivo_sem_entrega",
        "arquivo",
        "demonstrativo",
        "data_saldo",
        "referencia",
        "modelo",
        "inicio",
        "fim",
        "coleta",
    )
    saida = {k: valor[k] for k in campos if isinstance(valor.get(k), str)}
    if isinstance(valor.get("reserva"), bool) or _texto(valor.get("reserva")):
        saida["reserva"] = valor["reserva"]
    return saida


def _numero(valor: object) -> float | None:
    if not isinstance(valor, Real) or isinstance(valor, bool):
        return None
    try:
        return float(valor) if math.isfinite(valor) else None
    except OverflowError:
        return None


def _razao(numerador: float | None, denominador: float | None) -> float | None:
    if numerador is None or denominador is None or denominador <= 0:
        return None
    razao = _numero(numerador / denominador)
    return None if razao == 0 and numerador != 0 else razao


def _fonte(prov: object, instante: datetime, *, coleta: str = "data_coleta") -> bool:
    if not isinstance(prov, Mapping) or not _texto(prov.get("fonte")):
        return False
    try:
        capturado = datetime.fromisoformat(str(prov.get(coleta)))
        if capturado.utcoffset() is None or capturado > instante:
            return False
        entrega = prov.get("data_entrega")
        return (
            entrega is None
            or date.fromisoformat(str(entrega)) < instante.astimezone(FUSO).date()
        )
    except (TypeError, ValueError):
        return False


def _janela(e: Mapping, instante: datetime) -> bool:
    try:
        inicio, fim = (
            date.fromisoformat(str(e.get("inicio"))),
            date.fromisoformat(str(e.get("fim"))),
        )
        seguinte = fim + timedelta(days=1)
        return (
            inicio.day == seguinte.day == 1
            and (seguinte.year - inicio.year) * 12 + seguinte.month - inicio.month == 12
            and fim < instante.astimezone(FUSO).date()
            and fim.year == e.get("exercicio")
            and str(e.get("dt_refer")) == fim.isoformat()
            and bool(e.get("versao"))
        )
    except (TypeError, ValueError, OverflowError):
        return False


def _linha(e: Mapping, instante: datetime, modelo: str) -> dict:
    nomes = (
        "lucro_controladores",
        "pl_inicial_controladores",
        "lucro_liquido",
        "receita_liquida",
        "divida_liquida",
        "ebitda",
    )
    valores = {n: _numero(e.get(n)) for n in nomes}
    motivo = None
    if not _janela(e, instante):
        motivo = "janela anual/documento inválido, incompleto ou futuro"
    elif not _fonte(e.get("proveniencia"), instante) or not (
        e.get("proveniencia") or {}
    ).get("data_entrega"):
        motivo = "fonte/disponibilidade da DFP não demonstrada até o as_of"
    if motivo:
        valores = dict.fromkeys(nomes)
    lucro, pl = valores["lucro_controladores"], valores["pl_inicial_controladores"]
    margem = _razao(valores["lucro_liquido"], valores["receita_liquida"])
    roe = _razao(lucro, pl)
    alavancagem = _razao(valores["divida_liquida"], valores["ebitda"])
    motivos = {}
    if lucro is None:
        motivos["lucros"] = (
            motivo or "lucro dos controladores não demonstrado ou inválido"
        )
    if roe is None:
        motivos["roe"] = (
            motivo or "PL inicial não positivo, ausente ou razão não representável"
        )
    if margem is None:
        motivos["margem_consolidada"] = (
            motivo
            or "receita consolidada não positiva/ausente ou lucro consolidado inválido"
        )
    if alavancagem is None:
        divida, ebitda = valores["divida_liquida"], valores["ebitda"]
        if ebitda is not None and ebitda <= 0 and divida is not None:
            motivos["alavancagem"] = (
                "EBITDA não positivo com dívida financeira líquida positiva"
                if divida > 0
                else "EBITDA não positivo com dívida financeira líquida não positiva"
            )
        else:
            motivos["alavancagem"] = (
                motivo
                or "EBITDA não demonstrado ou dívida financeira não demonstrada/razão inválida"
            )
    if modelo == "banco":
        margem = alavancagem = None
        motivos.update(
            {
                n: "não aplicável ao modelo banco"
                for n in ("margem_consolidada", "alavancagem")
            }
        )
    distribuicao = e.get("proventos_b3")
    provento = None
    if isinstance(distribuicao, Mapping):
        total = _numero(distribuicao.get("valor"))
        if (
            motivo is None
            and distribuicao.get("cobertura_integral") is True
            and distribuicao.get("inicio") == e.get("inicio")
            and distribuicao.get("fim") == e.get("fim")
            and _fonte(distribuicao, instante, coleta="coleta")
            and total is not None
            and total >= 0
        ):
            provento = total
    if provento is None:
        motivos["proventos"] = (
            (distribuicao or {}).get(
                "motivo", "proventos B3 por data-ex sem cobertura integral demonstrada"
            )
            if isinstance(distribuicao, Mapping)
            else "proventos B3 por data-ex sem cobertura integral demonstrada"
        )
    return {
        "cnpj": e.get("cnpj") if isinstance(e.get("cnpj"), str) else None,
        "modelo": e.get("modelo") if isinstance(e.get("modelo"), str) else None,
        "exercicio": e.get("exercicio"),
        "inicio": e.get("inicio"),
        "fim": e.get("fim"),
        "pl_inicial_proveniencia": _proveniencia(e.get("pl_inicial_proveniencia")),
        "pl_inicial_motivo": e.get("pl_inicial_motivo"),
        "documento": {
            "referencia": e.get("dt_refer"),
            "versao": e.get("versao"),
            "proveniencia": _proveniencia(e.get("proveniencia")),
        },
        **valores,
        "roe": roe,
        "margem_consolidada": margem,
        "alavancagem": alavancagem,
        "proventos": provento,
        "fonte_proventos": _proveniencia(distribuicao),
        "motivos": motivos,
    }


def _resumo(linhas: list[dict], campo: str, comparavel: bool) -> dict:
    valores = [e[campo] for e in linhas if e[campo] is not None]
    out = {
        "observados": len(valores),
        "esperados": 5,
        "minimo": None,
        "maximo": None,
        "ultimo": None,
    }
    if valores and comparavel:
        out.update(minimo=min(valores), maximo=max(valores), ultimo=linhas[-1][campo])
    return out


class Qualidade:
    """Contrato de quadro empresarial independente do contrato de preço justo."""

    nome = "Qualidade descritiva"
    version = "1.0.0"
    regime = "razões/contagens, sem taxa de desconto"
    assumptions = (
        "faixas observadas sem pesos ou nota",
        "cinco exercícios completos comparáveis",
        "proventos B3 por data-ex, sem DVA como substituta",
    )

    def calcular(
        self,
        exercicios: Sequence[Mapping],
        *,
        as_of: datetime,
        classe: str,
        modelo: str | None,
    ) -> dict:
        resultado = {
            "nome": self.nome,
            "versao": self.version,
            "regime": self.regime,
            "hipoteses": list(self.assumptions),
            "comparavel": False,
            "exercicios": [],
            "cobertura": {"observados": 0, "esperados": 5, "completa": False},
        }
        if as_of.utcoffset() is None:
            resultado["motivo"] = "as_of exige fuso horário"
        elif classe not in ("STOCK", "UNIT") or modelo not in ("empresa", "banco"):
            resultado["motivo"] = (
                "quadro não aplicável à classe/modelo sem ficha de qualidade"
            )
        else:
            anos = [e.get("exercicio") for e in exercicios if isinstance(e, Mapping)]
            if (
                len(anos) != len(exercicios)
                or any(type(a) is not int for a in anos)
                or len(set(anos)) != len(anos)
            ):
                resultado["motivo"] = "identidade dos exercícios inválida ou duplicada"
            else:
                selecionados = sorted(exercicios, key=lambda e: e["exercicio"])[-5:]
                linhas = [_linha(e, as_of, modelo) for e in selecionados]
                comparavel = bool(linhas) and all(
                    _texto(e.get("perimetro"))
                    and _texto(e.get("evidencia_comparabilidade"))
                    and not e.get("mudanca_estrutural_sem_reconciliacao")
                    for e in selecionados
                )
                perimetros = {
                    e.get("perimetro")
                    for e in selecionados
                    if isinstance(e.get("perimetro"), str)
                }
                comparavel = comparavel and len(perimetros) == 1
                cnpjs = {
                    str(e["cnpj"])
                    .strip()
                    .replace(".", "")
                    .replace("/", "")
                    .replace("-", "")
                    for e in selecionados
                    if e.get("cnpj") is not None
                }
                modelos = {
                    str(getattr(e["modelo"], "value", e["modelo"])).strip().lower()
                    for e in selecionados
                    if e.get("modelo") is not None
                }
                comparavel = (
                    comparavel
                    and len(cnpjs) <= 1
                    and (not modelos or modelos == {modelo})
                )
                for anterior, atual in pairwise(selecionados):
                    try:
                        comparavel = comparavel and date.fromisoformat(
                            atual["inicio"]
                        ) == date.fromisoformat(anterior["fim"]) + timedelta(days=1)
                    except (ValueError, TypeError, KeyError):
                        comparavel = False
                validos = sum(
                    _janela(e, as_of)
                    and _fonte(e.get("proveniencia"), as_of)
                    and bool((e.get("proveniencia") or {}).get("data_entrega"))
                    for e in selecionados
                )
                resultado.update(
                    exercicios=linhas,
                    comparavel=bool(comparavel),
                    cobertura={
                        "observados": validos,
                        "esperados": 5,
                        "completa": validos == 5 and bool(comparavel),
                    },
                )
                if not comparavel:
                    resultado["motivo"] = (
                        "comparabilidade dos cinco exercícios não demonstrada; dados individuais preservados"
                    )
        linhas = resultado["exercicios"]
        for nome, campo in (
            ("roe", "roe"),
            ("lucros", "lucro_controladores"),
            ("margem_consolidada", "margem_consolidada"),
            ("alavancagem", "alavancagem"),
            ("proventos", "proventos"),
        ):
            resumo = _resumo(linhas, campo, resultado["comparavel"])
            if nome in ("lucros", "proventos"):
                resumo["positivos"] = (
                    sum(e[campo] > 0 for e in linhas if e[campo] is not None)
                    if resultado["comparavel"]
                    else None
                )
            if nome == "roe":
                valores = [e["roe"] for e in linhas if e["roe"] is not None]
                resumo.update(media=None, desvio_populacional_pp=None)
                if valores and resultado["comparavel"]:
                    try:
                        media, desvio = mean(valores), pstdev(valores) * 100
                        if math.isfinite(media) and math.isfinite(desvio):
                            resumo.update(media=media, desvio_populacional_pp=desvio)
                        else:
                            resumo["motivo"] = "estatística não representável"
                    except (OverflowError, ValueError):
                        resumo["motivo"] = "estatística não representável"
            if modelo == "banco" and nome in ("margem_consolidada", "alavancagem"):
                resumo["motivo"] = "não aplicável ao modelo banco"
            resultado[nome] = resumo
        return resultado
