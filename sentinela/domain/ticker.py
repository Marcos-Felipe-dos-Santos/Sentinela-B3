"""Validação do ticker por lista permitida (F2A-12; E-18).

O ticker digitado vai para a URL da brapi, para o yfinance e para o prompt do LLM. Cada
fronteira o normaliza (maiúsculas, sem espaços nas pontas, sem o sufixo `.SA`) e só aceita
raiz de 4 caracteres e 1 ou 2 dígitos: ações, units, FIIs, ETFs e BDRs como `A1MD34`. Não exige
que o ticker esteja no índice oficial; fora dele, a classe é `UNKNOWN` (F2A-20).

Função pura: sem rede, sem relógio.
"""

from __future__ import annotations

import re

PADRAO = re.compile(r"[A-Z0-9]{4}[0-9]{1,2}")
SUFIXO_B3 = ".SA"


def normalizar(texto: object) -> str | None:
    """O ticker normalizado, ou `None` se não for um ticker no formato da B3."""
    if not isinstance(texto, str):
        return None
    ticker = texto.strip().upper().removesuffix(SUFIXO_B3)
    return ticker if PADRAO.fullmatch(ticker) else None


def validar(texto: object) -> str:
    """O ticker normalizado; fora do formato, `ValueError`."""
    ticker = normalizar(texto)
    if ticker is None:
        raise ValueError(f"ticker inválido: {texto!r}")
    return ticker
