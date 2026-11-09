"""Payout contextual da fonte comum de DY, sem interferir no CAGR nominal."""

from __future__ import annotations

import math


def contexto(
    dy: float | None,
    preco: float | None,
    lpa: float | None,
    *,
    confiavel: bool,
    fonte: dict,
) -> dict:
    """Calcula DY × preço / LPA, preservando a fonte e valores acima de 100%."""
    try:
        if confiavel is not True:
            raise ValueError("fonte comum de DY não confiável")
        valores = []
        for nome, valor in (
            ("DY", dy),
            ("preço de referência", preco),
            ("LPA final", lpa),
        ):
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise TypeError(f"{nome} ausente ou não numérico")
            if not math.isfinite(valor):
                raise ValueError(f"{nome} não finito")
            if valor < 0 or (nome != "DY" and valor == 0):
                raise ValueError(f"{nome} fora do domínio")
            valores.append(float(valor))
        dy_valor, preco_valor, lpa_valor = valores
        if dy_valor == 0:
            payout = 0.0
        else:
            # Mantissas limitadas evitam overflow/underflow intermediário quando
            # o quociente final é representável (por exemplo, 1e300² / 1e300).
            md, ed = math.frexp(dy_valor)
            mp, ep = math.frexp(preco_valor)
            ml, el = math.frexp(lpa_valor)
            payout = math.ldexp(md * mp / ml, ed + ep - el)
        if dy_valor > 0 and payout == 0:
            raise ValueError("payout contextual positivo não representável")
        if not math.isfinite(payout):
            raise ValueError("payout contextual não finito")
    except (ValueError, TypeError, OverflowError) as erro:
        motivo = (
            str(erro)
            if isinstance(erro, (ValueError, TypeError))
            else "payout contextual não finito"
        )
        return {"abstencao": motivo, "fonte": fonte}
    return {
        "valor": payout,
        "dy": dy_valor,
        "preco_referencia": preco_valor,
        "lpa_final": lpa_valor,
        "fonte": fonte,
    }
