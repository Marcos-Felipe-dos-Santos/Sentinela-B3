"""Apresentação1.0: comparação aritmética por lente, sem classificação."""

from __future__ import annotations

import math
from typing import Any

from sentinela.domain.units import BRL
from sentinela.methods.base import MethodResult


def distancia(valor: object, preco: object) -> float | None:
    """Distância percentual quando valores monetários são positivos e representáveis."""
    for numero in (valor, preco):
        if (
            isinstance(numero, bool)
            or not isinstance(numero, (int, float))
            or not math.isfinite(numero)
            or numero <= 0
        ):
            return None
    resultado = 100 * (valor / preco - 1)
    return resultado if math.isfinite(resultado) else None


def bloco(metodo: Any, resultado: Any, preco: float, janela: dict) -> dict:
    """O P/VP contextual não é um preço monetário nem entra nesta coleção."""
    valor = (
        resultado.valor.valor
        if isinstance(resultado, MethodResult) and isinstance(resultado.valor, BRL)
        else None
    )
    motivo = getattr(resultado, "motivo", None)
    if valor is not None and (not math.isfinite(valor) or valor <= 0):
        valor, motivo = None, "valor da lente não positivo ou não finito"
    if valor is None and not motivo:
        motivo = "lente sem valor monetário"
    return {
        "versao": metodo.version,
        "valor": valor,
        "abstencao": motivo,
        "regime": metodo.regime.value,
        "janela": janela,
        "premissas": list(metodo.assumptions),
        "unidade": "BRL",
        "distancia_ao_preco_pct": distancia(valor, preco),
    }
